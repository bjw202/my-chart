"""M1 관측 1: 브라우저 선택(G2), 기존 초안 4개 높이·타일 분포(P26), 본문 글자 크기, y>0 clip(G3),
스크립트 비활성·네트워크 차단 효과(G3), --no-sandbox 불필요(G9), 차단/비차단 비교(G8). 읽기 전용."""
import asyncio
import glob
import http.server
import json
import math
import os
import subprocess
import sys
import threading

sys.path.insert(0, os.path.dirname(__file__))
from cdp import Session, TILE_H, VIEWPORTS, find_browser, png_wh, sha, tile_ranges  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.expanduser("~/.goose-harness/runs")
LIVE = "a5becbb9b1a14483a1055c118d1b0be8"


def out(*a):
    print(*a, flush=True)


async def measure_drafts():
    out("== P26 재측정: 네트워크 전면 차단 + 스크립트 비활성, 기존 초안 4개 ==")
    drafts = sorted(glob.glob(os.path.join(RUNS, "*", "draft", "report.html")))
    out("drafts", len(drafts))
    async with Session() as s:
        out("browser build", s.build, "argv", [a if not a.startswith("--user-data-dir") else "--user-data-dir=<tmp>" for a in s.argv])
        out("ws_found_after_s", s.ws_found_after, "blockedURLs", s.block_result, "scriptDisabled", s.script_result,
            "no --no-sandbox in argv:", "--no-sandbox" not in s.argv)
        mx = {"desktop": 0, "mobile": 0}
        for d in drafts:
            jid = d.split("/runs/")[1][:8]
            for name, w, h, mob in VIEWPORTS:
                v = await s.open("file://" + d, w, h, mob, settle=2.0)
                tiles = len(tile_ranges(v["sh"]))
                mx[name] = max(mx[name], tiles)
                out(jid, name, "bytes", os.path.getsize(d), v, "tiles", tiles, "overflow", v["sw"] > v["cw"])
        out("max tiles per viewport", mx, "1.5x ->", {k: math.ceil(1.5 * v) for k, v in mx.items()},
            "sum max(live)", )
    return mx


async def clip_and_g8():
    d = os.path.join(RUNS, LIVE, "draft", "report.html")
    url = "file://" + d
    res = {}
    out("== G3: y>0 clip (차단+스크립트 비활성), 라이브 초안 ==")
    async with Session() as s:
        for name, w, h, mob in VIEWPORTS:
            v = await s.open(url, w, h, mob, settle=2.0)
            rows = []
            for i, (y, th) in enumerate(tile_ranges(v["sh"])[:3] + tile_ranges(v["sh"])[-1:]):
                b = await s.tile(w, y, th)
                pw, ph = png_wh(b)
                rows.append((y, th, pw, ph, sha(b)))
                if i < 3:
                    open(os.path.join(HERE, f"live-{name}-blocked-y{y}.png"), "wb").write(b)
            out(name, v)
            for r in rows:
                out("  clip y=%d h=%d -> png %dx%d sha %s" % r)
            res[name] = {"v": v, "rows": rows}
            out("  y0 != y1568 hash:", rows[0][4] != rows[1][4], "| heights match clip:", all(r[3] == r[1] and r[2] == w for r in rows))
    out("== G8: 차단 vs 비차단(외부 글꼴 로드, 스크립트는 계속 비활성), 라이브 초안 ==")
    async with Session(block=False) as s:
        for name, w, h, mob in VIEWPORTS:
            v = await s.open(url, w, h, mob, settle=4.0)
            b = await s.tile(w, 0, TILE_H)
            b2 = await s.tile(w, TILE_H, TILE_H)
            open(os.path.join(HERE, f"live-{name}-unblocked-y0.png"), "wb").write(b)
            open(os.path.join(HERE, f"live-{name}-unblocked-y1568.png"), "wb").write(b2)
            out("unblocked", name, v, "y0 sha", sha(b)[:16], "blocked y0 sha", res[name]["rows"][0][4][:16],
                "same:", sha(b) == res[name]["rows"][0][4], "height delta", v["sh"] - res[name]["v"]["sh"])
    return res


class _Counter(http.server.BaseHTTPRequestHandler):
    hits = []

    def do_GET(self):
        _Counter.hits.append(self.path)
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"x")

    def log_message(self, *a):
        pass


async def isolation():
    out("== 격리 관측: 로컬 수신 소켓 요청 수 + 스크립트 비활성 효과 ==")
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Counter)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    html = (f"<html><head><link rel=stylesheet href='http://127.0.0.1:{port}/a.css'></head><body>"
            f"<img src='http://127.0.0.1:{port}/b.png'><div id=a>static</div>"
            f"<script>document.getElementById('a').textContent='SCRIPT-RAN';fetch('http://127.0.0.1:{port}/c')</script>"
            f"<script src='http://127.0.0.1:{port}/d.js'></script></body></html>")
    p = os.path.join(HERE, "isolation_fixture.html")
    open(p, "w").write(html)
    for label, kw in (("CONTROL(차단 없음, 스크립트 허용)", dict(block=False, script_off=False)),
                      ("SPEC(차단 + 스크립트 비활성)", dict(block=True, script_off=True))):
        _Counter.hits.clear()
        async with Session(**kw) as s:
            await s.open("file://" + p, 1280, 800, False, settle=2.0)
            m = await s.call("Runtime.evaluate", {"expression": "document.getElementById('a').textContent", "returnByValue": True})
            out(label, "div text =", m["result"]["result"]["value"], "| 로컬 소켓 수신 요청:", sorted(_Counter.hits))
    srv.shutdown()


async def main():
    out("python", sys.version.split()[0])
    b = find_browser()
    out("find_browser (Playwright cache, 최고 빌드 숫자 비교, AI_REPORT_GOOSE_BROWSER 없음):", b)
    out("browser --version:", subprocess.run([b[1], "--version"], capture_output=True, text=True).stdout.strip())
    await measure_drafts()
    await clip_and_g8()
    await isolation()


asyncio.run(main())
