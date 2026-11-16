# Narrated Video Studio - Mapa Completo da Arquitetura

Este documento mapeia todas as camadas, fluxos de dados, invariantes temporais e fronteiras de responsabilidade do repositorio.

## 1. Fluxo Ponta a Ponta (Conteudo Bruto -> Video MP4 1080p)

```text
  [Tema / Texto / PDF]
          |
          v
  +-----------------------+
  | 1. Roteiro & Tempo    | --> script.json (24-30 palavras / slot de 12s)
  +-----------------------+
          |
          +----------------------------------------+
          |                                        |
          v                                        v
  +-------------------------------+        +-------------------------------+
  | 2A. narrated_video_cli.py     |        | 2B. Geracao de Placas 16:9    |
  |     synth-audio --ambient     |        |     (image-generator / FLUX)  |
  | - MonotonicRateLimiter        |        | - Zero texto embutido         |
  | - edge-tts WordBoundary       |        | - Inspecao visual obrigatoria |
  | - Gain uniforme (-17 LUFS)    |        +-------------------------------+
  | - Ambient pad (-24 LUFS)      |                        |
  +-------------------------------+                        |
          |                                                |
          +------------------------+-----------------------+
                                   |
                                   v
  +-------------------------------------------------------------------+
  | 3. narrated_video_cli.py scaffold-video + build-captions          |
  | - index.html (root timeline, 1920x1080@30fps, audio tracks 3 & 4) |
  | - compositions/captions.html (34+ blocos WordBoundary title-safe) |
  | - compositions/scene-01..NN.html (GSAP + SVGs sincronizados)      |
  +-------------------------------------------------------------------+
                                   |
                                   v
  +-------------------------------------------------------------------+
  | 4. Quality Gates & Render (HyperFrames + FFmpeg + CLI Audit)      |
  | - npx hyperframes check --json --strict --samples 15              |
  | - npx hyperframes snapshot --review & midpoints (read_file)       |
  | - npx hyperframes render --quality delivery --output final.mp4    |
  | - narrated_video_cli.py audit --mp4 final.mp4 --strict-hyperframes|
  +-------------------------------------------------------------------+
```

## 2. Mapa de Arquivos do Repositorio

| Caminho | Funcao |
| :--- | :--- |
| `SKILL.md` | Espelho na raiz para descoberta automatica em instaladores de skills |
| `.agents/skills/narrated-video-studio/SKILL.md` | Definicao canonica da skill para Antigravity, Codex, Claude Code e Gemini CLI |
| `.agents/skills/narrated-video-studio/references/01_script_and_timing_math.md` | Matematica de palavras/minuto, slots e prevencao de mismatch `WordBoundary` |
| `.agents/skills/narrated-video-studio/references/02_voice_and_audio_engineering.md` | Vozes PT-BR, normalizacao `-17 LUFS`, trilha `-24 LUFS` e troca por voz humana |
| `.agents/skills/narrated-video-studio/references/03_visual_craft_and_prompts.md` | Tipografia >=28px, safe zones 80%/90%, crop >=1.10, regras anti-slop |
| `.agents/skills/narrated-video-studio/references/04_hyperframes_and_wordboundary.md` | Contrato HyperFrames (`window.__timelines`, `.clip`, GSAP) e sync por palavra |
| `.agents/skills/narrated-video-studio/references/05_qa_and_troubleshooting.md` | Checklist de QA pre/pos-render e resolucao de falhas comuns |
| `scripts/narrated_video_cli.py` | CLI completo em Python (`doctor`, `voices`, `synth-audio`, `synth-ambient`, `build-captions`, `scaffold-video`, `audit`) |
| `scripts/install_skill.ps1` / `install_skill.sh` | Instaladores locais/globais da skill para diferentes agentes |
| `docs/specs/*.md` | Especificacoes SDD (Main, Architecture, Domain, Security, Quality) |
| `examples/ciclo-da-banana-60s/` | Projeto completo funcional de 60s (5 cenas, 5 PNGs, audio, SRT, timings, SPEC e REVIEW) |
| `tests/test_narrated_video_cli.py` | Suite automatizada `unittest` validando parser, captions, scaffold, ambient, audit e seguranca |
