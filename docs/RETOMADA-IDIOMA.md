# Idioma por servidor — etapa em desenvolvimento, 21/10/2026

Branch `codex/idioma-ingles`, baseada em `338cfda`. Trabalho isolado para preservar as alterações de fim de linha da cópia original.

Implementados `/language` e `/idioma`, tradução de interface e guias, aliases em inglês, idioma persistente por servidor e por planilha criada. Arquivos existentes continuam no idioma original. Banco e protocolo mantêm situações canônicas em português; nomes e dados dos membros não são traduzidos.

Validação parcial: 149 testes Python, 29 JS da ponte e 7 JS da planilha passaram. Google real: fórmulas inglesas, expansão 20→40→60, visor, contador, ISO e transferência passaram num arquivo sintético privado; foi enviado à lixeira. Falta concluir a revisão editorial e as páginas públicas, conferir o pacote e publicar com backup e comparação de fontes de produção. Testes reais no Discord com as duas contas seguem pendentes. Sem implantação nesta etapa até aqui. Nenhuma chamada paga.

Projeto Guias em paralelo na PR 68; preferências são independentes. Não alterar planilhas oficiais nem reformar planilhas existentes. Não fazer merge sem autorização específica.
