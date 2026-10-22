# Arquivista no seu servidor

Para quem é dono ou gerencia um servidor: veja como convidar a Amiya, configurar os canais e receber a planilha pronta.

## 1. Convidar o bot

Abra o link de convite do Arquivista e escolha o servidor. Deixe marcadas as permissões que ele pede:

| Permissão | Pra quê |
|---|---|
| Ver canais, Enviar mensagens, Enviar mensagens em tópicos | responder os comandos |
| Incorporar links | as listas e a galeria são embeds |
| Anexar arquivos | backup e imagens enviadas por anexo |
| Ler histórico de mensagens | não repetir aviso depois de uma queda |
| Gerenciar webhooks | as respostas saírem com nome e foto da Amiya |

Sem **Gerenciar webhooks** tudo funciona, mas as mensagens saem com o ícone do bot. O `/diagnostico` avisa quando ela falta no canal.

## 2. Configurar

Use `/configurar` (só o dono, quem é Administrador ou quem tem Gerenciar Servidor vê):

1. **Cargos de staff:** quem pode mudar situação, transferir, remover cadastros de outras pessoas, limpar e ver o histórico. Dono e administradores já contam.
2. **Canal de histórico:** cada cadastro, mudança e remoção gera um aviso aqui. Não mostra justificativa nem situação.
3. **Canal de imagens:** onde o bot guarda as imagens enviadas por anexo. Sem ele, só dá pra usar link de imagem.
4. **Backup:** escolha um canal que **só a staff vê** e a frequência dos envios. Os arquivos incluem justificativas e nomes dos personagens no servidor, então o bot recusa canais com acesso de pessoas fora da staff. Use **Fazer backup agora** para conferir o envio e guarde o `.json` para recuperar os cadastros. Esse arquivo não inclui todas as configurações e o histórico do bot; o mantenedor também precisa guardar uma cópia completa da hospedagem.

Tudo isso é opcional. Sem nada configurado o bot já cadastra e consulta.

## Idioma

Antes de criar a planilha, use `/language` ou `/idioma` e escolha **English** ou **Português do Brasil**. Sem escolha, o comando só consulta. Os cargos de staff configurados também podem trocar o idioma; isso não lhes concede permissão para configurar ou compartilhar uma planilha.

As respostas novas do bot seguem a escolha. Uma planilha nova é montada nesse idioma. Se o arquivo já existe, ele mantém o idioma original e continua conectado; o bot não o traduz nem cria outro. Os nomes dos comandos no menu nativo seguem o idioma do seu Discord. A escolha é independente da feita nas Guias.

## Idioma do bot e das planilhas
Use /language ou /idioma para escolher português ou inglês. Dono, Administrador, Gerenciar servidor e os cargos de staff cadastrados podem mudar essa preferência. Ela vale só neste servidor e é independente das Guias. Os nomes dos comandos nativos seguem o idioma do seu aplicativo Discord; as respostas seguem o idioma do servidor. Conteúdo digitado pelos membros não é traduzido. Cada planilha gerenciada recebe seu idioma ao ser criada: mudar a preferência não converte arquivos existentes, não altera seus acessos e não exige novas permissões Google. Não mude a localidade do arquivo manualmente; se isso ocorrer, a sincronização avisa para restaurá-la.

## 3. Planilha (opcional)

Você pode preencher as fichas na planilha ou pelo Discord. O que mudar em um aparece no outro.

1. Use **`/planilha criar`**, ou `/configurar` → **Planilha** → **Criar ou retomar**.
2. Informe seu **e-mail Google no formulário privado**. Esse e-mail receberá edição e verá os cadastros internos do servidor.
3. Abra o link que o bot entregar. A planilha já estará montada e conectada; a sua aba terá posições vazias para preencher.

