# Política de privacidade do Arquivista do Ciclo

Atualizada em 20/10/2026.

Eu sou o Mizuki e mantenho o Arquivista do Ciclo, o bot da Amiya. Aqui está o que ele faz com os dados de quem usa o arquivo de aparências. Qualquer pedido sobre isso, me chame no servidor da guilda.

## O que o bot lê

O bot vê as mensagens dos canais em que está, mas só usa as que começam com `AC:`, que mencionam a Amiya ou que respondem a uma mensagem dela. O resto não é guardado nem enviado para lugar nenhum. Ele não lê mensagem privada, não entra em chamada de voz e não usa inteligência artificial.

## O que fica guardado

Separado por servidor:

- cada cadastro: aparência, obra, nome no servidor, situação, justificativa da staff, link da imagem, data do cadastro e o ID do Discord de quem é o responsável;
- o histórico de cada alteração, com o antes e o depois e o ID do Discord de quem fez;
- a confirmação de cada gravação, para que um clique repetido não cadastre duas vezes;
- a configuração do servidor: cargos de staff e canais escolhidos.
- na criação automática da planilha, o identificador e o endereço do arquivo, o andamento da criação e o e-mail Google informado para receber edição. Esse e-mail fica cifrado no banco e é enviado ao Google para conceder acesso ao arquivo.

Situação e justificativa são reservadas à staff. O nome no servidor aparece no atendimento privado autorizado, inclusive para o próprio responsável pelo cadastro. A lista, a galeria e os avisos públicos mostram só aparência, obra e responsável.

Quando alguém anexa uma imagem ao cadastro, o bot reenvia o arquivo no canal de imagens que a staff escolheu, dentro do próprio servidor, e guarda o endereço dessa mensagem.

Para saber quando alguém responde a ela, o bot guarda o ID das próprias mensagens por 7 dias. O texto dessas conversas não é guardado.

## Para onde os dados vão

Os dados ficam num banco do próprio bot, na hospedagem em que ele roda. Quando a criação automática estiver ativada pelo mantenedor, `/planilha criar` cria uma planilha na conta Google do Arquivista e concede edição ao e-mail informado em privado. O arquivo pertence à conta do Arquivista, e quem recebe edição pode consultar e alterar os cadastros internos daquele servidor. A planilha não é tornada pública. Planilhas conectadas pelo método anterior continuam pertencendo ao dono original. As edições feitas na planilha e pelo bot são sincronizadas nos dois sentidos e os arquivos seguem as regras do Google. Desconectar a sincronização não apaga o arquivo nem revoga as permissões: para retirar acessos ou excluir a planilha criada pelo Arquivista, fale comigo. Se a staff ligar o backup automático, o bot manda periodicamente uma cópia dos cadastros do servidor (inclusive justificativas e nomes no servidor) num canal do Discord escolhido por ela e fechado para @everyone. Os dados não são vendidos nem repassados a mais ninguém.

## Como ver e apagar

`AC:min` (ou `/aparencias` com você em membro) mostra os seus cadastros. Para mudar ou remover um cadastro, fale com a staff do servidor; remover tira o cadastro do arquivo, mas o histórico continua para a staff conferir. A staff também pode apagar todos os seus cadastros de uma vez com `/limpar`, mesmo depois que você saiu do servidor; o histórico fica para a staff. Para apagar tudo o que é seu, histórico incluído, num servidor ou em todos, me peça que eu apago. Quando o bot sai de um servidor, os dados dele ficam guardados para o caso de voltar; a staff ou o dono pode me pedir para apagar.

## Mudanças

Quando este texto mudar, a data do começo muda junto.
