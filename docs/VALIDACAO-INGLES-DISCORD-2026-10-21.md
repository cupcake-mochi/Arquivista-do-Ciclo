# Criação e sincronização em inglês · Discord e Google reais

Rodada posterior à publicação da versão 1.1.0. Sem alteração de código ou
implantação nova da Arquivista. Servidor de ensaio autorizado pelo usuário;
nenhum cadastro real ou arquivo oficial foi usado como dado de teste.

## O que foi conferido

1. A conta administrativa escolheu inglês por `/language`.
2. `/planilha criar` abriu o formulário privado em inglês. O e-mail autorizado
   foi enviado somente ao bot/Google; não foi publicado no chat ou neste registro.
3. O bot criou o arquivo privado na sua própria conta e concedeu edição à
   segunda conta. A conferência de permissões encontrou somente proprietário
   e editor, sem acesso público. A segunda conta abriu o arquivo no Sheets.
4. A planilha nasceu com `en_US`, `START HERE`, cabeçalhos e visor em inglês,
   fórmulas com vírgulas e data ISO. A lista nativa oferece `In preparation`,
   `In use`, `Archived` e `Released`.
5. Uma posição foi preenchida com dados fictícios no Sheets. O processamento
   normal do bot importou o cadastro; `AC:mine` o mostrou no Discord em inglês.
6. `AC:edit` abriu seleção, formulário e confirmação privados em inglês.
   A alteração confirmada voltou à mesma linha da planilha: mesmo Record ID,
   revisão de 1 para 2. Nenhum ID/revisão foi digitado manualmente.
7. O idioma do servidor voltou para pt-BR. Repetir `/planilha criar` abriu o
   mesmo arquivo, sem outro formulário/e-mail, sem criar cópia e sem traduzir
   ou reformatar a planilha inglesa.
8. O cadastro de QA foi removido com confirmação no Discord e sua posição foi
   limpa pela sincronização. O histórico sintético foi preservado, como prevê
   o produto. Não foi apagado histórico real.
9. `/planilha abrir` → Desconectar confirmou sincronização desligada. Só depois
   o arquivo sintético foi enviado à lixeira pela conta proprietária do bot.
   O Google confirmou `trashed=true`; não houve exclusão permanente.

Arquivo do ensaio: `1tXQnC7r6UG-x-hc3C46YqwAyXK4oGQjoe19bFlQdinw`.
O ID serve para auditoria/restauração, não como planilha pública de exemplo.
`managed_sheets` conserva sua referência de retomada. Para repetir este mesmo
teste, restaure esse arquivo da lixeira antes de reconectar; não apague o pedido
no banco para forçar outra criação. O servidor terminou sem sincronização ativa
e em pt-BR, como começou.

## Alcance

Esta rodada fecha a lacuna de concessão real de edição e do fluxo inglês
Discord → Google → Discord. Complementa os ensaios nativos anteriores de
expansão 20→40→60, transferência, fórmulas, visor e layout, sem contá-los como
repetidos agora. Também não certifica toda concorrência de rede possível,
todas as combinações de contas Google ou todo o conteúdo da interface.

Não houve chamadas a modelos, alteração de escopo OAuth, mudança de permissões
de arquivos oficiais, troca de chave mestra ou restauração de banco de produção.
As evidências privadas de permissões e limpeza ficam no checkpoint local
`retomada-publico-2026-10-21/arquivista-ingles-discord-limpeza.json`.
