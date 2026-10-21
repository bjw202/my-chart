"""PoC1 (S1 text secret + /etc/hosts) and PoC2 (S2 loopback listener) ported from t18-sync, run against either the
pre-M7 module (baseline commit) or the shipped module.

usage (cwd = worktree root, PYTHONPATH=.):  poc.py baseline|new
"""
import asyncio
import socket
import sys
import threading
from pathlib import Path

from backend.services import goose_screenshot as gs
from backend.tests import test_goose_screenshot_live as live

which = sys.argv[1]
module = live.load_baseline_module() if which == "baseline" else gs
base_dir = Path(".moai/state/verify/t18-m7/poc-" + which).resolve()

# PoC1 -- S1
job1 = base_dir / "job1"
(job1 / "draft").mkdir(parents=True, exist_ok=True)
secret = base_dir / "secret.txt"
secret.write_text("TOP-SECRET-LOCAL-FILE-CONTENT-12345\n")
html = (
    "<html><body style='font-size:30px'><h1>report</h1>"
    f'<iframe src="{secret.as_uri()}" width="700" height="100"></iframe>'
    '<iframe src="file:///etc/hosts" width="700" height="300"></iframe>'
    "</body></html>"
)
(job1 / "draft" / "report.html").write_text(html)
idx = asyncio.run(module.capture(job1))
print(which, "PoC1", idx["outcome"], [(v["name"], v["status"], v["error"], len(v["tiles"])) for v in idx["viewports"]])

# PoC2 -- S2
hits = []
srv = socket.socket()
srv.bind(("127.0.0.1", 0))
srv.listen(50)
port = srv.getsockname()[1]


def serve():
    while True:
        try:
            c, _ = srv.accept()
        except OSError:
            return
        try:
            c.settimeout(0.5)
            data = c.recv(2000)
        except OSError:
            data = b""
        hits.append(data.split(b"\r\n")[0] if data else b"<tcp-connect-only>")
        c.close()


threading.Thread(target=serve, daemon=True).start()
b = f"http://127.0.0.1:{port}"
job2 = base_dir / "job2"
(job2 / "draft").mkdir(parents=True, exist_ok=True)
(job2 / "draft" / "report.html").write_text(live._R2_VECTORS.format(b=b))
idx2 = asyncio.run(module.capture(job2))
asyncio.run(asyncio.sleep(0.5))
print(which, "PoC2", idx2["outcome"], [(v["name"], v["status"], v["error"]) for v in idx2["viewports"]])
print(which, "PoC2 HITS:", hits)
srv.close()
