import functools
import http.server
import json
import re
import socketserver
import threading
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(r"C:\Users\52319400\APRESENTACOES_BANANA")
AP02_DIR = BASE_DIR / "APRESENTACAO_02_DECK_EDITORIAL_HTML"
ROTEIRO_DIR = BASE_DIR / "ROTEIRO_E_AUDIO"
OUT_DIR = BASE_DIR / "AUDITORIA"
SHOT_DIR = OUT_DIR / "ap02_screenshots"
SHOT_DIR.mkdir(parents=True, exist_ok=True)

EMOJI_RE = re.compile(
    r"[\U00010000-\U0010ffff]|[\u2600-\u27BF]|[\u2300-\u23FF]|[\u2B50-\u2B55]|[\uD83C-\uDBFF\uDC00-\uDFFF]"
)


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


def start_http_server(directory: Path):
    handler = functools.partial(QuietHandler, directory=str(directory))
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, port


def static_text_scan():
    files_to_scan = [
        AP02_DIR / "index.html",
        AP02_DIR / "assets" / "ap02.srt",
        AP02_DIR / "assets" / "ap02_timings.json",
        ROTEIRO_DIR / "ROTEIROS.md",
        ROTEIRO_DIR / "ap02.srt",
        ROTEIRO_DIR / "ap02_timings.json",
    ]
    results = {}
    for fp in files_to_scan:
        if not fp.exists():
            results[str(fp)] = {"exists": False}
            continue
        content = fp.read_text(encoding="utf-8", errors="ignore")
        emojis = EMOJI_RE.findall(content)
        rounded_full = re.findall(r"rounded-full", content, re.IGNORECASE)
        pill_radius = re.findall(r"border-radius\s*:\s*(?:999\d*px|50%)", content, re.IGNORECASE)
        results[str(fp)] = {
            "exists": True,
            "bytes": fp.stat().st_size,
            "emojis_count": len(emojis),
            "rounded_full_count": len(rounded_full),
            "pill_radius_matches": pill_radius,
        }
    return results


