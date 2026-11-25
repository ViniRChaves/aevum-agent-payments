"""Deploy do AgentPayments na testnet Aevum (chain 44005) + registro público.

Uso: .venv/bin/python scripts/deploy.py
Grava o endereço em deployments.json (só dados públicos: endereço, tx hash).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web3 import Web3

from backend import config
from scripts.compile import main as compile_contract


def main() -> None:
    artifact = compile_contract()
    address, private_key = config.load_agent_account()

    w3 = Web3(Web3.HTTPProvider(config.RPC_URL))
    assert w3.is_connected() and w3.eth.chain_id == config.CHAIN_ID
    acct = w3.eth.account.from_key(private_key)
    assert acct.address == Web3.to_checksum_address(address), "keypair divergente do endereço"

    print(f"deployer (carteira do agente): {acct.address}")
    print(f"saldo tQDAY: {w3.from_wei(w3.eth.get_balance(acct.address), 'ether')}")

    contract = w3.eth.contract(abi=artifact["abi"], bytecode=artifact["bytecode"])
    tx = contract.constructor(
        Web3.to_checksum_address(config.TUSD8_ADDRESS)
    ).build_transaction(
        {
            "from": acct.address,
            "nonce": w3.eth.get_transaction_count(acct.address),
            "gas": 2_500_000,
            "gasPrice": w3.eth.gas_price,
            "chainId": config.CHAIN_ID,
        }
    )
    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"deploy enviado: {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    assert receipt.status == 1, "deploy revertido"
    deployed = receipt.contractAddress
    print(f"AgentPayments implantado em: {deployed}")
    print(f"bloco: {receipt.blockNumber} | gás usado: {receipt.gasUsed}")

    deployments = {
        "chain_id": config.CHAIN_ID,
        "rpc": config.RPC_URL,
        "token_tusd8": config.TUSD8_ADDRESS,
        "agent_wallet": acct.address,
        "agent_payments": deployed,
        "deploy_tx": tx_hash.hex(),
        "deploy_block": receipt.blockNumber,
    }
    config.DEPLOYMENTS_PATH.write_text(
        json.dumps(deployments, indent=2), encoding="utf-8"
    )
    print(f"registrado em: {config.DEPLOYMENTS_PATH}")


if __name__ == "__main__":
    main()