A planilha fica na conta Google do Arquivista, e você recebe acesso de editor. Se usar `/planilha criar` outra vez, recebe o mesmo arquivo. Desconectar só desliga a sincronização: a planilha e os acessos continuam no Google. Para conectar novamente, use o comando de criação.

### Trazer cadastros de outra planilha

Se este servidor ainda não tem cadastros nem planilha registrada, use **`/planilha importar`**. Informe o link da origem e o e-mail Google que poderá editar a **cópia nova**. Confira a autorização, os totais e o destino antes de confirmar.

A origem precisa ter o formato de cadastros do Arquivista e estar autorizada para o aplicativo Google. Se o bot pedir um código, quem já pode editar a origem deve colocá-lo em uma célula vazia e dar a esse intervalo de uma única célula o nome `ARQUIVISTA_AUTORIZACAO`. Essa pessoa deve conferir o destino antes de autorizar. O código vale por dez minutos e pode ser removido, junto com o intervalo, após a conclusão. O bot não concede edição no original. Se aparecer falta de acesso Google, peça ajuda ao mantenedor; tornar o link público não resolve essa autorização.

A cópia recebe IDs novos e sincronização própria. Responsáveis, datas e campos dos cadastros são mantidos; abas extras, scripts, imagens sem link e histórico antigo não são copiados. [Passo a passo e limites](IMPORTAR-PLANILHA.md).

Para recuperar o link depois, use **`/planilha abrir`** ou **`AC:planilha`** e clique em **Abrir planilha** no painel privado.

Quer preencher uma ficha para outra pessoa? Use **`/planilha membro` e selecione o @membro do servidor**. Digitar apenas um apelido não funciona: escolha a pessoa na lista do Discord. Ela precisa estar no servidor. Se cadastrar pelo bot, a aba é criada junto com a ficha.

Preencha as **posições prontas** na aba do membro: aparência, obra, situação e os campos opcionais. As mudanças feitas no Sheets entram no bot em cerca de **5 minutos**. O bot valida os dados e mostra recusas no `/diagnostico`. Para remover um cadastro, use `/remover`; apagar uma linha não remove o cadastro do bot.

Cada aba começa com **20 posições** e ganha mais **20** quando restam apenas duas livres. Preserve as fórmulas e as colunas de identificação; não insira nem apague linhas no meio das fichas.

Compartilhe edição **só com a staff**: quem edita a planilha pode mudar os cadastros do servidor. O link não torna o arquivo público.

Se a criação automática aparecer como indisponível, ela ainda precisa ser ativada pelo mantenedor. Você não precisa instalar código: o bot continua cadastrando e consultando normalmente. Planilhas conectadas pelo método anterior continuam funcionando.

## 4. Orientar os membros

Indique `/guia` para quem vai usar pela primeira vez e `/ajuda` para consultar os comandos. Para começar:

- `/registrar` cadastra a aparência de alguém;
- `/aparencias`, `/obra` e `AC:gal` consultam;
- `/editar` muda nome no servidor e imagem.
- `/remover` remove um cadastro próprio, com confirmação; o histórico fica com a staff.

A staff usa `/situacao`, `/transferir`, `/remover`, `/limpar`, `/apelido` e `/historico`. `/diagnostico` mostra se está tudo funcionando.

## Se algo der errado

- **Os comandos de barra não aparecem:** o Discord pode levar até 1 hora na primeira vez. `AC:ajuda` funciona na hora.
- **"Esse painel expirou":** o bot foi atualizado; abra o comando de novo.
- **A planilha parou de atualizar:** veja o `/diagnostico`. Ele diz o motivo (chave errada, script antigo, linha inserida no meio das fichas...).
- **Precisa recuperar os cadastros:** anexe o `.json` ao `/restaurar` e confira o resumo antes de confirmar. Ele substitui os cadastros atuais pelos do backup.

