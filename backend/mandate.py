"""Mandatos de pagamento verificáveis (EIP-712).

Um mandato é a intenção ASSINADA do dono: beneficiário + teto + validade
+ nonce anti-replay. O contrato só aceita o mandato se a assinatura
EIP-712 for do dono — qualquer um pode submeter a transação, ninguém pode
forjar a intenção.
"""

from __future__ import annotations

from eth_account import Account
from eth_account.messages import encode_typed_data

DOMAIN_NAME = "AgentPayments"
DOMAIN_VERSION = "1"


def sign_mandate(
    *,
    private_key: str,
    contract_address: str,
    chain_id: int,
    beneficiary: str,
    cap_base_units: int,
    expiry: int,
    nonce: int,
) -> bytes:
    """Assina a intenção de mandato (EIP-712) e devolve a assinatura (65 bytes)."""
    message = {
        "beneficiary": beneficiary,
        "cap": cap_base_units,
        "expiry": expiry,
        "nonce": nonce,
    }
    encoded = encode_typed_data(
        full_message={
            "types": {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                    {"name": "verifyingContract", "type": "address"},
                ],
                "Mandate": [
                    {"name": "beneficiary", "type": "address"},
                    {"name": "cap", "type": "uint256"},
                    {"name": "expiry", "type": "uint256"},
                    {"name": "nonce", "type": "uint256"},
                ],
            },
            "primaryType": "Mandate",
            "domain": {
                "name": DOMAIN_NAME,
                "version": DOMAIN_VERSION,
                "chainId": chain_id,
                "verifyingContract": contract_address,
            },
            "message": message,
        }
    )
    return Account.sign_message(encoded, private_key).signature
