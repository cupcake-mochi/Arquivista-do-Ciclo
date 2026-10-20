# Instalação — Arquivista do Ciclo

> **v0.3 (multi-servidor, sem planilha ainda):** pule as seções 2, 3 e 4. Rode `python configurar.py` (token e, opcional, servidor de testes), `python verificar.py` e `python iniciar.py`. No Discord, a gerência de cada servidor usa `/configurar` pra escolher cargos de staff e os canais de histórico e imagens. Pra trazer os cadastros da planilha, rode `exportarParaArquivista` no Apps Script (gera um .json no seu Drive), baixe o arquivo e rode `python importar.py arquivo.json --servidor ID` com o bot desligado; sem `--aplicar` ele só confere. Pra ligar uma planilha, veja a seção **Planilha conectada** logo abaixo. O restante deste guia descreve a ponte da v0.2 e não é usado na v0.3.

## Planilha conectada (v0.3, opcional)

A planilha recebe uma cópia de tudo que é cadastrado pelo bot, e o que a staff mudar nela volta pro bot.

**Editar pela planilha:** a cada 5 minutos o bot lê a planilha e compara com o banco. Aparência, nome no servidor, obra, situação, data, link da imagem e justificativa mudados à mão entram como alteração com autor "Planilha; autor não identificado" (aparece no canal de histórico e no `/historico`). Uma linha digitada numa posição vazia vira cadastro novo do dono daquela guia, naquela mesma linha. O que o bot recusa (aparência + obra já ocupadas, situação fora da lista, link sem https, data ilegível) é desfeito na planilha, e o motivo aparece no `/diagnostico`. Apagar uma linha à mão não apaga o cadastro: ela volta; para apagar, use `/remover` ou `/limpar`. Se a mesma ficha mudar pelo Discord antes de o bot ler a planilha, ele junta os dois: o campo mexido na planilha entra, e só o campo mexido dos dois lados fica com o Discord. Inserir ou apagar uma linha no meio das fichas de alguém trava a atualização daquela pessoa até desfazer (o `/diagnostico` avisa). Qualquer pessoa com permissão de edição na planilha consegue mudar cadastros por ela, então compartilhe só com a staff.

1. Crie uma planilha **nova e vazia** no Google Sheets.
2. Extensões → Apps Script. Apague o conteúdo de `Código.gs` e cole o de `apps_script/Planilha.gs`.
3. No editor, em Serviços (+), adicione **Google Sheets API**.
4. Salve, volte pra planilha e recarregue a página. No menu **Arquivista → Instalar ou reinstalar**, informe o ID do servidor do Discord e autorize.
5. No Apps Script: Implantar → Nova implantação → Tipo **App da Web**, executar como **você**, acesso **Qualquer pessoa**. Copie o link que termina em `/exec`.
6. Na planilha, **Arquivista → Mostrar a chave da conexão** e copie a chave.
7. No Discord, `/configurar` → **Conectar planilha**, cole o link e a chave. O bot testa a conexão antes de salvar e manda todos os cadastros do servidor.

Cada membro ganha uma guia própria, com o nome de usuário do Discord (o `@`, não o apelido do servidor). Se o nome de usuário mudar, a guia é renomeada na próxima vez que o bot gravar algo dessa pessoa. Não crie guias com o mesmo nome de um membro: se acontecer, a guia do membro vira `nome (2)`.

**O script não muda mais:** desde a versão 2.0 ele só confere a assinatura, lê e aplica o que o bot manda. Quem monta as guias (posições, cores, bordas, fórmulas) é o bot, então melhorias na planilha chegam só atualizando o bot. Quem tem o script 1.x precisa colar o 2.0 uma última vez: cole o `Planilha.gs` novo por cima, salve, e em Implantar → Gerenciar implantações → lápis → Versão **Nova versão** → Implantar (o link `/exec` continua o mesmo). Se o bot avisar "o script da planilha é antigo", é isso que falta.

