# Arquivista do Ciclo · Amiya

**Versão 0.3.0 (em desenvolvimento) · projeto independente dos Guias do Ciclo.**

> **Pra dono de servidor:** o passo a passo de convidar, configurar e ligar a planilha está no [guia público no Google Docs](https://docs.google.com/document/d/1xuehlkhU3EhMsSE4hjLIfQY9p-eEF6ynS5ikAmlqnhw/view). Quem usa o bot encontra os comandos e o passo a passo em `/ajuda` e `/guia`.
>
> [Política de privacidade](https://docs.google.com/document/d/1nMsutdyyrtb-YKCKziW3SmDY3ViKN31yO1OOW3zSRcw/view) · [Termos de uso](https://docs.google.com/document/d/1uZlohyKEn7eOlM1wP5TbSeDBm_PkpLc13YnGmPYpZx8/view) · [Código da planilha](https://drive.google.com/file/d/1-2UMIJg4TKzjXS5mFsy16221SVtZEncA/view)

Bot de cadastro de aparências com comandos `AC:` e `/`, consultas públicas, formulários privados e integração com a Planilha Aparências. A imagem fornecida da Amiya está em `assets/amiya.png`, sem alteração. Não usa um modelo de IA nem a chave de outro provedor.

**Estado:** multi-servidor, com banco próprio, planilha conectada nos dois sentidos, backup e restauração pelo Discord. Testes automáticos em `tests/` (rodam no CI a cada envio).

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
| Instalação | Assistente `.env`, diagnóstico sem escrita, configuração para Discloud e dois arquivos Apps Script. |

Situação, justificativa e nome interno do personagem **não saem na lista, galeria nem notificações públicas**. Arquivado continua ocupado. Liberado permite reutilização. Não há aprovação obrigatória para o cadastro inicial.

## Comece por aqui

**Leia [docs/INSTALACAO.md](docs/INSTALACAO.md).** Não substitua o Apps Script enquanto a ampliação da planilha estiver em execução.

Na máquina em que irá preparar o bot, com Python 3.11 ou mais recente:

```sh
python -m pip install -r requirements.txt
python configurar.py
```

O assistente cria um `.env` privado e gera uma chave separada para a ponte com o Google. Pode ser executado novamente depois de obter a URL `/exec`; ele preserva a chave existente. Nenhuma chave real acompanha este pacote.

Depois de instalar e implantar a ponte conforme o guia:

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

Este projeto não substitui os Guias, não publica o acesso da planilha, não cria um repositório e não contrata hospedagem. Os grupos precisam estar realmente preparados no Sheets: aceita a capacidade pronta de 50 ou 100 membros, com 200 posições por pessoa. O bot não inventa uma expansão além disso; informa à staff quando faltar espaço.

Os registros anteriores mantêm suas datas reais, inclusive data vazia quando desconhecida. A auditoria detalhada começa na ativação desta integração; não há histórico fictício retroativo.

## Testes

```sh
python -m unittest discover -s tests -v
node tests/test_bridge.js
```

A configuração de GitHub Actions acompanha o projeto para repetir os testes em um repositório próprio, com as dependências instaladas. Não modifica o repositório dos Guias.

## Referências

A estrutura dos Guias do Ciclo foi usada como referência de organização e apresentação, sobretudo o carteiro por webhooks. O Arquivista tem módulos próprios; não inclui dados narrativos, conversas, credenciais ou modelos de IA do outro bot.

Fontes oficiais e limites estão em [docs/SEGURANCA_E_LIMITES.md](docs/SEGURANCA_E_LIMITES.md).
