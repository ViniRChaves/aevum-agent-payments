"""Configuração do protótipo Aevum/QDay — SOMENTE testnet (chain 44005).

Nada aqui toca mainnet nem carteiras pessoais do usuário. A única chave
usada é a keypair PRÓPRIA do agente (a mesma do Synmerco), lida do arquivo
com permissão 600 em tempo de execução e NUNCA registrada em log.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent

RPC_URL = "https://rpc-test.qday.info"
CHAIN_ID = 44005

# tUSD8 oficial na testnet Aevum (6 decimais) — fonte: QDay Wiki / Official Links.
TUSD8_ADDRESS = "0x456569838f1d43009A91ebA4263147Afd7233483"
TUSD8_DECIMALS = 6

# Keypair PRÓPRIA do agente (nunca a carteira pessoal do usuário).
AGENT_KEY_PATH = Path(os.environ.get(
    "AEVUM_AGENT_KEY",
    str(Path.home() / "workspace/synmerco/agent-evm-key.json"),
))

AUDIT_PATH = PROJECT_DIR / "audit" / "audit.jsonl"
DEPLOYMENTS_PATH = PROJECT_DIR / "deployments.json"
ARTIFACTS_DIR = PROJECT_DIR / "artifacts"


def load_agent_account():
    """Lê a keypair do agente e devolve (address, private_key).

    A chave privada NUNCA é impressa nem registrada em log por este módulo.
    """
    data = json.loads(AGENT_KEY_PATH.read_text(encoding="utf-8"))
    return data["address"], data["private_key"]


def tusd8(amount: float) -> int:
    """Converte tUSD8 'humanos' (ex.: 0.5) para base units (6 decimais)."""
    return int(round(amount * 10 ** TUSD8_DECIMALS))


def fmt_tusd8(base_units: int) -> str:
    return f"{base_units / 10 ** TUSD8_DECIMALS:.6f} tUSD8"
