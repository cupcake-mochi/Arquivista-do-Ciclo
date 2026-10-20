# Segurança, arquitetura e limites · 1.0

## Banco e recuperação

O SQLite da hospedagem é a fonte dos cadastros, auditoria, configurações, confirmações idempotentes e filas. A atualização de uma ficha e a criação de seu evento/fila ocorrem na mesma transação. A planilha é uma interface de edição sincronizada; ela não substitui o banco nem guarda uma cópia completa da auditoria.

Preserve `dados/arquivista.sqlite3` e as credenciais da hospedagem. Para copiar o banco em execução, use a API de backup do SQLite, que inclui o estado confirmado do WAL; copiar só o arquivo principal pode perder alterações recentes. Rode uma única instância por banco.

O backup pelo Discord exporta os cadastros em JSON e, com planilha conectada, um XLSX com uma guia por membro. O JSON não exporta a auditoria antiga, as configurações nem as credenciais. `/restaurar` valida o JSON e pede confirmação antes de substituir os cadastros do servidor; preserva o histórico que já existe no banco e sincroniza o resultado com a planilha. Um backup completo da hospedagem continua necessário para recuperar todo o serviço.

## Planilha pronta e acesso Google

O mantenedor configura OAuth com escopo `drive.file`, usando uma conta dedicada. O bot cria arquivos nessa conta e concede edição ao e-mail informado pela gerência em formulário privado. O arquivo permanece privado. Repetir `/planilha criar` reutiliza o arquivo registrado; o marcador persistente do pedido permite procurar uma criação cuja resposta se perdeu. A retomada após compartilhar não reformata abas que o editor possa ter alterado.

As credenciais Google ficam nas variáveis da hospedagem. O e-mail do editor e as chaves de conexões antigas ficam cifrados no banco, autenticados por HMAC. Preserve `AC_MASTER_KEY`; quando ausente, a chave deriva do token Discord, e trocar esse token exige recuperar/reconectar os valores cifrados. Não publique `.env`, JSON de cliente OAuth ou backups do banco.

Desconectar encerra a sincronização, sem apagar o arquivo ou revogar permissões Google. O dono da conta deve administrar acessos e exclusões. Edição no Sheets dá acesso aos cadastros internos do servidor: conceda apenas à staff. `/planilha membro` exige um membro real do mesmo servidor e revalida sua presença; texto livre não cria abas.

Conexões legadas por Apps Script continuam disponíveis. Cada pedido da ponte usa assinatura HMAC-SHA256, servidor, autor, timestamp e identificador; a chave não vai na URL. O script usa trava compartilhada para suas operações. O fluxo novo acessa diretamente as APIs Google e dispensa instalação de script pelo dono do servidor.

## Sincronização e concorrência

Mudanças do bot entram em uma fila SQLite durável. A reconciliação procura edições manuais aproximadamente a cada cinco minutos, valida os dados e registra eventos de origem planilha, sem atribuir um autor Discord não identificado. Campos alterados manualmente podem ser conciliados com mudanças do bot; revisões antigas são recusadas. A fila usa retentativas com espera e expõe erros no diagnóstico.

As requisições de uma `spreadsheets.batchUpdate` são atômicas entre si; a leitura anterior e a escrita não formam uma transação com o mouse do editor. Não há garantia de capturar cada edição intermediária nem de impedir toda corrida entre uma edição humana e o envio do bot. Evite editar a mesma ficha simultaneamente nos dois lugares.

Cada aba nova começa com 20 posições e cresce em blocos de 20 quando restam duas livres. Não há limite fixo de 100 membros/200 posições do modelo antigo no fluxo novo. Continuam valendo limites e cotas dos serviços. Não foram feitos testes de carga em grande escala. Preserve fórmulas, IDs, revisões e linhas das fichas: uma estrutura quebrada interrompe as gravações daquela aba. Apagar uma ficha manualmente não a remove do bot; use `/remover`.

## Permissões e privacidade no Discord

Consultas públicas usam uma lista explícita de campos, sem situação, justificativa ou nome interno. Formulários, confirmações e consultas internas usam interações privadas. O prefixo `AC:` abre um botão público para atendimento privado; segredos digitados na própria mensagem pública já estarão expostos.

Membros gerenciam seus próprios campos permitidos. Situação, transferência, remoção, limpeza e auditoria exigem staff. Configuração, planilha e restauração exigem dono, Administrador ou Gerenciar Servidor. As gravações reconsultam o membro no Discord; perder o cargo não mantém autorização de um painel antigo. Os painéis também conferem quem os abriu.

Backups contêm dados internos. O bot verifica suas permissões de envio, recusa acesso de @everyone, cargos comuns com acesso ao canal e permissões individuais que concedem acesso a membros sem autorização de staff. A verificação se repete a cada envio. Administradores e quem pode gerenciar o servidor têm acesso de gerência; aplicativos com permissões administrativas também podem ver canais privados no Discord.

Notificações públicas de alterações não incluem situação/justificativa. O histórico detalhado permanece no SQLite; a consulta mostra até 200 eventos correspondentes recentes e avisa quando há corte. Notificações são entregues por fila independente da gravação. A recuperação busca até 100 mensagens recentes: não há garantia absoluta de entrega exatamente uma vez entre serviços independentes.

## Imagens

Links externos não são baixados pela hospedagem. O bot aceita URLs HTTPS validadas e anexos PNG/JPEG/GIF/WebP de até 8 MB, conferindo assinatura básica; isso não é análise antimalware. Anexos são preservados no canal configurado. A referência da mensagem permite recuperar URLs temporárias no Discord, tanto em consultas quanto na renovação em segundo plano. Apagar a mensagem ou retirar acesso pode quebrar a imagem.

Arquivos novos habilitam a propriedade Google de acesso externo para fórmulas de imagem durante a inicialização; ela não é regravada quando já habilitada. Conexões antigas não são modificadas automaticamente. Não há limpeza automática de imagens órfãs após uma gravação ambígua. A imagem da Amiya fornecida ao projeto foi preservada, sem comprovação de licença comercial.

## Evidência de validação

Os cenários e os limites do que foi exercitado estão em `TESTES.md` e `RESULTADO_TESTES.txt`. Testes simulados não demonstram disponibilidade, cotas ou latência reais do Google, Discord e Discloud. Os ensaios de expansão usam dados fictícios; as operações de remoção usam apenas fichas de teste identificadas.

Referências primárias: [SQLite Backup API](https://www.sqlite.org/backup.html), [OAuth drive.file](https://developers.google.com/workspace/drive/api/guides/api-specific-auth), [Sheets batchUpdate](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets/batchUpdate), [permissões Discord](https://docs.discord.com/developers/topics/permissions).
