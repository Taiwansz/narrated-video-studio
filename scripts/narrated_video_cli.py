"""Deterministic CLI pipeline for Narrated Video Studio (Edge-TTS + FFmpeg + HyperFrames)."""

from __future__ import annotations

import argparse
import asyncio
import html
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

SAFE_ID_RE = re.compile(r"^[a-zA-Z0-9_-]+$")
EMOJI_RE = re.compile(
    r"[\U00010000-\U0010ffff]|[\u2600-\u27BF]|[\u2300-\u23FF]|[\u2B50-\u2B55]|[\uD83C-\uDBFF\uDC00-\uDFFF]"
)
PUNCT_BREAK_CHARS = (".", ",", ";", ":", "!", "?")
TEXT_SCAN_EXTS = {".html", ".md", ".json", ".srt", ".py", ".txt"}


class RateLimitError(RuntimeError):
    """Raised when an upstream TTS endpoint hits rate limits (HTTP 429 or throttling)."""


class MonotonicRateLimiter:
    """Thread/async-safe monotonic spacing guard for external API requests."""

    def __init__(self, min_interval_sec: float = 0.4) -> None:
        self.min_interval_sec = max(0.0, float(min_interval_sec))
        self._last_ts: float | None = None

    async def wait_async(self) -> None:
        if self._last_ts is not None and self.min_interval_sec > 0:
            elapsed = time.monotonic() - self._last_ts
            remaining = self.min_interval_sec - elapsed
            if remaining > 0:
                await asyncio.sleep(remaining)
        self._last_ts = time.monotonic()


def safe_identifier(value: str, label: str = "identifier") -> str:
    """Validate identifier against path traversal and special characters."""
    if not value or not SAFE_ID_RE.match(value):
        raise ValueError(f"Invalid {label} '{value}': allowed pattern ^[a-zA-Z0-9_-]+$")
    return value


def safe_resolve(base_dir: Path, relative_path: str) -> Path:
    """Resolve a path strictly inside base_dir to prevent path traversal."""
    base_resolved = base_dir.resolve()
    candidate = (base_resolved / relative_path).resolve()
    try:
        candidate.relative_to(base_resolved)
    except ValueError as exc:
        raise ValueError(f"Path traversal blocked: '{relative_path}' escapes '{base_resolved}'") from exc
    return candidate


