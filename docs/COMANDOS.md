# Comandos e permissões

Use `AC:` ou os comandos de barra. `ac:`, `Ac:` e espaços após `:` também funcionam. O bot atende nos servidores em que está instalado e ignora mensagens privadas, de bots e de webhooks.

## Consulta pública

| Chat | Barra | Resultado |
|---|---|---|
| `AC:ajuda` (`AC:aj`) | `/ajuda` | Instruções da Amiya. Mostra a seção administrativa a quem tem permissão. |
| `AC:guia` (`AC:tutorial`) | `/guia` | Passo a passo em páginas: o que é o arquivo, consultar, registrar, mudar, situações. Staff vê também as páginas de staff e de configuração. |
| `AC:aparencias [aparência] [@membro]` (`AC:ap`) | `/aparencias [aparencia] [membro] [modo]` | Quinze por página, com responsável. O botão **Ver em galeria** troca para uma por página, com imagem. |
| `AC:minhas` (`AC:min`) | `/aparencias membro:` você | A própria lista. Lista de uma pessoa só mostra a foto dela no canto e a obra em cada linha. |
| `AC:galeria [aparência] [@membro]` (`AC:gal`) | `/aparencias modo:galeria` | Já abre em galeria. |
| `AC:consultar aparência` (`AC:busca`) | `/aparencias aparencia:` | Busca aproximada; a obra pode ir junto do nome. |
| `AC:obra [nome]` (`AC:ob`) | `/obra [nome] [modo]` | Aparências de uma obra. Junta grafias parecidas: `arknights` acha "Arknights", "Arknights Endfield", "Endfield" e "arknighs". Sem nome, lista as obras do arquivo com quantas aparências cada uma tem e como ela também foi escrita. |

Exemplos: `AC:gal Takao`, `AC:gal @Mizuki Takao`, `AC:busca Takao Azur Lane`, `AC:obra endfield`.

**Como a obra é agrupada:** duas grafias ficam juntas quando todas as palavras de uma estão na outra (com erro de digitação tolerado em palavra de 5+ letras), quando o nome inteiro é quase igual ou contido no outro ("Umamusume" e "Uma Musume Pretty Derby"), ou quando uma é a sigla da outra ("HSR"). Junta como franquia: "Fate" puxa "Fate/stay night" e "Fate/Grand Order". Palavra comum de título sozinha não junta ("Love Live" e "Live A Live" ficam separadas). Apelido sem relação com o nome ("JJK") a staff cadastra com `/apelido`; o apelido junta os grupos e dá o nome do grupo.

As consultas públicas mostram aparência, obra, responsável e imagem quando disponível. **Nome do personagem no servidor, situação, justificativa, data interna e link da planilha ficam fora delas.** Cadastros com situação Liberado não aparecem nessas listas. Se a busca não encontrar um nome, tente também a obra: ele pode ter sido cadastrado com outra grafia. A conferência de duplicidade acontece ao salvar.

Quem abriu uma lista usa seus botões; outra pessoa pode abrir a própria consulta. A Amiya responde quando mencionada ou quando alguém responde a uma mensagem sua lembrada pelo bot, orientando aos comandos. Essa resposta é escrita no código: não é conversa livre com IA.

## Cadastro e edição

| Chat | Barra | Acesso e fluxo |
|---|---|---|
| `AC:registrar` (`AC:reg`) | `/registrar` | Qualquer membro. Pela barra o formulário abre na hora; pelo chat, num botão. Depois vem a revisão com a situação, e o "Salvo" aparece na mesma mensagem. |
| `AC:registrar @membro` | `/registrar membro` | Só staff para terceiros. Autor e responsável permanecem distintos. |
| `AC:editar aparência` (`AC:ed`) | `/editar aparencia` | Membro: próprio nome no servidor/imagem. Staff: qualquer cadastro, também aparência e obra. Escolhida a ficha, o formulário abre direto. |
| `AC:remover aparência` (`AC:rm`) | `/remover aparencia` | Membro: remove um cadastro próprio, com confirmação. Staff: também remove de outras pessoas. A auditoria fica preservada. |

A imagem pode ir pelo link HTTPS no formulário ou pelo campo de anexo do próprio formulário. No chat, também dá pra anexar à mensagem do comando. O anexo precisa do canal de imagens escolhido no `/configurar`.

Não escreva uma justificativa secreta na mensagem pública. O formulário não publica as respostas no canal: mostra uma revisão privada antes de salvar. No campo de imagem da edição, `-` remove a imagem, inclusive quando ela estava inserida diretamente na célula.

Quem registra escolhe a situação na revisão, antes de confirmar; sem escolher, fica **Em preparação**. Depois, só a staff muda a situação. Na planilha conectada, o primeiro cadastro cria a aba do membro automaticamente. Para preencher antes de cadastrar pelo bot, a gerência usa `/planilha membro` e seleciona o @membro real do servidor.

Você pode buscar pelo nome, sem decorar o ID da ficha. Antes de editar, remover ou transferir, escolha a aparência e a obra na lista de resultados. A busca não faz essa escolha por você.

## Administração

