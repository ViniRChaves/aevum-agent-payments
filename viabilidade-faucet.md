# Viabilidade do faucet — Aevum Builder Challenge #1 (QDay)

Data da checagem: 2026-11-25
Rede: QDay Aevum Testnet — chain ID 44005
RPC pública oficial: https://rpc-test.qday.info
Endereço do agente avaliado (carteira própria do agente, não do usuário): 0xba495b5eb152ccDF7715460901a5c62f682dd4Ee

## Veredito

**(B) BLOQUEADO — exige passo humano.**

Não foi encontrada, nas fontes oficiais, uma rota para obter **tQDAY + tUSD8** na testnet pública a custo US$ 0 sem etapa exclusivamente humana e sem saldo pago em mainnet. Por isso, **nenhum probe de claim foi executado**: nenhuma rota atendia à condição de probe (formulário/API simples, sem captcha, sem Discord e sem outro gate humano).

## Rotas oficiais encontradas

### 1. Web faucet oficial — https://faucet.qday.info

Fonte oficial lida na íntegra (FAQ da própria página):

- Entrega **5 tQDAY por claim** (somente tQDAY; a página não oferece tUSD8).
- Limite: **1 claim a cada 24 horas por endereço destinatário**; há também um teto diário total do faucet.
- O faucet envia a transação (o destinatário não precisa de gás para o claim).
- Exige **conectar uma wallet** e passar por um **"quick bot check"** (verificação anti-bot/captcha).
- **Gate de saldo pago em mainnet:** o endereço destinatário precisa manter, na Ethereum mainnet, aproximadamente **0,0001 ETH, ou 1 USDT, ou 1 USDC** (qualquer um dos três). A checagem de saldo se aplica ao destinatário.

Conclusão sobre esta rota: bloqueada para o nosso critério por dois motivos independentes — verificação anti-bot e exigência de saldo em mainnet. Além disso, ela não resolve o tUSD8.

### 2. Discord faucet — rota recomendada aos participantes (Aevum Starter Kit oficial)

Fonte: documentação oficial do Aevum Starter Kit (PQA Labs/QDay), seção "Get test tokens".

- Entrega **1 tQDAY + 5 tUSD8** (a única rota oficial documentada que entrega os dois tokens).
- Limite: **uma vez por conta do Discord e uma vez por endereço**.
- **Não** checa saldo em mainnet — uma wallet só de testnet funciona.
- Etapas exigidas, exatamente como documentadas:
  1. **Entrar no Discord do QDay**;
  2. No canal **#verify**, **reagir com ✅** para receber o papel **Verified**;
  3. Digitar **/faucet**, colar o endereço da wallet e enviar.
- A documentação acrescenta que a conta do Discord **não pode ser recém-criada** ("It works for Discord accounts that aren't brand new").

Conclusão sobre esta rota: é gratuita e entrega os dois tokens, mas exige participação humana no Discord (ingresso + verificação por reação + conta não nova). É exatamente o tipo de passo que a regra do usuário manda parar e reportar antes de investir no desenvolvimento.

### 3. Faucet embutido na documentação (in-docs)

Fontes: FAQ oficial do QDay Wiki e guia oficial "Getting Started".

- Fica na página "Get testnet tokens" do wiki; exige **conectar a wallet** e fazer o claim de tQDAY chamando o contrato do faucet (contrato oficial QDayFaucet em 44005: 0xE5074CBbd046AFb491EB8692abD6cF7ECCC6dEE5).
- O claim é uma transação on-chain com **cooldown por endereço** e só aceita EOA.
- Uma wallet nova com **0 tQDAY não consegue pagar o gás desse primeiro claim** — a própria FAQ manda obter o primeiro tQDAY em faucet.qday.info (rota 1, com os gates acima).
- As fontes dessa rota falam apenas de tQDAY (gás); não documentam entrega de tUSD8.

Conclusão: não é uma API/formulário sem gate e não resolve o primeiro funding nem o tUSD8.

### Observação — fork local não conta

O Starter Kit oferece `make deal` em fork local (100 tUSD8 + 10 tQDAY), mas isso é apenas um fork local (chain 440050), não a testnet pública 44005 onde a atividade do desafio é julgada. Não substitui o faucet para fins do hackathon.

## Dados de referência confirmados em fontes oficiais

- tUSD8 (44005): 0x456569838f1d43009A91ebA4263147Afd7233483 — 6 decimais (QDay Wiki / Official Links).
- QDayFaucet (44005): 0xE5074CBbd046AFb491EB8692abD6cF7ECCC6dEE5 (Official Links).
- A página do desafio no DoraHacks (dorahacks.io/hackathon/qday) não pôde ser lida via fetch de texto nesta checagem (HTTP 405); o Starter Kit oficial registra que as regras completas estão nessa página e prevalecem sobre o kit. O veredito acima se apoia nas páginas oficiais do QDay/faucet, que são a fonte primária das regras de obtenção dos tokens.

## O que destrava

Um passo humano único e curto: entrar no Discord do QDay com uma conta que não seja recém-criada, reagir ✅ em #verify e rodar /faucet uma vez para o endereço de build — isso entrega 1 tQDAY + 5 tUSD8 sem custo e sem saldo em mainnet. Sem esse passo, não há rota oficial viável a US$ 0 para financiar o endereço na testnet pública.
