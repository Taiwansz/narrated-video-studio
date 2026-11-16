# SPEC: Architecture

## Topologia de Componentes
1. **Camada Cognitiva (`.agents/skills/narrated-video-studio/` + `SKILL.md`):**
   - Orquestra o agente em 7 fases: Brief -> 3 Storylines -> `SPEC.md` -> Matematica de Roteiro -> Sintese de Audio e Timings -> Ativos Visuais -> Coreografia HyperFrames -> QA e Render.
   - Delega contrato de timeline, snapshots e render para `hyperframes` e `hyperframes-cli`, componentes prontos para `hyperframes-registry`, e aquisicao/tratamento de midia para `media-use`.
2. **Camada Deterministica (`scripts/narrated_video_cli.py`):**
   - Python >= 3.10 utilizando apenas `stdlib` + `edge-tts` + binarios externos `ffmpeg`/`ffprobe` e `npx hyperframes`.
   - Toda saida estruturada e gravada em arquivos JSON/SRT/HTML/MP3 via `--output` / `--output-dir`, mantendo `stdout` enxuto.
3. **Camada de Referencia (`examples/ciclo-da-banana-60s/`):**
   - Contem a implementacao completa e validada de 60 segundos (`1800` frames, `5` cenas de `12s`, `140` palavras faladas em `55.51s`, `-17.3 LUFS`).

## Complexidade e Fluxo de Dados
- Agrupamento de legendas (`build_caption_groups`): passo unico linear $O(W)$ sobre a lista de $W$ palavras `WordBoundary` com divisao balanceada para evitar orfas de 1 palavra.
- Resolucao de sobreposicoes de legendas: varredura unica $O(G)$ garantindo invariante `caption[k].end < caption[k+1].start`.
- Sintese de cenas: concorrencia assincrona `asyncio.gather` limitada e governada por rate limiter monotonico (`time.monotonic()`), seguido de normalizacao uniforme em um unico passe de loudness para evitar variacao de ganho entre cenas.
