# AgentPayments — Pagamentos programáveis para agentes (Aevum/QDay)

Protótipo para o **Aevum Builder Challenge #1 (QDay, DoraHacks)**.
Submissões até **2026-12-11 08:00 UTC**. Meta interna: testado ponta a ponta
até 2026-12-08.

> **Somente testnet (chain 44005), somente tokens de teste (tQDAY/tUSD8),
> US$ 0 de gasto real. Nunca usa carteiras pessoais do usuário — só a
> keypair própria do agente. NÃO inscrito no hackathon; NÃO submetido.
> Inscrição e submissão exigem autorização final por escrito do usuário.**

## O problema

Agentes autônomos que pagam por serviços precisam de três coisas que os
modelos atuais não dão juntos: (1) gastar só dentro de um limite aprovado,
(2) sem expor a chave principal, (3) sem obedecer a instruções injetadas em
conteúdo externo. Este protótipo impõe as três em camadas independentes.

## Arquitetura

```
entrada externa (página/API/mensagem)
        │  tratado como DADO, nunca instrução
        ▼
┌─────────────────────────────┐
│ 1. GUARDA (backend/guard.py)│  anti-prompt-injection (reaproveitado
│    7 famílias de padrões    │  do Kit Agente Seguro): override,
│    override/role_play/      │  role_play, fake_system, imperative,
│    fake_system/exfil/       │  exfil, encoding, delimiter.
│    encoding/delimiter       │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ 2. SIMULAÇÃO (eth_call)     │  `simulatePayment` espelha TODAS as
│    sem estado, sem custo    │  regras do contrato antes de assinar.
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ 2b. PREFLIGHT               │  a chave que assina tem tQDAY p/ o gás?
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ 3. CONTRATO AgentPayments   │  cofre + mandatos EIP-712 + session keys
│    (testnet 44005)          │  — a última linha de defesa, on-chain.
└─────────────────────────────┘
        │  toda decisão (aprovar OU recusar) → audit/audit.jsonl
```

### (a) Mecânicas de agente

- **Session keys com escopo restrito** (`registerSessionKey`): cada chave é
  vinculada a UM mandato, com teto por pagamento e validade próprios. A
  chave principal nunca sai do cofre do operador. Chaves novas nascem sem
  gás — o dono patrocina 0,01 tQDAY por chave (testnet).
- **Mandatos de pagamento verificáveis** (`createMandate`, EIP-712): a
  intenção do dono — beneficiário, teto e validade — é assinada e verificada
  on-chain, com nonce anti-replay. Qualquer um pode submeter a transação;
  ninguém pode forjar a intenção.
- **Tetos rígidos de gasto em tUSD8 impostos em contrato**: `executePayment`
  reverte se o valor passar do restante do mandato, do teto da session key
  ou do saldo do cofre.

### (b) Segurança e confiança

- **Separação dado × instrução**: o guarda tria TODA entrada externa antes
  de ela tocar qualquer decisão. Bloqueio = recusa registrada, sem transação.
- **Simulação/validação antes de assinar**: nada é assinado sem passar por
  `simulatePayment` (eth_call gratuito). Transação fora do mandato é
  recusada e registrada no audit log — nenhuma assinatura acontece.
- **Auditoria completa**: `audit/audit.jsonl` registra aprovações e recusas,
  com estágio, motivo e (quando houver) hash da transação.

## Modelo de ameaças

| Ameaça | Defesa | Onde |
|---|---|---|
| Prompt injection em página/API/mensagem | Guarda (7 famílias de padrões) + dado nunca vira instrução | `backend/guard.py`, `backend/executor.py` |
| Pagamento acima do teto aprovado | Teto do mandato + teto da session key, checados off-chain E on-chain | `contracts/AgentPayments.sol` |
| Session key roubada | Escopo restrito (1 mandato, teto, validade), revogável, sem acesso ao cofre | `registerSessionKey` / `revokeSessionKey` |
| Mandato forjado | Assinatura EIP-712 do dono + nonce anti-replay | `createMandate` |
| Chave principal exposta | Só o dono assina mandatos; o dia a dia usa session keys | `backend/mandate.py` |
| Cofre drenado por bug de lógica | `simulatePayment` espelha as regras; saldo checado antes de transferir | `simulatePayment` / `executePayment` |

**Limites honestos**: o guarda é heurístico (pode ter falsos positivos e
não é prova formal); o contrato não usa multisig nem timelock; a demo usa
uma única chave de dono. Para produção, o dono deveria ser um multisig.

## Estado atual (testnet, verificado on-chain)

- Contrato `AgentPayments`: `0x19c37FEa76d8D4B688597EB3C65051f8b5D42a41`
  — deploy tx `736c747cc1ae59ea69e29ac7d7e9f5dcd98f0abf372e06fe900c976ddcc514ea`
  (bloco 4119479)
- Demonstração ponta a ponta: ver `demo-report.md`
  - 1 pagamento válido de 0,50 tUSD8 via session key — tx
    `5f06cd49618f9ef1b6d07008bb7087bdf9c21b6ffccc3f1d5b66500b928620a3`
  - 3 recusas antes de qualquer assinatura: acima do teto da session key,
    prompt injection (guarda), acima do restante do mandato
- Saldo do cofre: 3,50 tUSD8 · mandato: 0,50 de 2,00 gastos · tQDAY do
  agente: ~0,987

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
