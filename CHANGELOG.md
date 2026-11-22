# Histórico de versões

## 1.3.1 · 22/11/2026

**Imagem colada por link do Discord deixa de sumir da planilha.** Link de anexo do Discord vale cerca de 24 horas. O app do Discord renova sozinho, por isso a imagem continuava aparecendo no bot, mas a planilha recebia o link vencido e ficava em branco. Até aqui só eram renovadas as imagens enviadas como anexo, que o bot guarda no canal de imagens. Agora, em servidor com planilha e canal de imagens, o bot também "adota" o link colado à mão, seja pelo bot ou digitado na planilha: pega um link válido (pedindo ao Discord um novo quando o colado já venceu), baixa a imagem só do próprio Discord, até 8 MB e só PNG, JPEG, GIF ou WebP, reenvia no canal de imagens e troca o link no cadastro e na planilha. Não cria revisão nem evento, igual à renovação diária. O mesmo anexo em dois cadastros sobe uma vez só. São 10 por volta, e o que não der certo volta a ser tentado em 6 horas; o `/diagnostico` mostra quantas imagens coladas esperam cópia ou não puderam ser copiadas.

Publicada na Discloud em 22/11/2026, às 18:43 (horário de Brasília), pelo commit do ZIP de 29 arquivos, sem banco nem credenciais. O Discord aceitou o pedido de link novo para anexos já vencidos. Em três voltas (18:43, 18:45 e 18:46), o bot guardou as 29 imagens coladas da planilha do Era da Revolução, sem nenhuma falha: 28 já vencidas e uma que venceria no dia seguinte. Depois disso, a planilha não tinha nenhum link do Discord colado nem vencido (63 links do Discord, todos guardados pelo bot), e as imagens que estavam em branco voltaram a aparecer no site. Política de privacidade pública atualizada nas duas línguas.

## 1.3.0 · 22/11/2026

**Vermelho entre abas.** A planilha pinta de vermelho a aparência quando a mesma aparência + obra já tem cadastro em outra linha, de qualquer aba, inclusive na linha digitada à mão que ainda não tem ID. A comparação segue a do bot: ignora maiúsculas e espaços extras, e Liberado não conta. A regra anterior só comparava fichas da mesma aba e só linhas com ID, por isso não pegava o caso mais comum. Uma guia escondida, "Índice (bot)", junta as chaves dos cadastros; o bot a mantém quando cria ou renomeia abas.

Planilhas já existentes recebem o índice e a regra na primeira leitura depois da atualização, num pedido único que só acrescenta a guia escondida, a formatação e o texto de ajuda novo. Nenhuma ficha é regravada.

**Situação nas consultas.** Lista, galeria, busca e `/obra` mostram a situação de cada aparência. As liberadas voltam a aparecer, no fim, marcadas como livres. A justificativa continua só com a staff; os avisos do canal de histórico não mudam.

**Até 400 cadastros por membro** (antes 200). Liberados continuam contando, porque ocupam posição na planilha.

Publicada na Discloud em 22/11/2026, às 17:58 (horário de Brasília), pelo commit do ZIP de 29 arquivos, sem banco nem credenciais. Na planilha real do Era da Revolução, a migração rodou sozinha na primeira leitura: texto de ajuda novo em todas as abas, fichas intactas, e a linha digitada à mão que repetia "Don Quixote / Project Moon" ficou vermelha, enquanto a cadastrada continuou normal. No Discord, `AC:obra Project Moon` mostrou `Em uso` e `Em preparação`, e `AC:ap Archetto` mostrou `Liberado · livre` no fim da lista. Logs sem erro de planilha depois da subida. O backup manual da hospedagem não foi baixado antes do commit, porque o ZIP não leva o banco.

## 1.2.0 · 22/10/2026

Importação confirmada pela interface real do Discord em servidor temporário, com três cadastros fictícios. Cancelamento em português, operação completa em inglês, recusa de conta sem Gerenciar servidor e sincronização nos dois sentidos aprovados. Produção auditada: 29 fontes do pacote iguais, 19 cadastros e três conexões anteriores preservados. Guia público, privacidade e termos atualizados em português e inglês. Google Picker real validado com origem externa: conta dedicada, somente o arquivo selecionado, escopo mantido e credenciais existentes preservadas. A importação dessa origem também passou pela interface do Discord; o bot tinha apenas leitura no original. Cinco planilhas sintéticas enviadas à lixeira recuperável e servidor temporário excluído após confirmação do usuário.

