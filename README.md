# Arquivista do Ciclo · Amiya

**Versão 1.0.0 · projeto independente dos Guias do Ciclo.**

> **Pra dono de servidor:** o passo a passo de convidar, configurar e ligar a planilha está no [guia público no Google Docs](https://docs.google.com/document/d/1xuehlkhU3EhMsSE4hjLIfQY9p-eEF6ynS5ikAmlqnhw/view). Quem usa o bot encontra os comandos e o passo a passo em `/ajuda` e `/guia`.
>
> [Política de privacidade](https://docs.google.com/document/d/1nMsutdyyrtb-YKCKziW3SmDY3ViKN31yO1OOW3zSRcw/view) · [Termos de uso](https://docs.google.com/document/d/1uZlohyKEn7eOlM1wP5TbSeDBm_PkpLc13YnGmPYpZx8/view) · [Código da planilha](https://drive.google.com/file/d/1-2UMIJg4TKzjXS5mFsy16221SVtZEncA/view)

Bot de cadastro de aparências com comandos `AC:` e `/`, consultas públicas, formulários privados e integração com a Planilha Aparências. A imagem fornecida da Amiya está em `assets/amiya.png`, sem alteração. Não usa um modelo de IA nem a chave de outro provedor.

**Estado:** multi-servidor, com banco próprio, criação automática de planilhas e sincronização nos dois sentidos, backup e restauração pelo Discord. Testes automáticos em `tests/` (rodam no CI a cada envio). A criação automática exige a configuração Google única do mantenedor; sem ela o restante do bot continua funcionando.

**Planilha pronta:** `/planilha criar` pede um e-mail em privado e entrega o arquivo montado, conectado e com edição para esse e-mail. A planilha pertence à conta do Arquivista. `/planilha membro` exige selecionar um membro real do servidor e prepara uma aba para preenchimento manual; cadastros pelo bot também criam as abas. Não é preciso instalar script. Para ativar na hospedagem, veja [a configuração única do mantenedor](docs/GOOGLE-MANTENEDOR.md).

**Abrir novamente:** `/planilha abrir` ou `AC:planilha` recupera o painel privado com o link do arquivo já conectado.

## O que está incluído

| Área | Implementação |
|---|---|
| Amiya | Respostas públicas por webhook com nome/avatar da personagem; resposta a menções e a respostas às mensagens lembradas do bot. |
| Consulta | Lista paginada, galeria, filtro por membro e busca aproximada. A seleção confirma a aparência correta antes de editar. |
| Cadastro | Qualquer membro cadastra para si. A staff cadastra para terceiros. Formulário, revisão e confirmação. |
| Permissões | Membro edita nome no servidor e imagem dos próprios registros. Identidade da aparência, situação, transferência e remoção são da staff. |
| Histórico | Canal configurável, auditoria privada antes/depois e fila persistente de notificações. Captura de alterações manuais na planilha. |
| Imagens | Link direto, imagem na célula consultável e anexo preservado em um canal escolhido pela staff. |
| Planilha | Mesma estrutura visual; IDs/datas/vínculos/auditoria tratados em uma operação coordenada. |
| Instalação | Assistente `.env`, autorização Google única do mantenedor, diagnóstico sem escrita e pacote para Discloud. Apps Script mantido para conexões antigas. |

Situação, justificativa e nome interno do personagem **não saem na lista, galeria nem notificações públicas**. Arquivado continua ocupado. Liberado permite reutilização. Não há aprovação obrigatória para o cadastro inicial.

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

## O que não muda automaticamente

Este projeto não substitui os Guias, não torna as planilhas públicas e não contrata hospedagem. Cada aba de membro começa com 20 posições e ganha mais 20 quando restam duas livres, respeitando os limites do Google Sheets. Planilhas existentes não são substituídas automaticamente pelo comando de criação.

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