Guias criadas por versões antigas continuam funcionando, mas não ganham o visual novo sozinhas. Pra refazer: apague as guias dos membros (a planilha é só uma cópia do que está no bot) e use `/configurar` → **Conectar planilha** de novo com o mesmo link e chave.

A chave fica cifrada no banco do bot. Sem `AC_MASTER_KEY`, a cifra depende do token: se o token mudar, conecte a planilha de novo. Quem tiver a chave consegue escrever na planilha; se ela vazar, use **Trocar a chave da conexão** e reconecte.

## Antes de começar

Este é um **novo bot**, separado dos Guias do Ciclo. Não substitua a pasta, o token, os comandos nem o processo dos Guias.

**Espere a ampliação da planilha terminar.** No diagnóstico atual, confira `Grupos prontos: 100 de 100`, nenhuma ampliação pendente e nenhuma execução antiga ainda trabalhando. O adaptador também funciona com 50 grupos prontos, mas recusa gravações durante uma ampliação. Não troque a versão do script enquanto ela estiver em execução.

Faça uma cópia de segurança dos arquivos Apps Script atuais antes de substituir o módulo. A ponte preserva o visual e os dados; acrescenta três abas técnicas privadas para auditoria e retentativas. Não precisa importar outro XLSX.

## 1. Preparar a configuração local

Extraia este ZIP para uma pasta própria. Na pasta, execute:

```sh
python configurar.py
```

O assistente pede o token do **Arquivista**, o ID do servidor e, opcionalmente, IDs dos cargos de staff. O dono do servidor e membros com permissão de Administrador já são considerados staff. Outros cargos precisam ser informados por ID, separados por vírgula; nomes de cargos não são chaves.

Para obter os IDs, ative o Modo desenvolvedor no Discord. Copie o ID do servidor no menu do servidor; não use o ID da sua conta ou o do bot neste campo.

Use um token novo, gerado em **Discord Developer Portal → aplicação do Arquivista → Bot → Reset Token**, já que a chave anterior foi compartilhada. Digite-o somente no assistente local ou na configuração privada da hospedagem. O assistente não imprime o token e não faz login nesta etapa.

A URL do Web App pode ficar pendente. O assistente gera `AC_BRIDGE_SECRET`, uma chave diferente do token Discord, e mostra duas propriedades para você copiar para o Google. O arquivo `.env` criado **não pode ir ao GitHub**. Rode o assistente novamente depois para informar a URL, sem perder essa chave.

## 2. Atualizar o projeto Apps Script existente

Na **Planilha Aparências original**, abra **Extensões → Apps Script**.

No mesmo projeto que contém `Aparencias.gs`:

1. **Substitua o conteúdo de `Aparencias.gs`** pelo arquivo `apps_script/Aparencias.gs` deste pacote. É a versão 1.2.0 de compatibilidade. Não crie duas definições de `CM` e não mantenha outra cópia das mesmas funções ativa.
2. **Adicione um novo arquivo `Arquivista.gs`** com o conteúdo de `apps_script/Arquivista.gs`. Não substitua `Aparencias.gs` por este segundo arquivo.
3. Mantenha **Serviços → Google Sheets API**, versão **v4**, identificador **Sheets**. Ele já era usado na ampliação. Caso não exista, adicione pelo `+` de Serviços.

Não apague outros módulos próprios. Se já existir algum `doGet` ou `doPost` de outra integração no mesmo projeto, pare antes de instalar: esses pontos de entrada precisam ser combinados, não duplicados. Os arquivos anteriores fornecidos nesta conversa não continham essa outra API.

A mudança de compatibilidade usa uma trava compartilhada entre o bot e as edições processadas pelo Apps Script, e migra as propriedades internas necessárias para que funcionem também no Web App. Não é um redesenho da ficha.

## 3. Configurar e ativar a ponte

No Apps Script, abra **Configurações do projeto → Propriedades do script → Adicionar propriedade** e configure:

