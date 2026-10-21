"""SPEC-AI-REPORT-006 M1 전용 스파이크 라이브러리 (병합하지 않음, M2 모듈과 무관).

REQ-AIR6-006·009가 정한 것과 같은 DevTools 호출만 쓴다: 뷰포트 1280/390(모바일 에뮬레이션),
스크립트 비활성, 외부 네트워크 전면 차단(Network.setBlockedURLs ["*"]), file:// 로드, clip 타일.
"""
import asyncio
import base64
import glob
import hashlib
import json
import os
import re
import shutil
import socket
import struct
import subprocess
import tempfile
import time

import httpx
import websockets

TILE_H = 1568
VIEWPORTS = (("desktop", 1280, 800, False), ("mobile", 390, 844, True))
SCRATCH = "/private/tmp/claude-501/-Users-byunjungwon-Dev-my-project-01-my-chart/20ab84e9-52e3-48ae-8796-e9f9910c8ed3/scratchpad"


def find_browser():
    """Playwright 캐시의 chrome-headless-shell 중 빌드 번호(숫자)가 가장 큰 것 (T9)."""
    best = None
    for root in (os.path.expanduser("~/Library/Caches/ms-playwright"),):
        for d in glob.glob(os.path.join(root, "chromium_headless_shell-*")):
            m = re.search(r"chromium_headless_shell-(\d+)$", d)
            exe = glob.glob(os.path.join(d, "*", "chrome-headless-shell"))
            if m and exe and os.access(exe[0], os.X_OK):
                if best is None or int(m.group(1)) > best[0]:
                    best = (int(m.group(1)), exe[0])
    return best


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def png_wh(b):
    return struct.unpack(">II", b[16:24])


def sha(b):
    return hashlib.sha256(b).hexdigest()


class Session:
    def __init__(self, no_sandbox=False, block=True, script_off=True):
        self.no_sandbox = no_sandbox
        self.block = block
        self.script_off = script_off
        self.n = 0

    async def __aenter__(self):
        os.makedirs(SCRATCH, exist_ok=True)
        self.prof = tempfile.mkdtemp(prefix="t18m1-prof-", dir=SCRATCH)
        self.port = free_port()
        build, exe = find_browser()
        self.build, self.exe = build, exe
        argv = [exe, "--headless", "--disable-gpu", "--hide-scrollbars",
                f"--remote-debugging-port={self.port}", f"--user-data-dir={self.prof}"]
        if self.no_sandbox:
            argv.append("--no-sandbox")
        argv.append("about:blank")
        self.argv = argv
        self.proc = subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                     start_new_session=True)
        ws_url = None
        t0 = time.time()
        for _ in range(100):
            try:
                r = httpx.get(f"http://127.0.0.1:{self.port}/json/list", timeout=1)
                pages = [p for p in r.json() if p.get("type") == "page"]
                if pages:
                    ws_url = pages[0]["webSocketDebuggerUrl"]
                    break
            except Exception:
                pass
            time.sleep(0.1)
        self.ws_found_after = round(time.time() - t0, 2)
        if not ws_url:
            raise RuntimeError("devtools endpoint not found")
        self.ws = await websockets.connect(ws_url, max_size=256 * 1024 * 1024)
        await self.call("Page.enable")
        await self.call("Network.enable")
        if self.block:
            r = await self.call("Network.setBlockedURLs", {"urls": ["*"]})
            self.block_result = r.get("error") or "ok"
        if self.script_off:
            r = await self.call("Emulation.setScriptExecutionDisabled", {"value": True})
            self.script_result = r.get("error") or "ok"
        return self

    async def __aexit__(self, *a):
        try:
            await self.ws.close()
        except Exception:
            pass
        try:
            os.killpg(self.proc.pid, 15)
        except Exception:
            pass
        try:
            self.proc.wait(10)
        except Exception:
            os.killpg(self.proc.pid, 9)
        shutil.rmtree(self.prof, ignore_errors=True)

    async def call(self, method, params=None):
        self.n += 1
        await self.ws.send(json.dumps({"id": self.n, "method": method, "params": params or {}}))
        while True:
            msg = json.loads(await self.ws.recv())
            if msg.get("id") == self.n:
                return msg

    async def open(self, url, w, h, mobile, settle=2.0):
        await self.call("Emulation.setDeviceMetricsOverride",
                        {"width": w, "height": h, "deviceScaleFactor": 1, "mobile": mobile})
        await self.call("Page.navigate", {"url": url})
        await asyncio.sleep(settle)
        m = await self.call("Runtime.evaluate", {
            "expression": "JSON.stringify({sw:document.documentElement.scrollWidth,cw:document.documentElement.clientWidth,"
                          "sh:document.documentElement.scrollHeight,"
                          "fs:getComputedStyle(document.body).fontSize,ff:getComputedStyle(document.body).fontFamily})",
            "returnByValue": True})
        return json.loads(m["result"]["result"]["value"])

    async def tile(self, w, y, h):
        s = await self.call("Page.captureScreenshot", {
            "format": "png", "captureBeyondViewport": True,
            "clip": {"x": 0, "y": y, "width": w, "height": h, "scale": 1}})
        if "error" in s:
            raise RuntimeError(str(s["error"]))
        return base64.b64decode(s["result"]["data"])


def tile_ranges(sh):
    out, y = [], 0
    while y < sh:
        out.append((y, min(TILE_H, sh - y)))
        y += TILE_H
    return out
