"""M7 evidence runner (not shipped): R1/R2/R3 observations and the layer RED matrix.

usage (cwd = worktree root, PYTHONPATH=.):
  observe.py matrix            # R1 + R2 for each layer combination
  observe.py r3 [draft.html]   # R3 shape comparison (synthetic report, or the given draft copy)
  observe.py r1 | r2           # single scenario with the shipped configuration
"""

import asyncio
import json
import sys
import tempfile
from pathlib import Path

from backend.services import goose_screenshot as gs
from backend.tests import test_goose_screenshot_live as live

# variant -> (A2 flags, A1 request allow-list, B document CSP)
VARIANTS = {
    "none": (False, False, False),
    "A1 only": (False, True, False),
    "A2 only": (True, False, False),
    "B only": (False, False, True),
    "A1+B": (False, True, True),
    "A1+A2": (True, True, False),
    "A2+B": (True, False, True),
    "A1+A2+B": (True, True, True),
}


def apply(flags: bool, a1: bool, b: bool):
    saved = (gs.ISOLATION_FLAGS, gs.CdpDriver.isolate, gs.CdpDriver._answer, gs.CdpDriver._draft_headers)
    if not flags:
        gs.ISOLATION_FLAGS = ()
    if not a1 and not b:
        async def no_isolation(self, url, body):
            return None
        gs.CdpDriver.isolate = no_isolation
    elif b and not a1:
        gs.CdpDriver._answer = lambda self, url: "fulfill" if url == self._draft_url else "continue"
    elif a1 and not b:
        gs.CdpDriver._draft_headers = lambda self: [{"name": "Content-Type", "value": "text/html"}]
    return saved


def restore(saved):
    gs.ISOLATION_FLAGS, gs.CdpDriver.isolate, gs.CdpDriver._answer, gs.CdpDriver._draft_headers = saved


def r1_summary(root: Path) -> dict:
    out = {}
    for label, res in live.scenario_r1(root).items():
        out[label] = {"outcome": res["outcome"], "magenta_total": sum(res["magenta"].values()),
                      "blue_total": sum(res["blue"].values())}
    return out


