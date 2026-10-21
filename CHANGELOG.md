# Histórico de versões

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
