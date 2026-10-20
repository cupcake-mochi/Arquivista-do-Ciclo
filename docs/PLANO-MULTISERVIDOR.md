# Plano · Arquivista multi-servidor (banco + planilha)

**Decidido com o Mizuki em 19/10/2026:** o bot passa a ser público e funciona em
vários servidores. Um banco próprio vira a fonte dos dados, e cada servidor pode
**opcionalmente** conectar a sua própria cópia da Planilha Aparências, com
sincronização nos dois sentidos. **Etapas 1 e 2 implementadas** (branch `claude/project-thread-zzfh12`, não implantada).

## Como fica

```
Discord (N servidores) ──► bot ──► banco (fonte)
                                   │  ▲
                fila bot→planilha  ▼  │  eventos planilha→bot
                          ponte Apps Script do servidor (opcional)
                                   │
                          cópia da planilha daquele servidor
```

- **Servidor sem planilha:** convida o bot e já usa.
- **Servidor com planilha:** a staff copia o modelo, publica a ponte e conecta
  com `/configurar planilha`. A planilha continua servindo pra ver e editar sem
  o bot.
- Os dados de cada servidor ficam separados pelo ID do servidor. Um mesmo
  membro em dois servidores tem cadastros independentes, como no Mudae.

## O que muda hoje no código

O bot está preso a um servidor em três pontos:

| Onde | Hoje | Depois |
|---|---|---|
| `config.py` | `DISCORD_GUILD_ID`, `AC_BRIDGE_URL`, `AC_BRIDGE_SECRET` obrigatórios no `.env` | Só `DISCORD_TOKEN` e uma chave mestra (`AC_MASTER_KEY`) pra cifrar as chaves das pontes |
| `bot.py` | Recusa mensagens de outros servidores; comandos sincronizados só num servidor; uma ponte, um cursor, um canal de histórico | Comandos globais; configuração, cursor e canais por servidor; laço de sincronização percorre só os servidores com planilha |
| `Aparencias.gs` | `CM.id` fixo na planilha original | Usa a planilha onde o script está, então qualquer cópia funciona |

Telas, comandos, permissões, busca, galeria e a assinatura HMAC da ponte
continuam. A ponte já assina o ID do servidor em cada pedido.

## Banco

Começa em **SQLite** (WAL) na própria hospedagem, atrás de uma camada de
repositório. Migra pra **Postgres** quando o volume pedir, sem mexer nas telas.
Antes de qualquer serviço pago, os custos são apresentados pra aprovação.

Tabelas principais:

- `guilds`: configuração por servidor (cargos de staff, canais de histórico e
  imagens, modo da planilha, URL da ponte, chave cifrada, cursor de eventos).
- `appearances`: `id` (mantém o formato `AP-…`), `guild_id`, `owner_id`,
  aparência, obra, chave normalizada, nome no servidor, situação,
  justificativa, imagem, data de cadastro (pode ser vazia), `revision`,
  posição na planilha (quando conectada). Aparência + obra é única por servidor
  enquanto a situação não for Liberado, inclusive Arquivado, como hoje.
- `events`: auditoria antes/depois (origem: bot, planilha ou importação; autor
  quando conhecido). Substitui a auditoria que hoje vive só no Google.
- `requests`: idempotência das confirmações (mesma confirmação não duplica).
- `sheet_outbox` e `conflicts`: sincronização com a planilha.
- `outbox` atual: notificações no Discord, agora com `guild_id`.

## Sincronização com a planilha

**Bot → planilha.** Toda mudança no banco entra na `sheet_outbox` na mesma
transação. Um trabalhador envia à ponte uma ação nova `apply` (criar,
atualizar ou limpar por ID, com a `revision`). Se o Google estiver lento ou
fora, a fila tenta de novo com espera crescente. O bot nunca espera a planilha
pra responder.

**Planilha → bot.** A captura que já existe no `Arquivista.gs` (gatilho de
edição + conferência periódica + snapshots) gera eventos. O bot lê os eventos
de cada servidor pelo cursor, valida (duplicata, campos obrigatórios, ID
existente) e aplica no banco. Eventos gerados pelas próprias gravações do bot
levam o `request_id` e são ignorados, pra não voltarem em eco.

**Conflito.** Se a planilha mudou uma ficha cuja `revision` já é mais antiga
que a do banco, o bot não sobrescreve nenhum dos lados: registra em
`conflicts`, avisa a staff no canal de histórico e oferece manter um ou outro.

