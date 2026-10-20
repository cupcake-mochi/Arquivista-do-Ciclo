# Comandos e permissões

O prefixo é `AC:`; `ac:`, `Ac:` e espaços após `:` funcionam. Mensagens de bots, webhooks, DMs e outros servidores são ignoradas. Todas as funções abaixo também têm comando de barra.

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

O resultado público tem aparência original, obra, responsável e imagem quando disponível. **Não mostra o nome secreto no servidor, situação, justificativa, data interna nem link da planilha.** O cadastro Liberado fica fora dessas listas. A ausência de resultado aproximado não prova disponibilidade: aliases não padronizados continuam exigindo revisão humana.

Quem abriu uma lista usa seus botões; outra pessoa pode abrir a própria consulta. A Amiya responde quando mencionada ou quando alguém responde a uma mensagem sua lembrada pelo bot, orientando aos comandos. Essa resposta é escrita no código: não é conversa livre com IA.

## Cadastro e edição

| Chat | Barra | Acesso e fluxo |
|---|---|---|
| `AC:registrar` (`AC:reg`) | `/registrar` | Qualquer membro. Pela barra o formulário abre na hora; pelo chat, num botão. Depois vem a revisão com a situação, e o "Salvo" aparece na mesma mensagem. |
| `AC:registrar @membro` | `/registrar membro` | Só staff para terceiros. Autor e responsável permanecem distintos. |
| `AC:editar aparência` (`AC:ed`) | `/editar aparencia` | Membro: próprio nome no servidor/imagem. Staff: qualquer cadastro, também aparência e obra. Escolhida a ficha, o formulário abre direto. |

A imagem pode ir pelo link HTTPS no formulário ou pelo campo de anexo do próprio formulário. No chat, também dá pra anexar à mensagem do comando. O anexo precisa do canal de imagens escolhido no `/configurar`.

Não escreva uma justificativa secreta na mensagem pública. O formulário não publica as respostas no canal: mostra uma revisão privada antes de salvar. No campo de imagem da edição, `-` remove a imagem, inclusive quando ela estava inserida diretamente na célula.

Quem registra escolhe a situação na revisão, antes de confirmar; sem escolher, fica **Em preparação**. Depois, só a staff muda a situação. O primeiro cadastro bem-sucedido de alguém cria ou vincula sua linha em MEMBROS e associa um grupo livre, sem exigir ID digitado pelo jogador.

Não é preciso decorar UUID. Editar, remover e transferir apresentam uma seleção explícita por aparência/obra; uma correspondência aproximada não escolhe automaticamente o alvo.

## Administração

| Chat | Barra | Uso |
|---|---|---|
| `AC:situacao aparência` (`AC:sit`) | `/situacao aparencia` | Escolher situação e escrever justificativa interna. Exige confirmação. |
| `AC:transferir aparência @membro` (`AC:tr`) | `/transferir aparencia membro` | Muda o responsável preservando ID e data. |
| `AC:remover aparência` (`AC:rm`) | `/remover aparencia` | Remove o cadastro ativo, mas não sua auditoria. Confirmação destacada. |
| `AC:limpar @membro` ou `AC:limpar ID` | `/limpar [membro] [id]` | Apaga **todos** os cadastros de uma pessoa, inclusive quem já saiu do servidor (pelo ID do Discord). Só `AC:limpar` lista quem tem cadastro e saiu, com o ID. A confirmação mostra quantos são e quais; se alguém cadastrar ou remover algo no meio, pede de novo. A auditoria fica e o canal de histórico recebe um aviso só. |
| `AC:apelido JJK = Jujutsu Kaisen` (`AC:apl`) | `/apelido acao apelido obra` | Apelido de obra deste servidor para a busca por obra. `AC:apelido -JJK` tira, `AC:apelido` lista (até 500). |
| `AC:historico [aparência]` (`AC:hist`) | `/historico [aparencia]` | Histórico privado, inclusive registros removidos; vazio mostra eventos recentes. |
| `AC:diagnostico` (`AC:diag`, `AC:st`) | `/diagnostico` | Cadastros, membros, eventos, canais, avisos pendentes e estado da planilha (envios pendentes, último envio, último erro). |
| `AC:configurar` (`AC:cfg`) | `/configurar` | Só dono, Administrador ou quem gerencia o servidor: cargos de staff, canal de histórico, canal de imagens, planilha e backup num painel privado. |

Os comandos de configuração exibem um botão de atendimento privado quando usados por `AC:`; abrir esse painel executa a configuração com nova checagem de permissão. Não criam/deletam canais nem alteram permissões do servidor.

**Backup:** no `/configurar` → **Backup**, escolha um canal fechado para @everyone e a frequência (6 h, 12 h, 1 dia, 3 dias ou 1 semana). O bot manda um `.json` que restaura o arquivo (`python importar.py arquivo.json --servidor ID --aplicar`, num banco sem cadastros desse servidor) e, se houver planilha conectada, um `.xlsx` com uma guia por membro. O backup leva justificativas e nomes no servidor; por isso o bot recusa canal aberto. **Fazer backup agora** manda um na hora.

**Staff** = dono do servidor, Administrador, quem tem Gerenciar Servidor ou membro de um dos cargos escolhidos no `/configurar` daquele servidor. A permissão é checada novamente nas operações finais; ter aberto um painel antes não mantém um privilégio removido.

## Situações

**Em preparação**, **Em uso** e **Arquivado** mantêm a aparência ocupada. **Liberado** permite que outro cadastro a utilize. Remoção e liberação são administrativas; mudar a aparência/obra também fica com a staff para não criar uma liberação disfarçada por edição.

A duplicidade usa aparência + obra normalizadas, ignorando maiúsculas e excesso de espaços. Não faz fusão automática de apelidos nem pressupõe que dois desenhos da mesma pessoa sejam referências diferentes.

## Histórico e prazo das notificações

Notificações são normalmente consumidas pelo ciclo de sincronização, configurado inicialmente em **90 segundos**, não necessariamente no mesmo instante do salvamento. Falhas do Google/Discord e limites de serviço podem aumentar o prazo.

A mensagem pública informa uma inclusão, remoção ou alteração genérica, com aparência, obra, responsável, autor quando conhecido e horário. Ela **não revela que um personagem está preparado, morto/arquivado ou liberado**, nem o conteúdo da justificativa. O detalhe completo fica em `/historico`, privadamente para staff.

Trocar o visor, abrir +/− e recalcular fórmulas não são alterações de personagem. A configuração do canal não republica todo o passado. A tela de histórico mostra até 200 resultados recentes dentro dos últimos 5.000 eventos, avisando quando houve corte; a auditoria original permanece na aba técnica.
