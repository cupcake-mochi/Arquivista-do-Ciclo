# Histórico de versões

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