| Chat | Barra | Uso |
|---|---|---|
| `AC:situacao aparência` (`AC:sit`) | `/situacao aparencia` | Escolher situação e escrever justificativa interna. Exige confirmação. |
| `AC:transferir aparência @membro` (`AC:tr`) | `/transferir aparencia membro` | Muda o responsável preservando ID e data. |
| `AC:limpar @membro` ou `AC:limpar ID` | `/limpar [membro] [id]` | Apaga **todos** os cadastros de uma pessoa, inclusive quem já saiu do servidor (pelo ID do Discord). Só `AC:limpar` lista quem tem cadastro e saiu, com o ID. A confirmação mostra quantos são e quais; se alguém cadastrar ou remover algo no meio, pede de novo. A auditoria fica e o canal de histórico recebe um aviso só. |
| `AC:apelido JJK = Jujutsu Kaisen` (`AC:apl`) | `/apelido acao apelido obra` | Apelido de obra deste servidor para a busca por obra. `AC:apelido -JJK` tira, `AC:apelido` lista (até 500). |
| `AC:historico [aparência]` (`AC:hist`) | `/historico [aparencia]` | Histórico privado, inclusive registros removidos; vazio mostra eventos recentes. |
| `AC:diagnostico` (`AC:diag`, `AC:st`) | `/diagnostico` | Cadastros, membros, eventos, canais, avisos pendentes e estado da planilha (envios pendentes, último envio, último erro). |
| `AC:restaurar` com o .json anexado | `/restaurar arquivo` | Só gerência. Volta o arquivo para um backup: mostra quantos cadastros vêm e quantos atuais serão substituídos, e só grava no botão **Restaurar**. Os cadastros substituídos ficam no `/historico`, e a planilha conectada é regravada. |
| `AC:configurar` (`AC:cfg`) | `/configurar` | Só dono, Administrador ou quem gerencia o servidor: cargos de staff, canal de histórico, canal de imagens, planilha e backup num painel privado. |
| `AC:planilha` | `/planilha abrir` | Só gerência: painel privado da planilha e acesso ao arquivo. |
| Pelo painel de planilha | `/planilha criar` | Pede e-mail Google em formulário privado, cria o arquivo pronto e concede edição. Repetir reutiliza o mesmo arquivo; não substitui uma conexão antiga. Requer ativação Google única do mantenedor. |
| — | `/planilha membro membro:@pessoa` | Só gerência: prepara uma aba vazia para preencher manualmente. Exige selecionar um membro real do servidor e confirma que ele ainda está presente. Texto livre, apelido e ID digitado não servem. |

Os comandos de configuração exibem um botão de atendimento privado quando usados por `AC:`; abrir esse painel executa a configuração com nova checagem de permissão. Não criam/deletam canais nem alteram permissões do servidor.

**Backup:** no `/configurar` → **Backup**, escolha um canal só da staff e a frequência (6 h, 12 h, 1 dia, 3 dias ou 1 semana). O `.json` serve para recuperar os cadastros pelo `/restaurar`. Com a planilha conectada, o bot envia também um `.xlsx`, com uma aba por membro. Como os arquivos incluem justificativas e nomes dos personagens no servidor, o canal não pode ter acesso de cargos ou membros individuais fora da staff. **Fazer backup agora** envia uma cópia na hora. O JSON não inclui todas as configurações e o histórico do banco; o mantenedor também precisa guardar uma cópia completa da hospedagem.

**Quem conta como staff:** dono do servidor, quem tem Administrador ou Gerenciar Servidor e membros dos cargos escolhidos no `/configurar`. O bot confere o acesso novamente antes de salvar; um painel antigo não mantém uma permissão que foi retirada.

## Situações

**Planilha pronta:** cadastro e edição funcionam pelo Discord e diretamente no Sheets. As edições do Sheets entram no bot em cerca de cinco minutos, passam pela mesma validação e as recusas aparecem no `/diagnostico`. Começa com 20 posições por membro e ganha mais 20 quando faltam duas livres. Preserve as fórmulas e colunas de identificação; não insira/apague linhas no meio das fichas. Para remover um cadastro, use `/remover` ou `/limpar`. Compartilhe edição apenas com a staff. Desconectar só desliga a sincronização, preservando arquivo e permissões.

**Em preparação**, **Em uso** e **Arquivado** mantêm a aparência ocupada. **Liberado** permite que outro cadastro a utilize. Cada membro pode remover os próprios cadastros; só a staff remove cadastros de outras pessoas, muda situação, aparência ou obra e usa `/limpar`.

A duplicidade usa aparência + obra normalizadas, ignorando maiúsculas e excesso de espaços. Não faz fusão automática de apelidos nem pressupõe que dois desenhos da mesma pessoa sejam referências diferentes.

## Histórico e prazo das notificações

Notificações são normalmente consumidas pelo ciclo de sincronização, configurado inicialmente em **90 segundos**, não necessariamente no mesmo instante do salvamento. Falhas do Google/Discord e limites de serviço podem aumentar o prazo.

A mensagem pública informa uma inclusão, remoção ou alteração genérica, com aparência, obra, responsável, autor quando conhecido e horário. Ela **não revela que um personagem está preparado, morto/arquivado ou liberado**, nem o conteúdo da justificativa. O detalhe completo fica em `/historico`, privadamente para staff.

Trocar o visor, abrir +/− e recalcular fórmulas não cria uma mudança na ficha. Configurar o canal também não republica os avisos antigos. A consulta de histórico mostra até 200 resultados recentes e avisa quando há mais; o histórico completo continua no banco do bot.