| Propriedade no Google | Valor |
|---|---|
| `AC_GUILD_ID` | O mesmo ID do servidor de `DISCORD_GUILD_ID` no `.env`. |
| `AC_SECRET` | Exatamente a chave de `AC_BRIDGE_SECRET` gerada pelo assistente. |

**Não coloque o token Discord no Apps Script.** Não cole as chaves em células, notas, código-fonte público ou prints.

Salve os arquivos. Selecione e execute **`instalarIntegracaoArquivista`**, uma vez, com a **conta dona da planilha**. Revise e autorize os acessos solicitados pelo Google. Não é necessário executar `preparar100Membros` novamente.

A instalação exige que a planilha continue **Restrita**. Ela cria:

- `SISTEMA · AC EVENTOS`: auditoria durável de alterações;
- `SISTEMA · AC PEDIDOS`: confirmações para retentativas sem duplicar o cadastro;
- `SISTEMA · AC SNAPSHOTS`: último estado conhecido dos registros.

Se houver muitos cadastros existentes, a criação da base histórica continua em lotes. Execute **`acDiagnostico`** para acompanhar; feche a janela com OK ao terminar. A condição para prosseguir é:

```json
{
  "ativa": true,
  "base": true,
  "membros": 100,
  "erro": "nenhum"
}
```

O campo `membros` pode ser 50 quando essa for a capacidade concluída. Não force 100 editando propriedades. `base: false` indica preparação ainda pendente. A importação inicial não dispara notificações retroativas nem inventa datas antigas.

## 4. Implantar como Web App

No Apps Script:

**Implantar → Nova implantação → tipo Aplicativo da Web.**

Configure:

- **Executar como:** você, dono da planilha;
- **Quem tem acesso:** qualquer pessoa, para permitir chamadas do processo hospedado sem login interativo Google.

**Isso se refere à URL da ponte, não ao compartilhamento da planilha. Mantenha a planilha Restrita.** O código rejeita requisições sem assinatura HMAC válida e sem o servidor autorizado. A chave fica somente na configuração privada dos dois lados. Abrir a URL no navegador retorna `AUTH`; isso é esperado e não é um teste de autorização do bot.

Contas Google administradas podem proibir Web Apps com esse modo de acesso. Nesse caso, não torne o arquivo público: será necessário adaptar o acesso à política da conta antes de ligar o bot.

Copie a URL terminada em **`/exec`**. Não use `/dev`, nem a URL do editor. Execute `python configurar.py` de novo e informe essa URL; ela irá para `AC_BRIDGE_URL`.

Quando o código da ponte mudar no futuro, salve e atualize a implantação por **Gerenciar implantações → Editar → Nova versão**. Só salvar no editor não necessariamente atualiza o `/exec` da versão implantada.

## 5. Preparar o aplicativo Discord

Na aplicação separada do Arquivista:

- Ative **Message Content Intent** em **Bot → Privileged Gateway Intents**, necessário para `AC:` em mensagens comuns.
- Gere o convite com os escopos **bot** e **applications.commands**.
- Convide ao servidor cujo ID está configurado no `.env`.

Permissões necessárias nos canais usados: **Ver canal, Enviar mensagens, Incorporar links, Anexar arquivos, Ler histórico de mensagens, Gerenciar webhooks e Enviar mensagens em tópicos** quando usar tópicos. Não é preciso conceder Administrador ao bot.

Os webhooks da Amiya pertencem à aplicação do Arquivista. Não reutilize os webhooks dos Guias. Se faltar permissão ou associação à aplicação para botões interativos, o código usa uma resposta pela própria conta do Arquivista, mantendo o avatar e a identificação da personagem no cartão.

A conta do bot mantém o ícone dela. As respostas da Amiya no canal (ajuda, guia, listas, avisos) saem por um webhook com nome `Amiya` e a foto de `assets/amiya.png`, e o cabeçalho das respostas privadas usa a mesma foto. Para isso o bot precisa da permissão **Gerenciar Webhooks** no canal; sem ela, a mensagem sai pela conta do bot, com o ícone dele, e o `/diagnostico` avisa. `CONFIGURAR_AVATAR=true` troca também a foto da conta do bot pela da Amiya.