def run_cmd(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Execute an external command safely with shell=False and explicit error context."""
    res = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )
    if res.returncode != 0:
        raise RuntimeError(
            f"Command failed ({res.returncode}): {' '.join(cmd)}\n"
            f"STDOUT: {res.stdout.strip()}\nSTDERR: {res.stderr.strip()}"
        )
    return res


def _resolve_npx_executable() -> str:
    """Locate npx binary cleanly across Windows and POSIX hosts."""
    for name in ("npx.cmd", "npx.exe", "npx"):
        found = shutil.which(name)
        if found:
            return found
    return "npx"


def ffprobe_media(path: Path) -> dict[str, Any]:
    """Extract duration, bit rate, video and audio stream metadata via ffprobe."""
    if not path.exists():
        raise FileNotFoundError(f"Media file not found: {path}")
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration,size,bit_rate",
        "-show_entries",
        "stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels",
        "-of",
        "json",
        str(path),
    ]
    payload = json.loads(run_cmd(cmd).stdout)
    fmt = payload.get("format", {})
    streams = payload.get("streams", [])
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), {})
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
    return {
        "path": str(path),
        "size_bytes": int(fmt.get("size", path.stat().st_size)),
        "duration_sec": round(float(fmt.get("duration", 0.0)), 6),
        "bit_rate": int(fmt.get("bit_rate", 0)),
        "video": {
            "codec": video_stream.get("codec_name"),
            "width": video_stream.get("width"),
            "height": video_stream.get("height"),
            "r_frame_rate": video_stream.get("r_frame_rate"),
        }
        if video_stream
        else None,
        "audio": {
            "codec": audio_stream.get("codec_name"),
            "sample_rate": int(audio_stream["sample_rate"]) if audio_stream.get("sample_rate") else None,
            "channels": int(audio_stream["channels"]) if audio_stream.get("channels") else None,
        }
        if audio_stream
        else None,
    }


def analyze_loudness(path: Path) -> dict[str, float | None]:
    """Measure mean_volume, max_volume and integrated EBU R128 LUFS via ffmpeg."""
    res = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(path), "-af", "volumedetect,ebur128", "-f", "null", "-"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
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
    """Format floating seconds into SubRip HH:MM:SS,mmm timestamp."""
    ms_total = max(0, int(round(seconds * 1000)))
    hours = ms_total // 3_600_000
    ms_total %= 3_600_000
    minutes = ms_total // 60_000
    ms_total %= 60_000
    secs = ms_total // 1000
    ms = ms_total % 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def build_caption_groups(words: list[dict[str, Any]], max_words: int = 5) -> list[list[dict[str, Any]]]:
    """Group words into balanced 2-5 word caption phrases without single-word orphans."""
    if not words:
        return []
    clauses: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for idx, word in enumerate(words):
        current.append(word)
        ends_clause = str(word["text"]).endswith(PUNCT_BREAK_CHARS)
        next_gap = (float(words[idx + 1]["start"]) - float(word["end"])) if idx + 1 < len(words) else 0.0
        if ends_clause or next_gap >= 0.15:
            clauses.append(current)
            current = []
    if current:
        clauses.append(current)

    groups: list[list[dict[str, Any]]] = []
    for clause in clauses:
        n = len(clause)
        if n <= max_words:
            groups.append(clause)
            continue
        num_chunks = (n + max_words - 1) // max_words
        base, rem = divmod(n, num_chunks)
        pos = 0
        for c_idx in range(num_chunks):
            size = base + (1 if c_idx < rem else 0)
            groups.append(clause[pos : pos + size])
            pos += size
    return groups


def align_word_boundaries(
    display_tokens: list[str],
    wb_words: list[dict[str, Any]],
    strict: bool = False,
) -> list[dict[str, Any]]:
    """Map TTS WordBoundary timings to display tokens, handling rare tokenization splits."""
    if not display_tokens:
        return []
    if len(wb_words) == len(display_tokens):
        aligned: list[dict[str, Any]] = []
        for wb, disp in zip(wb_words, display_tokens):
            item = dict(wb)
            item["display_text"] = disp
            aligned.append(item)
        return aligned

    if strict:
        raise RuntimeError(
            f"WordBoundary token count mismatch: edge-tts={len(wb_words)} vs text={len(display_tokens)} "
            f"for tokens={display_tokens!r}"
        )

    print(
        f"[warn] WordBoundary token count mismatch (tts={len(wb_words)} vs text={len(display_tokens)}); "
        "applying proportional boundary interpolation.",
        file=sys.stderr,
    )
    if not wb_words:
        raise RuntimeError("No WordBoundary events returned by TTS engine.")

    span_start = float(wb_words[0]["local_start"])
    span_end = float(wb_words[-1]["local_end"])
    total_chars = sum(max(1, len(tok)) for tok in display_tokens)
    cursor = span_start
    total_span = max(0.05, span_end - span_start)
    aligned = []
    for tok in display_tokens:
        frac = max(1, len(tok)) / total_chars
        dur = total_span * frac
        aligned.append(
            {
                "wb_text": tok,
                "display_text": tok,
                "local_start": round(cursor, 4),
                "local_end": round(cursor + dur, 4),
            }
        )
        cursor += dur
    return aligned


async def synth_scene_with_retry(
    voice: str,
    text: str,
    raw_mp3: Path,
    limiter: MonotonicRateLimiter,
    max_retries: int = 4,
    strict_tokens: bool = False,
) -> list[dict[str, Any]]:
    """Synthesize a single scene with monotonic rate limiting and exponential backoff."""
    import edge_tts

    attempt = 0
    while True:
        attempt += 1
        await limiter.wait_async()
        try:
            comm = edge_tts.Communicate(
                text,
                voice,
                boundary="WordBoundary",
                connect_timeout=15,
                receive_timeout=30,
            )
            audio_buf = bytearray()
            wb_words: list[dict[str, Any]] = []
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
            if not audio_buf:
                raise RuntimeError("Empty audio buffer returned by edge-tts.")
            raw_mp3.write_bytes(audio_buf)
            return align_word_boundaries(text.split(), wb_words, strict=strict_tokens)
        except Exception as exc:
            msg = str(exc)
            is_rate_limit = "429" in msg or "rate limit" in msg.lower()
            is_transient = is_rate_limit or any(
                code in msg.lower() for code in ("500", "502", "503", "504", "timeout", "websocket", "403")
            )
            if attempt > max_retries or not is_transient:
                if is_rate_limit:
                    raise RateLimitError(f"edge-tts rate limited after {attempt - 1} retries: {msg}") from exc
                raise
            delay = min(16.0, (2 ** (attempt - 1)) * 1.2 + random.uniform(0.1, 0.6))
            print(
                f"[retry {attempt}/{max_retries}] transient edge-tts error ({msg}); sleeping {delay:.2f}s",
                file=sys.stderr,
            )
            await asyncio.sleep(delay)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_script_spec(spec_path: Path) -> dict[str, Any]:
    """Load and validate script.json specification."""
    data = json.loads(spec_path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("Spec JSON root must be an object.")
    scenes = data.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise ValueError("Spec JSON must include a non-empty 'scenes' array.")
    total_duration = float(data.get("total_duration_sec", 60.0))
    if total_duration <= 0:
        raise ValueError("total_duration_sec must be > 0.")

    default_slot = total_duration / len(scenes)
    cursor = 0.0
    normalized_scenes = []
    for idx, sc in enumerate(scenes, start=1):
        sid = safe_identifier(str(sc.get("id") or f"scene-{idx:02d}"), label="scene.id")
        comp_id = safe_identifier(str(sc.get("composition_id") or f"scene-{idx:02d}"), label="composition_id")
        text = str(sc.get("text", "")).strip()
        if not text:
            raise ValueError(f"Scene '{sid}' has empty narration text.")
        if EMOJI_RE.search(text):
            raise ValueError(f"Scene '{sid}' text contains forbidden emoji characters.")
        dur = float(sc.get("duration_sec", default_slot))
        if dur <= 0:
            raise ValueError(f"Scene '{sid}' duration_sec must be > 0.")
        normalized_scenes.append(
            {
                "id": sid,
                "composition_id": comp_id,
                "title": str(sc.get("title") or f"Cena {idx:02d}"),
                "kicker": str(sc.get("kicker") or f"ESTAGIO {idx:02d} / {len(scenes):02d}"),
                "subtitle": str(sc.get("subtitle") or ""),
                "image": str(sc.get("image") or f"{idx:02d}_{sid}.png"),
                "duration_sec": dur,
                "slot_start_sec": round(cursor, 4),
                "slot_end_sec": round(cursor + dur, 4),
                "keywords": [str(k) for k in sc.get("keywords", [])],
                "text": text,
            }
        )
        cursor += dur

    return {
        "title": str(data.get("title") or "Narrated Video Presentation"),
        "language": str(data.get("language") or "pt-BR"),
        "voice": str(data.get("voice") or "pt-BR-AntonioNeural"),
        "total_duration_sec": round(cursor, 4),
        "fps": int(data.get("fps", 30)),
        "width": int(data.get("width", 1920)),
        "height": int(data.get("height", 1080)),
        "slot_pad_sec": float(data.get("slot_pad_sec", 0.15)),
        "target_lufs": float(data.get("target_lufs", -17.0)),
        "ambient_lufs": float(data.get("ambient_lufs", -24.0)),
        "palette": data.get(
            "palette",
            {
                "ground": "#0B0D0A",
                "ink": "#F3EFE2",
                "ink_secondary": "#C7C1B0",
                "accent": "#E2B43B",
                "secondary": "#3B6E47",
                "secondary_readable": "#7AC289",
            },
        ),
        "scenes": normalized_scenes,
    }


def synthesize_ambient_bed(duration_sec: float, out_path: Path, target_lufs: float = -24.0) -> dict[str, Any]:
    """Generate a calm, royalty-free harmonic pad in MP3 via ffmpeg lavfi and calibrate LUFS."""
    if duration_sec <= 2.0:
        raise ValueError("Ambient duration must exceed 2.0 seconds.")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fade_out_start = round(max(0.5, duration_sec - 2.4), 3)
    with tempfile.TemporaryDirectory(prefix="nvs_amb_") as tmp:
        raw_wav = Path(tmp) / "ambient_raw.wav"
        filter_expr = (
            f"sine=frequency=130.81:sample_rate=48000:duration={duration_sec}[c3];"
            f"sine=frequency=196.00:sample_rate=48000:duration={duration_sec}[g3];"
            f"sine=frequency=293.66:sample_rate=48000:duration={duration_sec}[d4];"
            f"sine=frequency=440.00:sample_rate=48000:duration={duration_sec}[a4];"
            "[c3][g3][d4][a4]amix=inputs=4:normalize=0,"
            "lowpass=f=680,"
            "aecho=0.8:0.88:45|75:0.22|0.18,"
            f"afade=t=in:st=0:d=1.2,afade=t=out:st={fade_out_start}:d=2.4,"
            "aformat=channel_layouts=stereo[out]"
        )
        run_cmd(["ffmpeg", "-y", "-filter_complex", filter_expr, "-map", "[out]", "-c:a", "pcm_s24le", str(raw_wav)])
        stats = analyze_loudness(raw_wav)
        current_lufs = stats["integrated_lufs"] if stats["integrated_lufs"] is not None else -18.0
        max_db = stats["max_volume_db"] if stats["max_volume_db"] is not None else -3.0
        gain_db = round(min(target_lufs - current_lufs, -1.5 - max_db), 2)
        run_cmd(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(raw_wav),
                "-af",
                f"volume={gain_db}dB",
                "-ar",
                "48000",
                "-ac",
                "2",
                "-c:a",
                "libmp3lame",
                "-b:a",
                "192k",
                str(out_path),
            ]
        )
    return {"file": str(out_path), "probe": ffprobe_media(out_path), "volumedetect": analyze_loudness(out_path)}


def build_captions_html(timings: dict[str, Any], accent_color: str = "#E2B43B") -> str:
    """Render deterministic HyperFrames captions.html with WordBoundary groups."""
    duration = float(timings.get("timeline_duration_sec", 60.0))
    captions = timings.get("captions", [])
    words_by_id = {w["id"]: w for w in timings.get("words", [])}
    kw_set = set()
    for sc in timings.get("scenes", []):
        for kw in sc.get("keywords", []):
            kw_set.add(str(kw).lower())

    slot_divs: list[str] = []
    js_groups: list[dict[str, Any]] = []

    for c_idx, cap in enumerate(captions):
        c_id = f"cap-c{c_idx}"
        inner_id = f"{c_id}-inner"
        word_ids = cap.get("word_ids")
        if word_ids:
            group_words = [words_by_id[wid] for wid in word_ids if wid in words_by_id]
        else:
            # Fallback if timings came from a simplified caption payload
            tokens = str(cap.get("text", "")).split()
            c_start = float(cap["start"])
            c_end = float(cap["end"])
            step = max(0.05, (c_end - c_start) / max(1, len(tokens)))
            group_words = [
                {"text": t, "start": round(c_start + i * step, 4)} for i, t in enumerate(tokens)
            ]

        span_html: list[str] = []
        js_words: list[dict[str, Any]] = []
        for w_idx, w in enumerate(group_words):
            w_id = f"{c_id}-w{w_idx}"
            w_text = str(w["text"])
            clean_norm = w_text.strip(".,;:!?\"'").lower()
            is_em = bool(w.get("em")) or (w_text.lower() in kw_set) or (clean_norm in kw_set)
            cls = "cap-word cap-word--em" if is_em else "cap-word"
            span_html.append(f'<span id="{w_id}" class="{cls}">{html.escape(w_text)}</span>')
            js_words.append({"id": w_id, "start": float(w["start"]), "em": is_em})

        slot_divs.append(
            f'      <div id="{c_id}" class="cap-slot">'
            f'<div id="{inner_id}" class="cap-inner">{"".join(span_html)}</div></div>'
        )
        js_groups.append(
            {
                "id": inner_id,
                "start": float(cap["start"]),
                "end": float(cap["end"]),
                "words": js_words,
            }
        )

    groups_json = json.dumps(js_groups, ensure_ascii=False)
    slots_block = "\n".join(slot_divs)
    return f"""<template>
  <style>
    #root {{
      position: absolute;
      inset: 0;
      overflow: visible;
      pointer-events: none;
      background: transparent;
      font-family: "Inter", sans-serif;
    }}

    .cap-safe-band {{
      position: absolute;
      left: 192px;
      width: 1536px;
      bottom: 120px;
      height: 112px;
      overflow: visible;
    }}

    .cap-slot {{
      position: absolute;
      left: 0;
      right: 0;
      bottom: 0;
      text-align: center;
      overflow: visible;
    }}

    .cap-inner {{
      display: inline-block;
      background: rgba(11, 13, 10, 0.88);
      border-bottom: 2px solid {accent_color};
      padding: 12px 28px;
      opacity: 0;
      visibility: hidden;
    }}

    .cap-word {{
      display: inline-block;
      font-family: "Inter", sans-serif;
      font-size: 44px;
      font-weight: 600;
      line-height: 1.22;
      color: #A7A294;
      margin: 0 7px;
      text-shadow: 0 2px 10px rgba(0, 0, 0, 0.78);
    }}

    .cap-word--em {{
      font-weight: 700;
    }}
  </style>

  <div id="root" data-composition-id="captions" data-width="1920" data-height="1080">
    <div id="cap-safe-band" class="cap-safe-band" data-layout-allow-caption-zone>
{slots_block}
    </div>
  </div>

  <script>
    (function () {{
      const DURATION = {duration};
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});

      const groups = {groups_json};

      groups.forEach(function (g) {{
        const el = document.getElementById(g.id);
        if (!el) return;
        const fadeIn = Math.min(0.1, Math.max(0.04, (g.end - g.start) * 0.15));
        const fadeOut = Math.min(0.08, Math.max(0.04, (g.end - g.start) * 0.12));

        tl.set(el, {{ opacity: 0, visibility: "hidden" }}, 0);
        tl.set(el, {{ visibility: "visible" }}, g.start);
        tl.fromTo(
          el,
          {{ opacity: 0, y: 6 }},
          {{ opacity: 1, y: 0, duration: fadeIn, ease: "power3.out" }},
          g.start
        );

        g.words.forEach(function (w) {{
          const wEl = document.getElementById(w.id);
          if (!wEl) return;
          tl.fromTo(
            wEl,
            {{ color: "#A7A294" }},
            {{ color: w.em ? "{accent_color}" : "#F3EFE2", duration: 0.06, ease: "none" }},
            w.start
          );
        }});

        tl.to(el, {{ opacity: 0, duration: fadeOut, ease: "power2.in" }}, g.end - fadeOut);
        tl.set(el, {{ opacity: 0, visibility: "hidden" }}, g.end);
      }});

      tl.to({{}}, {{ duration: DURATION }}, 0);
      window.__timelines["captions"] = tl;
    }})();
  </script>
