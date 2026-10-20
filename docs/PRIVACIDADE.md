# Política de privacidade do Arquivista do Ciclo

Atualizada em 20/10/2026.

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

Situação e justificativa ficam nas consultas privadas da staff. O responsável pode ver e editar o nome do próprio personagem no formulário privado. A lista, a galeria e os avisos públicos mostram aparência, obra e responsável, sem esses campos internos.

Quando alguém anexa uma imagem ao cadastro, o bot reenvia o arquivo no canal de imagens que a staff escolheu, dentro do próprio servidor, e guarda o endereço dessa mensagem.

Para reconhecer quando alguém responde a uma mensagem da Amiya, o bot guarda o ID das próprias mensagens por 7 dias. Ele não guarda o texto dessas conversas.

## Para onde os dados vão

Os cadastros, o histórico e as configurações ficam no banco do bot, na hospedagem em que ele roda.

Quando a criação de planilhas está ativada, `/planilha criar` prepara um arquivo na conta Google do Arquivista. O e-mail informado no formulário privado recebe edição e pode ver e mudar os cadastros internos do servidor. O arquivo é privado; planilhas conectadas pelo método antigo continuam na conta do dono original. As edições pelo Sheets e pelo bot são sincronizadas, e os arquivos seguem as regras do Google.

Desconectar só desliga a sincronização. Para retirar acessos ou excluir uma planilha criada pelo Arquivista, fale comigo.

Se a staff ativar o backup, o bot envia cópias dos cadastros num canal do Discord restrito à equipe. Os arquivos incluem justificativas e nomes dos personagens no servidor. Os dados não são vendidos nem repassados a ninguém além dos serviços descritos aqui.

## Como ver e apagar

Use `AC:min` ou `/aparencias` com você no campo membro para consultar seus cadastros. Pelo `/editar`, você pode mudar o nome do personagem no servidor e a imagem. Para mudar outros campos ou remover uma ficha, fale com a staff.

`/remover` tira a ficha do arquivo, mas mantém o histórico para a staff. `/limpar` faz isso com todos os cadastros de uma pessoa, inclusive depois que ela sai do servidor.

Para excluir seus dados e o histórico, em um ou em todos os servidores, me chame. Se o bot sair de um servidor, os dados ficam guardados para o caso de ele voltar; o dono ou a staff também pode pedir a exclusão.

## Mudanças

Quando este texto mudar, a data do começo muda junto.
