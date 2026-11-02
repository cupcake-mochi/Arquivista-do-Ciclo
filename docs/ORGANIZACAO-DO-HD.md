# Organização do HD externo · 02/11/2026

Em 02/11/2026 a pasta `/media/mizuki/HD Externo II/Claude/` (no Windows, `E:\Claude\`) foi reorganizada. O mapa completo está no `LEIA-ME.md` da raiz do HD, fora do git. Nada foi apagado: o que saiu foi para `Claude/_quarentena-2026-11/`, com um `MOVIMENTOS.csv` de origem e destino.

## O que mudou para este repositório

- **O repositório continua em `Claude/Arquivista-do-Ciclo/`.** Nenhum arquivo dele foi tocado.
- **O worktree `Claude/Arquivista-publico-21out/`** (ramo `codex/clareza-siglas`, limpo e igual ao remoto) foi para `Claude/_quarentena-2026-11/Arquivista-publico-21out/`. O registro dele continua em `.git/worktrees/`. Para limpar, rode no Linux, dentro de `Claude/Arquivista-do-Ciclo/`:

  ```
  git worktree prune
  ```

  Para trazer o worktree de volta, mova a pasta para o lugar antigo e rode `git worktree repair "../Arquivista-publico-21out"`.
- **`Claude/arquivista-referencia-20261020/`**, uma cópia solta do `main` sem git, também foi para a quarentena.
