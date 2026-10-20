# Validação · Arquivista 1.0.3 · 20/10/2026

A 1.0.3 permite remover o próprio cadastro com confirmação. Os testes cobrem proprietário e terceiros, cancelamento, revisão antiga, transferência antes de confirmar, retentativa sem duplicar auditoria, preservação do histórico e fila de remoção da planilha. A suíte foi executada novamente; os ensaios reais descritos abaixo foram feitos nas versões indicadas.

O atendimento por menção também foi validado: conta do bot, cargo automático exclusivo e resposta à própria mensagem acionam a Amiya; `@everyone`, `@here`, cargo genérico, cargo de outro bot e menção a outro usuário não acionam. Comandos explícitos continuam funcionando.

## O que foi executado nesta entrega

Testes locais Python da lógica de comandos, permissões, projeção pública, pesquisa, assinatura de requisições, persistência operacional e configuração. Testes JavaScript executando as funções da ponte com **serviços Google simulados**. A simulação aplica as requisições planejadas em estruturas em memória: não usa a planilha real.

Os números e comandos estão em `RESULTADO_TESTES.txt`. O discord.py 2.7.1 está instalado: a construção real dos comandos, grupos e formulários faz parte da suíte, sem pular esse teste.

Também foram verificadas a sintaxe Python/JavaScript, a ausência de token Discord hardcoded e as coordenadas únicas das 20.000 posições do modelo de 100 membros.

## Conferência real no Discord e no Sheets

No servidor de testes, foram conferidos cadastro por slash e prefixo, anexo PNG preservado, consulta com prefixo minúsculo, lista/galeria, edição, duplicidade por caixa/espaços, busca por obra, situação/justificativa privadas, cancelamento de remoção e paginação da auditoria. Na conclusão da 1.0, as duas fichas fictícias foram removidas pela confirmação do bot, preservando os seis cadastros preexistentes e a auditoria dos testes.

O cadastro e a edição pelo bot chegaram à planilha conectada. A edição manual de nome e situação no Sheets voltou ao bot, mantendo ID/data e criando evento de origem planilha. A fila terminou sem mudanças esperando envio. O backup diário foi ativado em canal privado e enviou JSON e XLSX. O canal de notificações continua opcional e desligado; a auditoria no banco permanece ativa.

