"""Unit and integration tests for narrated_video_cli."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts import narrated_video_cli as cli

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_DIR = REPO_ROOT / "examples" / "ciclo-da-banana-60s"


class NarratedVideoCliTests(unittest.TestCase):
    def test_safe_identifier_and_path_traversal(self) -> None:
        self.assertEqual(cli.safe_identifier("scene-01_rizoma"), "scene-01_rizoma")
        with self.assertRaises(ValueError):
            cli.safe_identifier("../escape")
        with self.assertRaises(ValueError):
            cli.safe_identifier("scene with space")

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            resolved = cli.safe_resolve(base, "compositions/scene-01.html")
            self.assertTrue(str(resolved).startswith(str(base.resolve())))
            with self.assertRaises(ValueError):
                cli.safe_resolve(base, "../../outside.html")

    def test_fmt_srt_ts(self) -> None:
        self.assertEqual(cli.fmt_srt_ts(0.0), "00:00:00,000")
        self.assertEqual(cli.fmt_srt_ts(12.345), "00:00:12,345")
        self.assertEqual(cli.fmt_srt_ts(3661.08), "01:01:01,080")

    def test_build_caption_groups_balanced(self) -> None:
        words = [
            {"id": f"w{i}", "text": f"palavra{i}", "start": i * 0.4, "end": i * 0.4 + 0.35}
            for i in range(6)
        ]
        groups = cli.build_caption_groups(words, max_words=5)
        self.assertEqual([len(g) for g in groups], [3, 3])

    def test_align_word_boundaries_strict_and_fallback(self) -> None:
        tokens = ["a", "banana", "amadurece"]
        wb = [
            {"wb_text": "a", "local_start": 0.1, "local_end": 0.2},
            {"wb_text": "banana", "local_start": 0.25, "local_end": 0.6},
            {"wb_text": "amadurece", "local_start": 0.65, "local_end": 1.2},
        ]
        exact = cli.align_word_boundaries(tokens, wb, strict=True)
        self.assertEqual([x["display_text"] for x in exact], tokens)

        with self.assertRaises(RuntimeError):
            cli.align_word_boundaries(["a", "b"], wb, strict=True)

        approx = cli.align_word_boundaries(["a", "b"], wb, strict=False)
        self.assertEqual(len(approx), 2)
        self.assertEqual(approx[0]["local_start"], 0.1)
        self.assertAlmostEqual(approx[-1]["local_end"], 1.2, places=3)

    def test_load_example_script_spec_and_reject_emoji(self) -> None:
        spec = cli.load_script_spec(EXAMPLE_DIR / "script.json")
        self.assertEqual(spec["total_duration_sec"], 60.0)
        self.assertEqual(len(spec["scenes"]), 5)

        with tempfile.TemporaryDirectory() as tmp:
            bom_path = Path(tmp) / "bom_script.json"
            bom_path.write_bytes(b"\xef\xbb\xbf" + (EXAMPLE_DIR / "script.json").read_bytes())
            bom_spec = cli.load_script_spec(bom_path)
            self.assertEqual(bom_spec["total_duration_sec"], 60.0)

            bad = json.loads((EXAMPLE_DIR / "script.json").read_text(encoding="utf-8"))
            bad["scenes"][0]["text"] = "Texto com emoji \U0001f34c"
            bad_path = Path(tmp) / "bad.json"
            bad_path.write_text(json.dumps(bad), encoding="utf-8")
            with self.assertRaises(ValueError):
                cli.load_script_spec(bad_path)

    def test_build_captions_html_from_example_timings(self) -> None:
        timings = json.loads((EXAMPLE_DIR / "assets" / "ap01_timings.json").read_text(encoding="utf-8"))
        html_out = cli.build_captions_html(timings, accent_color="#E2B43B")
        self.assertIn('window.__timelines["captions"] = tl;', html_out)
        self.assertIn('data-layout-allow-caption-zone', html_out)
        self.assertIsNone(cli.EMOJI_RE.search(html_out))
        self.assertIn("cap-c0-w0", html_out)

    def test_scaffold_video_creates_valid_hyperframes_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "meu-video-teste"
            rc = cli.main(
                [
                    "scaffold-video",
                    "--spec",
                    str(EXAMPLE_DIR / "script.json"),
                    "--timings",
                    str(EXAMPLE_DIR / "assets" / "ap01_timings.json"),
                    "--images-dir",
                    str(EXAMPLE_DIR / "assets"),
                    "--output-dir",
                    str(out_dir),
                ]
            )
            self.assertEqual(rc, 0)
            self.assertTrue((out_dir / "index.html").exists())
            self.assertTrue((out_dir / "SPEC.md").exists())
            self.assertTrue((out_dir / "hyperframes.json").exists())
            self.assertTrue((out_dir / "compositions" / "captions.html").exists())
            self.assertTrue((out_dir / "compositions" / "scene-01-rizoma.html").exists())
            self.assertTrue((out_dir / "assets" / "01_rizoma_broto.png").exists())
            self.assertTrue((out_dir / "assets" / "timings.json").exists())

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg/ffprobe required")
    def test_synth_ambient_and_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            amb_mp3 = tmp_path / "ambient_test.mp3"
            report_json = tmp_path / "ambient_report.json"
            rc = cli.main(
                [
                    "synth-ambient",
                    "--duration",
                    "3.0",
                    "--lufs",
                    "-24.0",
                    "--output",
                    str(amb_mp3),
                    "--report",
                    str(report_json),
                ]
            )
            self.assertEqual(rc, 0)
            self.assertTrue(amb_mp3.exists())
            rep = json.loads(report_json.read_text(encoding="utf-8"))
            self.assertAlmostEqual(rep["probe"]["duration_sec"], 3.0, delta=0.15)
            self.assertIsNotNone(rep["volumedetect"]["mean_volume_db"])
            self.assertGreater(rep["volumedetect"]["mean_volume_db"], -35.0)

            # Audit clean example directory (without mp4 render)
            audit_json = tmp_path / "audit_clean.json"
            rc_audit = cli.main(
                [
                    "audit",
                    "--project-dir",
                    str(EXAMPLE_DIR),
                    "--output",
                    str(audit_json),
                ]
            )
            self.assertEqual(rc_audit, 0)
            audit_data = json.loads(audit_json.read_text(encoding="utf-8"))
            self.assertTrue(audit_data["passed"])
            self.assertEqual(audit_data["emoji_hits"], [])

            # Audit must fail if an emoji sneaks into any text file
            dirty_dir = tmp_path / "dirty_proj"
            dirty_dir.mkdir()
            (dirty_dir / "bad.html").write_text("<p>Oi \U0001f680</p>", encoding="utf-8")
            dirty_audit = tmp_path / "audit_dirty.json"
            rc_dirty = cli.main(
                [
                    "audit",
                    "--project-dir",
                    str(dirty_dir),
                    "--output",
                    str(dirty_audit),
                ]
            )
            self.assertEqual(rc_dirty, 1)
            dirty_data = json.loads(dirty_audit.read_text(encoding="utf-8"))
            self.assertFalse(dirty_data["passed"])
            self.assertEqual(len(dirty_data["emoji_hits"]), 1)


if __name__ == "__main__":
    unittest.main()