## 6. Testar antes de hospedar

Python 3.11 ou mais recente, na pasta extraída:

```sh
python -m pip install -r requirements.txt
python verificar.py
python -m unittest discover -s tests -v
python iniciar.py
```

A verificação inicial é somente de leitura. Um resultado positivo confirma acesso, mas não substitui os testes interativos no servidor. `iniciar.py` permanece rodando; ele sincroniza os 16 comandos de barra somente no servidor configurado.

Faça os testes de aceitação de `TESTES.md` em um canal da staff antes de abrir o uso geral. Use duas contas com permissões diferentes para validar o acesso aos formulários e botões.

## 7. Configurar os canais pelo próprio bot

Quem gerencia o servidor usa `/configurar` (ou `AC:cfg`) e escolhe, no painel privado:

- **Canal de histórico:** recebe as **próximas** inclusões e alterações. Não republica o catálogo anterior. O registro completo continua privado, em `/historico`.
- **Canal de imagens:** guarda os anexos dos cadastros. O bot confere tamanho e tipo (PNG, JPEG, GIF ou WebP, até 8 MB). Não apague as mensagens desse canal, porque é delas que vêm os links atuais das imagens. Sem esse canal, o cadastro por link continua funcionando, e o campo de anexo do formulário não aparece.

## 8. Hospedar na Discloud

O ZIP contém `iniciar.py`, `requirements.txt` e `discloud.config` na raiz. Não envie a pasta dos Guias por cima nem use o identificador de outro aplicativo.

Prepare uma cópia de implantação com seu `.env` **somente para envio privado à hospedagem**, ou configure os mesmos valores nas variáveis do ambiente, quando disponíveis. O `.env` não é incluído no ZIP entregue aqui. Não envie o pacote privado com segredos para um repositório público.

Configuração incluída: `TYPE=bot`, `MAIN=iniciar.py`, `RAM=256`, `VERSION=latest`. Ajuste a memória conforme o uso real e o plano disponível; não foi feita medição em produção. Não contrata, paga nem cria automaticamente uma aplicação na Discloud.

Preserve a pasta **`dados/`** ao atualizar ou reinstalar. Ela guarda o SQLite com canais configurados, cursor de auditoria e fila de envio. A planilha continua guardando o catálogo e a auditoria original; apagar o SQLite perde preferências locais e pode mudar a retomada das notificações.

Rode apenas **uma instância do bot por configuração**. Não deixe o processo local e o da Discloud ligados ao mesmo tempo durante a operação normal.

## Problemas comuns

| Sintoma | Verificação |
|---|---|
| `AUTH` em `verificar.py` | Confirme `/exec`, implantação correta, modo de acesso, `AC_SECRET` idêntico e relógio da hospedagem correto. Não compartilhe o segredo em prints. |
| `NOT_READY` ou base não pronta | Execute/acompanhe a instalação da ponte, não repita a expansão antiga. |
| `MAINTENANCE` | Há ampliação, estrutura deslocada ou revisão necessária. Leia o diagnóstico do Sheets; não apague propriedades para ignorar o erro. |
| `BUSY` | Outra tarefa mantém a trava. Aguarde; a mesma confirmação reutiliza o identificador do pedido. |
| `AC:` não responde | Confira Message Content Intent, permissões do canal, servidor configurado e processo em execução. |
| `/` não aparece | Confira convite com applications.commands, servidor configurado e erros de sincronização nos logs. |
| Botões não funcionam depois de minutos | Os painéis expiram após 5 minutos; a confirmação tem 10 minutos. Abra um comando novo. Reiniciar o bot também encerra painéis antigos. |
| Galeria sem imagem | Confira link direto, permissão do canal de arquivos e se a mensagem do anexo ainda existe. O cadastro não é removido por falta de imagem. |
| Data antiga continua vazia | É intencional quando a data real era desconhecida. O código não cria uma data histórica fictícia. |
