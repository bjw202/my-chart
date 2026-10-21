import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, ".")
from backend.services import goose_screenshot as gs  # noqa: E402

root = Path(".moai/state/verify/t18-sync/sec/job1").resolve()
(root / "draft").mkdir(parents=True, exist_ok=True)
secret = Path(".moai/state/verify/t18-sync/sec/secret.txt").resolve()
secret.write_text("TOP-SECRET-LOCAL-FILE-CONTENT-12345\n")
html = (
    "<html><body style='font-size:30px'><h1>report</h1>"
    f'<iframe src="{secret.as_uri()}" width="700" height="100"></iframe>'
    '<iframe src="file:///etc/hosts" width="700" height="300"></iframe>'
    "</body></html>"
)
(root / "draft" / "report.html").write_text(html)
idx = asyncio.run(gs.capture(root))
print(idx["outcome"], idx["browser"], [(v["name"], v["status"], v["error"], len(v["tiles"])) for v in idx["viewports"]])
