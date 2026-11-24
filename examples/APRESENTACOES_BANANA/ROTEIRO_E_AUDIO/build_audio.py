import asyncio
import json
import os
import re
import subprocess
import sys
from pathlib import Path
import edge_tts

BASE_DIR = Path(r"C:\Users\52319400\APRESENTACOES_BANANA\ROTEIRO_E_AUDIO")
SLOT_STARTS = [0.15, 12.15, 24.15, 36.15, 48.15]
SLOT_DURATION = 12.0

PRESENTATIONS = {
    "ap01": {
        "title": "Ciclo de Vida da Banana (Musa spp.) - Canal Dark Explainer",
        "voice": "pt-BR-AntonioNeural",
        "scenes": [
            {
                "id": "cena_01",
                "title": "Rizoma, Broto Espadim e Pseudocaule",
                "text": "A bananeira não é uma árvore; é a maior erva do planeta. Sob o solo, seu caule real é um rizoma subterrâneo que dispara o broto espadim e ergue um pseudocaule de folhas sobrepostas.",
            },
            {
                "id": "cena_02",
                "title": "Diferenciacao Floral e Mangara",
                "text": "Na maturidade, ocorre a diferenciação floral. O pendão atravessa o pseudocaule e irrompe como o mangará, o coração arroxeado cujas brácteas revelam flores femininas e masculinas.",
            },
            {
                "id": "cena_03",
                "title": "Partenocarpia e Geotropismo Negativo",
                "text": "Sem sementes nem polinização, os frutos nascem por partenocarpia. Embora o cacho penda pelo próprio peso, cada banana faz geotropismo negativo, curvando-se para o alto.",
            },
            {
                "id": "cena_04",
                "title": "Climaterio, Etileno e Amido em Acucares",
                "text": "Como fruto climatérico, a banana acelera a respiração e libera o gás etileno. Esse hormônio ativa enzimas que transformam amido em açúcares doces, amaciam a polpa e douram a casca.",
            },
            {
                "id": "cena_05",
                "title": "Senescencia, Corte e Sucessao pelo Perfilho",
                "text": "Cada pseudocaule frutifica uma única vez e entra em senescência. Ao cortá-lo após a colheita, o rizoma transfere energia ao perfilho filho, garantindo sucessão contínua.",
            },
        ],
    },
    "ap02": {
        "title": "Ciclo de Vida da Banana (Musa spp.) - Monografia Botanica Editorial",
        "voice": "pt-BR-ThalitaMultilingualNeural",
        "scenes": [
            {
                "id": "cena_01",
                "title": "Anatomia Basal: Rizoma e Pseudocaule",
                "text": "No gênero Musa, o tronco aparente é um pseudocaule de bainhas foliares compactadas. O caule verdadeiro oculta-se no solo: o rizoma perene, de onde emerge o broto espadim.",
            },
            {
                "id": "cena_02",
                "title": "Transicao Reprodutiva e Mangara",
                "text": "Atingida a maturidade vegetativa, o meristema inicia a diferenciação floral. A haste sobe pelo núcleo da planta e projeta o mangará pendente, revestido por brácteas violáceas.",
            },
            {
                "id": "cena_03",
                "title": "Partenocarpia e Arquitetura das Pencas",
                "text": "As flores femininas basais formam frutos sem sementes por partenocarpia natural. Guiadas pelo geotropismo negativo, as pencas em crescimento arqueiam-se contra a gravidade.",
            },
            {
                "id": "cena_04",
                "title": "Fisiologia Climaterica e Gas Etileno",
                "text": "Na maturação climatérica, um pico respiratório acompanha a síntese natural do gás etileno. Esse sinal converte o amido de reserva em açúcares solúveis e revela o dourado intenso da casca.",
            },
            {
                "id": "cena_05",
                "title": "Senescencia e Continuidade Clonal",
                "text": "Concluída a colheita do cacho, o pseudocaule entra em senescência e recebe o corte de manejo. O rizoma materno nutre com vigor o perfilho sucessor, perpetuando a linhagem clonal.",
            },
        ],
    },
}