O layout gerado pelo código também foi aplicado pela API ao [ensaio isolado no Google Sheets](https://docs.google.com/spreadsheets/d/11XYpi_yJT5Nf7mBIp0VeOBDFb1O5ZtoBL_b_zEMl4L0/edit#gid=1001), com dados fictícios. Aos 18 cadastros, a aba passou de 98 para 178 linhas e mostrou `18 / 40`; aos 38, passou a 258 linhas e mostrou `38 / 60`. A aba de controle manteve todos os valores e fórmulas. O visor selecionando a posição 38 mostrou nome, aparência, obra, situação, data e justificativa corretos. A API confirmou 61 grupos de linhas (um externo e 60 fichas), mesclas e validações preservadas. O teste usa a conta conectada à ferramenta; não usa nem valida as credenciais Google dedicadas do bot. A captura visual do navegador não ficou disponível; a conferência foi feita pelos valores calculados e metadados nativos da API.

A chave de duplicidade distingue acentos, embora a busca por obra agrupe variantes. Essa regra foi mantida para não mudar a identidade dos cadastros existentes.

`tests/test_managed.py` cobre criação concorrente, retomada após perda de resposta, compartilhamento recusado, e-mail cifrado, troca da chave mestra, falta de credenciais, rejeição de membros inválidos e expansão 20 → 40 → 60. Se a resposta do compartilhamento se perde depois de conceder acesso, a retomada não reformata nem renomeia abas que o editor possa ter alterado.

## Planilha conectada (v0.3)

- `tests/test_layout.py` monta a planilha pelo caminho real do bot (lê pelo script simulado em `tests/sheet_sim.py`, planeja, grava) e confere, depois de cada gravação, que o modelo do bot bate com a grade: criação, separador de fórmula, revisões antigas ignoradas, bloco que cresce, transferência, uma guia por pessoa com o nome de usuário, nome repetido com (2), renomear quando o nome de usuário muda, guia antiga renomeada, operação inválida isolada, imagem, limite de tamanho por gravação, recusa quando a planilha mudou e script antigo.
- `tests/test_planilha.js` roda o Web App fixo do `Planilha.gs`: assinatura, horário, servidor, tamanho, leitura em lotes, lista de pedidos permitidos, guia de sistema protegida, recusa quando a planilha mudou e bot antigo. Com `PLANILHA_CENARIO` (o CI define), também confere que todos os pedidos que o bot gera passam na lista do script.
- Os pedidos de um cenário reduzido foram enviados de verdade pela API do Sheets numa planilha de teste: visor, contagem e grupos funcionaram depois da expansão. O Apps Script em si (menu, implantação, trava) não rodou ao vivo.
- `tests/test_core.py` (`SheetTests`): cifra da chave, fila guardando só a última versão, envio com ponte falsa, conexão e desconexão, migração de banco antigo.

## Cobertura local

- Prefixo AC com maiúsculas/minúsculas, espaço, aliases e menções;
- Correspondência dos 16 comandos de barra com os comandos de chat;
- Busca com pequeno erro de grafia e resultados ambíguos não descartados;
- Nome no servidor visível nas consultas e na galeria; situação, justificativa e metadados excluídos da projeção pública. Nomes escapados, campo vazio e páginas com textos longos verificados;
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

## Limites da validação

O OAuth dedicado foi autorizado com `drive.file` e público em produção. O teste real do formulário privado no Discord criou uma planilha privada, concedeu edição ao e-mail informado e enviou os oito cadastros existentes, em duas abas de membros, sem estrutura quebrada. A API confirmou somente proprietário e editor, sem acesso público. Um ensaio separado nessa conta confirmou expansão aos 18 registros, contador `18 / 40`, visor correto e recuperação do mesmo arquivo pelo marcador do pedido. A interface do Sheets também foi conferida com a conta editora.

A configuração de acesso externo para imagens foi validada na API real num arquivo isolado. O teste automatizado também força uma retomada da inicialização quando essa propriedade já está habilitada, recusando nova escrita do campo que o Google torna somente leitura. Conexões antigas não recebem essa alteração automaticamente.

Na preparação da 1.0, uma segunda conta Discord sem staff consultou a galeria e foi impedida de acessar configuração, planilha, auditoria, painel de outra pessoa e edição de ficha alheia. A staff transferiu uma ficha fictícia para essa conta, preservando ID/data; o novo responsável editou somente os campos permitidos. Naquela versão, a remoção ainda era exclusiva da staff; a 1.0.3 permite a remoção pelo próprio responsável. A API do Sheets confirmou transferência e edição na aba correta, sem duplicar a ficha. As duas fichas fictícias foram removidas e a planilha terminou com os seis cadastros originais, sem estrutura quebrada.

O JSON realmente enviado pelo backup diário foi baixado e restaurado pelo importador do produto em um SQLite temporário vazio; depois foi restaurado novamente com substituição. Os oito registros do arquivo mantiveram campos, IDs e datas; as revisões subiram e o histórico anterior foi preservado. O XLSX foi validado como ZIP/XML, com duas guias de membros. Nenhuma restauração substituiu o banco de produção. Também foi criada uma cópia completa do SQLite na hospedagem pela API de backup, com `integrity_check` aprovado. A comparação final com essa cópia confirmou os seis registros originais intactos, descontando apenas URLs temporárias de imagem.

`tests/test_permissions.py` cobre permissões individuais de canal (inclusive membro fora do cache), cargos comuns, gerência, staff configurada, painéis de outro usuário e perda de cargo antes da confirmação. São nove testes novos, totalizando 130 Python + 28 JavaScript da ponte + 7 do script da planilha: 165 aprovados.

A simulação JavaScript não prova latência, cotas, concessão real de permissões nem entrega de gatilhos. O checklist abaixo continua necessário antes de anunciar a criação automática para outros servidores.

## Teste de aceitação no servidor

Faça em um canal da staff, com registros de teste explicitamente identificados e duas contas, uma delas sem cargo administrativo.

1. Execute `python verificar.py`, depois inicie somente uma instância. Confira os 16 comandos `/`, `AC:ajuda`, `ac: ajuda`, a Amiya no webhook e a menção ao bot.
2. Registre uma aparência de teste pelo membro comum. Confirme responsável, ID, data e grupo no Sheets; teste um nome interno que não deve aparecer publicamente. Cancele outro formulário e confira que nada foi cadastrado por ele.
3. Teste listagem, galeria, filtro por membro e consulta com erro de grafia. Verifique que outra pessoa não controla o painel e não edita o registro de terceiros.
4. Tente duplicar aparência + obra com diferenças de espaços/maiúsculas. Arquive e confirme que continua bloqueada. Libere com staff e verifique a possibilidade de um novo cadastro; o registro anterior permanece auditável.
5. Edite, transfira e remova com staff, observando ID/data preservados quando cabível. Envie um pedido repetido pela mesma confirmação após uma interrupção simulada e confirme que não foi criada uma segunda aparência.
6. Configure o canal de histórico. Faça uma alteração direta na ficha e aguarde a captura; confirme que uma atualização pelo bot gera apenas um evento lógico e que justificativa/status não aparecem no canal público.
7. Teste anexo, link direto e imagem nativa de célula; confirme galeria e ausência de imagem quando a fonte desaparece. Não remova arquivos de produção para testar.
8. Confira a expansão aos 18 e 38 cadastros: 20 → 40 → 60 posições, visor, fórmulas, agrupamentos e outra aba intacta. Não assuma que o teste de coordenadas prova escrita no Sheets real.
9. Reinicie o processo e confira canal configurado, cursor de eventos e fila preservados no SQLite. Teste um membro com permissão removida depois de abrir um painel.
10. Libere os cadastros de teste ao terminar. Preserve os eventos como evidência; não apague tabelas técnicas às cegas.

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
