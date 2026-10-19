# Segurança, arquitetura e limites conhecidos

## Dados e autoridade

A planilha visual permanece a fonte do catálogo. Não existe uma segunda tabela editável concorrente no SQLite. O SQLite local guarda configurações operacionais, cursor de eventos e entrega de notificações; a auditoria e os registros de idempotência ficam no Google.

As gravações do bot passam pelo Web App autenticado. O bot não recebe uma chave de conta de serviço com poder de edição geral e não escreve diretamente na API do Sheets fora da ponte. O módulo usa a mesma `ScriptLock` da automação da planilha. Isso evita dois escritores programáticos escolhendo a mesma vaga ao mesmo tempo.

Uma operação do bot planeja ficha, membro, data/ID, estado histórico, snapshot e confirmação do pedido em uma `spreadsheets.batchUpdate`. Essa chamada é atômica para suas requisições de alteração. A trava do Apps Script **não bloqueia o mouse de quem edita manualmente**. A planilha é compartilhada apenas com staff confiável; mantenha suas proteções de estrutura.

O bot não bloqueia drag-and-drop da conta dona da planilha, não redefine compartilhamento e não reverte mudanças estruturais às cegas. Alertas de estrutura/manutenção interrompem suas gravações até correção.

## Autenticação da ponte

A URL Web App responde a requisições da hospedagem sem login interativo, mas cada pedido contém um corpo assinado com **HMAC-SHA256**, chave privada com pelo menos 32 caracteres, servidor autorizado, autor da operação, carimbo de tempo e identificador do pedido. A chave não viaja em parâmetro da URL nem é escrita em células.

O Google valida a assinatura e o servidor antes de acessar o catálogo, e limita o desvio do relógio a cinco minutos. O bot obtém o usuário no próprio Discord e revalida cargos; não usa um ID ou `staff=true` digitado por um jogador. A ponte confia somente no processo que possui o segredo da assinatura. Portanto, quem obtém essa chave pode se passar por esse processo: proteja o `.env`, as Propriedades do script e a hospedagem.

Pedidos de escrita têm identificadores persistentes. A mesma confirmação reutiliza o identificador nas retentativas; não apague a aba `SISTEMA · AC PEDIDOS` para economizar espaço sem planejar a retenção. A combinação de autor/ação/dados não pode ser alterada sob um identificador já concluído.

O token Discord é independente de `AC_SECRET`. A chave enviada na conversa não foi incorporada, validada nem usada neste pacote. Gere um token novo e configure-o localmente. Nem os testes nem o workflow precisam de credenciais reais.

Um endpoint público autenticado ainda pode receber requisições inválidas e consumir cotas de execução. Este Web App é adequado a um servidor controlado, não um serviço público de grande escala ou uma garantia de resistência a negação de serviço. Para uso maior, a mesma interface pode ser migrada para um backend com controles de tráfego próprios.

## Privacidade no Discord

A projeção pública é uma lista explícita de campos. Ela não serializa o registro completo. Situação, justificativa e nome interno só aparecem em atendimento privado autorizado ou no histórico da staff. A lista, galeria, mensagens de erro e notificações não contêm a URL privada da planilha.

A staff pode configurar um canal público de notificações sem vazar detalhes: uma mudança de situação é anunciada como atualização genérica, não como o novo estado. Edições manuais sem autor Discord confiável aparecem como **Planilha; autor não identificado**. O dono do personagem nunca é inferido como autor da edição.

Mensagens comuns `AC:` não podem ser efêmeras; por isso recebem um botão público que abre atendimento privado. Formulários e confirmações são privados. Quem escreve segredos diretamente na mensagem pública já os expõe antes que o bot possa intervir; use os campos do painel.

Webhooks suportam nome/avatar por mensagem, mas componentes interativos exigem associação apropriada à aplicação. O código verifica isso e usa a própria conta do Arquivista como alternativa quando necessário. Respostas efêmeras são da interação do aplicativo, com identificação da Amiya no cartão; não são postagens públicas de webhook.

## Auditoria e entrega

A auditoria começa na instalação da ponte. A base anterior vira um snapshot inicial sem notificações e sem histórico inventado. IDs e datas anteriores são preservados, inclusive a ausência de data conhecida.

O gatilho de edição registra o último estado conhecido antes/depois. A reconciliação de fundo percorre até 50 registros por ciclo para recuperar alterações manuais não capturadas. Isso **não é um rastreamento forense garantido de cada edição intermediária**: mudanças muito rápidas entre capturas podem aparecer consolidadas; inserções de imagem e operações estruturais nem sempre disparam o mesmo evento. As proteções e a versão de histórico do próprio Sheets continuam importantes.