def run_cmd(cmd):
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\nSTDERR: {res.stderr}")
    return res


def ffprobe_info(path: Path) -> dict:
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration,bit_rate",
        "-show_entries", "stream=codec_name,sample_rate,channels",
        "-of", "json",
        str(path),
    ]
    data = json.loads(run_cmd(cmd).stdout)
    fmt = data.get("format", {})
    stream = (data.get("streams") or [{}])[0]
    return {
        "duration_sec": round(float(fmt["duration"]), 6),
        "bit_rate": int(fmt.get("bit_rate", 0)),
        "codec": stream.get("codec_name"),
        "sample_rate": int(stream.get("sample_rate", 0)),
        "channels": int(stream.get("channels", 0)),
    }


def analyze_loudness(path: Path) -> dict:
    res = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(path), "-af", "volumedetect,ebur128", "-f", "null", "-"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    stderr = res.stderr
    mean_m = re.search(r"mean_volume:\s*([-\d.]+)\s*dB", stderr)
    max_m = re.search(r"max_volume:\s*([-\d.]+)\s*dB", stderr)
    lufs_m = re.findall(r"I:\s*([-\d.]+)\s*LUFS", stderr)
    return {
        "mean_volume_db": float(mean_m.group(1)) if mean_m else None,
        "max_volume_db": float(max_m.group(1)) if max_m else None,
        "integrated_lufs": float(lufs_m[-1]) if lufs_m else None,
    }


def fmt_srt_ts(seconds: float) -> str:
    ms_total = max(0, int(round(seconds * 1000)))
    h = ms_total // 3_600_000
    ms_total %= 3_600_000
    m = ms_total // 60_000
    ms_total %= 60_000
    s = ms_total // 1000
    ms = ms_total % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_caption_groups(words: list[dict], max_words: int = 5) -> list[dict]:
    """Group words into 2-5 word caption phrases, breaking cleanly on punctuation or pauses >= 150ms."""
    clauses = []
    current = []
    for idx, w in enumerate(words):
        current.append(w)
        ends_clause = w["text"].endswith((".", ",", ";", ":"))
        next_gap = (words[idx + 1]["start"] - w["end"]) if idx + 1 < len(words) else 0.0
        if ends_clause or next_gap >= 0.15:
            clauses.append(current)
            current = []
    if current:
        clauses.append(current)

    groups = []
    for clause in clauses:
        n = len(clause)
        if n <= max_words:
            chunks = [clause]
        else:
            # Balanced split to avoid 1-word orphans
            num_chunks = (n + max_words - 1) // max_words
            base, rem = divmod(n, num_chunks)
            chunks = []
            pos = 0
            for c_idx in range(num_chunks):
                size = base + (1 if c_idx < rem else 0)
                chunks.append(clause[pos : pos + size])
                pos += size
        for ch in chunks:
            groups.append(ch)
    return groups