**Capacidade.** A planilha tem 100 membros × 200 posições. O banco não tem esse
limite, então um servidor conectado pode passar do que a planilha comporta.
Padrão proposto: o bot avisa a staff e mantém esses cadastros só no banco,
marcados como "fora da planilha", até ampliarem.

## Modelo novo da planilha (decidido em 20/10)

A ficha continua sendo onde se edita, no visual de blocos de hoje. O que muda é
como o espaço é reservado:

- **Guias por faixa de membros** ("FICHAS 1–20", "FICHAS 21–40"…), criadas só
  quando necessário, no lugar de uma guia única de 41 mil linhas.
- **Posições sob demanda:** cada membro começa com 20 posições e ganha mais 20
  quando chega perto do fim (ex.: posição 18), até 200. Os blocos + / − ficam.
  Pior caso (todos com 200): ~9 mil células por membro, como hoje, mas em guias
  de 20 membros (~8 mil linhas cada) em vez de uma guia de 41 mil.
- **Expansão automática:** o gatilho de edição que já existe acrescenta o
  bloco, copiando um modelo pequeno de uma guia escondida. Membro novo em
  MEMBROS ganha bloco (e guia nova, se a faixa estiver cheia). O bot pede a
  expansão pela ponte antes de gravar, porque edição pela API não dispara o
  gatilho. Um gatilho de tempo e um item de menu servem de rede de segurança.
- **Mapa de blocos:** a posição deixa de ser calculada por `5 + 822 × grupo`; a
  SISTEMA · MEMBROS guarda guia e linha inicial de cada bloco. O ID de cada
  ficha continua sendo a identidade.
- **Uma regra de cor por coluna em cada guia**, em vez dos milhares de pedaços
  atuais; duplicata conferida pelo banco quando conectado, com aviso leve na
  planilha.
- Estimativa: uns mil membros com as 200 posições cheias por arquivo. Servidor maior usa
  só o banco.

A migração da planilha atual pra esse modelo é feita por script, preservando
IDs e datas, com a versão antiga guardada como cópia.

## Importação da planilha atual

Uma ação de leitura completa na ponte (com campos internos, só pra staff) traz
todos os cadastros com IDs e datas reais preservados, inclusive data vazia. O
bot grava no banco, confere contagem e amostras, e só então liga a
sincronização. Sem histórico inventado: a auditoria do banco começa na
importação.

## Para ser público

- **Verificação:** a partir de 100 servidores o Discord exige verificação, e o
  Message Content Intent (usado pelo `AC:`) precisa de aprovação. Os comandos
  `/` e as menções funcionam sem ele.
- **Sharding:** obrigatório a partir de 2.500 servidores (`AutoShardedClient`).
- **Política de privacidade e termos**, exigidos pra verificação.
- **Limites por servidor:** taxa de comandos, tamanho de anexos (já existe) e
  limite de polling às pontes.
- **Backups** do banco.

## Etapas

1. **Núcleo multi-servidor sem planilha:** banco, repositório, configuração por
   servidor, comandos globais, `/configurar` (cargos e canais). Testes locais.
   *Feito:* `store.py` (tabelas), `archive.py` (mesmas ações e erros da ponte),
   limite de 200 aparências ocupadas por membro em cada servidor, avisos de
   histórico gravados na mesma transação, `DISCORD_DEV_GUILD_ID` pra testar
   (comandos só nesse servidor e na hora). Configuração da v0.2 (canais e
   `STAFF_ROLE_IDS`) é levada pro servidor de testes uma vez.
2. **Importação** da Planilha Aparências atual pro banco.
   *Feito:* ação `export` na ponte e função `exportarParaArquivista` (grava um
   .json no Drive do dono, só leitura na planilha, funciona sem a ponte
   instalada). `python importar.py arquivo.json --servidor ID` confere tudo e só
   grava com `--aplicar`. Em 20/10 a planilha tinha 1 cadastro (Takao, de teste).
3. **Bot → planilha:** modelo novo da planilha (guias por faixa e posições sob demanda), ação `apply` na ponte, fila e `/configurar planilha`.
   Script sem ID fixo.
4. **Planilha → bot:** consumo dos eventos por servidor, eco e conflitos.
5. **Guia de instalação** pra donos de servidor e planilha modelo pública.
6. **Público:** privacidade, termos, verificação.

Cada etapa sai com testes e sem implantar nada sem pedido do Mizuki.

## Decisões em aberto

- Capacidade da planilha conectada (padrão acima).
- Quando o banco migra pra Postgres e qual serviço.
- Quais dados passam entre servidores (ex.: perfil global).
