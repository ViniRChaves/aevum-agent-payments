"""Camada de segurança + execução de pagamentos (backend do protótipo).

Ordem OBRIGATÓRIA antes de qualquer assinatura — nada é assinado sem
passar por todas as etapas:

1. GUARDA (anti-prompt-injection): toda entrada externa é DADO, nunca
   instrução. Se o guarda bloquear, nada segue — e a recusa é registrada.
2. SIMULAÇÃO on-chain: `simulatePayment` via eth_call (grátis, sem estado)
   espelha todas as checagens do contrato (mandato ativo, validade, teto,
   escopo da session key, saldo do cofre). Fora do mandato = recusa.
   2b. PREFLIGHT: a chave que assina precisa de tQDAY para o gás — sem
   isso a transação nem é montada.
3. EXECUÇÃO: só então a transação é montada, assinada pela session key
   (ou pelo dono) e enviada. O recibo é conferido antes de declarar sucesso.

Toda decisão — aprovação OU recusa — vai para o audit log JSONL.
Nenhuma chave privada é registrada em log.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from web3 import Web3

from . import config
from .guard import Guard

TUSD8_ABI = json.loads(
    """[
      {"constant": true, "inputs": [{"name": "account", "type": "address"}],
       "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}],
       "type": "function"},
      {"constant": false, "inputs": [{"name": "spender", "type": "address"},
       {"name": "amount", "type": "uint256"}],
       "name": "approve", "outputs": [{"name": "", "type": "bool"}],
       "type": "function"},
      {"constant": false, "inputs": [{"name": "to", "type": "address"},
       {"name": "amount", "type": "uint256"}],
       "name": "transfer", "outputs": [{"name": "", "type": "bool"}],
       "type": "function"}
    ]"""
)


@dataclass
class Decision:
    """Uma decisão da camada de segurança (aprovar ou recusar)."""

    approved: bool
    reason: str
    stage: str  # guard | simulation | execution | onchain
    tx_hash: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_audit(self) -> dict[str, Any]:
        return {
            "ts": int(time.time()),
            "approved": self.approved,
            "stage": self.stage,
            "reason": self.reason,
            "tx_hash": self.tx_hash,
            "details": self.details,
        }


class Executor:
    def __init__(self, contract_address: str, abi: list[dict], w3: Web3 | None = None):
        self.w3 = w3 or Web3(Web3.HTTPProvider(config.RPC_URL))
        assert self.w3.is_connected(), "sem conexão com o RPC da testnet Aevum"
        assert self.w3.eth.chain_id == config.CHAIN_ID, (
            f"chain errada: {self.w3.eth.chain_id} (esperado {config.CHAIN_ID})"
        )
        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(contract_address), abi=abi
        )
        self.token = self.w3.eth.contract(
            address=Web3.to_checksum_address(config.TUSD8_ADDRESS), abi=TUSD8_ABI
        )
        self.guard = Guard()
        self.audit_path = config.AUDIT_PATH
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------- auditoria
    def _audit(self, decision: Decision) -> None:
        with self.audit_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(decision.to_audit(), ensure_ascii=False) + "\n")

    # ------------------------------------------------------------- simulação
    def simulate(self, caller: str, mandate_id: bytes, amount_base_units: int) -> Decision:
        ok, reason = self.contract.functions.simulatePayment(
            Web3.to_checksum_address(caller), mandate_id, amount_base_units
        ).call()
        return Decision(bool(ok), str(reason), "simulation")

    # ------------------------------------------------------------- pagamento
    def request_payment(
        self,
        *,
        external_text: str,
        external_source: str,
        mandate_id: bytes,
        amount_base_units: int,
        signer_private_key: str,
    ) -> Decision:
        """Pipeline completo: guarda -> simulação -> execução.

        `external_text` é QUALQUER conteúdo vindo de fora (mensagem, página,
        API). Ele é tratado como DADO: pode descrever um pagamento, nunca
        ordená-lo. Os parâmetros de pagamento (mandato, valor) vêm do
        operador, nunca do texto externo.
        """
        signer = self.w3.eth.account.from_key(signer_private_key)
        caller = signer.address

        # 1 — GUARDA: separação dado x instrução.
        verdict = self.guard.check(external_text, source=external_source)
        if not verdict.allowed:
            d = Decision(
                False,
                f"prompt-injection bloqueado pelo guarda: {'; '.join(verdict.reasons)}",
                "guard",
                details={"risk": verdict.risk, "source": external_source},
            )
            self._audit(d)
            return d

        # 2 — SIMULAÇÃO: espelho on-chain de todas as regras do mandato.
        sim = self.simulate(caller, mandate_id, amount_base_units)
        if not sim.approved:
            d = Decision(
                False,
                f"simulação recusou: {sim.reason}",
                "simulation",
                details={
                    "mandate_id": mandate_id.hex(),
                    "amount": config.fmt_tusd8(amount_base_units),
                    "caller": caller,
                },
            )
            self._audit(d)
            return d

        # 2b — PREFLIGHT: a chave que assina precisa de tQDAY para o gás.
        #      A simulação on-chain não cobre isso; sem este cheque o erro
        #      só apareceria no envio. Nenhuma assinatura acontece aqui.
        gas_price = self.w3.eth.gas_price
        gas_cost = 300_000 * gas_price
        native_balance = self.w3.eth.get_balance(caller)
        if native_balance < gas_cost:
            d = Decision(
                False,
                f"saldo tQDAY insuficiente para o gás "
                f"({self.w3.from_wei(native_balance, 'ether')} < "
                f"{self.w3.from_wei(gas_cost, 'ether')} estimado)",
                "preflight",
                details={"caller": caller},
            )
            self._audit(d)
            return d

        # 3 — EXECUÇÃO: só agora a transação é assinada e enviada.
        try:
            tx = self.contract.functions.executePayment(
                mandate_id, amount_base_units
            ).build_transaction(
                {
                    "from": caller,
                    "nonce": self.w3.eth.get_transaction_count(caller),
                    "gas": 300_000,
                    "gasPrice": self.w3.eth.gas_price,
                    "chainId": config.CHAIN_ID,
                }
            )
            signed = signer.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            if receipt.status != 1:
                d = Decision(
                    False, "transação revertida on-chain", "onchain",
                    tx_hash=tx_hash.hex(),
                    details={"mandate_id": mandate_id.hex()},
                )
                self._audit(d)
                return d
            d = Decision(
                True, "pagamento executado dentro do mandato", "execution",
                tx_hash=tx_hash.hex(),
                details={
                    "mandate_id": mandate_id.hex(),
                    "amount": config.fmt_tusd8(amount_base_units),
                    "caller": caller,
                    "block": receipt.blockNumber,
                    "gas_used": receipt.gasUsed,
                },
            )
            self._audit(d)
            return d
        except Exception as exc:  # erro de rede/RPC — nada foi assinado à toa
            d = Decision(False, f"falha ao enviar transação: {exc}", "execution")
            self._audit(d)
            return d

    # ------------------------------------------------------------- leitura
    def vault_balance(self) -> int:
        return self.token.functions.balanceOf(self.contract.address).call()

    def mandate(self, mandate_id: bytes) -> dict[str, Any]:
        m = self.contract.functions.mandates(mandate_id).call()
        return {
            "beneficiary": m[0],
            "cap": config.fmt_tusd8(m[1]),
            "spent": config.fmt_tusd8(m[2]),
            "expiry": m[3],
            "active": m[4],
        }