</template>
"""


def cmd_doctor(args: argparse.Namespace) -> int:
    """Verify local runtime prerequisites for Narrated Video Studio."""
    checks: dict[str, Any] = {
        "python_version": sys.version.split()[0],
        "python_ok": sys.version_info >= (3, 10),
        "edge_tts": False,
        "ffmpeg": shutil.which("ffmpeg"),
        "ffprobe": shutil.which("ffprobe"),
        "node": shutil.which("node"),
        "npx": shutil.which("npx") or shutil.which("npx.cmd"),
        "hyperframes_version": None,
    }
    try:
        import edge_tts  # noqa: F401

        checks["edge_tts"] = True
    except ImportError:
        checks["edge_tts"] = False

    if checks["npx"]:
        try:
            res = run_cmd([_resolve_npx_executable(), "hyperframes", "--version"])
            checks["hyperframes_version"] = res.stdout.strip()
        except Exception as exc:
            checks["hyperframes_error"] = str(exc)

    checks["healthy"] = bool(
        checks["python_ok"] and checks["edge_tts"] and checks["ffmpeg"] and checks["ffprobe"] and checks["node"]
    )
    out_path = Path(args.output)
    write_json(out_path, checks)
    print(f"Doctor report written to: {out_path} (healthy={checks['healthy']})")
    return 0 if checks["healthy"] else 1


def cmd_voices(args: argparse.Namespace) -> int:
    """List available Edge-TTS neural voices filtered by locale."""
    import edge_tts

    async def _fetch() -> list[dict[str, Any]]:
        voices = await edge_tts.list_voices()
        locale_filter = args.locale.lower()
        selected = [
            {
                "ShortName": v.get("ShortName"),
                "Locale": v.get("Locale"),
                "Gender": v.get("Gender"),
                "FriendlyName": v.get("FriendlyName"),
            }
            for v in voices
            if locale_filter == "all" or str(v.get("Locale", "")).lower().startswith(locale_filter)
        ]
        return selected

    result = asyncio.run(_fetch())
    out_path = Path(args.output)
    write_json(out_path, {"locale": args.locale, "count": len(result), "voices": result})
    print(f"Found {len(result)} voices for '{args.locale}'. Saved to: {out_path}")
    return 0


def cmd_synth_audio(args: argparse.Namespace) -> int:
    """Synthesize per-scene and full narration MP3, SRT, WordBoundary JSON and optional ambient bed."""
    spec_path = Path(args.spec)
    spec = load_script_spec(spec_path)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    scenes_dir = out_dir / "cenas"
    scenes_dir.mkdir(parents=True, exist_ok=True)

    limiter = MonotonicRateLimiter(min_interval_sec=args.rate_interval)

    async def _run() -> dict[str, Any]:
        with tempfile.TemporaryDirectory(prefix="nvs_tts_") as tmp:
            tmp_dir = Path(tmp)
            trimmed_wavs: list[Path] = []
            all_wb: list[list[dict[str, Any]]] = []
            total_spoken = 0.0
            slot_errors: list[str] = []

            for idx, sc in enumerate(spec["scenes"]):
                raw_mp3 = tmp_dir / f"{sc['id']}_raw.mp3"
                wb_list = await synth_scene_with_retry(
                    voice=spec["voice"],
                    text=sc["text"],
                    raw_mp3=raw_mp3,
                    limiter=limiter,
                    strict_tokens=args.strict_tokens,
                )
                all_wb.append(wb_list)

                first_start = float(wb_list[0]["local_start"])
                last_end = float(wb_list[-1]["local_end"])
                total_spoken += max(0.0, last_end - first_start)

                offset_s = round(sc["slot_start_sec"] + spec["slot_pad_sec"], 4)
                trim_end = round(last_end + 0.14, 4)
                fade_start = round(max(0.0, trim_end - 0.025), 4)
                is_last = idx == len(spec["scenes"]) - 1
                ceiling = (sc["slot_end_sec"] - 0.5) if is_last else sc["slot_end_sec"]
                if offset_s + trim_end > ceiling:
                    slot_errors.append(
                        f"Scene '{sc['id']}' speech ends at {offset_s + trim_end:.3f}s (> slot ceiling {ceiling:.3f}s)."
                    )

                trimmed_wav = tmp_dir / f"{sc['id']}_trimmed.wav"
                run_cmd(
                    [
                        "ffmpeg",
                        "-y",
                        "-i",
                        str(raw_mp3),
                        "-af",
                        f"atrim=0:{trim_end},asetpts=PTS-STARTPTS,afade=t=out:st={fade_start}:d=0.025",
                        "-ar",
                        "48000",
                        "-ac",
                        "2",
                        "-c:a",
                        "pcm_s24le",
                        str(trimmed_wav),
                    ]
                )
                trimmed_wavs.append(trimmed_wav)

            if slot_errors:
                raise RuntimeError(" ; ".join(slot_errors))

            concat_wav = tmp_dir / "speech_concat.wav"
            concat_inputs: list[str] = []
            concat_labels: list[str] = []
            for idx, w in enumerate(trimmed_wavs):
                concat_inputs.extend(["-i", str(w)])
                concat_labels.append(f"[{idx}:a]")
            run_cmd(
                [
                    "ffmpeg",
                    "-y",
                    *concat_inputs,
                    "-filter_complex",
                    f"{''.join(concat_labels)}concat=n={len(trimmed_wavs)}:v=0:a=1[out]",
                    "-map",
                    "[out]",
                    "-c:a",
                    "pcm_s24le",
                    str(concat_wav),
                ]
            )
            stats = analyze_loudness(concat_wav)
            curr_lufs = stats["integrated_lufs"] if stats["integrated_lufs"] is not None else -18.0
            max_db = stats["max_volume_db"] if stats["max_volume_db"] is not None else -3.0
            gain_db = round(min(spec["target_lufs"] - curr_lufs, -1.5 - max_db), 2)

            scene_mp3_paths: list[Path] = []
            for sc, twav in zip(spec["scenes"], trimmed_wavs):
                out_mp3 = scenes_dir / f"{sc['id']}.mp3"
                run_cmd(
                    [
                        "ffmpeg",
                        "-y",
                        "-i",
                        str(twav),
                        "-af",
                        f"volume={gain_db}dB",
                        "-ar",
                        "48000",
                        "-ac",
                        "2",
                        "-c:a",
                        "libmp3lame",
                        "-b:a",
                        "192k",
                        str(out_mp3),
                    ]
                )
                scene_mp3_paths.append(out_mp3)

            full_mp3 = out_dir / "narration.mp3"
            full_inputs: list[str] = []
            filter_chains: list[str] = []
            mix_labels: list[str] = []
            for idx, (sc, twav) in enumerate(zip(spec["scenes"], trimmed_wavs)):
                offset_s = sc["slot_start_sec"] + spec["slot_pad_sec"]
                delay_ms = int(round(offset_s * 1000))
                full_inputs.extend(["-i", str(twav)])
                filter_chains.append(f"[{idx}:a]adelay={delay_ms}|{delay_ms}[d{idx}]")
                mix_labels.append(f"[d{idx}]")
            mix_expr = (
                ";".join(filter_chains)
                + f";{''.join(mix_labels)}amix=inputs={len(trimmed_wavs)}:duration=longest:normalize=0,volume={gain_db}dB[out]"
            )
            run_cmd(
                [
                    "ffmpeg",
                    "-y",
                    *full_inputs,
                    "-filter_complex",
                    mix_expr,
                    "-map",
                    "[out]",
                    "-ar",
                    "48000",
                    "-ac",
                    "2",
                    "-c:a",
                    "libmp3lame",
                    "-b:a",
                    "192k",
                    str(full_mp3),
                ]
            )

            full_probe = ffprobe_media(full_mp3)
            full_loud = analyze_loudness(full_mp3)
            if full_loud["mean_volume_db"] is None or full_loud["mean_volume_db"] < -35.0:
                raise RuntimeError(f"Generated narration audio failed loudness floor: {full_loud}")

            scenes_json: list[dict[str, Any]] = []
            global_words: list[dict[str, Any]] = []
            global_captions: list[dict[str, Any]] = []
            g_w_idx = 0
            g_c_idx = 0

            for idx, (sc, wb_list, sm_path) in enumerate(zip(spec["scenes"], all_wb, scene_mp3_paths)):
                s_num = idx + 1
                offset_s = round(sc["slot_start_sec"] + spec["slot_pad_sec"], 4)
                s_probe = ffprobe_media(sm_path)
                s_loud = analyze_loudness(sm_path)
                kw_lower = {k.lower() for k in sc["keywords"]}

                scene_words: list[dict[str, Any]] = []
                for w_i, wb in enumerate(wb_list):
                    g_start = round(offset_s + float(wb["local_start"]), 4)
                    g_end = round(offset_s + float(wb["local_end"]), 4)
                    disp = wb["display_text"]
                    is_em = disp.lower() in kw_lower or disp.strip(".,;:!?").lower() in kw_lower
                    w_obj = {
                        "id": f"s{s_num}_w{w_i}",
                        "global_id": f"w{g_w_idx}",
                        "text": disp,
                        "word": wb["wb_text"],
                        "em": is_em,
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
                            "text": disp,
                            "em": is_em,
                            "start": g_start,
                            "end": g_end,
                        }
                    )
                    g_w_idx += 1

                raw_groups = build_caption_groups(scene_words, max_words=5)
                scene_captions: list[dict[str, Any]] = []
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
                            "word_ids": c_obj["word_ids"],
                            "_ref": c_obj,
                        }
                    )
                    g_c_idx += 1

                scenes_json.append(
                    {
                        "id": sc["id"],
                        "composition_id": sc["composition_id"],
                        "index": s_num,
                        "title": sc["title"],
                        "keywords": sc["keywords"],
                        "file": f"cenas/{sc['id']}.mp3",
                        "slot_start_sec": sc["slot_start_sec"],
                        "slot_end_sec": sc["slot_end_sec"],
                        "audio_offset_sec": offset_s,
                        "ffprobe_duration_sec": s_probe["duration_sec"],
                        "spoken_start_sec": scene_words[0]["start"],
                        "spoken_end_sec": scene_words[-1]["end"],
                        "volumedetect": s_loud,
                        "text": sc["text"],
                        "words": scene_words,
                        "caption_groups": scene_captions,
                    }
                )

            for k in range(len(global_captions) - 1):
                if global_captions[k]["end"] > global_captions[k + 1]["start"]:
                    clamped = round(global_captions[k + 1]["start"] - 0.01, 4)
                    global_captions[k]["end"] = clamped
                    global_captions[k]["_ref"]["end"] = clamped

            clean_captions = [{k: v for k, v in c.items() if k != "_ref"} for c in global_captions]
            srt_lines = [
                f"{i + 1}\n{fmt_srt_ts(c['start'])} --> {fmt_srt_ts(c['end'])}\n{c['text']}\n"
                for i, c in enumerate(clean_captions)
            ]
            srt_path = out_dir / "narration.srt"
            srt_path.write_text("\n".join(srt_lines), encoding="utf-8")

            ambient_info = None
            ambient_name = None
            if args.ambient:
                ambient_name = "ambient_bed.mp3"
                ambient_info = synthesize_ambient_bed(
                    duration_sec=spec["total_duration_sec"],
                    out_path=out_dir / ambient_name,
                    target_lufs=spec["ambient_lufs"],
                )

            timings_path = out_dir / "timings.json"
            payload = {
                "title": spec["title"],
                "voice": spec["voice"],
                "sample_rate_hz": full_probe["audio"]["sample_rate"] if full_probe["audio"] else 48000,
                "channels": full_probe["audio"]["channels"] if full_probe["audio"] else 2,
                "audio_file": "narration.mp3",
                "ambient_file": ambient_name,
                "srt_file": "narration.srt",
                "timeline_duration_sec": spec["total_duration_sec"],
                "ffprobe_duration_sec": full_probe["duration_sec"],
                "spoken_duration_sec": round(total_spoken, 4),
                "volumedetect": full_loud,
                "scenes": scenes_json,
                "words": global_words,
                "captions": clean_captions,
            }
            write_json(timings_path, payload)
            return {
                "narration_mp3": str(full_mp3),
                "srt": str(srt_path),
                "timings_json": str(timings_path),
                "ambient": ambient_info,
                "ffprobe_duration_sec": full_probe["duration_sec"],
                "spoken_duration_sec": round(total_spoken, 4),
                "volumedetect": full_loud,
            }

    summary = asyncio.run(_run())
    if args.output:
        write_json(Path(args.output), summary)
    print(f"Audio synthesis complete. Timings saved to: {summary['timings_json']}")
    return 0


def cmd_synth_ambient(args: argparse.Namespace) -> int:
    """Synthesize a standalone calm harmonic ambient bed MP3."""
    out_mp3 = Path(args.output)
    info = synthesize_ambient_bed(args.duration, out_mp3, target_lufs=args.lufs)
    if args.report:
        write_json(Path(args.report), info)
    print(f"Ambient bed generated at: {out_mp3} (LUFS={info['volumedetect']['integrated_lufs']})")
    return 0


def cmd_build_captions(args: argparse.Namespace) -> int:
    """Generate HyperFrames compositions/captions.html deterministically from timings.json."""
    timings = json.loads(Path(args.timings).read_text(encoding="utf-8-sig"))
    html_text = build_captions_html(timings, accent_color=args.accent)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_text, encoding="utf-8")
    print(f"Captions composition written to: {out_path}")
    return 0


def _build_starter_scene_html(scene: dict[str, Any], palette: dict[str, str], index: int, total: int) -> str:
    """Create a starter HyperFrames sub-composition honoring the strict render contract."""
    comp_id = scene["composition_id"]
    dur = scene["duration_sec"]
    ground = palette.get("ground", "#0B0D0A")
    ink = palette.get("ink", "#F3EFE2")
    ink2 = palette.get("ink_secondary", "#C7C1B0")
    accent = palette.get("accent", "#E2B43B")
    leaf = palette.get("secondary", "#3B6E47")
    img_path = f"assets/{scene['image']}"

    return f"""<template>
  <style>
    #root {{
      position: absolute;
      inset: 0;
      overflow: hidden;
      background: {ground};
      color: {ink};
      font-family: "Inter", sans-serif;
    }}

    .plate-wrap {{
      position: absolute;
      inset: 0;
      overflow: hidden;
      z-index: 1;
    }}

    .plate-inner {{
      position: absolute;
      inset: 0;
      width: 1920px;
      height: 1080px;
      transform-origin: 50% 50%;
    }}

    .plate-img {{
      width: 1920px;
      height: 1080px;
      object-fit: cover;
      display: block;
    }}

    .scrim-left {{
      position: absolute;
      inset: 0;
      z-index: 2;
      background: linear-gradient(
        90deg,
        rgba(11, 13, 10, 0.94) 0%,
        rgba(11, 13, 10, 0.80) 44%,
        rgba(11, 13, 10, 0.25) 75%,
        rgba(11, 13, 10, 0.56) 100%
      );
    }}

    .scrim-bottom {{
      position: absolute;
      left: 0;
      right: 0;
      bottom: 0;
      height: 300px;
      z-index: 3;
      background: linear-gradient(0deg, rgba(11, 13, 10, 0.95) 0%, rgba(11, 13, 10, 0) 100%);
    }}

    .editorial {{
      position: absolute;
      left: 192px;
      top: 118px;
      width: 740px;
      z-index: 10;
    }}

    .kicker {{
      font-family: "JetBrains Mono", monospace;
      font-size: 28px;
      font-weight: 500;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: {accent};
      border-left: 4px solid {accent};
      padding-left: 18px;
      margin-bottom: 20px;
    }}

    .title {{
      font-family: "Playfair Display", serif;
      font-size: 76px;
      font-weight: 800;
      line-height: 1.04;
      letter-spacing: -0.025em;
      color: {ink};
      margin-bottom: 14px;
    }}

    .subtitle {{
      font-family: "Playfair Display", serif;
      font-size: 34px;
      font-style: italic;
      color: {ink2};
      margin-bottom: 24px;
    }}

    .rule {{
      width: 520px;
      height: 3px;
      background: {leaf};
      transform-origin: left center;
    }}
  </style>

  <div id="root" data-composition-id="{comp_id}" data-width="1920" data-height="1080">
    <div class="plate-wrap" data-layout-allow-overflow>
      <div id="{comp_id}-plate-inner" class="plate-inner">
        <img class="plate-img" src="{html.escape(img_path)}" alt="{html.escape(scene['title'])}" />
      </div>
    </div>
    <div class="scrim-left" data-layout-ignore></div>
    <div class="scrim-bottom" data-layout-ignore></div>

    <div class="editorial">
      <div id="{comp_id}-kicker" class="kicker">{html.escape(scene['kicker'])}</div>
      <h1 id="{comp_id}-title" class="title">{html.escape(scene['title'])}</h1>
      <div id="{comp_id}-subtitle" class="subtitle">{html.escape(scene['subtitle'])}</div>
      <div id="{comp_id}-rule" class="rule"></div>
    </div>
  </div>

  <script>
    (function () {{
      const SCENE_DURATION = {dur};
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});

      tl.fromTo(
        "#{comp_id}-plate-inner",
        {{ scale: 1.10, x: 0, y: 0 }},
        {{ scale: 1.17, x: -16, y: -14, duration: SCENE_DURATION - 0.1, ease: "power2.inOut" }},
        0
      );

      tl.fromTo(
        "#{comp_id}-title",
        {{ opacity: 0.72, filter: "blur(4px)" }},
        {{ opacity: 1, filter: "blur(0px)", duration: 0.35, ease: "power4.out" }},
        0
      );

      tl.fromTo(
        "#{comp_id}-rule",
        {{ scaleX: 0 }},
        {{ scaleX: 1, duration: 0.55, ease: "expo.out" }},
        0.2
      );

      tl.to("#root", {{ opacity: 0.88, duration: 0.16, ease: "power3.in" }}, SCENE_DURATION - 0.18);
      tl.to({{}}, {{ duration: SCENE_DURATION }}, 0);
      window.__timelines["{comp_id}"] = tl;
    }})();
  </script>
