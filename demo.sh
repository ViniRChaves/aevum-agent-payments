#!/usr/bin/env bash
# Demo em 1 comando — Aevum/QDay (testnet 44005, só tokens de teste, US$ 0 real).
#
# O que faz:
#   1. cria o venv (.venv) e instala as dependências (web3, py-solc-x);
#   2. instala o solc 0.8.24;
#   3. implanta o contrato AgentPayments (scripts/deploy.py);
#   4. roda a demonstração ponta a ponta (scripts/demo.py):
#      depósito no cofre -> mandato EIP-712 -> session key com escopo
#      restrito -> 1 pagamento válido + 3 recusas antes de qualquer
#      assinatura (acima do teto da session key, prompt injection
#      bloqueado pelo guarda, acima do restante do mandato).
#
# Pré-requisitos:
#   - Python 3.10+;
#   - carteira do agente com tQDAY + tUSD8 de teste (faucet via Discord
#     do QDay — ver viabilidade-faucet.md);
#   - a chave do agente é lida do arquivo apontado pela variável de
#     ambiente AEVUM_AGENT_KEY (JSON {"address": ..., "private_key": ...},
#     permissão 600) ou, se a variável não estiver definida, do caminho
#     padrão ~/workspace/synmerco/agent-evm-key.json. Nunca é registrada
#     em log. Formato de referência: demo-session-key.example.json.
#
# Segurança: a chave descartável da session key da demo fica em
# demo-session-key.json (600, só testnet, sem valor real) e está no
# .gitignore — nunca commitar esse arquivo.
#
# Uso: ./demo.sh
set -euo pipefail
cd "$(dirname "$0")"

# Preflight: sem a chave do agente (arquivo JSON 600 FORA do repositório),
# deploy e demo não têm como assinar nada — parar com instrução clara.
KEY_FILE="${AEVUM_AGENT_KEY:-$HOME/workspace/synmerco/agent-evm-key.json}"
if [ ! -f "$KEY_FILE" ]; then
  cat >&2 <<EOF
ERRO: arquivo de chave do agente não encontrado: $KEY_FILE

A demo assina transações na testnet com a chave de uma carteira de TESTE
(chain 44005), que por segurança NUNCA fica dentro deste repositório.
Para rodar a demo:

  1. crie (ou reuse) uma carteira somente de testnet e peça tQDAY + tUSD8
     no faucet do QDay (ver viabilidade-faucet.md);
  2. salve a chave dela num arquivo JSON com permissão 600, no formato
     {"address": "0x...", "private_key": "..."} — modelo em
     demo-session-key.example.json (NUNCA commite a chave real);
  3. aponte a variável de ambiente para esse arquivo e rode de novo:

       export AEVUM_AGENT_KEY=/caminho/para/agent-key.json
       ./demo.sh
EOF
  exit 1
fi

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet web3 py-solc-x
.venv/bin/python -c "import solcx; solcx.install_solc('0.8.24')"
.venv/bin/python scripts/deploy.py
.venv/bin/python scripts/demo.py
echo "Demo concluída — ver demo-report.md e audit/audit.jsonl"
