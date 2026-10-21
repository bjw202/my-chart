"""Does Network.setBlockedURLs ["*"] itself block data: images? (evidence only)"""
import asyncio
import sys
from pathlib import Path

from PIL import Image

from backend.services import goose_screenshot as gs
from backend.tests import test_goose_screenshot_live as live

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
html = live._normal_report()


async def no_block(self, patterns):
    return None


def green(job):
    im = Image.open(job / "screens" / "desktop-01.png").convert("RGB")
    return sum(c for c, rgb in im.getcolors(1 << 24) if all(abs(a - b) <= 40 for a, b in zip(rgb, live._GREEN)))


for label, patch in (("new (setBlockedURLs *)", False), ("new, setBlockedURLs disabled", True)):
    saved = gs.CdpDriver.block_network
    if patch:
        gs.CdpDriver.block_network = no_block
    try:
        job = live._job(out, label.split()[0] + ("-noblock" if patch else "-block"), html)
        idx = asyncio.run(gs.capture(job))
        print(label, idx["outcome"], "green px:", green(job),
              "heights:", [[t["height"] for t in v["tiles"]] for v in idx["viewports"]])
    finally:
        gs.CdpDriver.block_network = saved
