# Narrated Video Studio

Pipeline completo, gratuito e deterministico para que qualquer agente de IA (Antigravity, Claude Code, Codex, Gemini CLI, Cursor) transforme um tema, texto ou roteiro em um video explicativo `1920x1080 @ 30fps` narrado em PT-BR (ou outro idioma), com legendas sincronizadas por `WordBoundary`, ilustracoes 16:9, diagramas vetoriais SVG animados em GSAP e trilha ambiente calibrada.

Este repositorio consolida a skill completa, o CLI Python de automacao, as especificacoes tecnicas, guias de referencia e o projeto-modelo validado da apresentacao de 60 segundos em `examples/ciclo-da-banana-60s/`.

---

## O Que Esta Incluido

1. **Skill Agentica Completa (`narrated-video-studio`):**
   - Localizada em [`.agents/skills/narrated-video-studio/SKILL.md`](.agents/skills/narrated-video-studio/SKILL.md) (com espelho em [`SKILL.md`](SKILL.md) na raiz).
   - Inclui 5 manuais de referencia detalhando matematica de roteiro, engenharia de audio/loudness, direcao visual anti-slop, contrato HyperFrames com sincronizacao `WordBoundary` e checklist de QA.
2. **CLI Deterministico (`scripts/narrated_video_cli.py`):**
   - `doctor`: verifica Python, `edge-tts`, `ffmpeg`, `ffprobe`, `node`, `npx` e HyperFrames.
   - `voices`: consulta vozes neurais PT-BR ou globais disponiveis no `edge-tts`.
   - `synth-audio`: gera MP3s por cena, normaliza o conjunto de forma uniforme para `-17.0 LUFS` (`max <= -1.5 dBFS`), monta `narration.mp3` alinhado por slots, gera `.srt`, `timings.json` (`WordBoundary`) e opcionalmente a cama ambiente harmonica (`-24.0 LUFS`) via `ffmpeg`. Incorpora rate limiter monotonico e retry exponencial.
   - `synth-ambient`: gera trilha ambiente livre de direitos autorais diretamente via `ffmpeg`.
   - `build-captions`: gera `compositions/captions.html` no formato HyperFrames com destaque palavra por palavra.
   - `scaffold-video`: cria toda a estrutura inicial HyperFrames (`index.html`, `hyperframes.json`, `SPEC.md`, `compositions/scene-*.html` e `captions.html`) a partir de `script.json`.
   - `audit`: varre emojis, audita `mp4` via `ffprobe`/`volumedetect` e executa `npx hyperframes check --json --strict`.
3. **Projeto de Referencia Completo (`examples/ciclo-da-banana-60s/`):**
   - Codigo-fonte integral da apresentacao de `60.0s` (`1800` frames, `5` cenas, `5` pranchas `1376x768`, `ap01_narration.mp3`, `ambient_bed_60s.mp3`, `ap01.srt`, `ap01_timings.json`, `SPEC.md`, `STORYLINES.md`, `REVIEW.md` e `script.json`).
4. **Documentacao SDD e Testes (`docs/specs/`, `docs/ARCHITECTURE_MAP.md`, `tests/`):**
   - Especificacoes formais e suite `unittest` cobrindo CLI, parser, seguranca de caminhos, geracao de legendas, scaffold, trilha ambiente e auditoria.

---

## Pre-Requisitos (100% Gratuitos)

- **Python >= 3.10**
- **Node.js >= 22** (para `npx hyperframes`)
- **FFmpeg + FFprobe** no `PATH`
- Um gerador de imagens 16:9 opcional (ex.: subagente `image-generator`, FLUX local ou assets proprios)

---

## Instalacao Rapida (Ambiente Isolado)

```bash
git clone <URL_DO_REPO>
cd narrated-video-studio

# Criar virtualenv isolada (nunca instalar globalmente)
python -m venv .venv

# Windows (PowerShell):
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"

# Linux / macOS:
.venv/bin/pip install -e ".[dev]"

# Validar ambiente:
.\.venv\Scripts\python.exe scripts\narrated_video_cli.py doctor --output doctor.json
```

### Instalar a Skill em Seu Agente de IA

**Windows (PowerShell):**
```powershell
# Instala na pasta .agents/skills e .claude/skills de um projeto especifico:
.\scripts\install_skill.ps1 -Scope local -TargetProject "C:\caminho\do\projeto"

# Ou globalmente para Codex / Claude Code / Antigravity:
.\scripts\install_skill.ps1 -Scope global
```

**Linux / macOS:**
```bash
./scripts/install_skill.sh local /caminho/do/projeto
# ou global:
./scripts/install_skill.sh global
```

---

## Reproduzir o Video de Exemplo (`ciclo-da-banana-60s`)

```bash
cd examples/ciclo-da-banana-60s
npx hyperframes check --json --strict --samples 15
npx hyperframes snapshot --review
npx hyperframes render --quality delivery --output apresentacao_01_ciclo_banana.mp4
```

Para auditar o MP4 final com nosso CLI:
```bash
python ../../scripts/narrated_video_cli.py audit \
  --project-dir . \
  --mp4 apresentacao_01_ciclo_banana.mp4 \
  --strict-hyperframes \
  --output audit_report.json
```

---

## Como Criar um Novo Video do Zero (Prompt para a IA)

Com a skill instalada, basta instruir o agente:

> *"Use a skill `narrated-video-studio` para criar um video explicativo narrado de 60 segundos em 1080p sobre [SEU TEMA]. Crie o `script.json`, sintetize o audio e os timings WordBoundary, gere as 5 ilustracoes 16:9 sem texto, construa as composicoes HyperFrames com diagramas SVG sincronizados a fala, rode a auditoria estrita e renderize o MP4 final."*

Para trocar a voz sintetica pela sua propria gravacao em qualquer projeto gerado:
1. Grave o roteiro lendo `script.json` em `.mp3` ou `.wav`.
2. Substitua `assets/narration.mp3`.
3. Rode `npx hyperframes transcribe assets/narration.mp3 --model small --language pt --json --output transcript.json`.
4. Atualize `timings.json` e execute `build-captions` antes de re-renderizar.

---

## Executar Testes do Repositorio

```bash
python -m unittest discover -s tests -v
```

Consulte [`docs/ARCHITECTURE_MAP.md`](docs/ARCHITECTURE_MAP.md) e [`docs/specs/main.md`](docs/specs/main.md) para detalhes completos de arquitetura, contratos e seguranca.
