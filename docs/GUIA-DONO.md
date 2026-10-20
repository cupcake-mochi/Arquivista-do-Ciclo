# Arquivista no seu servidor

Guia curto pra quem é dono ou gerencia um servidor e quer usar o Arquivista. Leva uns 10 minutos.

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
4. **Backup:** um canal que **só a staff vê** e a frequência. O bot recusa canal que algum cargo fora da staff consegue ver, porque o backup tem dados internos.

Tudo isso é opcional. Sem nada configurado o bot já cadastra e consulta.

## 3. Planilha (opcional)

A planilha mostra o arquivo de um jeito fácil de ler, uma guia por membro, e o que a staff mudar nela volta pro bot.

1. Crie uma planilha **nova e vazia** no Google Sheets.
2. Extensões → Apps Script. Apague o conteúdo e cole o `Planilha.gs`. Em **Serviços (+)**, adicione **Google Sheets API**. Salve.
3. Volte na planilha e recarregue. No menu **Arquivista → Instalar ou reinstalar**, informe o ID do servidor (botão direito no servidor → Copiar ID, com o Modo Desenvolvedor ligado) e autorize.
4. No Apps Script: **Implantar → Nova implantação → App da Web**, executar como **você**, acesso **Qualquer pessoa**. Copie o link que termina em `/exec`.
5. Na planilha: **Arquivista → Mostrar a chave da conexão** e copie.
6. No Discord: `/configurar` → **Conectar planilha**, cole o link e a chave.

"Qualquer pessoa" é sobre o link do script, não sobre a planilha: deixe a planilha restrita e compartilhe a edição só com a staff, porque quem edita a planilha muda cadastros. O script recusa qualquer pedido sem a assinatura do bot.

O script não precisa ser atualizado depois: melhorias na planilha chegam pelo bot.

## 4. Contar pro servidor

Mande os membros usarem `/guia`, que explica tudo em páginas. O resumo:

- `/registrar` cadastra a aparência de alguém;
- `/aparencias`, `/obra` e `AC:gal` consultam;
- `/editar` muda nome no servidor e imagem.

A staff usa `/situacao`, `/transferir`, `/remover`, `/limpar`, `/apelido` e `/historico`. `/diagnostico` mostra se está tudo funcionando.

## Se algo der errado

- **Os comandos de barra não aparecem:** o Discord pode levar até 1 hora na primeira vez. `AC:ajuda` funciona na hora.
- **"Esse painel expirou":** o bot foi atualizado; abra o comando de novo.
- **A planilha parou de atualizar:** veja o `/diagnostico`. Ele diz o motivo (chave errada, script antigo, linha inserida no meio das fichas...).
- **Precisa voltar no tempo:** `/restaurar` com o `.json` de um backup.

Dados e regras: [PRIVACIDADE.md](PRIVACIDADE.md) e [TERMOS.md](TERMOS.md).
