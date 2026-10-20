# Comandos e permissões

O prefixo é `AC:`; `ac:`, `Ac:` e espaços após `:` funcionam. Mensagens de bots, webhooks, DMs e outros servidores são ignoradas. Todas as funções abaixo também têm comando de barra.

## Consulta pública

| Chat | Barra | Resultado |
|---|---|---|
| `AC:ajuda` | `/ajuda` | Instruções da Amiya. Mostra a seção administrativa a quem tem permissão. |
| `AC:aparencias [@membro]` | `/aparencias [membro]` | Quinze aparências por página, com responsável. |
| `AC:minhas` | `/minhas` | A própria lista, sem precisar mencionar a si mesmo. |
| `AC:galeria [nome] [@membro]` | `/galeria [nome] [membro]` | Uma aparência por página, imagem maior e busca aproximada. |
| `AC:consultar nome` | `/consultar nome [obra]` | Pesquisa de aparências ocupadas. Na mensagem, a obra pode acompanhar o nome. |

Exemplos: `AC:galeria Takao`, `AC:galeria @Mizuki Takao`, `AC:consultar Takao Azur Lane`.

O resultado público tem aparência original, obra, responsável e imagem quando disponível. **Não mostra o nome secreto no servidor, situação, justificativa, data interna nem link da planilha.** O cadastro Liberado fica fora dessas listas. A ausência de resultado aproximado não prova disponibilidade: aliases não padronizados continuam exigindo revisão humana.

Quem abriu uma lista usa seus botões; outra pessoa pode abrir a própria consulta. A Amiya responde quando mencionada ou quando alguém responde a uma mensagem sua lembrada pelo bot, orientando aos comandos. Essa resposta é escrita no código: não é conversa livre com IA.

## Cadastro e edição

| Chat | Barra | Acesso e fluxo |
|---|---|---|
| `AC:registrar` | `/registrar [imagem]` | Qualquer membro. Abre atendimento privado, formulário, revisão e confirmação. |
| `AC:registrar @membro` | `/registrar membro [imagem]` | Só staff para terceiros. Autor e responsável permanecem distintos. |
| `AC:editar nome` | `/editar personagem [imagem]` | Membro: próprio nome no servidor/imagem. Staff: qualquer cadastro, também aparência e obra. |

No chat, anexe a imagem à mesma mensagem do comando. Por barra, use o parâmetro `imagem`. Isso requer o canal de imagens previamente configurado pela staff. Também se pode usar o campo de link HTTPS direto no formulário.

Não escreva uma justificativa secreta na mensagem pública. O formulário não publica as respostas no canal: mostra uma revisão privada antes de salvar. No campo de imagem da edição, `-` remove a imagem, inclusive quando ela estava inserida diretamente na célula.

O cadastro inicial recebe **Em preparação**. A staff pode mudar a situação depois. O primeiro cadastro bem-sucedido de alguém cria ou vincula sua linha em MEMBROS e associa um grupo livre, sem exigir ID digitado pelo jogador.

Não é preciso decorar UUID. Editar, remover e transferir apresentam uma seleção explícita por aparência/obra; uma correspondência aproximada não escolhe automaticamente o alvo.

## Administração

| Chat | Barra | Uso |
|---|---|---|
| `AC:situacao nome` | `/situacao personagem` | Escolher situação e escrever justificativa interna. Exige confirmação. |
| `AC:transferir nome @membro` | `/transferir personagem membro` | Muda o responsável preservando ID e data. |
| `AC:remover nome` | `/remover personagem` | Remove o cadastro ativo, mas não sua auditoria. Confirmação destacada. |
| `AC:historico [nome]` | `/historico [personagem]` | Histórico privado, inclusive registros removidos; vazio mostra eventos recentes. |
| `AC:registrarhistorico` | `/registrar_historico` | Usa o canal atual para as próximas notificações. |
| `AC:desativarhistorico` | `/desativar_historico` | Desliga o envio sem apagar histórico. |
| `AC:registrarimagens` | `/registrar_imagens` | Usa o canal atual para preservar os futuros anexos do cadastro. |
| `AC:desativarimagens` | `/desativar_imagens` | Interrompe novos uploads; preserva os antigos. |
| `AC:status` | `/status` | Contagem de cadastros, membros e eventos deste servidor, canais e avisos pendentes. |
| `AC:configurar` | `/configurar` | Só dono, Administrador ou quem gerencia o servidor: cargos de staff, canal de histórico e canal de imagens num painel privado. |

Os comandos de configuração exibem um botão de atendimento privado quando usados por `AC:`; abrir esse painel executa a configuração com nova checagem de permissão. Não criam/deletam canais nem alteram permissões do servidor.

**Staff** = dono do servidor, Administrador, quem tem Gerenciar Servidor ou membro de um dos cargos escolhidos no `/configurar` daquele servidor. A permissão é checada novamente nas operações finais; ter aberto um painel antes não mantém um privilégio removido.

## Situações

**Em preparação**, **Em uso** e **Arquivado** mantêm a aparência ocupada. **Liberado** permite que outro cadastro a utilize. Remoção e liberação são administrativas; mudar a aparência/obra também fica com a staff para não criar uma liberação disfarçada por edição.

A duplicidade usa aparência + obra normalizadas, ignorando maiúsculas e excesso de espaços. Não faz fusão automática de apelidos nem pressupõe que dois desenhos da mesma pessoa sejam referências diferentes.

## Histórico e prazo das notificações

Notificações são normalmente consumidas pelo ciclo de sincronização, configurado inicialmente em **90 segundos**, não necessariamente no mesmo instante do salvamento. Falhas do Google/Discord e limites de serviço podem aumentar o prazo.

A mensagem pública informa uma inclusão, remoção ou alteração genérica, com aparência, obra, responsável, autor quando conhecido e horário. Ela **não revela que um personagem está preparado, morto/arquivado ou liberado**, nem o conteúdo da justificativa. O detalhe completo fica em `/historico`, privadamente para staff.

Trocar o visor, abrir +/− e recalcular fórmulas não são alterações de personagem. A configuração do canal não republica todo o passado. A tela de histórico mostra até 200 resultados recentes dentro dos últimos 5.000 eventos, avisando quando houve corte; a auditoria original permanece na aba técnica.