A tela do histórico limita a consulta a 200 resultados recentes nos últimos 5.000 eventos por desempenho. Quando há corte, mostra um aviso. Os eventos completos permanecem na aba técnica; sua preservação depende de não apagar o arquivo/tabelas e de manter backups.

Notificações são separadas da gravação. Falhar ao enviar no Discord não provoca outro cadastro. Uma fila SQLite preserva o progresso e tenta entregar de novo com espera crescente. O identificador do evento no rodapé permite reconhecer uma entrega já aceita quando o processo cai antes de confirmar no banco.

Há uma janela inevitável entre serviços independentes: a recuperação examina até 100 mensagens recentes do canal. Não é uma garantia matemática de entrega exatamente uma vez em qualquer cenário. Evite apagar mensagens de histórico, mantenha o banco local e rode uma única instância. A base original no Google não depende da entrega de cada mensagem.

## Imagens

O arquivo da Amiya é a imagem fornecida, copiada sem transformação. Não é uma nova imagem gerada nem uma comprovação de licença comercial da arte.

Links arbitrários não são baixados pelo host do bot. Só se aceitam URLs HTTPS sem credenciais, portas alternativas ou endereços locais/IP explícitos; ainda assim, valide fontes externas da comunidade, pois uma URL por nome pode mudar. URLs de imagem são exibidas pelo Discord/Sheets, serviços externos com seus próprios comportamentos.

Anexos recebidos pelo Discord são validados por tamanho e assinatura básica de arquivo; a validação não equivale a análise antimalware. Apenas PNG, JPEG, GIF e WebP até 8 MB entram no canal de preservação autorizado. Esse canal contém cópias das imagens; configure quem pode acessá-lo segundo as regras do servidor.

A referência persistente guarda IDs do servidor/canal/mensagem/anexo. A galeria recupera a mensagem para obter uma URL atual e pode atualizar o link da ficha sem criar uma notificação de alteração. Apagar a mensagem de origem ou remover permissões torna a imagem indisponível. Alterações de URL de anexos não mantêm automaticamente todas as 20.000 imagens do Sheets atualizadas a cada momento; a atualização ocorre sob demanda.

Se um upload for aceito e a gravação do cadastro falhar, uma cópia sem uso pode permanecer no canal. O código evita apagar arquivos em uma falha ambígua para não quebrar um cadastro que talvez tenha sido salvo. A limpeza de arquivos órfãos não está automatizada nesta versão.

Imagens nativas de célula usam `getContentUrl()` quando acessíveis pelo Apps Script. Essa URL é temporária e dá acesso à imagem específica; ela não torna a planilha editável/pública. A compatibilidade visual precisa ser validada no arquivo real. A galeria continua funcionando sem imagem.

## Capacidade e desempenho

A estrutura aceita os 50 ou 100 membros **realmente preparados**, 200 posições por pessoa. A capacidade máxima do modelo não é uma autorização para cadastrar mais slots. A criação de novos grupos além de 100, ou fichas além de 200 por membro, não é implementada automaticamente pelo bot.

As listagens usam o índice derivado do Sheets; ele não é reescrito como uma tabela canônica. O código valida sentinelas/IDs antes de operar, mas não garante que toda possível edição destrutiva do dono será identificada. Não mova células da estrutura.

Apps Script, Sheets e Discord têm cotas, limites de duração e rate limits. Não foram feitos testes de carga com 20.000 registros reais, dezenas de usuários simultâneos, imagens nativas em massa ou o plano Discloud do usuário. `RAM=256` é uma configuração inicial, não medição de consumo. Noventa segundos de sincronização é intervalo configurado, não prazo garantido de notificação.

## Documentação oficial consultada

- Webhooks, identificação de aplicação, avatar/nome e componentes: https://docs.discord.com/developers/resources/webhook
- discord.py 2.7.1: https://pypi.org/project/discord.py/
- Implementação oficial de Webhook.send e gerenciamento de views: https://github.com/Rapptz/discord.py/blob/v2.7.1/discord/webhook/async_.py
- Message Content Intent: https://discordpy.readthedocs.io/en/stable/intents.html
- Apps Script Web Apps e implantação: https://developers.google.com/apps-script/guides/web
- LockService: https://developers.google.com/apps-script/reference/lock/lock-service
- Propriedades do script: https://developers.google.com/apps-script/reference/properties/properties-service
- Sheets batchUpdate: https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets/batchUpdate
- Gatilhos instaláveis e gravações por API: https://developers.google.com/apps-script/guides/triggers/installable
- URLs de CellImage: https://developers.google.com/apps-script/reference/spreadsheet/cell-image
- Cotas de Apps Script: https://developers.google.com/apps-script/guides/services/quotas
- Configuração Discloud: https://docs.discloud.com/configurations/discloud.config

Consulta técnica: 19/10/2026. Revalidar versões e permissões ao atualizar a dependência ou o ambiente.
