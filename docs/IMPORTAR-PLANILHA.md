# Importar uma planilha existente

Versão 1.2.0 publicada e validada em 22/10/2026. Importação, cancelamento, permissões e sincronização validados na interface real do Discord e no Google, incluindo uma origem externa selecionada pelo Picker. Documentos públicos atualizados. O fechamento e a limpeza estão registrados ao final desta página.

## Como usar

1. No **servidor de destino**, use `/planilha importar` ou abra `AC:planilha` → **Importar existente**. Exige dono, Administrador ou Gerenciar servidor, com acesso conferido novamente na confirmação.
2. Informe o link da planilha de origem e o e-mail Google que receberá **edição somente na cópia nova**, em formulário privado.
3. Autorize a origem. Se o arquivo foi criado pelo aplicativo e você ainda gerencia o servidor de origem, a permissão é revalidada pelo Discord. Caso contrário, peça ao responsável que **já pode editar** a origem para colar o código do painel em uma célula vazia e criar o intervalo nomeado `ARQUIVISTA_AUTORIZACAO` para essa única célula. Ele deve conferir o servidor de destino antes de aprovar. O bot não concede edição na origem.
4. Escolha **Validar arquivo**. Confira na prévia arquivo, servidor, quantidade de cadastros e e-mail do editor da cópia.
5. Escolha **Importar e criar cópia**. A nova planilha será privada e pertencente à conta do Arquivista. O e-mail informado recebe edição nessa nova planilha. Use `/planilha abrir` para reencontrá-la.

O responsável pode remover o código e o intervalo de autorização da origem após a conclusão. O código expira em dez minutos, é de uso único e fica associado ao arquivo, solicitante e destino; não é uma chave permanente de conexão.

## O que é copiado

Cadastros válidos dos blocos de membros: aparência, obra, nome no servidor, situação, justificativa, link da imagem, data e ID Discord do responsável. Cada cadastro recebe um ID novo e revisão inicial 1. A importação registra um evento próprio com o responsável pela operação, sem inventar o histórico anterior nem publicar os cadastros como eventos novos no canal de histórico.

O arquivo novo usa o idioma escolhido no **servidor de destino**, sem traduzir nomes, obras ou justificativas. A localidade da origem precisa ser Brasil ou Estados Unidos para leitura correta das situações e datas. Datas desconhecidas continuam vazias.

É uma **nova planilha do Arquivista com os dados importados**, não uma clonagem integral do arquivo. Layout personalizado, abas extras, scripts, histórico antigo, imagens inseridas diretamente nas células e outros elementos fora dos campos de cadastro não são copiados. Links de imagem são preservados; sua disponibilidade continua dependendo de onde estão hospedados. A sincronização da origem permanece separada.

## Proteções e limites

- Não altera o conteúdo, o proprietário, os editores ou a conexão da origem; todas as chamadas do bot à origem são de leitura.
- O destino precisa estar sem cadastros e sem planilha registrada. Não substitui uma planilha desconectada já registrada nem faz fusão automática.
- Link conhecido ou acesso público não comprovam autorização de importação. A prévia com dados só aparece após a autorização da origem.
- Revalida permissão da gerência, autorização da origem, estrutura e conteúdo antes da confirmação. Mudança nos dados cancela a prévia; faça outra conferência.
- Importação e reserva da cópia são gravadas na mesma transação SQLite. Uma falha posterior no Google pode ser retomada com `/planilha criar`, sem importar novamente ou criar arquivos duplicados. Não remova o banco nem o pedido pendente.
- Até 5.000 cadastros, 200 abas e um milhão de células nas onze colunas lidas. Acima disso, a operação é recusada integralmente; não há truncamento silencioso.
- Estruturas deslocadas, IDs duplicados, responsáveis inválidos, datas ilegíveis e demais registros inválidos são recusados antes da importação.
- Não oferece bloqueio transacional do mouse no Sheets: evite editar a origem durante a conferência.

## Quando o aplicativo não consegue abrir a origem

O escopo atual é `drive.file`. Ele permite arquivos criados pelo aplicativo e os arquivos explicitamente selecionados para o aplicativo; compartilhar um link ou deixar o arquivo público não basta.

Para uma origem ainda não autorizada, o **mantenedor** deve ativar **Google Picker API** no mesmo projeto Google e, na máquina que já guarda as credenciais privadas da conta dedicada, executar:

