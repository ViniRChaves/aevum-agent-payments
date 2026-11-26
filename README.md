# AgentPayments — Pagamentos programáveis para agentes (Aevum/QDay)

Protótipo para o **Aevum Builder Challenge #1 (QDay, DoraHacks)**.
Submissões até **2026-12-11 08:00 UTC**. Meta interna: testado ponta a ponta
até 2026-12-08.

> **Somente testnet (chain 44005), somente tokens de teste (tQDAY/tUSD8),
> US$ 0 de gasto real. Nunca usa carteiras pessoais do usuário — só a
> keypair própria do agente.**
>
> **Submetido ao Aevum Builder Challenge #1 (DoraHacks) em 25/11/2026 —
> BUIDL: https://dorahacks.io/build/51924**

**Tagline (EN):** Programmable stablecoin payments for autonomous agents on
Aevum Testnet: EIP-712 payment mandates, scope-restricted session keys with
per-payment caps, cumulative mandate limits enforced on-chain, and heuristic
screening plus pre-signing simulation in the reference executor.

## O problema

Agentes autônomos que pagam por serviços precisam de autoridade de gasto
estreita, revogável e verificável: um limite aprovado pelo dono, a
assinatura do dia a dia separada da chave do dono, e tetos impostos pelo
contrato que valem mesmo se o software do agente for manipulado por
instruções injetadas em conteúdo externo. O AgentPayments implementa essa
separação na Aevum Testnet (chain 44005), usando a stablecoin de teste
tUSD8.

## Arquitetura

```
entrada externa (página/API/mensagem)
        │  tratado como DADO, nunca instrução
        ▼
┌─────────────────────────────┐
│ 1. GUARDA (backend/guard.py)│  triagem heurística anti-prompt-
│    7 famílias de padrões    │  injection: override, role_play,
│    override/role_play/      │  fake_system, imperative, exfil,
│    fake_system/imperative/  │  encoding, delimiter. Reduz a
│    exfil/encoding/delimiter │  superfície de ataque; não captura
│                             │  toda injeção possível.
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ 2. SIMULAÇÃO (eth_call)     │  `simulatePayment` via eth_call:
│                             │  chamada executada por um nó contra
│                             │  o estado consultado, sem transmitir
│                             │  transação; espelha as verificações
│                             │  de `executePayment`.
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ 2b. PREFLIGHT               │  a chave que assina tem tQDAY p/ o gás?
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ 3. CONTRATO AgentPayments   │  cofre + mandatos EIP-712 + session keys
│    (testnet 44005)          │  — impõe seus tetos quando a transação
│                             │  é executada.
└─────────────────────────────┘
        │  toda decisão (aprovar OU recusar) → audit/audit.jsonl
```

### (a) Mecânicas de agente

- **Mandatos de pagamento verificáveis** (`createMandate`, EIP-712): a
  intenção do dono — beneficiário, teto, validade e nonce anti-replay — é
  assinada e o contrato verifica a assinatura on-chain (recuperação ECDSA).
  Qualquer um pode submeter (relay) a transação; o contrato só honra a
  intenção assinada pelo dono.
- **Session keys com escopo restrito** (`registerSessionKey`): cada chave é
  vinculada a UM mandato, com teto **por pagamento** (`maxValue`) e validade
  próprios. O teto da chave é por pagamento, **não** acumulado: múltiplos
  pagamentos podem consumir o restante autorizado do mandato, até o teto
  acumulado do mandato (`cap`/`spent`) ou a expiração. A validade de 1 dia
  da demo é a **expiração** da chave. A assinatura do dia a dia fica separada
  da chave do dono. Chaves novas nascem sem gás — o dono patrocina 0,01
  tQDAY por chave (testnet).
- **Limites impostos pelo contrato**: quando uma transação de pagamento é
  executada, `executePayment` reverte se o valor passar do teto por
  pagamento da session key, do restante do mandato ou do saldo do cofre.

### (b) Segurança e confiança

- **Triagem heurística + simulação no executor de referência**: a entrada
  externa é tratada como dado e triada por um guarda heurístico (7 famílias
  documentadas de padrões de injeção: override, role-play, fake-system,
  imperative, exfiltration, encoding, delimiter). A triagem reduz a
  superfície de ataque, mas não captura toda injeção possível. Em seguida, o
  executor testa o pagamento candidato com `simulatePayment` via eth_call —
  uma chamada executada por um nó contra o estado atual, sem transmitir uma
  transação — e roda um preflight de gás antes de assinar. **Neste
  executor**, pedidos que falham na triagem ou na simulação são recusados
  antes da assinatura, e cada decisão é escrita no log de auditoria
  (`audit/audit.jsonl`). O contrato aplica suas próprias verificações quando
  a transação é executada.
- **Evidência**: The deployed contract, successful testnet transactions and
  resulting state can be verified on-chain. Pre-signing rejection cases are
  documented in the application's execution logs and can be reproduced from
  the code. Os logs são registros de execução da própria aplicação — não são
  auditoria independente nem prova imutável.

## Diferença para um ERC-20 allowance

