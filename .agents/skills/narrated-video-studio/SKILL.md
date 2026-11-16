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

The reference implementation built and verified with this exact workflow lives in `examples/ciclo-da-banana-60s/` (`60.0s`, `1800` frames, `5` animated scenes, `pt-BR-AntonioNeural` at `-17.3 LUFS`, ambient bed at `-24.2 LUFS`, `51/51` contrast checks passing).

## Dependencies

This skill orchestrates the following existing capabilities rather than reimplementing video rendering or media acquisition:

- **`hyperframes`**: Required for the HTML-to-MP4 deterministic seekable timeline contract (`window.__timelines`, `.clip`, `data-start`, `data-duration`, safe zones).
- **`hyperframes-cli`**: Required for `lint`, `check --json --strict`, `snapshot`, `preview`, `render`, and `audio` verification.
- **`hyperframes-registry`**: Search before hand-coding common transitions, grain overlays, or caption primitives.
- **`media-use`**: Required for sourcing/treating media assets, `normalize-audio`, or Whisper word-level transcription (`npx hyperframes transcribe --language pt`) when replacing synthetic TTS with a human voice recording.
- **Image generator tool (`image-generator` subagent or local FLUX)**: Used to generate text-free 16:9 visual plates.

## Quick Start

1. Verify environment prerequisites inside an isolated Python `.venv` (never install globally):
   ```bash
   python -m venv .venv
   # Windows: .venv\Scripts\pip install -e .
   # POSIX:   .venv/bin/pip install -e .
   python scripts/narrated_video_cli.py doctor --output doctor.json
   ```
2. Author `script.json` following `references/01_script_and_timing_math.md`.
3. Synthesize narration, `WordBoundary` JSON, SRT, and calm ambient bed:
   ```bash
   python scripts/narrated_video_cli.py synth-audio \
     --spec script.json \
     --output-dir audio_out \
     --ambient \
     --output audio_out/summary.json
   ```
4. Generate 16:9 text-free illustrations (`references/03_visual_craft_and_prompts.md`) into `images/`.
5. Scaffold the HyperFrames project and inspect/enrich each scene composition with synced vector diagrams:
   ```bash
   python scripts/narrated_video_cli.py scaffold-video \
     --spec script.json \
     --timings audio_out/timings.json \
     --images-dir images \
     --output-dir meu_video_hf
   ```
6. Validate visually and render (`references/05_qa_and_troubleshooting.md`):
   ```bash
   cd meu_video_hf
   npx hyperframes check --json --strict --samples 15
   npx hyperframes snapshot --review
   npx hyperframes render --quality delivery --output video_final.mp4
   python ../scripts/narrated_video_cli.py audit --project-dir . --mp4 video_final.mp4 --strict-hyperframes --output audit.json
   ```

## Utility Scripts (CLI)

All programmatic work goes through `scripts/narrated_video_cli.py` (writes structured outputs to files via `--output`):

- `doctor --output <json>`: Checks Python >= 3.10, `edge_tts`, `ffmpeg`, `ffprobe`, `node`, `npx`, and HyperFrames CLI.
- `voices --locale pt-BR --output <json>`: Lists available Edge-TTS neural voices for a locale.
- `synth-audio --spec <script.json> --output-dir <dir> [--ambient] [--strict-tokens] [--rate-interval 0.4] [--output <json>]`: Synthesizes per-scene MP3s, measures combined loudness, applies one uniform gain to target `-17.0 LUFS` (`max <= -1.5 dBFS`), builds aligned `narration.mp3`, `narration.srt`, `timings.json` (`WordBoundary`), and optionally `ambient_bed.mp3`.
- `synth-ambient --duration <sec> --lufs -24.0 --output <mp3> [--report <json>]`: Generates a calm, royalty-free harmonic pad via FFmpeg `lavfi` without external files.
- `build-captions --timings <timings.json> --accent "#E2B43B" --output <captions.html>`: Generates deterministic `compositions/captions.html` with 2-5 word balanced phrases and per-word `WordBoundary` highlighting.
- `scaffold-video --spec <script.json> --output-dir <dir> [--timings <timings.json>] [--images-dir <dir>]`: Creates a HyperFrames project pre-wired with `index.html`, `SPEC.md`, `hyperframes.json`, starter scene compositions, and `captions.html`.
- `audit --project-dir <dir> [--mp4 <file.mp4>] [--strict-hyperframes] --output <json>`: Scans all text/HTML/JSON/SRT files for zero emojis, checks MP4 streams via `ffprobe`/`volumedetect`, and optionally runs `npx hyperframes check --json --strict`.

