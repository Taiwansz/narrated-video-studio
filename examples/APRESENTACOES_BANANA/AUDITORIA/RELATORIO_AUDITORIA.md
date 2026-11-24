# Relatorio Consolidado de Auditoria Tecnica e Visual

Veredito Geral: **APROVADAS (2 / 2)**

## 1. Apresentacao 01 — Video MP4 HyperFrames (60s, Canal Dark Explainer)
- **MP4 Final**: `C:\Users\52319400\APRESENTACOES_BANANA\APRESENTACAO_01_VIDEO_HYPERFRAMES\apresentacao_01_ciclo_banana.mp4` (`57.083.421` bytes)
- **Projeto Fonte**: `C:\Users\52319400\APRESENTACOES_BANANA\APRESENTACAO_01_VIDEO_HYPERFRAMES\index.html` + `compositions/scene-01..05` + `compositions/captions.html`

### 1.1 Metricas `ffprobe` e `ffmpeg -af volumedetect`
- **Stream 0 (Video)**: `h264` (High), `yuv420p`, `bt709`, `1920x1080` (`16:9`), `30/1 fps`, `nb_frames: 1800`, `duration: 60.000000s`, `bit_rate: 7.411.681 bps`
- **Stream 1 (Audio)**: `aac` (LC), `48000 Hz`, `stereo` (2 canais), `duration: 60.000000s`, `bit_rate: 192.233 bps`
- **Loudness / Volume (`volumedetect`)**: `mean_volume: -20.4 dB`, `max_volume: -2.5 dB` (audio real presente, sem silencio mudo, sem clipping)

### 1.2 Gate `npx hyperframes check --json --strict --samples 15`
- **Status**: `ok: true`, `browserSkipped: false`
- **Lint**: `0` erros, `0` warnings (`filesScanned: 7`)
- **Runtime**: `0` erros, `0` warnings
- **Layout**: `0` erros em `15` amostras (`2s..58s`)
- **Contrast**: `51/51` aprovados (`0` erros)
- **Craft**: `0` erros em `480` amostras (`step: 0.125s`)
- **Audio**: `0` erros
- **Relatorio salvo**: `C:\Users\52319400\APRESENTACOES_BANANA\APRESENTACAO_01_VIDEO_HYPERFRAMES\.hyperframes\artifacts\checks\ed9ce5b0-10d7-44c1-b7f8-5be63ef62c24.json`

### 1.3 Inspecao Visual de Snapshots e Quadros do MP4
- **Snapshots HyperFrames** (`read_file`): `frame-00-at-9.5s.png`, `frame-01-at-22s.png`, `frame-02-at-34s.png`, `frame-03-at-45.5s.png`, `frame-04-at-58.5s.png` em `.hyperframes\artifacts\snapshots\074f6e53-f10e-44df-a2e2-2d4bed43d856\`
- **Quadros decodificados do MP4** (`read_file`): `mp4_cena_01_6.0s.png` .. `mp4_cena_05_54.0s.png` em `C:\Users\52319400\APRESENTACOES_BANANA\AUDITORIA\ap01_mp4_frames\`
- **Avaliacao**: Enquadramento fiel em 1920x1080, todas as 5 ilustracoes botanicas carregadas sem artefatos, diagramas vetoriais progressivos nitidos (ex.: transicao de amido 22% -> 2% e acucares 1% -> 19% na cena 04), legendas sincronizadas na zona segura inferior com fundo translucido e destaque por palavra, zero sobreposicoes quebradas.

---

## 2. Apresentacao 02 — Deck Editorial Botanico HTML Interativo (60s)
- **HTML Principal**: `C:\Users\52319400\APRESENTACOES_BANANA\APRESENTACAO_02_DECK_EDITORIAL_HTML\index.html` (`86.294` bytes)
- **Assets Locais**: `assets/01_rizoma_broto.png` .. `05_sucessao_perfilho.png`, `assets/ap02_narration.mp3`, `assets/ap02_timings.json`, `assets/ap02.srt`, `assets/ap02_cenas/cena_01..05.mp3`

### 2.1 Auditoria Estatica (`python -m engine.visual.cli audit`)
- **Status**: `passed: true` | **Score**: `100`
- **Erros / Warnings**: `errors: []`, `warnings: []`, `emojis_count: 0`
- **Metricas**: `has_css_variables: true`, `has_display_font: true`, `has_active_feedback: true`, `has_spring_physics: true`, `has_reduced_motion: true` (+ `prefers-reduced-transparency`, `tabular-nums`, scrub 1:1 com `setPointerCapture`).

### 2.2 Audio AP02 (`ffprobe` + `ffmpeg -af volumedetect`)
- **Formato**: `mp3`, `48000 Hz`, `stereo`, `192.206 bps`, `duration: 59.290000s`
- **Volume**: `mean_volume: -20.6 dB`, `max_volume: -3.8 dB`

### 2.3 Playwright via Servidor HTTP Local (`127.0.0.1`)
- **Script e Relatorio**: `C:\Users\52319400\APRESENTACOES_BANANA\AUDITORIA\audit_ap02.py` e `C:\Users\52319400\APRESENTACOES_BANANA\AUDITORIA\ap02_playwright_report.json`
- **Desktop (`1440x900`)**:
  - `console_errors: []`, `page_errors: []`, `failed_requests: []`, `bad_responses: []`
  - Geometria: `scrollWidth: 1440 / innerWidth: 1440`, `scrollHeight: 900 / innerHeight: 900` em todas as 5 cenas (zero overflow ou clipping; dock em `821..900px`).
  - Imagens: todas as 5 pranchas com `complete: true` e `1376x768`.
  - Audio no navegador: `readyState: 4`, `duration: 59.29s`, `error: null`. Clique em Reproduzir validado (`audioPaused: false`, `audioCurrentTime: 1.369689s`, destaque WordBoundary ativo). Troca das 5 cenas, clique no scrub (`00:39`, Estagio 04) e atalhos (`1`, `M`, `ArrowRight`) verificados.
- **Mobile (`390x844`)**:
  - `console_errors: []`, `page_errors: []`, `failed_requests: []`, `bad_responses: []`
  - Geometria: `scrollWidth: 390 / innerWidth: 390` (zero overflow horizontal), `dockHeight: 77px`.
  - Imagens (`1376x768`) e audio (`readyState: 4`, `duration: 59.29s`, `audioTime: 1.04694s`) validados.
- **Capturas inspecionadas (`read_file`)**: `desktop_play_cena1.png`, `desktop_cena_2.png` .. `desktop_cena_5.png`, `mobile_cena1_play.png`, `mobile_cena4.png` em `C:\Users\52319400\APRESENTACOES_BANANA\AUDITORIA\ap02_screenshots\`.

---

## 3. Varredura Global Anti-Slop e Zero Emojis
- **Arquivos escaneados**: `26` arquivos (`.html`, `.srt`, `.json`, `.md`) em `APRESENTACAO_01_VIDEO_HYPERFRAMES`, `APRESENTACAO_02_DECK_EDITORIAL_HTML` e `ROTEIRO_E_AUDIO`.
- **Resultado**: `0` emojis encontrados; `0` ocorrencias de `rounded-full` em codigo HTML/CSS/JS (unica ocorrencia textual encontrada e a clausula de proibicao em `APRESENTACAO_01_VIDEO_HYPERFRAMES\SPEC.md:25`).