Um allowance ERC-20 já limita o montante total que um spender pode sacar do
dono. Um mandato acrescenta: **beneficiário vinculado** (pagamentos só vão
para o beneficiário nomeado), **janela de validade** e **session keys com
escopo** que assinam os pagamentos do dia a dia sob tetos por pagamento, sem
possuir a chave do dono.

## Modelo de ameaças

| Ameaça | Defesa | Onde |
|---|---|---|
| Prompt injection em página/API/mensagem | Triagem heurística (7 famílias) no executor; parâmetros de pagamento nunca vêm do conteúdo externo; simulação pré-assinatura neste executor; o contrato impõe tetos, beneficiário e validade quando a transação executa | `backend/guard.py`, `backend/executor.py`, `contracts/AgentPayments.sol` |
| Pagamento acima do teto aprovado | Teto por pagamento da session key + teto acumulado do mandato (`cap`/`spent`), verificados on-chain em `executePayment` e espelhados em `simulatePayment` | `contracts/AgentPayments.sol` |
| Session key vazada/roubada | Alcance limitado às permissões daquele mandato neste contrato: o restante autorizado, somente para o beneficiário nomeado, até a expiração ou revogação | `registerSessionKey` / `revokeSessionKey` |
| Mandato forjado | Assinatura EIP-712 do dono verificada via `ecrecover` + nonce anti-replay | `createMandate` |
| Chave principal exposta | Assinatura do dia a dia separada: session keys operam os pagamentos; o dono só autoriza mandatos | `backend/mandate.py` |
| Cofre drenado por bug de lógica | `simulatePayment` espelha as verificações; saldo do cofre checado antes de transferir | `simulatePayment` / `executePayment` |

**Limites honestos**: protótipo de testnet, somente tokens de teste. O
guarda é heurístico (triagem por padrões — falsos positivos e negativos são
possíveis; não é prova formal de segurança). A autorização do dono verifica
assinaturas de EOA via recuperação ECDSA (`ecrecover`); o suporte a
carteiras contratuais (EIP-1271), como donos multisig, é **trabalho futuro**
a implementar e testar. Sem timelock no protótipo.

## Estado registrado (execução de novembro/2026, testnet)

- Contrato `AgentPayments`: `0x19c37FEa76d8D4B688597EB3C65051f8b5D42a41`
  — deploy tx `736c747cc1ae59ea69e29ac7d7e9f5dcd98f0abf372e06fe900c976ddcc514ea`
  (bloco 4119479)
- Demonstração ponta a ponta: ver `demo-report.md`
  - 1 pagamento válido de 0,50 tUSD8 via session key — tx
    `5f06cd49618f9ef1b6d07008bb7087bdf9c21b6ffccc3f1d5b66500b928620a3`
    (bloco 4119617)
  - 3 pedidos recusados pelo executor antes de qualquer assinatura,
    registrados no log de execução: 1,50 tUSD8 acima do teto por pagamento
    da session key; tentativa de prompt injection bloqueada pelo guarda;
    2,00 tUSD8 acima de AMBOS os limites — o restante do mandato (1,50) e o
    teto por pagamento (1,00); o motivo registrado foi o teto do mandato.
- Estado final daquela execução: cofre 3,50 tUSD8 · mandato: 0,50 de 2,00
  gastos · tQDAY do agente: ~0,987

## Como reproduzir

Atalho de 1 comando: `./demo.sh` (cria o venv, instala as dependências, implanta o contrato e roda a demo ponta a ponta).

```bash
cd ~/workspace/dorahacks/aevum-qday
python3 -m venv .venv && .venv/bin/pip install web3 py-solc-x
.venv/bin/python -c "import solcx; solcx.install_solc('0.8.24')"
.venv/bin/python scripts/deploy.py   # implanta o contrato (testnet)
.venv/bin/python scripts/demo.py     # demonstração ponta a ponta
```

Pré-requisitos: a carteira do agente precisa de tQDAY + tUSD8 de teste
(faucet via Discord do QDay — ver `viabilidade-faucet.md`). A chave do
agente é lida de `~/workspace/synmerco/agent-evm-key.json` (600) e nunca
é registrada em log.

## Estrutura

```
contracts/AgentPayments.sol   contrato (cofre + mandatos EIP-712 + session keys)
backend/guard.py              anti-prompt-injection (do Kit Agente Seguro)
backend/config.py             RPC/chain/endereços (só testnet)
backend/mandate.py            assinatura EIP-712 de mandatos
backend/executor.py           guarda → simulação → preflight → execução + audit log
scripts/compile.py            compilação (solc 0.8.24)
scripts/deploy.py             deploy na testnet + deployments.json
scripts/demo.py               demonstração ponta a ponta (retomável)
audit/audit.jsonl             decisões de segurança (aprovações e recusas)
deployments.json              endereços e hashes públicos
demo-report.md                relatório da demonstração
viabilidade-faucet.md         por que só o faucet via Discord destrava
```

## Custo

US$ 0. Gás total da demo: ~0,013 tQDAY (tokens de teste do faucet).
Nenhum pagamento, assinatura ou depósito em mainnet.
