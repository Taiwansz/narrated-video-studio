# SPEC: Domain & Contracts

## Contrato do Manifesto `script.json`
Campos obrigatorios:
- `title`: string nao vazia.
- `voice`: string de voz neural (ex.: `pt-BR-AntonioNeural`, `pt-BR-ThalitaMultilingualNeural`).
- `total_duration_sec`: float > 0 (ex.: `60.0`).
- `scenes`: lista nao vazia de objetos `{id, composition_id, title, kicker, subtitle, image, duration_sec, keywords, text}`.

## Contrato do Arquivo `timings.json`
- Topo: `presentation`, `title`, `voice`, `sample_rate_hz`, `channels`, `audio_file`, `ambient_file`, `srt_file`, `timeline_duration_sec`, `ffprobe_duration_sec`, `spoken_duration_sec`, `volumedetect`, `scenes[]`, `words[]`, `captions[]`.
- Invariantes temporais:
  1. Para cada cena `i`, a fala deve encerrar dentro de `[slot_start_sec, slot_end_sec - 0.15]`.
  2. `ffprobe_duration_sec <= timeline_duration_sec`.
  3. Nenhuma legenda sobrepoe a seguinte (`captions[k].end <= captions[k+1].start`).
  4. Todo `id` de elemento em `captions.html` corresponde 1:1 a `groups[].id` e `words[].id`.