Dados e regras: [política de privacidade](https://docs.google.com/document/d/1nMsutdyyrtb-YKCKziW3SmDY3ViKN31yO1OOW3zSRcw/view) e [termos de uso](https://docs.google.com/document/d/1uZlohyKEn7eOlM1wP5TbSeDBm_PkpLc13YnGmPYpZx8/view).

---

# Set up Arquivista in your server — English
Invite and permissions
Invite Arquivista using its invitation link. Keep its requested channel permissions. Manage Webhooks allows messages to use Amiya’s picture; without it, the bot still works with its own icon. The private diagnostic command identifies missing webhook permission.
Configure your server
Use the configuration command as server owner, administrator or a member with Manage Server. Choose staff roles, a history channel, an image channel and optionally backups and a spreadsheet. Staff roles can manage internal statuses, transfers, other members’ records, cleanup and history; they do not become Discord administrators.
The history channel receives change notices without internal statuses or reasons. The image channel stores uploaded registration images; keep those messages. Backups must go to a channel restricted to authorized staff because they include internal reasons and server character names. Use Back up now to check delivery. A JSON record backup does not include all settings or full audit history; the maintainer must also retain full hosting backups.
Language
Use /language or /idioma to choose Portuguese or English. The server owner, administrators, members with Manage Server and configured staff roles can change this setting. It applies only to this server and is independent of Guias do Ciclo. Native command names follow the Discord client language; replies follow the server setting. Member-written names and content are not translated. Each managed spreadsheet keeps the language assigned when it was created. Changing the server setting does not convert existing files, change sharing or require new Google permissions. Do not manually change the spreadsheet locale: synchronization will ask you to restore it.
Optional spreadsheet
Use /spreadsheet create (Portuguese: /planilha criar), or the configuration panel’s spreadsheet option, then Create or resume. Enter the authorized editor’s Google email in the private form. That address receives access to internal server data. Open the supplied link: the file is already prepared and connected. If automatic creation is unavailable, contact the maintainer and continue registering through the bot.
Repeating creation resumes or opens the same managed file. To retrieve the link, open the spreadsheet command or AC:spreadsheet. Disconnecting only stops synchronization; the file and Google access remain. Use the creation flow to reconnect.
To import records from an existing compatible spreadsheet, use /spreadsheet import in a destination server without records or a registered file. Supply the source URL and the authorized editor’s email for the new independent copy. The source must be authorized for the Google application and by its responsible manager or existing editor. Review the destination and record totals before confirming. Only the new copy receives edit access; the original remains unchanged. Record owners and dates are preserved, IDs are new, and previous audit history, custom tabs, scripts and images without URLs are not copied. Contact the maintainer if Google application access is missing; making the source public does not authorize it.
To prepare another member’s tab, use the spreadsheet member option and select that person from Discord’s member list. Typing a nickname alone does not select a member. Registering through the bot also creates the needed tab.
Fill the prepared slots with appearance, source work, status and optional fields. Sheets edits reach the bot in about five minutes after validation. Check the private diagnostic panel for rejected changes. Use the remove command to delete a record: clearing a row does not remove it from the bot.
Tabs start with 20 slots and expand by 20 when only two are free. Preserve formulas and identifier columns; do not insert or delete rows inside record blocks. English files display ISO dates. Give edit access only to staff. Previously connected Portuguese files remain compatible.
Guide your members
AC:guide introduces the bot; AC:help lists commands. AC:register opens registration, AC:appearances searches, AC:gallery shows images and AC:edit changes server character name or image. Members can remove their own records after confirmation.
Staff can manage statuses, transfer or remove records, clear a former member’s records, define source-work aliases and inspect private history. Diagnostics reports bot and spreadsheet status.
Troubleshooting
Native slash commands may take time to appear; prefix commands are available immediately. If a panel expires after an update, reopen the command. Check diagnostics for synchronization errors. To restore a record backup, attach the JSON to the restore command and review the summary before confirming; it replaces current records with those in the backup.
Privacy and terms are linked in help and the bot profile.
