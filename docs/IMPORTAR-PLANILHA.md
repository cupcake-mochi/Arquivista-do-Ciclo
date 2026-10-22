# Importar uma planilha existente

Versão 1.2.0 instalada na Discloud para validação em 22/10/2026. Google real validado com banco isolado; teste completo pela interface do Discord e atualização dos documentos públicos ainda pendentes.

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

A suíte automática usa Google e Discord simulados. O fechamento offline abaixo foi seguido pela validação real registrada ao final desta página. Antes de publicar como validado de ponta a ponta, testar o Picker real de uma origem autorizada, prévia e cancelamento, criação da cópia, permissões privadas e sincronização nos dois sentidos, com dois servidores e duas contas. Confirmar que origem e dados do outro servidor permanecem iguais.

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

**Pendente antes de anunciar validação completa:** criação do servidor temporário `QA Arquivista - Importação - 22-10`, inclusão do bot e confirmação/cancelamento da importação pela interface. O Discord apresenta aceite das diretrizes da comunidade no botão de criação; foi pedido ao usuário o aceite específico, sem clicar nesse botão. Também permanecem pendentes teste com membro comum/segunda conta, navegação em inglês na operação real, Picker real de uma origem externa, atualização dos três documentos públicos e merge da PR.

**Retomada exata:** conferir a PR e o estado remoto; manter a produção existente e a reserva de M&S; receber o aceite pendente antes de criar o servidor temporário. A aba do Discord foi deixada no formulário preenchido, sem confirmar. A origem e a cópia sintéticas, os scripts de teste, relatórios, imagens e o backup privado estão em `dados/` desta checkout, ignorados pelo Git. Não publicar credenciais, banco, código temporário de autorização ou o conteúdo dos backups. O arquivo `teste-importacao-real.json` identifica os dois arquivos sintéticos para continuar e, ao encerrar, enviá-los à lixeira pelo fluxo recuperável. Não tocar nas planilhas reais do usuário.