def run_playwright_audit():
    httpd, port = start_http_server(AP02_DIR)
    url = f"http://127.0.0.1:{port}/index.html"
    report = {"url": url, "desktop": {}, "mobile": {}}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            # 1. Desktop 1440x900
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()
            console_errors = []
            page_errors = []
            failed_requests = []
            bad_responses = []

            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
            page.on("pageerror", lambda err: page_errors.append(str(err)))
            page.on("requestfailed", lambda req: failed_requests.append({"url": req.url, "failure": req.failure}))
            page.on("response", lambda res: bad_responses.append({"url": res.url, "status": res.status}) if res.status >= 400 else None)

            page.goto(url, wait_until="networkidle")
            page.evaluate("() => document.fonts.ready")
            page.wait_for_function("() => { const a = document.getElementById('narration-audio'); return a && a.readyState >= 1 && a.duration > 0; }", timeout=10000)
            page.wait_for_timeout(500)

            base_metrics = page.evaluate("""() => {
                const audio = document.getElementById('narration-audio');
                const imgs = Array.from(document.querySelectorAll('img')).map(img => ({
                    src: img.getAttribute('src'),
                    complete: img.complete,
                    naturalWidth: img.naturalWidth,
                    naturalHeight: img.naturalHeight
                }));
                const h1Style = getComputedStyle(document.querySelector('.brand-title'));
                const headlineStyle = getComputedStyle(document.querySelector('.scene-headline'));
                const bodyStyle = getComputedStyle(document.body);
                return {
                    audio: audio ? {
                        src: audio.currentSrc || audio.src,
                        readyState: audio.readyState,
                        duration: audio.duration,
                        error: audio.error ? audio.error.message : null
                    } : null,
                    images: imgs,
                    fonts: {
                        bodyFamily: bodyStyle.fontFamily,
                        headlineFamily: headlineStyle.fontFamily,
                        brandFamily: h1Style.fontFamily,
                        bgColor: bodyStyle.backgroundColor,
                        color: bodyStyle.color
                    },
                    geometry: {
                        innerWidth: window.innerWidth,
                        innerHeight: window.innerHeight,
                        scrollWidth: document.documentElement.scrollWidth,
                        clientWidth: document.documentElement.clientWidth,
                        scrollHeight: document.documentElement.scrollHeight,
                        clientHeight: document.documentElement.clientHeight
                    }
                };
            }""")

            # Test Play button
            page.click("#btn-play")
            page.wait_for_timeout(1400)
            play_state = page.evaluate("""() => {
                const audio = document.getElementById('narration-audio');
                return {
                    btnText: document.getElementById('btn-play-label').textContent,
                    pressed: document.getElementById('btn-play').getAttribute('aria-pressed'),
                    timeCurrent: document.getElementById('time-current').textContent,
                    audioPaused: audio ? audio.paused : null,
                    audioCurrentTime: audio ? audio.currentTime : null,
                    currentWords: document.querySelectorAll('.caption-word.is-current').length,
                    spokenWords: document.querySelectorAll('.caption-word.is-spoken').length,
                    captionText: document.getElementById('caption-text').textContent
                };
            }""")
            page.screenshot(path=str(SHOT_DIR / "desktop_play_cena1.png"), full_page=False)

            # Pause and inspect all 5 scenes
            page.click("#btn-play")
            page.wait_for_timeout(200)

            scene_checks = []
            for idx in range(5):
                page.click(f'[data-scene-jump="{idx}"]')
                page.wait_for_timeout(750)
                info = page.evaluate("""(idx) => {
                    const dock = document.querySelector('.player-dock').getBoundingClientRect();
                    const main = document.querySelector('.stage-shell').getBoundingClientRect();
                    const activePlate = document.querySelector('.plate-slide.is-active img');
                    const activeSvg = document.querySelector('.bio-svg.is-active');
                    return {
                        idx,
                        tabSelected: document.querySelector(`[data-scene-jump="${idx}"]`).getAttribute('aria-selected'),
                        kicker: document.getElementById('scene-kicker').textContent,
                        headline: document.getElementById('scene-headline').textContent,
                        timeCurrent: document.getElementById('time-current').textContent,
                        dockStatus: document.getElementById('dock-stage-status').textContent,
                        activeImgSrc: activePlate ? activePlate.getAttribute('src') : null,
                        activeSvgVisible: activeSvg ? getComputedStyle(activeSvg).opacity : null,
                        scrollWidth: document.documentElement.scrollWidth,
                        innerWidth: window.innerWidth,
                        scrollHeight: document.documentElement.scrollHeight,
                        innerHeight: window.innerHeight,
                        mainBottom: main.bottom,
                        dockTop: dock.top,
                        dockBottom: dock.bottom
                    };
                }""", idx)
                scene_checks.append(info)
                page.screenshot(path=str(SHOT_DIR / f"desktop_cena_{idx + 1}.png"), full_page=False)

            # Test scrub bar click (~66% -> Scene 4 ~39.6s) and keyboard shortcuts
            scrub_box = page.locator("#scrubber").bounding_box()
            page.mouse.click(scrub_box["x"] + scrub_box["width"] * 0.66, scrub_box["y"] + scrub_box["height"] / 2)
            page.wait_for_timeout(300)
            scrub_state = page.evaluate("""() => ({
                timeCurrent: document.getElementById('time-current').textContent,
                dockStatus: document.getElementById('dock-stage-status').textContent,
                scene4Selected: document.querySelector('[data-scene-jump="3"]').getAttribute('aria-selected')
            })""")

            # Keyboard tests: 1, Space, M, R
            page.keyboard.press("1")
            page.wait_for_timeout(200)
            key1_status = page.evaluate("() => document.getElementById('dock-stage-status').textContent")
            page.keyboard.press("m")
            page.wait_for_timeout(150)
            mute_state = page.evaluate("() => ({ pressed: document.getElementById('btn-mute').getAttribute('aria-pressed'), audioMuted: document.getElementById('narration-audio').muted })")
            page.keyboard.press("m")
            page.keyboard.press("ArrowRight")
            page.wait_for_timeout(200)
            arrow_status = page.evaluate("() => document.getElementById('dock-stage-status').textContent")

            report["desktop"] = {
                "console_errors": console_errors,
                "page_errors": page_errors,
                "failed_requests": failed_requests,
                "bad_responses": bad_responses,
                "base_metrics": base_metrics,
                "play_state": play_state,
                "scene_checks": scene_checks,
                "scrub_state": scrub_state,
                "keyboard_checks": {
                    "key1_status": key1_status,
                    "mute_state": mute_state,
                    "arrow_right_status": arrow_status,
                },
            }
            context.close()

            # 2. Mobile 390x844
            m_context = browser.new_context(viewport={"width": 390, "height": 844})
            m_page = m_context.new_page()
            m_console = []
            m_page_err = []
            m_failed = []
            m_bad = []
            m_page.on("console", lambda msg: m_console.append(msg.text) if msg.type == "error" else None)
            m_page.on("pageerror", lambda err: m_page_err.append(str(err)))
            m_page.on("requestfailed", lambda req: m_failed.append({"url": req.url, "failure": req.failure}))
            m_page.on("response", lambda res: m_bad.append({"url": res.url, "status": res.status}) if res.status >= 400 else None)

            m_page.goto(url, wait_until="networkidle")
            m_page.evaluate("() => document.fonts.ready")
            m_page.wait_for_function("() => { const a = document.getElementById('narration-audio'); return a && a.readyState >= 1 && a.duration > 0; }", timeout=10000)
            m_page.wait_for_timeout(400)

            m_page.click("#btn-play")
            m_page.wait_for_timeout(1100)
            m_metrics = m_page.evaluate("""() => {
                const dock = document.querySelector('.player-dock').getBoundingClientRect();
                const audio = document.getElementById('narration-audio');
                const imgs = Array.from(document.querySelectorAll('img')).map(i => ({src: i.getAttribute('src'), w: i.naturalWidth, h: i.naturalHeight}));
                return {
                    innerWidth: window.innerWidth,
                    scrollWidth: document.documentElement.scrollWidth,
                    clientWidth: document.documentElement.clientWidth,
                    scrollHeight: document.documentElement.scrollHeight,
                    dockHeight: dock.height,
                    dockWidth: dock.width,
                    audioReady: audio ? audio.readyState : null,
                    audioDuration: audio ? audio.duration : null,
                    audioTime: audio ? audio.currentTime : null,
                    imgs
                };
            }""")
            m_page.screenshot(path=str(SHOT_DIR / "mobile_cena1_play.png"), full_page=False)

            m_page.click('[data-scene-jump="3"]')
            m_page.wait_for_timeout(650)
            m_page.screenshot(path=str(SHOT_DIR / "mobile_cena4.png"), full_page=False)

            report["mobile"] = {
                "console_errors": m_console,
                "page_errors": m_page_err,
                "failed_requests": m_failed,
                "bad_responses": m_bad,
                "metrics": m_metrics,
            }
            m_context.close()
            browser.close()
    finally:
        httpd.shutdown()
        httpd.server_close()

    return report


if __name__ == "__main__":
    full_report = {
        "static_scan": static_text_scan(),
        "playwright": run_playwright_audit(),
    }
    report_path = OUT_DIR / "ap02_playwright_report.json"
    report_path.write_text(json.dumps(full_report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(full_report, indent=2, ensure_ascii=False))
