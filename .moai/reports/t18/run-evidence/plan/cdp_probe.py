"""plan-phase 프로브(SPEC-AI-REPORT-006 research §P): 헤드리스 Chrome을 DevTools 프로토콜로 구동해
전체 높이 스크린샷과 가로 넘침 수치를 얻을 수 있는지 관측한다. 운영 코드가 아니다."""
import asyncio, base64, json, subprocess, time
import httpx
import websockets

CHROME = "/Users/byunjungwon/Library/Caches/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-mac-arm64/chrome-headless-shell"
URL = "file:///Users/byunjungwon/.goose-harness/runs/a5becbb9b1a14483a1055c118d1b0be8/draft/report.html"
OUT = "/Users/byunjungwon/Dev/my-project-01/my_chart/.claude/worktrees/t18/.moai/state/verify/t18-plan/"
PORT = 9333


async def main():
    t0 = time.time()
    proc = subprocess.Popen([CHROME, "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                             f"--remote-debugging-port={PORT}", "--user-data-dir=/private/tmp/claude-501/t18-cdp-profile",
                             "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        ws_url = None
        for _ in range(60):
            try:
                r = httpx.get(f"http://127.0.0.1:{PORT}/json/list", timeout=1)
                pages = [p for p in r.json() if p.get("type") == "page"]
                if pages:
                    ws_url = pages[0]["webSocketDebuggerUrl"]
                    break
            except Exception:
                pass
            time.sleep(0.1)
        print("ws_found", bool(ws_url), "t=", round(time.time() - t0, 2))
        async with websockets.connect(ws_url, max_size=64 * 1024 * 1024) as ws:
            n = 0

            async def call(method, params=None):
                nonlocal n
                n += 1
                await ws.send(json.dumps({"id": n, "method": method, "params": params or {}}))
                while True:
                    msg = json.loads(await ws.recv())
                    if msg.get("id") == n:
                        return msg

            await call("Page.enable")
            for name, w, mobile in (("desktop", 1280, False), ("mobile", 390, True)):
                await call("Emulation.setDeviceMetricsOverride",
                           {"width": w, "height": 800, "deviceScaleFactor": 1, "mobile": mobile})
                await call("Page.navigate", {"url": URL})
                await asyncio.sleep(3)
                m = await call("Runtime.evaluate", {"expression": "JSON.stringify({sw:document.documentElement.scrollWidth,cw:document.documentElement.clientWidth,sh:document.documentElement.scrollHeight})", "returnByValue": True})
                dims = json.loads(m["result"]["result"]["value"])
                print(name, dims)
                shot = await call("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": True,
                                  "clip": {"x": 0, "y": 0, "width": w, "height": dims["sh"], "scale": 1}})
                data = base64.b64decode(shot["result"]["data"])
                open(OUT + f"cdp_{name}.png", "wb").write(data)
                print(name, "png_bytes", len(data))
        print("done t=", round(time.time() - t0, 2))
    finally:
        proc.terminate()
        proc.wait(5)


asyncio.run(main())
