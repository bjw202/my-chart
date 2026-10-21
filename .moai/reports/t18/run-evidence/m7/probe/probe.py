"""G20 observation probe (not shipped): flags + Fetch + fulfillRequest on file:// main doc + CSP.

usage: probe.py <draft.html> [--no-csp] [--no-flags]
"""
import asyncio
import base64
import json
import os
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

import httpx
import websockets

EXE = sorted(Path.home().glob("Library/Caches/ms-playwright/chromium_headless_shell-*/*/chrome-headless-shell"))[-1]
draft = Path(sys.argv[1]).resolve()
USE_CSP = "--no-csp" not in sys.argv
USE_FLAGS = "--no-flags" not in sys.argv
FLAGS = ["--proxy-server=127.0.0.1:1", "--proxy-bypass-list=<-loopback>", "--host-resolver-rules=MAP * ~NOTFOUND"]
CSP = (
    "default-src 'none'; style-src 'unsafe-inline'; img-src data:; font-src data:; "
    "frame-src 'none'; object-src 'none'; form-action 'none'; base-uri 'none'"
)
s = socket.socket()
s.bind(("127.0.0.1", 0))
port = s.getsockname()[1]
s.close()
prof = tempfile.mkdtemp()
env = {k: os.environ[k] for k in ("PATH", "HOME", "USER", "LANG", "LC_ALL", "TZ", "TMPDIR", "SHELL") if k in os.environ}
argv = [str(EXE), "--headless", "--disable-gpu", "--hide-scrollbars", f"--remote-debugging-port={port}",
        f"--user-data-dir={prof}", *(FLAGS if USE_FLAGS else []), "about:blank"]
p = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True, env=env)


async def main():
    pages = []
    async with httpx.AsyncClient(timeout=1) as c:
        for _ in range(100):
            try:
                pages = [x for x in (await c.get(f"http://127.0.0.1:{port}/json/list")).json() if x["type"] == "page"]
                if pages:
                    break
            except Exception:
                pass
            await asyncio.sleep(0.1)
    ws = await websockets.connect(pages[0]["webSocketDebuggerUrl"], max_size=1 << 26)
    state = {"seq": 0, "loaded": False}
    res = {}
    log = []
    url = draft.as_uri()
    body = draft.read_bytes()

    async def call(method, params=None, sid=None):
        state["seq"] += 1
        i = state["seq"]
        m = {"id": i, "method": method, "params": params or {}}
        if sid:
            m["sessionId"] = sid
        await ws.send(json.dumps(m))
        while i not in res:
            await pump()
        r = res.pop(i)
        if "error" in r:
            log.append(("ERR", method, r["error"]))
        return r.get("result", {})

    async def pump():
        m = json.loads(await ws.recv())
        if "id" in m:
            res[m["id"]] = m
            return
        meth = m.get("method")
        sid = m.get("sessionId")
        pr = m.get("params", {})
        if meth == "Page.loadEventFired" and not sid:
            state["loaded"] = True
        elif meth == "Target.attachedToTarget":
            ns = pr["sessionId"]
            log.append(("attach", pr["targetInfo"]["type"], pr["targetInfo"]["url"][:60], pr["waitingForDebugger"]))
            await call("Fetch.enable", {"patterns": [{"urlPattern": "*"}]}, ns)
            await call("Target.setAutoAttach", {"autoAttach": True, "waitForDebuggerOnStart": True, "flatten": True}, ns)
            await call("Runtime.runIfWaitingForDebugger", {}, ns)
        elif meth == "Fetch.requestPaused":
            u = pr["request"]["url"]
            rid = pr["requestId"]
            if u == url:
                log.append(("paused-draft", pr.get("resourceType")))
                headers = [{"name": "Content-Type", "value": "text/html"}]
                if USE_CSP:
                    headers.append({"name": "Content-Security-Policy", "value": CSP})
                await call("Fetch.fulfillRequest", {"requestId": rid, "responseCode": 200, "responseHeaders": headers,
                                                     "body": base64.b64encode(body).decode()}, sid)
            elif u.startswith("data:"):
                log.append(("paused-data", u[:30]))
                await call("Fetch.continueRequest", {"requestId": rid}, sid)
            else:
                log.append(("paused-fail", u[:70], pr.get("resourceType")))
                await call("Fetch.failRequest", {"requestId": rid, "errorReason": "BlockedByClient"}, sid)

    await call("Page.enable")
    await call("Network.enable")
    await call("Network.setBlockedURLs", {"urls": ["*"]})
    await call("Emulation.setScriptExecutionDisabled", {"value": True})
    await call("Target.setAutoAttach", {"autoAttach": True, "waitForDebuggerOnStart": True, "flatten": True})
    await call("Fetch.enable", {"patterns": [{"urlPattern": "*"}]})
    await call("Emulation.setDeviceMetricsOverride", {"width": 1280, "height": 800, "deviceScaleFactor": 1, "mobile": False})
    nav = await call("Page.navigate", {"url": url})
    log.append(("nav", nav))

    async def wait_load():
        while not state["loaded"]:
            await pump()

    try:
        await asyncio.wait_for(wait_load(), 20)
    except asyncio.TimeoutError:
        log.append(("LOAD TIMEOUT",))
    ev = await call("Runtime.evaluate", {
        "expression": "JSON.stringify([document.documentElement.scrollWidth, document.documentElement.scrollHeight,"
                      " document.characterSet, document.contentType])", "returnByValue": True})
    print("metrics", ev.get("result", {}).get("value"))
    for entry in log:
        print(entry)
    await ws.close()


try:
    asyncio.run(main())
finally:
    import signal
    try:
        os.killpg(p.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    p.wait()
