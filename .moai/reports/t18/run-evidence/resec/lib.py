import asyncio, socket, sys, threading, shutil, time
from pathlib import Path
sys.path.insert(0, ".")
from backend.services import goose_screenshot as gs

HERE = Path(".moai/state/verify/t18-resec").resolve()
SECRET = Path(".moai/state/verify/t18-sync/sec/secret.txt").resolve()
hits = []
srv = socket.socket(); srv.bind(("127.0.0.1", 0)); srv.listen(200)
PORT = srv.getsockname()[1]
BASE = f"http://127.0.0.1:{PORT}"


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
        try:
            c.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: 20\r\n\r\n<h1>LEAKED-PAGE</h1>")
        except OSError:
            pass
        c.close()


threading.Thread(target=serve, daemon=True).start()


def run(name, html, relaxed=False, extra=None):
    root = HERE / "jobs" / (name + ("_relaxed" if relaxed else ""))
    shutil.rmtree(root, ignore_errors=True)
    (root / "draft").mkdir(parents=True)
    if extra:
        extra(root)
    else:
        (root / "draft" / "report.html").write_text(html)
    old = gs.DOCUMENT_CSP
    if relaxed:
        gs.DOCUMENT_CSP = "default-src * data: blob: filesystem: 'unsafe-inline' 'unsafe-eval'"
    before = len(hits)
    try:
        idx = asyncio.run(gs.capture(root))
    finally:
        gs.DOCUMENT_CSP = old
    time.sleep(0.5)
    print(f"[{name}{' RELAXED' if relaxed else ''}]", idx["outcome"],
          [(v["name"], v["status"], v["error"], len(v["tiles"])) for v in idx["viewports"]],
          "NEWHITS:", hits[before:], flush=True)
    return idx
