"""auditor probe: page heights of the other historical goose drafts (tile-cap headroom). scratch, gitignored."""
import asyncio, json, subprocess, time, os, shutil, math, glob
import httpx
import websockets

CHROME = os.path.expanduser("~/Library/Caches/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-mac-arm64/chrome-headless-shell")
PORT = 9468
PROF = "/private/tmp/claude-501/t18-audit-profile2"


async def main():
    drafts = sorted(glob.glob(os.path.expanduser("~/.goose-harness/runs/*/draft/report.html")))
    print("drafts", len(drafts))
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
            await call("Network.setBlockedURLs", {"urls": ["*"]})
            await call("Emulation.setScriptExecutionDisabled", {"value": True})
            for d in drafts:
                for name, w, mobile in (("desktop", 1280, False), ("mobile", 390, True)):
                    await call("Emulation.setDeviceMetricsOverride", {"width": w, "height": 800, "deviceScaleFactor": 1, "mobile": mobile})
                    await call("Page.navigate", {"url": "file://" + d})
                    await asyncio.sleep(2)
                    m = await call("Runtime.evaluate", {"expression": "JSON.stringify({sw:document.documentElement.scrollWidth,cw:document.documentElement.clientWidth,sh:document.documentElement.scrollHeight})", "returnByValue": True})
                    v = json.loads(m["result"]["result"]["value"])
                    print(d.split("/runs/")[1][:8], os.path.getsize(d), name, v, "tiles", math.ceil(v["sh"] / 1568))
    finally:
        try:
            os.killpg(proc.pid, 15)
        except Exception:
            pass
        proc.wait(10)
        shutil.rmtree(PROF, ignore_errors=True)


asyncio.run(main())
