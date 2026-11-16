---
name: narrated-video-studio
description: >-
  Creates complete 1080p narrated explainer videos from any topic or text using
  Edge-TTS WordBoundary sync, FFmpeg loudness calibration, generated 16:9 visual
  plates, and frame-exact HyperFrames GSAP compositions in Portuguese or any
  supported neural voice without paid APIs.
---

# Narrated Video Studio

## Overview

`narrated-video-studio` distills a verified end-to-end production pipeline that converts a topic, document, or raw notes into a deterministic `1920x1080 @ 30fps` narrated MP4 explainer video with synchronized word-by-word captions, animated vector diagrams, background ambience, and bespoke 16:9 illustrations — using zero paid APIs.

The canonical skill bundle and reference manuals live at `.agents/skills/narrated-video-studio/` (and a complete verified 60s reference build lives in `examples/ciclo-da-banana-60s/`).

## Dependencies

- **`hyperframes`** and **`hyperframes-cli`**: Frame-by-frame HTML-to-MP4 timeline contract, `lint`, `check --json --strict`, `snapshot`, `preview`, `render`, and `audio`.
- **`hyperframes-registry`**: Reusable transitions, grain overlays, and caption components.
- **`media-use`**: Media sourcing, treatments, loudness normalization, and Whisper PT-BR alignment (`npx hyperframes transcribe --language pt`) for human voice replacement.
- **Image generator tool (`image-generator` subagent or local FLUX)**: Text-free 16:9 visual plates.

## Quick Start

```bash
python -m venv .venv
# Windows: .venv\Scripts\python.exe -m pip install -e ".[dev]"
# POSIX:   .venv/bin/pip install -e ".[dev]"

python scripts/narrated_video_cli.py doctor --output doctor.json
python scripts/narrated_video_cli.py synth-audio --spec script.json --output-dir audio_out --ambient --output audio_out/summary.json
python scripts/narrated_video_cli.py scaffold-video --spec script.json --timings audio_out/timings.json --images-dir images --output-dir video_hf
```

## Reference Manuals

- `.agents/skills/narrated-video-studio/references/01_script_and_timing_math.md`
- `.agents/skills/narrated-video-studio/references/02_voice_and_audio_engineering.md`
- `.agents/skills/narrated-video-studio/references/03_visual_craft_and_prompts.md`
- `.agents/skills/narrated-video-studio/references/04_hyperframes_and_wordboundary.md`
- `.agents/skills/narrated-video-studio/references/05_qa_and_troubleshooting.md`