def main() -> None:
    mode = sys.argv[1]
    root = Path(tempfile.mkdtemp(prefix="m7-observe-"))
    if mode == "matrix":
        for name, (flags, a1, b) in VARIANTS.items():
            saved = apply(flags, a1, b)
            try:
                r1 = r1_summary(root / name.replace(" ", "_").replace("+", "_") / "r1")
                r2 = live.scenario_r2(root / name.replace(" ", "_").replace("+", "_") / "r2")
            finally:
                restore(saved)
            print(json.dumps({"layers_on": name, "R1": r1, "R2": {"outcome": r2["outcome"],
                  "statuses": r2["statuses"], "hits": [h.decode() for h in r2["hits"]]}}, ensure_ascii=False))
    elif mode == "a1child":
        # A1 on the page target only (no Fetch.enable on auto-attached targets), no flags, no CSP: does R2 leak again?
        saved = apply(False, True, False)
        real = gs.CdpDriver._protect_target

        async def resume_only(self, session):
            await self._call("Target.setAutoAttach", gs._AUTO_ATTACH, session)
            await self._call("Runtime.runIfWaitingForDebugger", None, session)

        gs.CdpDriver._protect_target = resume_only
        try:
            r2 = live.scenario_r2(root / "r2")
            r1 = r1_summary(root / "r1")
        finally:
            gs.CdpDriver._protect_target = real
            restore(saved)
        print(json.dumps({"layers_on": "A1 page-target only", "R1": r1, "R2": {"outcome": r2["outcome"],
              "hits": [h.decode() for h in r2["hits"]]}}))
    elif mode == "attachcount":
        # How often does a real browser actually attach a child target during R1/R2/live-draft? (G20 observation)
        real = gs.CdpDriver._protect_target
        seen: list[str] = []

        async def counting(self, session):
            seen.append(session)
            await real(self, session)

        gs.CdpDriver._protect_target = counting
        try:
            live.scenario_r1(root / "r1")
            n1 = len(seen)
            live.scenario_r2(root / "r2")
            n2 = len(seen) - n1
            # same-process data: iframe plus a cross-site http iframe whose request is answered by A1
            print(json.dumps({"attached_targets": {"R1": n1, "R2": n2}}))
        finally:
            gs.CdpDriver._protect_target = real
    elif mode == "attachprobe":
        # Force a real cross-site child target: A2/CSP off and A1 answering "continue" for everything, with a loopback
        # server whose iframe document pulls a sub-resource. Shows whether the auto-attach protocol sequence is accepted
        # by the real browser and whether requests from the child session reach the handler.
        import socket
        import threading

        hits: list[str] = []
        server = socket.socket()
        server.bind(("127.0.0.1", 0))
        server.listen(50)
        base = f"http://127.0.0.1:{server.getsockname()[1]}"
        page = b"<html><body><img src='%s/childimg'></body></html>" % base.encode()

        def serve() -> None:
            while True:
                try:
                    conn, _ = server.accept()
                except OSError:
                    return
                conn.settimeout(0.5)
                try:
                    req = conn.recv(2000).split(b"\r\n")[0].decode()
                except OSError:
                    req = ""
                hits.append(req)
                body = page if "/iframe" in req else b""
                conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: %d\r\n\r\n%s" % (len(body), body))
                conn.close()

        threading.Thread(target=serve, daemon=True).start()
        saved = apply(False, False, True)
        gs.CdpDriver._answer = lambda self, url: "fulfill" if url == self._draft_url else "continue"
        gs.CdpDriver._draft_headers = lambda self: [{"name": "Content-Type", "value": "text/html"}]
        events: list[tuple] = []
        real_protect, real_decide = gs.CdpDriver._protect_target, gs.CdpDriver._decide

        async def protect(self, session):
            events.append(("attached", "child-session"))
            await real_protect(self, session)

        async def decide(self, msg):
            events.append(("paused", "child" if msg.get("sessionId") else "page", msg["params"]["request"]["url"][:48]))
            await real_decide(self, msg)

        gs.CdpDriver._protect_target, gs.CdpDriver._decide = protect, decide
        try:
            job = live._job(root, "attachprobe", f"<html><body><iframe src='{base}/iframe' width=300 height=200></iframe></body></html>")
            index = asyncio.run(gs.capture(job))
        finally:
            gs.CdpDriver._protect_target, gs.CdpDriver._decide = real_protect, real_decide
            restore(saved)
            server.close()
        print(json.dumps({"probe": "forced child target", "outcome": index["outcome"], "statuses": live._statuses(index),
                          "events": events, "server_hits": hits}))
    elif mode == "charset":
        # Korean text, no <meta charset>: does serving via Fetch.fulfillRequest (Content-Type: text/html, no charset)
        # decode differently from the file:// load? Compare tile bytes baseline vs new.
        import hashlib

        html = "<html><body style='font:30px sans-serif'><h1>한글 제목 확인</h1><p>가나다라마바사 — 본문 문단</p></body></html>"
        baseline = live.load_baseline_module()
        out = {}
        for label, mod in (("baseline", baseline), ("new", gs)):
            job = live._job(root, f"charset-{label}", html)
            idx = asyncio.run(mod.capture(job))
            out[label] = {v["name"]: [t["sha256"][:16] for t in v["tiles"]] for v in idx["viewports"]}
        print(json.dumps({"charset_probe": out, "identical": out["baseline"] == out["new"]}))
    elif mode == "r1":
        print(json.dumps(r1_summary(root), ensure_ascii=False))
    elif mode == "r2":
        r2 = live.scenario_r2(root)
        print(json.dumps({"outcome": r2["outcome"], "hits": [h.decode() for h in r2["hits"]]}))
    elif mode == "r3":
        html = Path(sys.argv[2]).read_bytes() if len(sys.argv) > 2 else live._normal_report()
        print(json.dumps(live.scenario_r3(root, html), ensure_ascii=False, indent=1))


main()