</template>
"""


def cmd_scaffold_video(args: argparse.Namespace) -> int:
    """Scaffold a HyperFrames 1080p video project from script.json and optional timings/images."""
    spec = load_script_spec(Path(args.spec))
    out_dir = Path(args.output_dir)
    comp_dir = out_dir / "compositions"
    assets_dir = out_dir / "assets"
    (comp_dir / "components").mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    palette = spec["palette"]
    total_dur = spec["total_duration_sec"]

    if args.images_dir:
        src_imgs = Path(args.images_dir)
        for sc in spec["scenes"]:
            candidate = src_imgs / sc["image"]
            if candidate.exists():
                shutil.copy2(candidate, assets_dir / sc["image"])

    timings: dict[str, Any] | None = None
    narration_dur = total_dur
    has_ambient = False
    if args.timings:
        timings_path = Path(args.timings)
        timings = json.loads(timings_path.read_text(encoding="utf-8-sig"))
        shutil.copy2(timings_path, assets_dir / "timings.json")
        narration_dur = float(timings.get("ffprobe_duration_sec", total_dur))
        src_audio_dir = timings_path.parent
        narr_mp3 = src_audio_dir / str(timings.get("audio_file", "narration.mp3"))
        if narr_mp3.exists():
            shutil.copy2(narr_mp3, assets_dir / "narration.mp3")
        amb_file = timings.get("ambient_file")
        if amb_file and (src_audio_dir / amb_file).exists():
            shutil.copy2(src_audio_dir / amb_file, assets_dir / "ambient_bed.mp3")
            has_ambient = True

    scene_hosts: list[str] = []
    for sc in spec["scenes"]:
        comp_id = sc["composition_id"]
        rel_src = f"compositions/{sc['id']}.html"
        safe_resolve(out_dir, rel_src).write_text(
            _build_starter_scene_html(sc, palette, 1, len(spec["scenes"])),
            encoding="utf-8",
        )
        scene_hosts.append(
            f'      <div id="{comp_id}" class="clip scene-host" data-composition-id="{comp_id}" '
            f'data-composition-src="{rel_src}" data-start="{sc["slot_start_sec"]}" '
            f'data-duration="{sc["duration_sec"]}" data-track-index="1" data-track-kind="graphics" '
            f'data-width="{spec["width"]}" data-height="{spec["height"]}"></div>'
        )

    captions_host = ""
    if timings is not None:
        (comp_dir / "captions.html").write_text(
            build_captions_html(timings, accent_color=palette.get("accent", "#E2B43B")),
            encoding="utf-8",
        )
        captions_host = (
            f'      <div id="captions" class="clip captions-host" data-composition-id="captions" '
            f'data-composition-src="compositions/captions.html" data-start="0" data-duration="{total_dur}" '
            f'data-track-index="2" data-track-kind="captions" data-width="{spec["width"]}" data-height="{spec["height"]}"></div>'
        )

    ambient_tag = ""
    if has_ambient:
        ambient_tag = (
            f'      <audio id="ambient-bed" class="clip" src="assets/ambient_bed.mp3" data-start="0" '
            f'data-duration="{total_dur}" data-track-index="4" data-volume="0.32" data-fade-in="0.8" data-fade-out="2.2"></audio>'
        )

    index_html = f"""<!doctype html>
