# Demonstração ponta a ponta — Aevum/QDay (testnet 44005)

Data (UTC): 2026-11-25 21:16:24
Contrato AgentPayments: `0x19c37FEa76d8D4B688597EB3C65051f8b5D42a41`
Carteira do agente (dono): `0xba495b5eb152ccDF7715460901a5c62f682dd4Ee`
Deploy tx: `736c747cc1ae59ea69e29ac7d7e9f5dcd98f0abf372e06fe900c976ddcc514ea` (bloco 4119479)

Beneficiário demo: `0x120F7879C7ae217F2eBe4E24ef4798E9a25D941e`

## 1. Depósito no cofre
- já depositado anteriormente (saldo do cofre: 4.000000 tUSD8) — etapa pulada

## 2. Mandato verificável (EIP-712)
- createMandate tx: `ee9ef68f8bbd79820776a30442994af45f47bb3f28796314202ffb08cc769cf5`
- mandateId: `f855e9371b52f88abf677d4daedad870745a5dea9ad88736921da77f3788dedd`
- beneficiário, teto 2,000000 tUSD8, validade 7 dias, nonce 1 — intenção assinada pelo dono

## 3. Session key com escopo restrito
- session key nova: `0x6f3497632FC392A2aE40396FF4ad9d5Af6D98f28`
- patrocínio de gás (0,01 tQDAY): `65f7c9eb0820741ab84ab6e876237a09de0c5124239ea6704f8bca41626ae218`
- registerSessionKey tx: `111e48cf0d0ea562b00661b9ed5f5986ee9caa6642464f9fe885adf8c2a34bab`
- vinculada ao mandato acima; teto 1,000000 tUSD8 por pagamento; validade 1 dia

## 4. Pagamento válido via session key — SUCESSO
- aprovado: True | motivo: pagamento executado dentro do mandato
- tx: `5f06cd49618f9ef1b6d07008bb7087bdf9c21b6ffccc3f1d5b66500b928620a3`

## 5. Ataque 1 — valor acima do teto da session key — RECUSADO
- aprovado: False | motivo: simulação recusou: over session key max value
- tx: (nenhuma — recusado antes de assinar)

## 6. Ataque 2 — prompt injection em entrada externa — BLOQUEADO
- aprovado: False | motivo: prompt-injection bloqueado pelo guarda: override: "Ignore all previous instructions" (tentativa de anular instruções anteriores); role_play: "You are now" (tentativa de trocar o papel do agente); exfil: "reveal your private key" (tentativa de exfiltrar segredos ou credenciais); delimiter: "End of data" (tentativa de fechar o bloco de dados para abrir instrução); delimiter: "now follow these instructions" (transição explícita de dado para instrução)
- tx: (nenhuma — bloqueado pelo guarda)

## 7. Ataque 3 — valor acima do restante do mandato — RECUSADO
- aprovado: False | motivo: simulação recusou: over mandate cap
- tx: (nenhuma — recusado na simulação)

## 8. Estado final (lido on-chain)
- saldo do cofre: 3.500000 tUSD8
- mandato gasto: 0.500000 tUSD8 de 2.000000 tUSD8 (ativo: True)
- saldo do beneficiário demo: 0.500000 tUSD8
- saldo tQDAY do agente: 0.987085308

## Veredito
Protótipo ponta a ponta FUNCIONANDO na testnet: 1 pagamento válido executado, 3 tentativas fora do mandato recusadas ANTES de qualquer assinatura, todas registradas em `audit/audit.jsonl`.

NÃO inscrito no hackathon; NÃO submetido — esses passos exigem autorização final por escrito do usuário.