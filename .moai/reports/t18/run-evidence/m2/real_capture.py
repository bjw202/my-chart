"""M2 수동 검증: 실제 Playwright 캐시 브라우저로 goose_screenshot.capture를 1회 실행한다(pytest 밖).

pytest 쪽 네트워크 가드가 루프백 연결을 막으므로 실제 구동 시험은 여기서만 한다.
"""
import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = sys.argv[1]
sys.path.insert(0, ROOT)
from backend.services import goose_screenshot as gs  # noqa: E402

HTML = """<!doctype html><html><head><meta charset=utf-8>
<link rel=stylesheet href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR">
<script>document.title='SCRIPT-RAN'</script></head>
<body style="margin:0"><div id=a style="height:4200px;background:linear-gradient(#fff,#09f)">static</div></body></html>"""


async def main():
    job = Path(tempfile.mkdtemp(prefix="m2-real-"))
    (job / "draft").mkdir()
    (job / "draft" / "report.html").write_text(HTML)
    index = await gs.capture(job, environ={k: v for k, v in os.environ.items() if k != gs.ENV_BROWSER})
    print(json.dumps(index, indent=1, ensure_ascii=False))
    print("FILES", sorted(p.name for p in (job / "screens").iterdir()))
    print("JOB", job)


asyncio.run(main())
