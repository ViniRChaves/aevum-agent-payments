"""Compila contracts/AgentPayments.sol com solc 0.8.24 e grava o artefato."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import solcx

PROJECT_DIR = Path(__file__).resolve().parent.parent
CONTRACT = PROJECT_DIR / "contracts" / "AgentPayments.sol"
OUT_DIR = PROJECT_DIR / "artifacts"


def main() -> dict:
    solcx.set_solc_version("0.8.24")
    compiled = solcx.compile_files(
        [str(CONTRACT)],
        output_values=["abi", "bin"],
        solc_version="0.8.24",
    )
    key = next(k for k in compiled if k.endswith(":AgentPayments"))
    artifact = {
        "contractName": "AgentPayments",
        "abi": compiled[key]["abi"],
        "bytecode": "0x" + compiled[key]["bin"],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "AgentPayments.json").write_text(
        json.dumps(artifact, indent=2), encoding="utf-8"
    )
    print(f"compilado: {CONTRACT.name} -> {OUT_DIR / 'AgentPayments.json'}")
    print(f"bytecode: {len(compiled[key]['bin']) // 2} bytes")
    return artifact


if __name__ == "__main__":
    main()
