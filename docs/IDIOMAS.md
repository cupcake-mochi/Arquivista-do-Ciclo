# Idioma da Arquivista · 1.1.0

`/idioma` e `/language` usam a autorização atual de staff: dono, Administrador, Gerenciar servidor ou cargo registrado em `/configurar`. O cargo não recebe permissão administrativa do Discord por causa desta opção. A configuração vale somente no servidor da interação e é independente das Guias.

## Interface e compatibilidade

As respostas usam a opção do servidor. Controles abertos mantêm o idioma com que foram criados. Os nomes dos comandos e opções nativos são localizados pelo idioma do cliente Discord. Aliases ingleses com `AC:` e comandos portugueses coexistem. Conteúdo digitado pelo membro é preservado.

O banco usa códigos canônicos de situação em português. A apresentação inglesa e a leitura da planilha convertem apenas os quatro rótulos conhecidos. IDs, revisões, datas internas e formato restaurável do backup JSON permanecem estáveis. Fórmulas traduzem somente os literais de apresentação auditados; referências e contas não mudam.

Cada planilha gerenciada recebe `language` na criação. Essa propriedade não acompanha mudanças posteriores do servidor: arquivos antigos continuam pt-BR; novos arquivos ingleses usam `en_US`, vírgula nas fórmulas e data exibida em ISO. Alterar manualmente a localidade do arquivo continua sendo erro de sincronização. Não há conversão de arquivo existente nem mudança de acesso Google.

## Validação de 21/10/2026

- 149 testes Python passaram, incluindo autorização, concorrência de idiomas, migração aditiva, criação retomável, idioma fixo do arquivo, expansão, transferência, leitura manual, escrita de volta, erros e backup inglês.
- 29 testes JS da ponte e 7 do script da planilha passaram; o cenário de pedidos do layout foi fornecido. Sintaxe dos três scripts aprovada.
- Google real, arquivo privado sintético: criação, fórmulas inglesas calculadas, contador e visor, datas ISO, expansão 20→40→60, transferência sem mudar ID. 61 grupos, 316 mesclas e 5 regras condicionais presentes. Nenhuma fórmula de erro detectada. Sem compartilhar com terceiros; arquivo enviado à lixeira após o teste.
- Esse ensaio nativo não valida a concessão de edição por e-mail nem uma criação completa por interação Discord: essas partes têm regressões com Google/Discord simulados. Planilhas oficiais não foram alteradas.

Publicação e testes nas contas reais do Discord ainda serão registrados no fechamento. Nenhuma chamada a modelos de IA foi usada.

## Retomada

Worktree `codex/idioma-ingles`, base `338cfda`. Compare backup novo da produção antes de publicar. Preserve banco, variáveis, chave mestra e planilhas conectadas. A cópia original do projeto contém mudanças apenas de fim de linha e foi preservada.
