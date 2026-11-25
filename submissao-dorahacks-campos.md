# Submissão DoraHacks — Aevum Builder Challenge #1 (QDay)
Campos preenchidos e prontos para colar na página do hackathon:
https://dorahacks.io/hackathon/qday
Prazo: **2026-12-11 08:00 UTC**. Submissão exige login web na conta DoraHacks
(ytlvinnyl) — não existe rota de submissão via API pública documentada.

> ✅ REPOSITÓRIO PUBLICADO em 25/11/2026:
> https://github.com/ViniRChaves/aevum-agent-payments
> A árvore foi publicada SEM o arquivo local `demo-session-key.json` (chave
> descartável da demo, já prevista no .gitignore do projeto), conforme a
> auditoria de segredos de 25/11/2026 — nenhuma chave real, nenhuma carteira
> pessoal e nenhum segredo estão no repositório. O repo inclui `demo.sh`
> (reprodução em 1 comando) e `demo-session-key.example.json` (só placeholders).

---

## Nome do projeto (BUIDL name)
AgentPayments — Programmable Payments for AI Agents on Aevum (QDay)

## Descrição curta (tagline)
Programmable stablecoin payments for autonomous agents on Aevum Testnet:
EIP-712 payment mandates, scope-restricted session keys, hard tUSD8 spending
caps enforced on-chain, and an anti-prompt-injection guard that simulates and
validates every transaction before anything is signed.

## Track / categoria
**Native AI Assistants**
(alternativa, se o formulário pedir outra: Decentralized Payments)

## Descrição longa (vision / description)
Autonomous agents that pay for services need three guarantees that today's
models do not provide together: (1) spend only inside an owner-approved
limit, (2) never expose the main wallet key, and (3) never obey instructions
injected into external content. AgentPayments enforces all three in
independent layers on Aevum Testnet (chain 44005), using the tUSD8 test
stablecoin.

How it works:
1. **Verifiable payment mandates (EIP-712).** The owner signs a mandate —
   beneficiary, spending cap, expiry, anti-replay nonce — verified on-chain
   by the AgentPayments contract. Anyone can relay the transaction; nobody
   can forge the owner's intent.
2. **Scope-restricted session keys.** Day-to-day payments are executed by a
   session key bound to a single mandate, with its own per-payment cap and
   expiry. The main key never leaves the operator's vault; a leaked session
   key can only spend within its mandate's remaining cap and can be revoked.
3. **Hard caps enforced in contract.** `executePayment` reverts if the amount
   exceeds the mandate remainder, the session-key cap, or the vault balance.
4. **Anti-prompt-injection guard + simulation before signing.** Every piece
   of external input is treated as DATA, never as instruction, and is
   screened by a guard (7 documented injection-pattern families: override,
   role-play, fake-system, imperative, exfiltration, encoding, delimiter).
   Every candidate transaction is then simulated with `simulatePayment`
   (eth_call, zero cost) and a gas preflight runs before any signature.
   Anything outside the mandate is refused BEFORE signing — and every
   decision, approval or refusal, is written to an audit log.

Live proof on Aevum Testnet (all verifiable on-chain):
- Contract deployed and a full end-to-end demo executed: a 4.00 tUSD8 vault
  deposit, a signed mandate (2.00 tUSD8 cap / 7 days), a restricted session
  key (1.00 tUSD8 per payment / 1 day), one valid 0.50 tUSD8 payment executed
  through the session key, and three attacks refused before any signature:
  an over-session-key-cap payment, a prompt-injection attempt blocked by the
  guard, and an over-mandate-cap payment rejected in simulation.
- Final on-chain state: vault 3.50 tUSD8; mandate 0.50 of 2.00 tUSD8 spent.

Tech stack: Solidity 0.8.24 (single contract: vault + EIP-712 mandates +
session keys), Python backend (web3.py) with guard, simulation, preflight
and audit log. Testnet only, test tokens only, US$ 0 real spent.

## URL do repositório (GitHub)
https://github.com/ViniRChaves/aevum-agent-payments

## Evidência on-chain (Aevum Testnet, chain 44005, RPC https://rpc-test.qday.info)
- Contrato AgentPayments: `0x19c37FEa76d8D4B688597EB3C65051f8b5D42a41`
- Deploy tx: `736c747cc1ae59ea69e29ac7d7e9f5dcd98f0abf372e06fe900c976ddcc514ea` (bloco 4119479)
- createMandate tx: `ee9ef68f8bbd79820776a30442994af45f47bb3f28796314202ffb08cc769cf5`
- registerSessionKey tx: `111e48cf0d0ea562b00661b9ed5f5986ee9caa6642464f9fe885adf8c2a34bab`
- Pagamento válido de 0,50 tUSD8 via session key:
  `5f06cd49618f9ef1b6d07008bb7087bdf9c21b6ffccc3f1d5b66500b928620a3`
- Carteira do agente (ator da demo, endereço público operacional):
  `0xba495b5eb152ccDF7715460901a5c62f682dd4Ee`
- tUSD8 oficial: `0x456569838f1d43009A91ebA4263147Afd7233483`

## Como reproduzir a demo
Pré-requisito: uma carteira na Aevum Testnet com tQDAY + tUSD8 de teste
(faucet do QDay) e a chave dessa carteira em um arquivo JSON local
`{"address": ..., "private_key": ...}` (permissão 600), apontado pela
variável de ambiente `AEVUM_AGENT_KEY` ou no caminho padrão documentado
no README.

```bash
git clone https://github.com/ViniRChaves/aevum-agent-payments
cd aevum-agent-payments
./demo.sh   # atalho de 1 comando: venv + dependências + deploy + demo
```

Equivalente manual, passo a passo:

```bash
python3 -m venv .venv && .venv/bin/pip install web3 py-solc-x
.venv/bin/python -c "import solcx; solcx.install_solc('0.8.24')"
.venv/bin/python scripts/deploy.py   # implanta o contrato (testnet)
.venv/bin/python scripts/demo.py     # demonstração ponta a ponta
```

A demo executa: depósito no cofre → mandato EIP-712 assinado → session key
restrita → 1 pagamento válido → 3 recusas pré-assinatura (teto da session
key, prompt injection, teto do mandato), tudo registrado em
`audit/audit.jsonl` e resumido em `demo-report.md`.

## O que o pitch (Top 5, 3–5 min, videochamada ao vivo em 15/12) deve cobrir
1. O problema: agentes autônomos pagando sem limites = chave principal
   exposta + obediência a instruções injetadas em conteúdo externo.
2. A arquitetura em 3 camadas independentes: guarda anti-injection →
   simulação/preflight → contrato (mandatos EIP-712 + session keys + tetos).
3. A demo ao vivo na testnet: 1 pagamento válido + os 3 ataques recusados
   ANTES de assinar, com os hashes verificáveis na tela.
4. Por que session keys com escopo são a peça que falta para pagamentos
   agente-a-agente (A2A) seguros: vazamento limitado ao mandato, revogável.
5. Limites honestos: guarda heurístico (não é prova formal), sem multisig
   nem timelock no protótipo — dono deveria ser multisig em produção.
6. Próximo passo: fast track para o programa de builders da mainnet QDay.
