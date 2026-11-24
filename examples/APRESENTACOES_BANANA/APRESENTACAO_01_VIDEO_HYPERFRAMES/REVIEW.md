# REVIEW — Apresentacao 01: Ciclo de Vida da Banana (Musa spp.)

## Decisoes Criativas e Alternativas Nao Construidas
- **Escolha realizada**: *Cronica Subterranea* (documentario escuro `#0B0D0A` com acentos `#E2B43B` e `#3B6E47`, pranchas botanicas 16:9 e cinco instrumentos vetoriais SVG sincronizados a voz de `ap01_timings.json`).
- **Storylines descartadas**: *Microscopia do Fruto* (zoom continuo a partir do fruto maduro na bancada) e *Linha do Tempo Agronomica* (cronologia dia 0 a dia 360 com foco comercial).
- **Variacao de composicao e entradas**: Cena 01 abre com frame 0 ja povoado e push lento; Cena 02 aplica split editorial 60/40 com cortina vertical `clip-path`; Cena 03 ancora a prancha a direita com vetores de gravidade vs geotropismo negativo; Cena 04 usa palco bilateral com curva climaterica de etileno e barras percentuais de conversao amido-acucares; Cena 05 executa pull-out com anel fechado de sucessao e tese final imovel.

## O Que Foi Medido vs Inspecionado
- **Medido algoritmicamente**:
  - `npx hyperframes check --json --strict --samples 15`: `ok: true`, `lint` (`0` erros, `0` warnings, `7` arquivos), `runtime` (`0` erros), `layout` (`0` erros em 15 amostras), `contrast` (`51/51` aprovados), `craft` (`0` erros, `0` warnings em 480 amostras a 8 fps), `audio` (`0` erros).
  - `ffprobe apresentacao_01_ciclo_banana.mp4`: `1920x1080`, `30/1 fps`, `h264 (High)`, `yuv420p (bt709)`, `1800` frames, duracao exata `60.000000s`, audio `aac (LC)`, `48000 Hz`, `stereo`, `192 kb/s`, tamanho `57.083.421` bytes (`54.4 MB`).
  - `ffmpeg -af volumedetect`: `mean_volume: -20.4 dB`, `max_volume: -2.5 dB` (`0` clipping).
  - `npx hyperframes audio apresentacao_01_ciclo_banana.mp4 --json`: `lufsIntegrated: -17.3`, `lufsShortTermMax: -15.5`, `truePeakDb: -2.5`, `clipping.count: 0`.
- **Inspecionado visualmente (`read_file`)**:
  - `review-beats.jpg`, `review-phone.jpg`, `review-seam-01.jpg`, 5 snapshots intermediarios (`6s, 18s, 30s, 42s, 54s`), 5 snapshots tardios (`9.5s, 22s, 34s, 45.5s, 58.5s`) e 3 quadros decodificados diretamente do MP4 (`9.5s, 34.0s, 58.5s`).
- **Nao auditado auditivamente**: O audio foi medido por assinatura espectral, envelope e LUFS/dB, nao ouvido por dispositivo de reproducao humana.

## Ponto Mais Fraco e Melhorias Futuras
- A transicao `12.0s` (Cena 01 -> Cena 02) inicia a cortina vertical do zero (`inset(100% 0% 0% 0%)`), deixando a moldura esquerda vazia nos primeiros ~60 ms antes da prancha surgir; em iteracoes futuras, iniciar o `clipPath` em `inset(35% 0% 0% 0%)` reduz o flash escuro no corte seco.
- Warnings mantidos de proposito: nenhum (todos os gates passaram com zero warnings sob `--strict`).
