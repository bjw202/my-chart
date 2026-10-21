"""auditor probe: G3 (y>0 tile clip, script-disable, network block) -- scratch only, gitignored."""
import asyncio, base64, json, subprocess, time, struct, os, shutil
import httpx
import websockets

CHROME = os.path.expanduser("~/Library/Caches/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-mac-arm64/chrome-headless-shell")
URL = "file://" + os.path.expanduser("~/.goose-harness/runs/a5becbb9b1a14483a1055c118d1b0be8/draft/report.html")
PORT = 9467
PROF = "/private/tmp/claude-501/t18-audit-profile"


def png_wh(b):
    return struct.unpack(">II", b[16:24])


async def main():
    proc = subprocess.Popen([CHROME, "--disable-gpu", "--hide-scrollbars", f"--remote-debugging-port={PORT}",
                             f"--user-data-dir={PROF}", "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    try:
        ws_url = None
        for _ in range(80):
            try:
                r = httpx.get(f"http://127.0.0.1:{PORT}/json/list", timeout=1)
                pages = [p for p in r.json() if p.get("type") == "page"]
                if pages:
                    ws_url = pages[0]["webSocketDebuggerUrl"]; break
            except Exception:
                pass
            time.sleep(0.1)
        print("ws_found", bool(ws_url), "(no --no-sandbox used)")
        async with websockets.connect(ws_url, max_size=128 * 1024 * 1024) as ws:
            n = 0
            async def call(method, params=None):
                nonlocal n
                n += 1
                await ws.send(json.dumps({"id": n, "method": method, "params": params or {}}))
                while True:
                    msg = json.loads(await ws.recv())
                    if msg.get("id") == n:
                        return msg
            await call("Page.enable"); await call("Network.enable")
            r = await call("Network.setBlockedURLs", {"urls": ["*"]}); print("blockedURLs", r.get("error") or "ok")
            r = await call("Emulation.setScriptExecutionDisabled", {"value": True}); print("scriptDisabled", r.get("error") or "ok")
            await call("Emulation.setDeviceMetricsOverride", {"width": 390, "height": 844, "deviceScaleFactor": 1, "mobile": True})
            await call("Page.navigate", {"url": URL})
            await asyncio.sleep(3)
            m = await call("Runtime.evaluate", {"expression": "JSON.stringify({sw:document.documentElement.scrollWidth,cw:document.documentElement.clientWidth,sh:document.documentElement.scrollHeight})", "returnByValue": True})
            val = m.get("result", {}).get("result", {}).get("value")
            print("metrics_under_script_disabled", val or m)
            sh = json.loads(val)["sh"]
            for y, h in ((0, 1568), (1568, 1568), (sh - 100, 100)):
                s = await call("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": True,
                                                          "clip": {"x": 0, "y": y, "width": 390, "height": h, "scale": 1}})
                if "error" in s:
                    print("tile", y, h, "ERROR", s["error"]); continue
                d = base64.b64decode(s["result"]["data"])
                print("tile y=%d h=%d -> png %s bytes=%d" % (y, h, png_wh(d), len(d)))
                if y == 1568:
                    open("/Users/byunjungwon/Dev/my-project-01/my_chart/.claude/worktrees/t18/.moai/state/verify/t18-audit/tile2.png", "wb").write(d)
    finally:
        try:
            os.killpg(proc.pid, 15)
        except Exception:
            pass
        proc.wait(10)
        shutil.rmtree(PROF, ignore_errors=True)


asyncio.run(main())