```sh
python autorizar_arquivo_google.py 'https://docs.google.com/spreadsheets/d/ID/edit'
```

O responsável pelo original precisa ter dado à conta dedicada acesso de leitura e permissão de cópia. O mantenedor seleciona a conta dedicada e **somente o arquivo indicado** na página oficial do Google. O assistente usa PKCE, retorno local e compara a conta selecionada com a da autorização já usada pelo bot. Não amplia escopos, não adiciona editores, não imprime tokens nem substitui `.env.google`; verifica que o refresh token atual já consegue acessar o arquivo selecionado.

Esta etapa não cria a cópia nem substitui a autorização de origem e a confirmação no Discord. Não entregue credenciais do mantenedor a donos de servidores. O assistente não vai para o ZIP de produção.

Fontes: [escopo drive.file](https://developers.google.com/workspace/drive/api/guides/api-specific-auth) e [Picker para aplicativos de computador](https://developers.google.com/workspace/drive/picker/guides/desktop-mobile-picker).

## Validação e publicação

A suíte automática usa Google e Discord simulados. O fechamento offline abaixo foi seguido pela validação real registrada ao final desta página. A operação por código de origem, a criação da cópia e o Google Picker de uma origem externa passaram pela interface real. Os resultados abaixo distinguem cada ensaio; o teste externo foi feito depois do primeiro fechamento.

### Resultado offline — 22/10/2026

- Base remota conferida: `main` em `8ae5be3f4a2ba549c293bf613e2bab7e7121edf8`. Branch de implementação: `codex/conectar-planilha-existente`.
- 182 testes Python aprovados, incluindo 33 novos testes de importação e autorização Google; 29 testes JavaScript da ponte e 7 do script da planilha aprovados. O cenário gerado pelo modelo Python também foi aceito pelo script.
- Casos novos cobrem autorização antes da prévia, direitos revogados, código incorreto ou expirado, isolamento entre servidores, original sem escritas, edição somente na cópia, mudança da origem, destino ocupado, registros sem ID, limites sem truncamento, falha com rollback, retomada após resposta Google perdida, cliques repetidos e cancelamento após confirmação.
- Textos dos novos formulários, botões, erros e prévia conferidos em português e inglês. Catálogo dos textos novos completo.
- ZIP regenerado com 29 arquivos, todos comparados aos fontes; sem banco, credenciais ou assistentes de autorização. Nesse fechamento inicial, `MANIFESTO_SHA256.json` descrevia o pacote preparado com `live_deployment_audited: false`; a auditoria posterior está registrada abaixo.
- Até esse fechamento offline, não havia chamadas pagas a modelos, envio ao Discord, publicação na Discloud ou modificação em arquivos Google reais. As operações posteriores estão registradas abaixo.

### Retomada e critérios de liberação

1. Continuar a branch desta entrega e conferir o estado remoto da PR antes de editar. Não usar o manifesto preparado como prova de publicação.
2. Usar uma origem sintética em formato Arquivista, com dois responsáveis, situações diferentes, justificativa fictícia, uma data vazia e um link de imagem. Fazer backup do banco de teste e registrar as permissões e os dados da origem antes da operação.
3. Para uma origem externa, ativar Google Picker API no projeto atual e executar o assistente na máquina das credenciais privadas. Conferir a seleção da conta dedicada e do único arquivo; não ampliar o escopo ou publicar credenciais.
4. No Discord, comprovar recusa de membro comum e de gerência sem autorização sobre a origem. A prévia não pode mostrar nome, contagens ou conteúdo dos cadastros antes da autorização. Conferir também recusa de destino ocupado.
5. Autorizar a origem sintética, conferir a prévia, cancelar e confirmar que nada foi criado. Abrir outro pedido e importar. Conferir dono do novo arquivo, editor correto, ausência de acesso público, responsáveis e datas preservados e IDs novos.
6. Alterar um cadastro pelo bot e outro pelo Sheets da cópia; aguardar a sincronização e conferir a origem e o outro servidor sem alterações. Retirar permissão do solicitante durante uma nova prévia deve impedir a confirmação.
7. Conferir o formulário e as mensagens em inglês, sem traduzir os dados dos membros. Se houver falha Google após a gravação local, `/planilha criar` deve retomar o único arquivo reservado.
8. Antes de publicar, atualizar os documentos públicos do dono, privacidade e termos com as versões revisadas neste repositório. Guardar o backup da hospedagem, preservar banco e variáveis, publicar o ZIP conferido e conferir `/diagnostico` e a versão em execução. Só então registrar implantação e auditoria reais no manifesto.


### Validação real e instalação — 22/10/2026

A pedido do usuário, foi usada a sessão autenticada do Discord e da Discloud no navegador do aplicativo. A versão `1.2.0` correspondente ao runtime `4710955` foi instalada no app **Arquivista do Ciclo**, ID `1792461187549`, após backup manual baixado e verificado. Não houve merge da PR nesta etapa.

**Produção conferida pelo console, somente leitura:** 29 arquivos iguais aos fontes do pacote, banco com integridade `ok`, 19 cadastros e três conexões gerenciadas idênticos à referência anterior. O ZIP não levou banco nem credenciais. O console foi desconectado ao final. O manifesto passou a registrar a auditoria física dessa instalação; isso não significa que os testes de interface pendentes foram concluídos.

**Discord real:** `AC:diagnostico`, `AC:planilha`, abertura do painel privado, botão **Importar existente**, formulário e envio funcionaram. Uma tentativa no servidor `1357866906341736488` foi recusada porque existe uma planilha gerenciada anterior, embora a sincronização esteja desligada. O arquivo e a reserva anteriores foram preservados; não se deve apagar esse vínculo para destravar um teste. Um painel emitido antes da reinicialização também respondeu com a orientação de reabrir o comando.

**Google real com SQLite isolado e solicitante Discord simulado:** origem sintética com três cadastros, dois responsáveis, situações diferentes e uma data vazia. A autorização sem código atual foi recusada; código correto no intervalo de célula única foi aceito. A importação gerou outro arquivo, com três IDs novos, responsáveis e datas preservados. Apenas a cópia recebeu edição para o e-mail autorizado pelo usuário, sem acesso público. Os cadastros e permissões da origem permaneceram iguais. Os cadastros não foram colocados no banco de produção.

A sincronização real também foi conferida nos dois sentidos pelo código do bot: mudança no Sheets entrou no SQLite isolado, e edição pelo módulo de cadastros voltou à cópia. Nenhum modelo de linguagem foi chamado. A cópia foi aberta no navegador como o usuário autorizado e está editável.

### Fechamento da interface real — 22/10/2026

Após autorização explícita do usuário para criar o servidor temporário e convidar a conta secundária, foi usado **QA Arquivista - Importação - 22-10**, com dados inteiramente fictícios. O bot foi adicionado sem Administrador. Nenhum acesso da conta secundária foi elevado.

- **Autorização:** código ausente ou de um pedido anterior recusado antes da prévia; o responsável pela origem sintética colocou o código atual na célula vazia de autorização. Os cadastros e as permissões da origem ficaram iguais. Essa preparação do responsável é separada das chamadas de leitura feitas pelo bot.
- **Português:** formulário, autorização e prévia de três cadastros de dois responsáveis; cancelar encerrou o pedido sem criar arquivo nem reservar o destino. Um pedido novo pôde prosseguir.
- **Inglês:** preferência alterada apenas no servidor temporário. Novo pedido, código atual, validação, prévia e **Import and create copy** concluídos. A planilha nova usa localidade `en_US`, sem traduzir os dados dos membros.
- **Dados e acesso:** um único arquivo gerenciado para o destino, três IDs novos, responsáveis e datas preservados, inclusive data desconhecida. Apenas a cópia recebeu edição para o e-mail autorizado, sem acesso público. Planilha original e sua conexão não receberam edição ou concessão de acesso.
- **Duas contas reais:** a conta secundária entrou no servidor temporário como membro comum e recebeu **Only members with Manage Server can access this panel.** ao tentar abrir o painel. A recusa também foi vista no servidor original, em português.
- **Discord → Sheets:** edição de nome no servidor de `QA Aparência 1`, com formulário, prévia e confirmação reais; o valor chegou à cópia.
- **Sheets → Discord:** edição de `QA Aparência 2` diretamente na célula da cópia pelo navegador; após a sincronização normal, o formulário do bot mostrou o nome atualizado. O formulário foi cancelado, sem outra gravação.
- **Auditoria posterior, só leitura:** versão `1.2.0`, 29 arquivos iguais ao pacote, integridade SQLite `ok`, 19 cadastros e três conexões anteriores idênticos à referência. O servidor temporário tem somente os três registros sintéticos, conexão `ready`, idioma `en` e fila de envio vazia. O console foi desconectado.
- **Documentos públicos:** guia do dono, política de privacidade e termos receberam a descrição da importação, autorização e edição somente na cópia, em português e inglês. Conteúdo relido pela API; estrutura anterior preservada. Não foram alterados os acessos dos documentos.

O ensaio da interface usou uma origem criada pelo aplicativo, porém sem autorização pelo servidor de origem: foi exigido o código de editor. Portanto, não valida o assistente Google Picker para um arquivo externo. Recusa por permissão revogada durante uma prévia, falhas Google, retomada e concorrência continuam cobertas pelos testes automatizados, sem alegação de reprodução nativa nesta rodada.

### Fechamento do Picker e limpeza — 22/10/2026

Uma cópia sintética foi criada fora do aplicativo do Arquivista, na conta do usuário. A conta dedicada recebeu **somente leitura** no original. Antes da seleção, o token que o bot já usava não conseguia abrir o arquivo (`GOOGLE_MISSING`). O usuário entrou na conta dedicada no navegador.

O assistente entregue abriu o Google Picker oficial com um único arquivo disponível. O arquivo foi selecionado e confirmado. A conta dedicada, o arquivo escolhido, o escopo único `drive.file` e o acesso com o refresh token anterior foram conferidos; o arquivo privado de credenciais ficou idêntico. Após o Picker, o Google retornou `isAppAuthorized: true` e permissão de copiar. A restrição de leitura permaneceu: a conta do bot não pôde listar as permissões da origem. O responsável conferiu os acessos pela própria conta, sem conceder edição ao bot.

Para repetir a importação sem criar outro servidor, o ambiente temporário foi desconectado pelo painel. Um backup SQLite privado foi criado, e somente os três cadastros fictícios e a reserva daquele servidor foram removidos, com checagem dos IDs, nomes e responsáveis. Esse descarte do ambiente de QA não faz parte do comando de importação e não permite substituir uma conexão real.

Pela interface do Discord, foi informado o link externo e o e-mail autorizado. O responsável pela origem colocou o código atual em uma célula vazia com intervalo nomeado de uma única célula. **Validate file** mostrou três cadastros; **Import and create copy** concluiu a operação. Conferência real confirmou três IDs novos, revisão inicial 1, responsáveis, datas e campos preservados. O original manteve seus cadastros e acessos; apenas a nova cópia recebeu edição para o e-mail informado e pertence à conta do bot. Nenhum arquivo ficou público.

A suíte foi repetida: **182 testes Python e 36 JavaScript aprovados**. A revisão do diff não encontrou defeito novo que exigisse alteração do runtime. Revogação durante uma prévia, falhas Google, retomada e concorrência permanecem cobertas automaticamente, sem alegação de reprodução nativa nesta rodada.

**Limpeza concluída:** as duas cópias criadas pelo Discord foram desconectadas antes do descarte. As cinco planilhas sintéticas desta bateria foram enviadas à lixeira recuperável de suas respectivas contas, com nomes e IDs conferidos; não houve exclusão permanente de planilhas. Os registros, filas, eventos e reservas do único servidor temporário foram retirados com backup e sem atingir os dados de outros servidores. O usuário confirmou especificamente a exclusão permanente do servidor temporário no botão final e concluiu a autenticação multifatorial exigida pelo Discord; sua ausência foi conferida na conta principal.

**Auditoria final:** runtime `1.2.0`, 29 arquivos iguais ao pacote, SQLite íntegro, 19 cadastros e três conexões anteriores preservados. Nenhum cadastro ou conexão gerenciada do servidor temporário ficou no banco. Não houve chamada paga a modelos nem reinício adicional da aplicação nesta etapa. O runtime publicado permanece o de `4710955`; os commits seguintes registram os ensaios e a documentação. A PR 14 reúne esta entrega; consulte o GitHub para seu estado de merge.

**Retomada:** conferir `main` e a PR 14 antes de editar. O escopo desta importação foi validado e encerrado; não há teste externo pendente nesta bateria. Os limites continuam valendo: destino vazio, formato Arquivista compatível, autorização do responsável e acesso do aplicativo a cada origem externa. Documentos públicos do dono, privacidade e termos estão atualizados em português e inglês.

Relatórios, imagens, identificadores dos cinco arquivos descartados, códigos temporários e backups ficam nos arquivos ignorados de `dados/`; não os publicar no Git. Os backups privados de QA continuam guardados para recuperação. As planilhas reais do usuário não foram modificadas ou enviadas à lixeira.
