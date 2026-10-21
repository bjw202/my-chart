"""Look at how a data: PNG renders in baseline vs new capture (evidence only)."""
import asyncio
import sys
from pathlib import Path

from backend.services import goose_screenshot as gs
from backend.tests import test_goose_screenshot_live as live

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
html = live._normal_report()
baseline = live.load_baseline_module()
for label, mod in (("baseline", baseline), ("new", gs)):
    job = live._job(out, label, html)
    idx = asyncio.run(mod.capture(job))
    print(label, idx["outcome"], [(v["name"], v["status"], len(v["tiles"])) for v in idx["viewports"]])
    from PIL import Image
    im = Image.open(job / "screens" / "desktop-01.png").convert("RGB")
    colors = sorted(im.getcolors(1 << 24), reverse=True)[:5]
    print(label, "top colors", colors)
