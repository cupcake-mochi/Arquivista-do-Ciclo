# Idioma por servidor — etapa em desenvolvimento, 21/10/2026

Branch `codex/idioma-ingles`, baseada em `338cfda`. Trabalho isolado para preservar as alterações de fim de linha da cópia original.

Implementados `/language` e `/idioma`, tradução de interface e guias, aliases em inglês, idioma persistente por servidor e por planilha criada. Arquivos existentes continuam no idioma original. Banco e protocolo mantêm situações canônicas em português; nomes e dados dos membros não são traduzidos.

Validação parcial: 143 testes Python passaram, incluindo oito regressões de criação/expansão/transferência/idioma fixo e isolamento concorrente. Falta revisão das mensagens de erro, autorização dos comandos, backup inglês, localização dos menus nativos, testes JS, suíte final e publicação autorizada com backup e comparação de fontes de produção. Sem implantação nesta etapa até aqui. Nenhuma chamada paga.

Projeto Guias em paralelo na PR 68; preferências são independentes. Não alterar planilhas oficiais nem reformar planilhas existentes. Não fazer merge sem autorização específica.