<html lang="{html.escape(spec['language'])}" data-resolution="landscape">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={spec['width']}, height={spec['height']}" />
    <title>{html.escape(spec['title'])}</title>
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: {spec['width']}px; height: {spec['height']}px; overflow: hidden; background: {palette.get('ground', '#0B0D0A')}; }}
      #root {{ position: relative; width: {spec['width']}px; height: {spec['height']}px; overflow: hidden; }}
      .scene-host {{ position: absolute; inset: 0; z-index: 10; }}
      .captions-host {{ position: absolute; inset: 0; z-index: 80; pointer-events: none; }}
      .progress-rail {{ position: absolute; left: 192px; top: 52px; width: 1536px; height: 4px; background: rgba(243, 239, 226, 0.16); z-index: 70; pointer-events: none; }}
      .progress-fill {{ width: 100%; height: 100%; background: {palette.get('accent', '#E2B43B')}; transform-origin: left center; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{total_dur}" data-fps="{spec['fps']}" data-width="{spec['width']}" data-height="{spec['height']}">
{chr(10).join(scene_hosts)}
{captions_host}
      <div class="progress-rail" data-layout-ignore><div id="global-progress-fill" class="progress-fill"></div></div>
      <audio id="narration-track" class="clip" src="assets/narration.mp3" data-start="0" data-duration="{narration_dur}" data-track-index="3" data-volume="1"></audio>
{ambient_tag}
    </div>
    <script>
      (function () {{
        window.__timelines = window.__timelines || {{}};
        const tl = gsap.timeline({{ paused: true }});
        tl.fromTo("#global-progress-fill", {{ scaleX: 0 }}, {{ scaleX: 1, duration: {total_dur}, ease: "none" }}, 0);
        window.__timelines["main"] = tl;
      }})();
    </script>
  </body>
</html>
"""
    (out_dir / "index.html").write_text(index_html, encoding="utf-8")
    write_json(
        out_dir / "hyperframes.json",
        {
            "$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
            "paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"},
            "media": {"autoProxy": True},
        },
    )
    write_json(
        out_dir / "package.json",
        {
            "name": safe_identifier(out_dir.name.lower().replace(" ", "-"), "project_name") if SAFE_ID_RE.match(out_dir.name.lower().replace(" ", "-")) else "narrated-video-project",
            "private": True,
            "type": "module",
            "scripts": {
                "dev": "npx --yes hyperframes preview",
                "check": "npx --yes hyperframes check",
                "render": "npx --yes hyperframes render",
            },
        },
    )

    spec_lines = [
        f"# SPEC - {spec['title']}",
        "",
        f"OUTPUT: HyperFrames, {spec['width']} x {spec['height']}, {spec['fps']} fps.",
        f"TIME: {total_dur} s ({int(round(total_dur * spec['fps']))} frames).",
        f"LOOK: ground {palette.get('ground')}; ink {palette.get('ink')}; accent {palette.get('accent')}; secondary {palette.get('secondary')}.",
        "BANNED: emojis, rounded-full badges, AI-purple/dark meshes, text smaller than 28px, frame 0 black.",
        "QA: npx hyperframes check --json --strict, snapshot midpoint per scene, ffprobe & volumedetect on final MP4.",
    ]
    (out_dir / "SPEC.md").write_text("\n".join(spec_lines) + "\n", encoding="utf-8")

    print(f"HyperFrames project scaffolded at: {out_dir}")
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    """Audit project files for emojis, MP4 stream integrity, audio loudness and HyperFrames checks."""
    proj_dir = Path(args.project_dir)
    if not proj_dir.exists():
        raise FileNotFoundError(f"Project directory not found: {proj_dir}")

    emoji_hits: list[dict[str, Any]] = []
    files_scanned = 0
    for root, dirs, files in os.walk(proj_dir):
        dirs[:] = [d for d in dirs if d not in {".venv", "node_modules", ".hyperframes", ".git", "__pycache__"}]
        for fname in files:
            p = Path(root) / fname
            if p.suffix.lower() not in TEXT_SCAN_EXTS:
                continue
            files_scanned += 1
            txt = p.read_text(encoding="utf-8", errors="ignore")
            matches = EMOJI_RE.findall(txt)
            if matches:
                emoji_hits.append({"file": str(p), "count": len(matches)})

    mp4_report = None
    mp4_ok = True
    if args.mp4:
        mp4_path = Path(args.mp4)
        probe = ffprobe_media(mp4_path)
        loud = analyze_loudness(mp4_path)
        has_video = bool(probe.get("video") and probe["video"].get("width"))
        has_audio = bool(probe.get("audio") and probe["audio"].get("sample_rate"))
        not_silent = loud["mean_volume_db"] is not None and loud["mean_volume_db"] > -35.0
        no_clip = loud["max_volume_db"] is not None and loud["max_volume_db"] <= 0.0
        mp4_ok = has_video and has_audio and not_silent and no_clip and probe["duration_sec"] > 0
        mp4_report = {"probe": probe, "volumedetect": loud, "passed": mp4_ok}

    hf_report = None
    hf_ok = True
    if args.strict_hyperframes:
        res = run_cmd([_resolve_npx_executable(), "hyperframes", "check", "--json", "--strict", "--samples", "15"], cwd=proj_dir)
        hf_report = json.loads(res.stdout)
        hf_ok = bool(hf_report.get("ok"))

    passed = (len(emoji_hits) == 0) and mp4_ok and hf_ok
    report = {
        "passed": passed,
        "project_dir": str(proj_dir),
        "files_scanned": files_scanned,
        "emoji_hits": emoji_hits,
        "mp4_audit": mp4_report,
        "hyperframes_check": hf_report,
    }
    out_path = Path(args.output)
    write_json(out_path, report)
    print(f"Audit complete (passed={passed}). Report written to: {out_path}")
    return 0 if passed else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="narrated-video",
        description="Deterministic CLI toolkit for Narrated Video Studio (Edge-TTS + FFmpeg + HyperFrames).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_doc = sub.add_parser("doctor", help="Verify Python, edge-tts, ffmpeg, ffprobe, node and HyperFrames")
    p_doc.add_argument("--output", required=True, help="Output JSON report path")
    p_doc.set_defaults(func=cmd_doctor)

    p_voi = sub.add_parser("voices", help="List available Edge-TTS voices")
    p_voi.add_argument("--locale", default="pt-BR", help="Locale prefix (e.g. pt-BR, en-US, or all)")
    p_voi.add_argument("--output", required=True, help="Output JSON file path")
    p_voi.set_defaults(func=cmd_voices)

    p_syn = sub.add_parser("synth-audio", help="Synthesize narrated audio, SRT, WordBoundary JSON and optional ambient bed")
    p_syn.add_argument("--spec", required=True, help="Path to script.json")
    p_syn.add_argument("--output-dir", required=True, help="Directory to store MP3s, SRT and timings.json")
    p_syn.add_argument("--ambient", action="store_true", help="Also generate calm harmonic ambient_bed.mp3")
    p_syn.add_argument("--strict-tokens", action="store_true", help="Fail if edge-tts WordBoundary count differs from text.split()")
    p_syn.add_argument("--rate-interval", type=float, default=0.4, help="Minimum seconds between TTS requests")
    p_syn.add_argument("--output", help="Optional JSON summary report file path")
    p_syn.set_defaults(func=cmd_synth_audio)

    p_amb = sub.add_parser("synth-ambient", help="Synthesize standalone harmonic ambient MP3 bed")
    p_amb.add_argument("--duration", type=float, required=True, help="Duration in seconds")
    p_amb.add_argument("--lufs", type=float, default=-24.0, help="Target integrated LUFS")
    p_amb.add_argument("--output", required=True, help="Output MP3 file path")
    p_amb.add_argument("--report", help="Optional JSON report path")
    p_amb.set_defaults(func=cmd_synth_ambient)

    p_cap = sub.add_parser("build-captions", help="Generate HyperFrames compositions/captions.html from timings.json")
    p_cap.add_argument("--timings", required=True, help="Path to timings.json")
    p_cap.add_argument("--accent", default="#E2B43B", help="Hex color for emphasized keywords")
    p_cap.add_argument("--output", required=True, help="Output HTML file path")
    p_cap.set_defaults(func=cmd_build_captions)

    p_scf = sub.add_parser("scaffold-video", help="Scaffold a HyperFrames project from script.json")
    p_scf.add_argument("--spec", required=True, help="Path to script.json")
    p_scf.add_argument("--output-dir", required=True, help="Target HyperFrames project directory")
    p_scf.add_argument("--timings", help="Optional timings.json (copies audio and builds captions.html)")
    p_scf.add_argument("--images-dir", help="Optional directory containing scene images")
    p_scf.set_defaults(func=cmd_scaffold_video)

    p_aud = sub.add_parser("audit", help="Audit project for emojis, MP4 streams/loudness and HyperFrames check")
    p_aud.add_argument("--project-dir", required=True, help="HyperFrames project directory")
    p_aud.add_argument("--mp4", help="Optional rendered MP4 path to verify with ffprobe/volumedetect")
    p_aud.add_argument("--strict-hyperframes", action="store_true", help="Run npx hyperframes check --json --strict")
    p_aud.add_argument("--output", required=True, help="Output JSON audit report path")
    p_aud.set_defaults(func=cmd_audit)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
