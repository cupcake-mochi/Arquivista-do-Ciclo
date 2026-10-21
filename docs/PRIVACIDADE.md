# Política de privacidade do Arquivista do Ciclo

Atualizada em 21/10/2026.

Sou o Mizuki, mantenedor do Arquivista do Ciclo, o bot da Amiya. Para tirar dúvidas sobre seus dados ou pedir a exclusão, me chame no servidor da guilda.

## O que o bot lê

O bot vê as mensagens dos canais em que está, mas só usa as que começam com `AC:`, que mencionam a Amiya ou que respondem a uma mensagem dela. O resto não é guardado nem enviado para lugar nenhum. Ele não lê mensagem privada, não entra em chamada de voz e não usa inteligência artificial.

## O que fica guardado

Para cada servidor, o bot guarda:

- cada cadastro: aparência, obra, nome no servidor, situação, justificativa da staff, link da imagem, data do cadastro e o ID do Discord de quem é o responsável;
- o histórico de cada alteração, com o antes e o depois e o ID do Discord de quem fez;
- a confirmação de cada gravação, para que um clique repetido não cadastre duas vezes;
- a configuração do servidor: cargos de staff e canais escolhidos;
- na criação automática da planilha, o identificador e o endereço do arquivo, o andamento da criação e o e-mail Google informado para receber edição. Esse e-mail fica cifrado no banco e é enviado ao Google para conceder acesso ao arquivo.

O nome do personagem no servidor aparece nas listas e na galeria, junto da aparência, da obra e do responsável. O responsável pode editar esse nome no formulário privado. Situação e justificativa continuam restritas às consultas privadas da staff. Os avisos públicos não incluem o nome no servidor, a situação nem a justificativa.

Quando alguém anexa uma imagem ao cadastro, o bot reenvia o arquivo no canal de imagens que a staff escolheu, dentro do próprio servidor, e guarda o endereço dessa mensagem.

Para reconhecer quando alguém responde a uma mensagem da Amiya, o bot guarda o ID das próprias mensagens por 7 dias. Ele não guarda o texto dessas conversas.

## Para onde os dados vão

Os cadastros, o histórico e as configurações ficam no banco do bot, na hospedagem em que ele roda.

Quando a criação de planilhas está ativada, `/planilha criar` prepara um arquivo na conta Google do Arquivista. O e-mail informado no formulário privado recebe edição e pode ver e mudar os cadastros internos do servidor. O arquivo é privado; planilhas conectadas pelo método antigo continuam na conta do dono original. As edições pelo Sheets e pelo bot são sincronizadas, e os arquivos seguem as regras do Google.

Desconectar só desliga a sincronização. Para retirar acessos ou excluir uma planilha criada pelo Arquivista, fale comigo.

Se a staff ativar o backup, o bot envia cópias dos cadastros num canal do Discord restrito à equipe. Os arquivos incluem justificativas e nomes dos personagens no servidor. Os dados não são vendidos nem repassados a ninguém além dos serviços descritos aqui.

## Como ver e apagar

Use `AC:min` ou `/aparencias` com você no campo membro para consultar seus cadastros. Pelo `/editar`, você pode mudar o nome do personagem no servidor e a imagem. Use `/remover` para apagar um cadastro seu, com confirmação; o histórico fica preservado para a staff. Para mudar outros campos ou alterar cadastros de outra pessoa, fale com a staff.

`/remover` tira a ficha do arquivo, mas mantém o histórico para a staff. `/limpar` faz isso com todos os cadastros de uma pessoa, inclusive depois que ela sai do servidor.

Para excluir seus dados e o histórico, em um ou em todos os servidores, me chame. Se o bot sair de um servidor, os dados ficam guardados para o caso de ele voltar; o dono ou a staff também pode pedir a exclusão.

## Idioma por servidor e por arquivo
Use /language ou /idioma para escolher português ou inglês. Dono, Administrador, Gerenciar servidor e os cargos de staff cadastrados podem mudar essa preferência. Ela vale só neste servidor e é independente das Guias. Os nomes dos comandos nativos seguem o idioma do seu aplicativo Discord; as respostas seguem o idioma do servidor. Conteúdo digitado pelos membros não é traduzido. Cada planilha gerenciada recebe seu idioma ao ser criada: mudar a preferência não converte arquivos existentes, não altera seus acessos e não exige novas permissões Google. Não mude a localidade do arquivo manualmente; se isso ocorrer, a sincronização avisa para restaurá-la.
O bot guarda a preferência do servidor e o idioma de criação de cada arquivo junto às demais configurações. Situações e backups JSON mantêm os códigos internos canônicos, sem mudar quem pode ver os dados.

## Mudanças

Quando este texto mudar, a data do começo muda junto.

---

# Arquivista do Ciclo privacy policy — English
Updated October 21, 2026. Maintainer: Mizuki. Contact me through the guild server for data questions or deletion requests.
Messages and records
The bot processes AC: commands, mentions of Amiya and replies to her messages. Other messages are not retained or forwarded. It does not read direct messages, join voice calls or use artificial intelligence.
For each server it stores appearance records, source works, server character names, internal statuses and staff reasons, image URLs, registration dates and responsible members’ Discord IDs. It also stores before-and-after audit events with the actor’s ID, confirmation identifiers to prevent duplicate writes, staff roles and configured channels. Managed-spreadsheet records include the file ID and URL, creation progress and the Google email supplied to receive edit access. That email is encrypted in the bot database and sent to Google to grant access.
Public lists and galleries show appearance, source work, responsible member and server character name. Internal statuses and reasons remain in private staff views. Public notices omit server character name, status and reason. Uploaded registration images are copied into the server’s configured image channel; the message URL is retained. IDs of the bot’s own messages are retained for seven days to recognize replies, without storing conversation text.
Language and files
Use /language or /idioma to choose Portuguese or English. The server owner, administrators, members with Manage Server and configured staff roles can change this setting. It applies only to this server and is independent of Guias do Ciclo. Native command names follow the Discord client language; replies follow the server setting. Member-written names and content are not translated. Each managed spreadsheet keeps the language assigned when it was created. Changing the server setting does not convert existing files, change sharing or require new Google permissions. Do not manually change the spreadsheet locale: synchronization will ask you to restore it.
The bot stores the server language and each managed file’s creation language alongside its configuration. Internal record status codes and restorable JSON backups retain their canonical format; translated labels do not change record ownership or staff access.
Services and sharing
The bot database is held on its hosting service. Where automatic spreadsheet creation is enabled, the bot creates a private file in the Arquivista Google account. The email entered in the private form receives edit access to internal server records. Files connected through the old method remain in their original owner’s account. Bot and Sheets edits are synchronized and Google’s terms apply.
Disconnecting stops synchronization; it does not delete the file or revoke Google access. Contact the maintainer to remove access or delete a managed file. Staff can enable backups in a staff-only Discord channel. Backup files include staff reasons and server character names. Data is not sold or shared beyond the services described here.
Access and deletion
Use AC:min or the appearance-list command with yourself selected to view your records. You can edit your server character name and image and remove your own record after confirmation. Other fields and other people’s records require staff. Removing a record, including through staff bulk cleanup, preserves its audit history.
For deletion of your personal data and history in one or all servers, contact the maintainer. Data is retained if the bot leaves a server so it can resume if invited back; the owner or staff can request deletion.
The date changes when this policy is updated.