async def synth_scene(voice: str, text: str, raw_mp3: Path):
    comm = edge_tts.Communicate(text, voice, boundary="WordBoundary", connect_timeout=15, receive_timeout=30)
    audio_buf = bytearray()
    wb_words = []
    async for chunk in comm.stream():
        if chunk["type"] == "audio":
            audio_buf.extend(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            wb_words.append(
                {
                    "wb_text": chunk["text"],
                    "local_start": round(chunk["offset"] / 10_000_000, 4),
                    "local_end": round((chunk["offset"] + chunk["duration"]) / 10_000_000, 4),
                }
            )
    raw_mp3.write_bytes(audio_buf)

    display_tokens = text.split()
    if len(wb_words) != len(display_tokens):
        raise RuntimeError(
            f"Word count mismatch: edge-tts={len(wb_words)} vs text={len(display_tokens)} for: {text}"
        )
    for wb, disp in zip(wb_words, display_tokens):
        wb["display_text"] = disp
    return wb_words


async def build_presentation(pres_key: str, cfg: dict):
    print(f"\n=== Building {pres_key} ({cfg['voice']}) ===", flush=True)
    scenes_dir = BASE_DIR / f"{pres_key}_cenas"
    scenes_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = BASE_DIR / f"_tmp_{pres_key}"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    # 1. Synthesize all 5 scenes concurrently
    tasks = [
        synth_scene(cfg["voice"], sc["text"], tmp_dir / f"{sc['id']}_raw.mp3")
        for sc in cfg["scenes"]
    ]
    all_wb = await asyncio.gather(*tasks)

    # 2. Decode raw MP3 to trimmed 48kHz stereo WAV (preserving t=0 so local timestamps stay exact)
    trimmed_wavs = []
    total_spoken = 0.0
    errors_slot = []
    for idx, (sc, wb_list) in enumerate(zip(cfg["scenes"], all_wb)):
        raw_mp3 = tmp_dir / f"{sc['id']}_raw.mp3"
        trimmed_wav = tmp_dir / f"{sc['id']}_trimmed.wav"
        first_start = wb_list[0]["local_start"]
        last_end = wb_list[-1]["local_end"]
        spoken_span = last_end - first_start
        total_spoken += spoken_span

        slot_offset = SLOT_STARTS[idx]
        trim_end = round(last_end + 0.14, 4)
        fade_start = round(max(0.0, trim_end - 0.025), 4)

        print(
            f"  {sc['id']}: words={len(wb_list):2d} | local={first_start:.3f}s..{last_end:.3f}s "
            f"(span={spoken_span:.3f}s) | global={slot_offset + first_start:.3f}s..{slot_offset + last_end:.3f}s",
            flush=True,
        )

        # Defer raising until all 5 scenes are printed so tuning is single-pass
        if idx < 4 and (slot_offset + trim_end) > (idx + 1) * SLOT_DURATION:
            errors_slot.append(f"{pres_key} {sc['id']} overflows its 12s slot: {slot_offset + trim_end:.3f}s")
        if idx == 4 and (slot_offset + trim_end) > 59.45:
            errors_slot.append(f"{pres_key} {sc['id']} exceeds 59.45s hard ceiling: {slot_offset + trim_end:.3f}s")

        run_cmd(
            [
                "ffmpeg", "-y", "-i", str(raw_mp3),
                "-af", f"atrim=0:{trim_end},asetpts=PTS-STARTPTS,afade=t=out:st={fade_start}:d=0.025",
                "-ar", "48000", "-ac", "2", "-c:a", "pcm_s24le",
                str(trimmed_wav),
            ]
        )
        trimmed_wavs.append(trimmed_wav)

    print(f"  Total active spoken span: {total_spoken:.3f}s", flush=True)
    if errors_slot:
        raise RuntimeError("; ".join(errors_slot))
    if not (55.0 <= total_spoken <= 59.0):
        raise RuntimeError(f"{pres_key} spoken span {total_spoken:.3f}s outside 55s..59s window!")

    # 3. Measure combined speech loudness to choose one clean uniform gain (target -17.0 LUFS, peak <= -1.5 dBFS)
    concat_wav = tmp_dir / "speech_concat.wav"
    inputs = []
    concat_parts = []
    for i, w in enumerate(trimmed_wavs):
        inputs.extend(["-i", str(w)])
        concat_parts.append(f"[{i}:a]")
    run_cmd(
        [
            "ffmpeg", "-y", *inputs,
            "-filter_complex", f"{''.join(concat_parts)}concat=n={len(trimmed_wavs)}:v=0:a=1[out]",
            "-map", "[out]", "-c:a", "pcm_s24le", str(concat_wav),
        ]
    )
    stats = analyze_loudness(concat_wav)
    delta_lufs = -17.0 - stats["integrated_lufs"]
    headroom_cap = -1.5 - stats["max_volume_db"]
    gain_db = round(min(delta_lufs, headroom_cap), 2)
    print(
        f"  Raw speech loudness: {stats['integrated_lufs']:.1f} LUFS, max={stats['max_volume_db']:.1f} dB -> applying uniform gain {gain_db:+.2f} dB",
        flush=True,
    )

    # 4. Encode individual scene MP3s with uniform gain
    scene_mp3_paths = []
    for idx, (sc, twav) in enumerate(zip(cfg["scenes"], trimmed_wavs)):
        out_mp3 = scenes_dir / f"{sc['id']}.mp3"
        run_cmd(
            [
                "ffmpeg", "-y", "-i", str(twav),
                "-af", f"volume={gain_db}dB",
                "-ar", "48000", "-ac", "2", "-c:a", "libmp3lame", "-b:a", "192k",
                str(out_mp3),
            ]
        )
        scene_mp3_paths.append(out_mp3)

    # 5. Assemble full narration MP3 from trimmed WAVs at exact slot offsets + uniform gain
    full_mp3 = BASE_DIR / f"{pres_key}_narration.mp3"
    full_inputs = []
    filter_chains = []
    mix_labels = []
    for i, (twav, offset_s) in enumerate(zip(trimmed_wavs, SLOT_STARTS)):
        delay_ms = int(round(offset_s * 1000))
        full_inputs.extend(["-i", str(twav)])
        filter_chains.append(f"[{i}:a]adelay={delay_ms}|{delay_ms}[d{i}]")
        mix_labels.append(f"[d{i}]")
    filter_expr = ";".join(filter_chains) + f";{''.join(mix_labels)}amix=inputs=5:duration=longest:normalize=0,volume={gain_db}dB[out]"
    run_cmd(
        [
            "ffmpeg", "-y", *full_inputs,
            "-filter_complex", filter_expr,
            "-map", "[out]",
            "-ar", "48000", "-ac", "2", "-c:a", "libmp3lame", "-b:a", "192k",
            str(full_mp3),
        ]
    )

    # 6. Audit all MP3s via ffprobe + volumedetect
    full_probe = ffprobe_info(full_mp3)
    full_loud = analyze_loudness(full_mp3)
    print(
        f"  Full MP3: {full_mp3.name} | duration={full_probe['duration_sec']:.3f}s | "
        f"LUFS={full_loud['integrated_lufs']} | mean={full_loud['mean_volume_db']}dB | max={full_loud['max_volume_db']}dB",
        flush=True,
    )
    if not (55.0 <= full_probe["duration_sec"] <= 59.5):
        raise RuntimeError(f"{full_mp3.name} duration {full_probe['duration_sec']}s violates 55.0..59.5s!")
    if full_loud["mean_volume_db"] < -35.0 or full_loud["max_volume_db"] > 0.0:
        raise RuntimeError(f"{full_mp3.name} audio check failed: {full_loud}")

    # 7. Build timings JSON and SRT
    scenes_json = []
    global_words = []
    global_captions = []
    srt_lines = []
    g_w_idx = 0
    g_c_idx = 0

    for idx, (sc, wb_list, sm_path) in enumerate(zip(cfg["scenes"], all_wb, scene_mp3_paths)):
        s_num = idx + 1
        offset_s = SLOT_STARTS[idx]
        s_probe = ffprobe_info(sm_path)
        s_loud = analyze_loudness(sm_path)
        if s_loud["mean_volume_db"] < -35.0 or s_loud["max_volume_db"] > 0.0:
            raise RuntimeError(f"{sm_path.name} loudness invalid: {s_loud}")

        scene_words = []
        for w_i, wb in enumerate(wb_list):
            g_start = round(offset_s + wb["local_start"], 4)
            g_end = round(offset_s + wb["local_end"], 4)
            w_obj = {
                "id": f"s{s_num}_w{w_i}",
                "global_id": f"w{g_w_idx}",
                "text": wb["display_text"],
                "word": wb["wb_text"],
                "start": g_start,
                "end": g_end,
                "local_start": wb["local_start"],
                "local_end": wb["local_end"],
            }
            scene_words.append(w_obj)
            global_words.append(
                {
                    "id": f"w{g_w_idx}",
                    "scene": s_num,
                    "text": wb["display_text"],
                    "start": g_start,
                    "end": g_end,
                }
            )
            g_w_idx += 1

        raw_groups = build_caption_groups(scene_words, max_words=5)
        scene_captions = []
        for c_i, ch in enumerate(raw_groups):
            c_start = ch[0]["start"]
            c_end = round(ch[-1]["end"] + 0.08, 4)
            c_text = " ".join(x["text"] for x in ch)
            c_obj = {
                "id": f"s{s_num}_c{c_i}",
                "global_id": f"c{g_c_idx}",
                "text": c_text,
                "start": c_start,
                "end": c_end,
                "local_start": ch[0]["local_start"],
                "local_end": round(ch[-1]["local_end"] + 0.08, 4),
                "word_ids": [x["global_id"] for x in ch],
            }
            scene_captions.append(c_obj)
            global_captions.append(
                {
                    "id": f"c{g_c_idx}",
                    "scene": s_num,
                    "text": c_text,
                    "start": c_start,
                    "end": c_end,
                    "_ref": c_obj,
                }
            )
            g_c_idx += 1

        # Prevent overlap between consecutive captions if +0.08 tail reaches next cue
        for k in range(len(global_captions) - 1):
            if global_captions[k]["end"] > global_captions[k + 1]["start"]:
                clamped = round(global_captions[k + 1]["start"] - 0.01, 4)
                global_captions[k]["end"] = clamped
                global_captions[k]["_ref"]["end"] = clamped
                global_captions[k]["_ref"]["local_end"] = round(
                    clamped - SLOT_STARTS[global_captions[k]["scene"] - 1], 4
                )

        scenes_json.append(
            {
                "id": sc["id"],
                "index": s_num,
                "title": sc["title"],
                "file": f"{pres_key}_cenas/{sc['id']}.mp3",
                "slot_start_sec": idx * SLOT_DURATION,
                "slot_end_sec": (idx + 1) * SLOT_DURATION,
                "audio_offset_sec": offset_s,
                "ffprobe_duration_sec": s_probe["duration_sec"],
                "spoken_start_sec": scene_words[0]["start"],
                "spoken_end_sec": scene_words[-1]["end"],
                "spoken_duration_sec": round(scene_words[-1]["end"] - scene_words[0]["start"], 4),
                "volumedetect": s_loud,
                "text": sc["text"],
                "words": scene_words,
                "caption_groups": scene_captions,
            }
        )

    # Strip internal helper key before serializing
    clean_global_captions = [
        {k: v for k, v in c.items() if k != "_ref"} for c in global_captions
    ]
    srt_lines = [
        f"{i + 1}\n{fmt_srt_ts(c['start'])} --> {fmt_srt_ts(c['end'])}\n{c['text']}\n"
        for i, c in enumerate(clean_global_captions)
    ]

    srt_path = BASE_DIR / f"{pres_key}.srt"
    srt_path.write_text("\n".join(srt_lines), encoding="utf-8")

    timings_path = BASE_DIR / f"{pres_key}_timings.json"
    timings_payload = {
        "presentation": pres_key,
        "title": cfg["title"],
        "voice": cfg["voice"],
        "sample_rate_hz": full_probe["sample_rate"],
        "channels": full_probe["channels"],
        "audio_file": f"{pres_key}_narration.mp3",
        "ambient_file": "ambient_bed_60s.mp3",
        "srt_file": f"{pres_key}.srt",
        "timeline_duration_sec": 60.0,
        "ffprobe_duration_sec": full_probe["duration_sec"],
        "spoken_duration_sec": round(total_spoken, 4),
        "volumedetect": full_loud,
        "scenes": scenes_json,
        "words": global_words,
        "captions": clean_global_captions,
    }
    timings_path.write_text(json.dumps(timings_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # Cleanup temp directory
    for f in tmp_dir.iterdir():
        f.unlink()
    tmp_dir.rmdir()


async def main():
    for key, cfg in PRESENTATIONS.items():
        await build_presentation(key, cfg)
    print("\nALL AUDIO AND TIMINGS BUILT AND VALIDATED SUCCESSFULLY.", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
