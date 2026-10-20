# Relatório de testes · Arquivista 0.2.0

## O que foi executado nesta entrega

Testes locais Python da lógica de comandos, permissões, projeção pública, pesquisa, assinatura de requisições, persistência operacional e configuração. Testes JavaScript executando as funções da ponte com **serviços Google simulados**. A simulação aplica as requisições planejadas em estruturas em memória: não usa a planilha real.

Os números e saídas finais estão em `RESULTADO_TESTES.txt`. Incluem um teste de construção dos comandos/formulários com discord.py, que é executado quando essa dependência está disponível. Neste ambiente ela não pôde ser instalada por indisponibilidade de acesso à rede; esse teste ficou explicitamente **pulado**, não aprovado.

Também foram verificadas a sintaxe Python/JavaScript, a ausência de token Discord hardcoded e as coordenadas únicas das 20.000 posições do modelo de 100 membros.

## Planilha conectada (v0.3)

- `tests/test_planilha.js` roda o planejador real do `Planilha.gs` contra uma grade simulada e confere, depois de cada gravação, que o modelo interno bate com a grade: criação, separador de fórmula, revisões antigas ignoradas, bloco que cresce, transferência, uma guia por pessoa com o nome de usuário, nome repetido com (2), renomear quando o nome de usuário muda, guia antiga renomeada, operação inválida isolada, imagem e a Web App (assinatura, horário, servidor, tamanho, pedido repetido).
- Os pedidos de um cenário reduzido foram enviados de verdade pela API do Sheets numa planilha de teste: visor, contagem e grupos funcionaram depois da expansão. O Apps Script em si (menu, implantação, trava) não rodou ao vivo.
- `tests/test_core.py` (`SheetTests`): cifra da chave, fila guardando só a última versão, envio com ponte falsa, conexão e desconexão, migração de banco antigo.

## Cobertura local

- Prefixo AC com maiúsculas/minúsculas, espaço, aliases e menções;
- Correspondência dos 16 comandos de barra com os comandos de chat;
- Busca com pequeno erro de grafia e resultados ambíguos não descartados;
- Exclusão de status, justificativa, nome interno e metadados da projeção pública;
- Cadastro próprio/por staff e rejeição de tentativa de alterar terceiros;
- IDs e data original preservados; novos membros vinculados uma única vez;
- Aparência + obra ocupadas, incluindo Arquivado, e reutilização após Liberado;
- Confirmação idempotente, pedido repetido e pedido adulterado;
- Alteração concorrente detectada pela revisão, trava ocupada e manutenção;
- Transferência, remoção com histórico e campos de entrada gravados como texto;
- Captura de mudanças manuais significativas, sem evento duplicado na reconciliação;
- HMAC válido/inválido, timestamp expirado e servidor errado;
- URLs rejeitadas, assinatura/tamanho de anexos e remoção explícita de imagem;
- Fila de notificação, configurações duráveis, cursor e recuperação de tentativa interrompida;
- Migração para propriedades/trava compartilhadas entre editor e Web App.

## O que não foi testado ao vivo

Não houve login com o token fornecido, envio de mensagens, criação de webhooks, sincronização real de slash commands, atualização do avatar, chamada a `/exec`, alteração da planilha, instalação de gatilhos, autorização da conta Google, execução Discloud ou push no GitHub. Os Guias e a base de aparências não foram modificados nesta etapa.

A biblioteca Discord não foi carregada nos testes locais deste ambiente. Sintaxe e checagem pela documentação não substituem isso. O workflow incluído instala a biblioteca e executa o teste pendente; ele ainda precisa rodar em uma máquina com rede ou no novo repositório.

A simulação JavaScript não prova recalculo de fórmulas, comportamento de imagem nativa/mesclas, permissões Google, latência, cotas ou entrega de gatilhos. Não há garantia de desempenho de produção antes dos testes abaixo.

## Teste de aceitação no servidor

Faça em um canal da staff, com registros de teste explicitamente identificados e duas contas, uma delas sem cargo administrativo.

1. Execute `python verificar.py`, depois inicie somente uma instância. Confira os 16 comandos `/`, `AC:ajuda`, `ac: ajuda`, a Amiya no webhook e a menção ao bot.
2. Registre uma aparência de teste pelo membro comum. Confirme responsável, ID, data e grupo no Sheets; teste um nome interno que não deve aparecer publicamente. Cancele outro formulário e confira que nada foi cadastrado por ele.
3. Teste listagem, galeria, filtro por membro e consulta com erro de grafia. Verifique que outra pessoa não controla o painel e não edita o registro de terceiros.
4. Tente duplicar aparência + obra com diferenças de espaços/maiúsculas. Arquive e confirme que continua bloqueada. Libere com staff e verifique a possibilidade de um novo cadastro; o registro anterior permanece auditável.
5. Edite, transfira e remova com staff, observando ID/data preservados quando cabível. Envie um pedido repetido pela mesma confirmação após uma interrupção simulada e confirme que não foi criada uma segunda aparência.
6. Configure o canal de histórico. Faça uma alteração direta na ficha e aguarde a captura; confirme que uma atualização pelo bot gera apenas um evento lógico e que justificativa/status não aparecem no canal público.
7. Teste anexo, link direto e imagem nativa de célula; confirme galeria e ausência de imagem quando a fonte desaparece. Não remova arquivos de produção para testar.
8. Confira um registro nos blocos +50 e no último grupo realmente preparado; não assuma que o teste de coordenadas prova escrita no Sheets real.
9. Reinicie o processo e confira canal configurado, cursor de eventos e fila preservados no SQLite. Teste um membro com permissão removida depois de abrir um painel.
10. Remova os cadastros de teste pelo fluxo administrativo. Preserve os eventos de teste como evidência ou exporte-os antes de qualquer política futura de retenção; não apague tabelas técnicas às cegas.

## Repetir localmente

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
node tests/test_bridge.js
node --check < apps_script/Arquivista.gs
node --check < apps_script/Aparencias.gs
node tests/test_planilha.js
node --check < apps_script/Planilha.gs
```

Use Node 22 para o simulador. O bot hospedado usa Python; Node não é necessário na Discloud para executar os comandos.
