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

1. **Cargos de staff:** quem pode mudar situação, transferir, remover, limpar e ver o histórico. Dono e administradores já contam.
2. **Canal de histórico:** cada cadastro, mudança e remoção gera um aviso aqui. Não mostra justificativa nem situação.
3. **Canal de imagens:** onde o bot guarda as imagens enviadas por anexo. Sem ele, só dá pra usar link de imagem.
4. **Backup:** escolha um canal que **só a staff vê** e a frequência dos envios. Os arquivos incluem justificativas e nomes dos personagens no servidor, então o bot recusa canais com acesso de pessoas fora da staff. Use **Fazer backup agora** para conferir o envio e guarde o `.json` para recuperar os cadastros. Esse arquivo não inclui todas as configurações e o histórico do bot; o mantenedor também precisa guardar uma cópia completa da hospedagem.

Tudo isso é opcional. Sem nada configurado o bot já cadastra e consulta.

## 3. Planilha (opcional)

Você pode preencher as fichas na planilha ou pelo Discord. O que mudar em um aparece no outro.

1. Use **`/planilha criar`**, ou `/configurar` → **Planilha** → **Criar ou retomar**.
2. Informe seu **e-mail Google no formulário privado**. Esse e-mail receberá edição e verá os cadastros internos do servidor.
3. Abra o link que o bot entregar. A planilha já estará montada e conectada; a sua aba terá posições vazias para preencher.

A planilha fica na conta Google do Arquivista, e você recebe acesso de editor. Se usar `/planilha criar` outra vez, recebe o mesmo arquivo. Desconectar só desliga a sincronização: a planilha e os acessos continuam no Google. Para conectar novamente, use o comando de criação.

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

A staff usa `/situacao`, `/transferir`, `/remover`, `/limpar`, `/apelido` e `/historico`. `/diagnostico` mostra se está tudo funcionando.

## Se algo der errado

- **Os comandos de barra não aparecem:** o Discord pode levar até 1 hora na primeira vez. `AC:ajuda` funciona na hora.
- **"Esse painel expirou":** o bot foi atualizado; abra o comando de novo.
- **A planilha parou de atualizar:** veja o `/diagnostico`. Ele diz o motivo (chave errada, script antigo, linha inserida no meio das fichas...).
- **Precisa recuperar os cadastros:** anexe o `.json` ao `/restaurar` e confira o resumo antes de confirmar. Ele substitui os cadastros atuais pelos do backup.

Dados e regras: [política de privacidade](https://docs.google.com/document/d/1nMsutdyyrtb-YKCKziW3SmDY3ViKN31yO1OOW3zSRcw/view) e [termos de uso](https://docs.google.com/document/d/1uZlohyKEn7eOlM1wP5TbSeDBm_PkpLc13YnGmPYpZx8/view).
