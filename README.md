# Arquivista do Ciclo · Amiya

**Versão 1.2.0 publicada e validada em 22/10/2026.** Importação de origem externa pelo Google Picker, permissões e sincronização conferidas no Discord e no Google reais. Última versão estável anterior: 1.1.2, publicada em 21/10/2026. Idioma por servidor, planilhas novas em inglês e arquivos antigos preservados. [Clareza de siglas](docs/CLAREZA-SIGLAS.md). [Revisão final de apresentação](docs/REVISAO-FINAL-APRESENTACAO.md). [Validação e retomada](docs/RETOMADA-IDIOMA.md). Projeto independente das Guias do Ciclo.

> **Para configurar no seu servidor:** siga o [guia público no Google Docs](https://docs.google.com/document/d/1xuehlkhU3EhMsSE4hjLIfQY9p-eEF6ynS5ikAmlqnhw/view). Para aprender a usar o bot, comece por `/guia`; `/ajuda` traz a lista de comandos.
>
> [Política de privacidade](https://docs.google.com/document/d/1nMsutdyyrtb-YKCKziW3SmDY3ViKN31yO1OOW3zSRcw/view) · [Termos de uso](https://docs.google.com/document/d/1uZlohyKEn7eOlM1wP5TbSeDBm_PkpLc13YnGmPYpZx8/view) · [Código da planilha](https://drive.google.com/file/d/1-2UMIJg4TKzjXS5mFsy16221SVtZEncA/view)

A Amiya cuida do arquivo de aparências do servidor. Os membros cadastram suas aparências pelo Discord, consultam a lista e a galeria e procuram personagens pela obra. A equipe autorizada (staff) cuida das situações, transferências e cadastros de outras pessoas. Os registros também podem ser preenchidos pelo Google Sheets.

Cada servidor tem seus próprios cadastros e configurações. O banco SQLite guarda os cadastros e o histórico; a planilha recebe as mudanças do bot e envia de volta as edições manuais. Backup e restauração ficam no Discord. Os testes em `tests/` rodam no GitHub Actions a cada envio.

**Planilha pronta:** `/planilha criar` pede um e-mail em privado e entrega o arquivo montado, conectado e com edição para esse e-mail. A planilha pertence à conta do Arquivista. `/planilha membro` exige selecionar um membro real do servidor e prepara uma aba para preenchimento manual; cadastros pelo bot também criam as abas. Não é preciso instalar script. Para ativar na hospedagem, veja [a configuração única do mantenedor](docs/GOOGLE-MANTENEDOR.md).

**Importar de outro arquivo:** `/planilha importar` lê uma planilha compatível e autorizada e cria uma nova planilha independente para um servidor vazio. Somente a cópia recebe edição para o e-mail informado. O original não é alterado; IDs dos cadastros são novos, responsáveis e datas são mantidos. [Funcionamento, autorização Google e limites](docs/IMPORTAR-PLANILHA.md).

**Abrir novamente:** `/planilha abrir` ou `AC:planilha` recupera o painel privado com o link do arquivo já conectado.

## Idioma por servidor

`/language` ou `/idioma` escolhe **English** ou **Português do Brasil**. Dono, administradores, quem tem Gerenciar servidor e os cargos de staff configurados podem mudar essa opção. A configuração é independente da das Guias.

A interface e os guias seguem o idioma do servidor. Os nomes no menu nativo seguem o idioma do aplicativo Discord; os aliases em inglês também funcionam com `AC:`. Planilhas **novas** usam o idioma escolhido; arquivos existentes mantêm o idioma em que foram criados. Nomes, obras e justificativas escritos pelos membros não são traduzidos. Dados e backups JSON mantêm códigos estáveis.

[Implementação, testes e limites](docs/IDIOMAS.md).

## O que está incluído

| Área | Implementação |
|---|---|
| Amiya | Respostas públicas por webhook com nome/avatar da personagem; atende menções diretas à conta ou ao cargo exclusivo do bot e respostas às próprias mensagens. Ignora chamadas por `@everyone`, `@here` e outros cargos. |
| Consulta | Lista paginada, galeria, filtro por membro e busca aproximada. A seleção confirma a aparência correta antes de editar. |
| Cadastro | Qualquer membro cadastra para si. A staff cadastra para terceiros. Formulário, revisão e confirmação. |
| Permissões | Membro edita nome no servidor e imagem dos próprios registros. Só a staff muda aparência, obra ou situação após o cadastro, transfere e remove registros de outras pessoas. |
| Histórico | Canal configurável, auditoria privada antes/depois e fila persistente de notificações. Captura de alterações manuais na planilha. |
| Imagens | Link direto, imagem na célula consultável e anexo preservado em um canal escolhido pela staff. |
| Planilha | Uma aba por membro, com visor, imagens e posições que crescem conforme o uso. IDs e datas ligam a ficha ao cadastro no banco. |
| Instalação | Assistente `.env`, autorização Google única do mantenedor, diagnóstico sem escrita e pacote para Discloud. Apps Script mantido para conexões antigas. |

O nome do personagem no servidor aparece na lista e na galeria, junto da aparência e do responsável. Situação e justificativa continuam privadas; as notificações públicas também não incluem o nome no servidor. Arquivado continua ocupado. Liberado permite reutilização. Não há aprovação obrigatória para o cadastro inicial.

Cada membro pode editar o nome e a imagem dos próprios registros e removê-los com `/remover`, depois de confirmar. Só a staff altera cadastros de outras pessoas, muda aparência, obra ou situação, transfere e usa a limpeza em lote. A remoção preserva o histórico para a staff.

## Comece por aqui

**Leia [docs/INSTALACAO.md](docs/INSTALACAO.md).** A conta Google é configurada uma vez pelo mantenedor; donos de servidor recebem a planilha pronta pelo Discord.

Na máquina em que irá preparar o bot, com Python 3.11 ou mais recente:

```sh
python -m pip install -r requirements.txt
python configurar.py
```

O assistente cria um `.env` privado para o token e o servidor de testes. A autorização Google fica no assistente separado `configurar_google.py`, conforme o guia do mantenedor. Nenhuma credencial real acompanha este pacote.

Depois de configurar o bot:

```sh
python verificar.py
python iniciar.py
```

`verificar.py` apenas consulta a identidade do bot, o servidor autorizado e o estado da ponte. Não envia mensagens, não configura canais e não cria cadastros.

## Comandos principais

```text
AC:ajuda
AC:aparencias
AC:aparencias @membro
AC:gal Takao
AC:gal @membro
AC:busca Takao Azur Lane
AC:min
AC:registrar
AC:editar Takao
```

A staff também tem `AC:sit`, `AC:tr`, `AC:rm`, `AC:hist`, `AC:diag` e `AC:cfg`, com os equivalentes por barra. Veja [docs/COMANDOS.md](docs/COMANDOS.md).

## Planilha e cadastros existentes

Cada aba de membro começa com 20 posições e ganha mais 20 quando restam duas livres, dentro dos limites do Google Sheets. A planilha é privada, e o comando de criação mantém o arquivo quando já existe uma conexão.

Os registros anteriores mantêm suas datas reais, inclusive data vazia quando desconhecida. A auditoria detalhada começa na ativação desta integração; não há histórico fictício retroativo.

## Testes

```sh
python -m unittest discover -s tests -v
node tests/test_bridge.js
node tests/test_planilha.js
```

A configuração de GitHub Actions acompanha o projeto para repetir os testes em um repositório próprio, com as dependências instaladas. Não modifica o repositório dos Guias.

## Referências

A estrutura dos Guias do Ciclo foi usada como referência de organização e apresentação, sobretudo o carteiro por webhooks. O Arquivista tem módulos próprios; não inclui dados narrativos, conversas, credenciais ou modelos de IA do outro bot.

Fontes oficiais e limites estão em [docs/SEGURANCA_E_LIMITES.md](docs/SEGURANCA_E_LIMITES.md).