`/planilha importar` e botão **Importar existente**: importação autorizada de cadastros para uma nova planilha por servidor, com prévia privada, novos IDs e edição somente na cópia. O original e sua sincronização ficam preservados. Cancelamento, revisão do acesso e retomada usam o mesmo banco e a criação idempotente já existente.

A origem precisa estar acessível ao aplicativo com `drive.file`; o mantenedor pode autorizar um arquivo específico pelo Picker oficial, sem ampliar escopos nem trocar credenciais. Registros existentes no destino não são mesclados ou substituídos. Veja `docs/IMPORTAR-PLANILHA.md`.

## 1.1.0 · 21/10/2026

Idioma por servidor: português ou inglês, com autorização da gerência ou de cargos de staff cadastrados. Interface, formulários, guias e mensagens em inglês; aliases ingleses disponíveis. Dados dos membros e códigos internos permanecem canônicos.

Planilhas gerenciadas novas seguem o idioma escolhido na criação. Arquivos existentes conservam localidade, idioma, acesso e sincronização; não são convertidos pela troca de idioma do servidor. Documentação pública bilíngue e preferências independentes das Guias.

Publicada e auditada: 27 arquivos instalados iguais ao pacote, bancos/WAL íntegros e dados anteriores preservados. 149 testes Python e 36 JavaScript; ensaio privado Google com fórmulas, expansão e transferência; Discord com duas contas, idiomas e permissões. A concessão real de editor por e-mail não foi repetida nesta rodada. Detalhes em docs/RETOMADA-IDIOMA.md.

## 1.0.3 · 20/10/2026

Cada membro pode remover os próprios cadastros pelo `/remover` ou `AC:rm`, com confirmação. A permissão e a revisão da ficha são conferidas novamente ao salvar; transferir a ficha revoga o acesso do antigo responsável. A auditoria fica preservada e a remoção segue para a planilha.

Cadastros de outras pessoas, mudanças de situação, transferências e limpeza em lote continuam restritos à staff. Ajuda, guia e documentos públicos atualizados.

Amiya só é acionada por menção direta à conta ou ao cargo automático vinculado a ela, além dos comandos e respostas às próprias mensagens. `@everyone`, `@here`, cargos genéricos e cargos de outros bots não a chamam.

## 1.0.2 · 20/10/2026

As consultas por aparência, obra ou membro e a galeria agora mostram também o nome do personagem no servidor. O campo continua opcional e pode ser editado pelo responsável. Situação e justificativa permanecem privadas. As listas mostram até 12 fichas por página para acomodar o nome dentro do limite do Discord.

Atualização sem mudança no banco ou na conexão das planilhas.

## 1.0.1 · 20/10/2026

Revisão dos textos da Amiya: ajuda, guia, formulários, confirmações, avisos e instruções das planilhas. As mensagens estão mais curtas e os exemplos acompanham o que o bot faz. O guia público, a política de privacidade e os termos também foram revisados, mantendo suas regras e condições.

Corrigidas duas orientações: a consulta de histórico mostra até 200 resultados recentes guardados no banco, e novas variáveis da Discloud precisam de rebuild ou deploy. As regras de cadastro, permissões e sincronização continuam as mesmas.

## 1.0.0 · 20/10/2026

- Planilha privada pronta pelo `/planilha criar`, com formulário de e-mail, edição concedida e sincronização nos dois sentidos. Donos de servidor não instalam scripts.
- `/planilha abrir` e `AC:planilha` recuperam o link; `/planilha membro` aceita somente um membro real do servidor. Abas crescem de 20 em 20 posições perto do limite.
- Cadastros, auditoria, confirmações e filas persistidos no SQLite; consultas públicas e atendimento privado com permissões distintas.
- Backup periódico em JSON/XLSX e restauração com confirmação. A proteção do canal também verifica permissões individuais, além de cargos.
- Guia público atualizado e documentação técnica corrigida para a arquitetura atual.

Validação: 165 testes automatizados aprovados, duas contas Discord, transferência/edição/remoção apenas de fichas fictícias, sincronização com Google real e restauração de um backup real em cópia isolada. Consulte `docs/TESTES.md` para cenários e limites.