## Production Workflow (7 Phases)

1. **Brief & Storylines (`STORYLINES.md`)**: Propose 3 genuinely distinct visual metaphors/storylines before coding; pick one with a crisp structural device.
2. **Contract Specification (`SPEC.md`)**: Pin exact duration, FPS, resolution (`1920x1080`), palette hex tokens, font sizes (`>=28px` reading, `>=64px` display), safe zones, shot-by-shot plan, and banned AI-slop defaults.
3. **Spoken Script & Timing Math**: Write concise, speakable sentences matching `~130-148 words/min` (`24-30 words` per `12s` slot). Spell out formulas/acronyms in `text` while keeping formal notation on screen (`references/01_script_and_timing_math.md`).
4. **Audio Synthesis & Loudness Calibration**: Run `synth-audio --ambient` and inspect slot spans in `timings.json`. If any scene exceeds its slot ceiling, trim 3-5 words and re-run (`references/02_voice_and_audio_engineering.md`).
5. **16:9 Text-Free Visual Plates**: Generate one coherent 16:9 illustration per scene with zero baked-in text/watermarks and inspect every asset visually via `read_file` (`references/03_visual_craft_and_prompts.md`).
6. **HyperFrames Scene Choreography**: Run `scaffold-video`, then customize each scene's SVG vector diagrams and GSAP timelines using the exact word timestamps in `timings.json` (`references/04_hyperframes_and_wordboundary.md`).
7. **Strict QA, Visual Snapshot Inspection & Delivery Render**: Run `npx hyperframes check --json --strict`, capture and read `--review` and per-scene snapshots, render with `--quality delivery`, run `narrated_video_cli.py audit`, inspect decoded MP4 frames, and log `REVIEW.md` (`references/05_qa_and_troubleshooting.md`).

## Rate Limiting & Fallback Strategy

- `synth_scene_with_retry` enforces a `MonotonicRateLimiter` (`time.monotonic()`, default `0.4s` minimum spacing) plus exponential backoff with jitter (`4` retries) on transient HTTP `429`/`5xx`/`403`/WebSocket errors from Microsoft Edge Read Aloud.
- Never bypass rate limits with unthrottled loops. Raise `--rate-interval 1.0` if generating >15 scenes in batch.
- **Human Voice Swap / Offline Fallback**: Replace `assets/narration.mp3` with a human recording (or local `Kokoro-82M` `pt-br` output), run `npx hyperframes transcribe assets/narration.mp3 --model small --language pt --json`, and rebuild `captions.html` via `build-captions`.

## Common Mistakes

1. **Letting AI image generators draw text**: Never ask for labels inside generated images; render all typography cleanly in HTML/SVG.
2. **Showing an empty SVG frame waiting 5 seconds for a speech cue**: Draw structural axes/guides early (`0.4s-1.2s`), then animate data curves when the narrator speaks the target keyword.
3. **Leaving CSS `transform:` on GSAP-animated elements or animating `.clip` visibility directly**: Violates HyperFrames' deterministic `seek()` contract and triggers lint failures.
4. **Forgetting `scale >= 1.10` on illustrated plates**: Paper-textured illustrations often carry subtle borders; crop them cleanly inside an `overflow: hidden` wrapper from frame `0`.
5. **Running `npx hyperframes transcribe` without `--language pt`**: Defaults to `small.en`, translating Portuguese narration into broken English text.
