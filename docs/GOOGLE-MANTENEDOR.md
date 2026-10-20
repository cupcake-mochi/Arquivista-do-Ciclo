# Conta Google do Arquivista · configuração única

Esta configuração é do mantenedor do bot, uma vez para a hospedagem. Donos de servidor só usam `/planilha criar`, informam o e-mail em privado e recebem a planilha pronta.

## Preparar a conta e o aplicativo

1. Crie uma conta Google dedicada ao Arquivista. Ela será dona dos arquivos, que usam seu armazenamento e os limites das APIs Google. Não use a conta pessoal que guarda documentos privados.
2. Num projeto do Google Cloud, ative **Google Drive API** e **Google Sheets API**.
3. Configure o aplicativo OAuth no Google Auth Platform com público externo e o escopo **`https://www.googleapis.com/auth/drive.file`**. Esse escopo permite administrar os arquivos criados pelo aplicativo; não é preciso pedir acesso ao Drive inteiro.
4. Crie um cliente OAuth do tipo **Aplicativo para computador** e baixe o JSON. Salve como `client_secret_arquivista.json`, dentro da pasta do projeto. Esse nome está ignorado pelo Git. Nunca publique o conteúdo.
5. Para os primeiros testes, inclua a conta dedicada como usuário de teste do aplicativo. Antes de manter a integração ligada permanentemente, passe o consentimento OAuth para **Em produção** e siga as exigências que o Google mostrar. Tokens de atualização de um aplicativo externo em modo de teste podem expirar em sete dias.

Não use uma conta de serviço comum para criar arquivos no Meu Drive: ela não tem armazenamento nem pode ser dona desses arquivos. O fluxo implementado usa a conta Google dedicada autorizada por OAuth.

## Autorizar na sua máquina

Com as dependências do projeto instaladas:

```sh
python configurar_google.py client_secret_arquivista.json
```

O assistente abre a página oficial do Google. Escolha a conta dedicada e conclua o consentimento pessoalmente. Ele usa um retorno local em `127.0.0.1`, estado aleatório e PKCE; o código da autorização não é registrado no terminal.

O resultado é salvo em **`.env.google`**, ignorado pelo Git e pelo pacote Discloud. Não imprime tokens nem altera o `.env` do Discord. Se precisar autorizar novamente, guarde o arquivo anterior num local privado e renomeie-o antes de executar o assistente. Em sistemas Unix, o arquivo é criado com permissão `0600`; no Windows, mantenha a pasta acessível somente à sua conta.

## Ativar na Discloud

No painel de variáveis da aplicação, cadastre os valores de `.env.google`:

- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REFRESH_TOKEN`

Use também uma **`AC_MASTER_KEY` estável, com pelo menos 32 caracteres**, para cifrar o e-mail de edição guardado no banco. Sem ela, a cifra depende do token Discord; se esse token mudar durante uma criação interrompida, será necessário recuperar a chave antiga para retomar o pedido.

Envie o pacote gerado por `python empacotar.py` e reinicie o bot. O diagnóstico informa se as três variáveis estão preenchidas; a autorização real é conferida quando uma operação Google é executada. O assistente e o JSON OAuth não vão para a hospedagem.

## Teste real antes de anunciar

1. No servidor de testes, `/planilha criar`: informe seu e-mail e confira acesso de editor e ausência de compartilhamento público.
2. Repita o comando e confirme que ele devolve o mesmo arquivo, inclusive após reiniciar o bot.
3. `/planilha membro`: selecione um membro real do servidor. Confira que nick como texto e pessoa que saiu são recusados.
4. Preencha uma posição vazia e aguarde cerca de cinco minutos; confira no bot. Edite pelo bot e confira a volta ao Sheets.
5. Preencha até 18 posições: a aba deve ter 40. Continue até 38: deve ter 60. Confira fórmula do visor, imagens, agrupamentos e a outra aba intacta. Teste também preencher as 20 posições manualmente antes de uma sincronização.
6. Desconecte e reconecte pelo comando; o arquivo deve ser preservado.

Os testes automáticos simulam a API e a grade. Não substituem a conferência de layout e permissões no Google real. **Nenhuma conta dedicada foi configurada nem este teste real foi executado nesta entrega.**

## Interrupções e manutenção

O progresso fica em `managed_sheets`, no mesmo SQLite do bot. Preserve esse banco e a chave mestra nas atualizações. Uma criação que perdeu a resposta é procurada pelo marcador privado do pedido no Drive; se o resultado continuar incerto, o bot não cria outra planilha. Nesse caso o mantenedor deve conferir o arquivo pela conta dedicada antes de corrigir o estado local. Não apague o pedido só para tentar de novo sem essa conferência.

O e-mail de edição é cifrado no banco. Repetir o comando não compartilha o arquivo com outro e-mail. Alterações de acesso posteriores são feitas no próprio Google Drive pelo responsável autorizado. Desconectar a planilha só desliga a sincronização: não apaga o arquivo nem revoga acessos.

O bot revalida estrutura e valores lidos antes de enviar um lote. O Sheets não oferece uma transação que bloqueie a edição humana durante toda a leitura e gravação: evite editar o mesmo campo nos dois lugares ao mesmo tempo. Nas mudanças detectadas em ambos os lados, o campo alterado no Discord tem prioridade; alterações em campos diferentes são conciliadas.

Planilhas antigas continuam pela ponte Apps Script. O novo comando não substitui uma conexão antiga silenciosamente. Para migrar, primeiro confira se todas as edições manuais entraram no banco; depois desconecte a antiga e use `/planilha criar`. A antiga continua guardada no Drive do seu dono.

## Fontes oficiais

- [Escopo drive.file](https://developers.google.com/workspace/drive/api/guides/api-specific-auth)
- [OAuth para aplicativos de computador](https://developers.google.com/identity/protocols/oauth2/native-app)
- [Expiração de tokens de atualização](https://developers.google.com/identity/protocols/oauth2#expiration)
- [Contas de serviço e propriedade de arquivos](https://developers.google.com/workspace/drive/api/guides/about-shareddrives)
- [Compartilhamento e papel de editor](https://developers.google.com/workspace/drive/api/guides/manage-sharing)
