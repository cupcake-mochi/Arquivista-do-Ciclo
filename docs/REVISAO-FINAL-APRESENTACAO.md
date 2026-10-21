# Revisão final de clareza e apresentação · 21/10/2026

Manutenção editorial **1.1.1**, sem alterar cadastro, permissões, sincronização,
fórmulas ou idioma de planilhas já criadas.

## Texto e organização

- A ajuda se chama **Comandos da Arquivista**. Os títulos do guia indicam a
  tarefa: consultar, cadastrar, editar/remover, entender situações e configurar.
- O cadastro explica onde colocar a imagem: link direto no formulário ou anexo
  na mensagem do comando antes de abrir o formulário.
- Exemplos ingleses de planilha usam `create`, `open` e `member`, os nomes
  localizados dos subcomandos. Os nomes portugueses continuam aceitos pelo bot;
  o menu nativo segue o idioma do cliente Discord.
- O README usa **cadastro de aparência** para evitar confundir com a ficha de RPG
  e distingue remoção própria das ações sobre registros de outras pessoas.
- A documentação de idioma aponta à validação inglesa de ponta a ponta já
  encerrada; a ausência desse ensaio não é apresentada como pendência atual.

A leitura teve três passadas: próxima ação e permissões; português/inglês;
apresentação, nomes de menus e limites do Discord. Os textos gerados a partir
de dados do membro continuam preservados, sem tradução de nomes ou obras.

## Avaliação visual

O retrato da Amiya, o azul (`#559EA6`) e o destaque da imagem na galeria já
sustentam a identidade. Foram mantidos. As listas agora separam cada cadastro
por uma linha em branco, inclusive na busca por obra, facilitando distinguir
nome, obra e responsável. Não foi inserido banner repetido nem arte nova na
planilha; a revisão não toca arquivos Google existentes.

## Testes e entrega

149 testes Python e 36 JavaScript aprovados. Ajuda de membro/staff e sete
páginas de guia por idioma ficaram dentro dos limites. Seis listas com 12 nomes
longos, em português/inglês, tiveram descrições entre 3.145 e 3.721 caracteres,
abaixo de 4.096. As 253 chamadas estáticas de tradução têm entrada no catálogo.

Pacote preparado com 27 arquivos, sem ambiente, banco ou credenciais; hashes em
`MANIFESTO_SHA256.json`. Publicado na Discloud, online às **15:57:26 de Brasília**, em seis servidores.
Os 27 arquivos instalados conferem com o pacote. O ambiente é idêntico; SQLite
e WAL passaram na integridade. Cadastros (18), histórico (46 eventos), pedidos,
planilhas gerenciadas e configurações foram preservados. Só o registro de duas
mensagens e a data de atualização do servidor mudaram no ensaio.

Discord: ajuda administrativa com o título novo e guia público de membro sem
cargo, páginas 1→2→3, confirmados. O texto de imagem e os títulos novos ficaram
legíveis no painel real. O fallback de webhook apareceu no guia e conservou
retrato/autoria no embed; ajuda enviada como Amiya. Não há erro de aplicação
nos logs desta inicialização. Nenhuma chamada a modelo de IA foi usada.

A criação inglesa, editor Google e sincronização nos dois sentidos continuam
validados no relatório de 21/10. Não se repetiu esse fluxo por uma mudança de
texto e espaçamento. Recursos adicionais e melhorias de gosto podem ficar para
versões seguintes; não são bloqueadores conhecidos desta versão estável.
