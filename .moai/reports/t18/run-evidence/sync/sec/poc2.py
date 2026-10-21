import asyncio
import json
import socket
import sys
import threading
from pathlib import Path

sys.path.insert(0, ".")
from backend.services import goose_screenshot as gs  # noqa: E402

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
base = f"http://127.0.0.1:{port}"
root = Path(".moai/state/verify/t18-sync/sec/job2").resolve()
(root / "draft").mkdir(parents=True, exist_ok=True)
html = f"""<html><head>
<link rel="preconnect" href="{base}/preconnect">
<link rel="prefetch" href="{base}/prefetch">
<link rel="dns-prefetch" href="{base}/dnsprefetch">
<link rel="stylesheet" href="{base}/css">
<meta http-equiv="refresh" content="3;url={base}/metarefresh">
</head><body>
<img src="{base}/img"><iframe src="{base}/iframe"></iframe>
<object data="{base}/object"></object><embed src="{base}/embed">
<video poster="{base}/poster"></video>
<form action="{base}/form"><input type=submit></form>
<a href="{base}/a" ping="{base}/ping">x</a>
<svg><image href="{base}/svgimg"/></svg>
<div style="background:url({base}/cssbg)">bg</div>
</body></html>"""
(root / "draft" / "report.html").write_text(html)
idx = asyncio.run(gs.capture(root))
print(idx["outcome"], [(v["name"], v["status"], v["error"]) for v in idx["viewports"]])
print("HITS:", hits)
