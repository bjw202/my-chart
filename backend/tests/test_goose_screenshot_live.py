"""SPEC-AI-REPORT-006 M7 — 격리 회귀 시험 R1·R2·R3 (AC-AIR6-009 (5)(6), REQ-AIR6-017 예외).

실제 `chrome-headless-shell`과 루프백 수신 소켓을 쓰므로 공용 네트워크 가드(conftest)가 막는다. 그래서
이 파일의 시험은 `goose_real_browser` 표지로 가드를 벗어나고, 아래 조건이 모두 맞을 때만 실행한다.

  1. 환경 변수 `AI_REPORT_GOOSE_REAL_BROWSER_TESTS=1`
  2. 캡처 모듈이 찾을 수 있는 브라우저(`AI_REPORT_GOOSE_BROWSER` 또는 Playwright 캐시)

기본 `pytest backend/tests -k goose` 실행에서는 전부 건너뛴다(건너뜀 개수가 집계된다).

실행(손 실행 포함):
  AI_REPORT_GOOSE_REAL_BROWSER_TESTS=1 python -m pytest backend/tests/test_goose_screenshot_live.py -q
R3를 라이브 초안으로도 돌리려면 `AI_REPORT_GOOSE_R3_DRAFT=<report.html 사본 경로>`를 더한다(읽기 전용으로만 쓴다).

R3의 기준선은 이 개정 이전 커밋(`_BASELINE_COMMIT`)의 캡처 모듈이다. git에서 읽어 임시 모듈로 불러온다.
시나리오 함수(`scenario_*`)는 단언 없이 관측값만 돌려준다 — 되돌림 행렬 스크립트가 같은 함수를 쓴다.
"""

from __future__ import annotations

import asyncio
import base64
import importlib.util
import os
import socket
import subprocess
import tempfile
import threading
import urllib.parse
from pathlib import Path

import pytest

from backend.services import goose_screenshot as gs

_ENV_FLAG = "AI_REPORT_GOOSE_REAL_BROWSER_TESTS"
_ENV_R3_DRAFT = "AI_REPORT_GOOSE_R3_DRAFT"
_BASELINE_COMMIT = "f0926e2"  # 격리 층을 넣기 직전 커밋(M7 기준)
_REPO_ROOT = Path(__file__).resolve().parents[2]
_MAGENTA = (255, 0, 255)
_BLUE = (0, 0, 255)

pytestmark = [
    pytest.mark.goose_real_browser,
    pytest.mark.skipif(os.environ.get(_ENV_FLAG) != "1", reason=f"{_ENV_FLAG}=1일 때만 실행(실제 브라우저)"),
    pytest.mark.skipif(gs.find_browser(os.environ)[0] is None, reason="캡처용 브라우저를 찾을 수 없다"),
]


# ─────────────────────────────────────────────────────────────────────────────
# 시나리오 (관측값만 돌려준다)
# ─────────────────────────────────────────────────────────────────────────────


def _color_count(png: Path, color: tuple[int, int, int]) -> int:
    from PIL import Image

    with Image.open(png) as image:
        colors = image.convert("RGB").getcolors(maxcolors=1 << 24) or []
    return sum(count for count, rgb in colors if rgb == color)


def _tile_pixels(job_dir: Path, color: tuple[int, int, int]) -> dict[str, int]:
    return {p.name: _color_count(p, color) for p in sorted((job_dir / "screens").glob("*.png"))}


def _job(root: Path, name: str, html: str | bytes) -> Path:
    job_dir = root / name
    (job_dir / "draft").mkdir(parents=True)
    data = html if isinstance(html, bytes) else html.encode("utf-8")
    (job_dir / "draft" / "report.html").write_bytes(data)
    return job_dir


def _statuses(index: dict) -> list[tuple[str, str, str | None]]:
    return [(v["name"], v["status"], v["error"]) for v in index["viewports"]]


def scenario_r1(root: Path, module=gs) -> dict:
    """R1 (PoC1, S1): 초안이 file:// 프레임으로 다른 파일을 그리려 한다. 비밀 파일은 마젠타 한 색이다."""
    root.mkdir(parents=True, exist_ok=True)
    secret = root / "secret-magenta.html"
    other = root / "other-magenta.html"
    for path in (secret, other):
        path.write_text("<html><body style='margin:0;background:#ff00ff'><h1>x</h1></body></html>")
    nested = "data:text/html," + urllib.parse.quote(f"<iframe src='{secret.as_uri()}' width=600 height=200></iframe>")
    variants = {
        "file_iframes": (
            f'<iframe src="{secret.as_uri()}" width="600" height="200"></iframe>'
            f'<iframe src="{other.as_uri()}" width="600" height="200"></iframe>'
        ),
        "object_embed": (
            f'<object data="{secret.as_uri()}" width="600" height="200"></object>'
            f'<embed src="{other.as_uri()}" width="600" height="200">'
        ),
        "data_nested_iframe": f'<iframe src="{nested}" width="700" height="300"></iframe>',
    }
    out: dict = {}
    for label, frames in variants.items():
        html = (
            "<html><body style='font-size:30px'><h1>report</h1>"
            "<div style='width:100px;height:100px;background:#0000ff'></div>"
            f"{frames}</body></html>"
        )
        job_dir = _job(root, f"r1-{label}", html)
        index = asyncio.run(module.capture(job_dir))
        out[label] = {
            "outcome": index["outcome"],
            "statuses": _statuses(index),
            "magenta": _tile_pixels(job_dir, _MAGENTA),
            "blue": _tile_pixels(job_dir, _BLUE),
        }
    return out


_R2_VECTORS = """<html><head>
<link rel="preconnect" href="{b}/preconnect"><link rel="prefetch" href="{b}/prefetch">
<link rel="dns-prefetch" href="{b}/dnsprefetch"><link rel="stylesheet" href="{b}/css">
<meta http-equiv="refresh" content="3;url={b}/metarefresh">
</head><body>
<img src="{b}/img"><iframe src="{b}/iframe"></iframe>
<object data="{b}/object"></object><embed src="{b}/embed">
<video poster="{b}/poster"></video>
<form action="{b}/form"><input type=submit></form>
<a href="{b}/a" ping="{b}/ping">x</a>
<svg><image href="{b}/svgimg"/></svg>
<div style="background:url({b}/cssbg)">bg</div>
</body></html>"""


def scenario_r2(root: Path, module=gs) -> dict:
    """R2 (PoC2, S2): 루프백 수신 소켓. 연결만 하고 데이터가 없는 접속도 기록한다."""
    hits: list[bytes] = []
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(50)
    base = f"http://127.0.0.1:{server.getsockname()[1]}"

    def serve() -> None:
        while True:
            try:
                conn, _ = server.accept()
            except OSError:
                return
            try:
                conn.settimeout(0.5)
                data = conn.recv(2000)
            except OSError:
                data = b""
            hits.append(data.split(b"\r\n")[0] if data else b"<tcp-connect-only>")
            conn.close()

    threading.Thread(target=serve, daemon=True).start()
    try:
        job_dir = _job(root, "r2", _R2_VECTORS.format(b=base))
        index = asyncio.run(module.capture(job_dir))
        # 늦게 도착하는 요청(메타 새로고침 등)까지 잡도록 짧게 더 기다린다
        asyncio.run(asyncio.sleep(0.5))
    finally:
        server.close()
    return {"outcome": index["outcome"], "statuses": _statuses(index), "hits": list(hits)}


def _png_data_uri() -> str:
    """정상 보고서가 쓰는 `data:image/png` 이미지의 대역. 크기 속성 없이 써서 이미지가 그려지는지에 문서 높이가 따른다.

    관측(M7): 이 호스트에서는 `Network.setBlockedURLs ["*"]`가 `data:` 이미지도 막아 기준선·새 캡처 모두 이미지가
    그려지지 않는다(progress.md §E.2 M7 기록). 그래서 R3는 층 A1·B의 `data:` 예외 유무를 가려내지 못한다 — 그 예외는
    핸들러 계약 시험(AC-009 (3) `data:` 행)이 맡는다.
    """
    from io import BytesIO

    from PIL import Image

    buffer = BytesIO()
    Image.new("RGB", (300, 200), (30, 120, 60)).save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def _normal_report() -> str:
    """정상 보고서 모양: 인라인 style, data:image/png img, 두 뷰포트에서 각각 타일 둘 이상인 인라인 svg, 외부 글꼴 link 2개."""
    return (
        "<!doctype html><html lang='ko'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'><title>정상 보고서</title>"
        '<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard/x.css">'
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Gowun+Batang">'
        "<style>body{margin:0;font:17px/1.6 sans-serif;background:#f3f3f0}"
        "main{max-width:1240px;margin:32px auto}svg{display:block;width:100%}</style></head><body><main>"
        f"<h1>한글 제목 report</h1><img alt='logo' src='{_png_data_uri()}'>"
        "<svg viewBox='0 0 100 300' preserveAspectRatio='none' height='3300'>"
        "<rect width='100' height='300' fill='#902531'/></svg>"
        "<p>본문 문단</p></main></body></html>"
    )


def _shape(index: dict) -> list[dict]:
    return [
        {
            "name": v["name"],
            "status": v["status"],
            "tiles": len(v["tiles"]),
            "heights": [t["height"] for t in v["tiles"]],
            "scroll_height": v["metrics"]["scroll_height"],
            "overflow": v["metrics"]["horizontal_overflow"],
        }
        for v in index["viewports"]
    ]


def load_baseline_module():
    """격리 층 이전 커밋의 goose_screenshot을 임시 모듈로 불러온다. 커밋을 못 찾으면 None."""
    probe = subprocess.run(["git", "cat-file", "-e", f"{_BASELINE_COMMIT}^{{commit}}"], cwd=_REPO_ROOT, capture_output=True)
    if probe.returncode != 0:
        return None
    source = subprocess.run(
        ["git", "show", f"{_BASELINE_COMMIT}:backend/services/goose_screenshot.py"],
        cwd=_REPO_ROOT, capture_output=True, check=True,
    ).stdout
    path = Path(tempfile.mkdtemp(prefix="goose-baseline-")) / "goose_screenshot_baseline.py"
    path.write_bytes(source)
    spec = importlib.util.spec_from_file_location("goose_screenshot_baseline", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def scenario_r3(root: Path, html: str | bytes, module=gs) -> dict:
    """R3: 같은 초안을 격리 미적용 모듈과 새 모듈로 각각 캡처해 두 뷰포트의 타일 수·높이 목록을 비교한다."""
    baseline = load_baseline_module()
    if baseline is None:
        pytest.skip(f"기준 커밋 {_BASELINE_COMMIT}를 이 체크아웃에서 찾을 수 없다")
    result = {}
    for label, mod in (("baseline", baseline), ("new", module)):
        job_dir = _job(root, f"r3-{label}", html)
        result[label] = _shape(asyncio.run(mod.capture(job_dir)))
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 시험
# ─────────────────────────────────────────────────────────────────────────────


def test_air6_009_live_r1_file_frames_never_render(tmp_path):
    observed = scenario_r1(tmp_path)

    for label, result in observed.items():
        assert result["outcome"] == "complete", (label, result["statuses"])
        assert result["magenta"] and all(count == 0 for count in result["magenta"].values()), (label, result["magenta"])
        assert sum(result["blue"].values()) >= 10_000, (label, "초안 자체는 그려져야 한다")


def test_air6_009_live_r2_no_request_reaches_a_loopback_listener(tmp_path):
    observed = scenario_r2(tmp_path)

    assert observed["outcome"] == "complete", observed["statuses"]
    assert observed["hits"] == [], observed["hits"]


def _assert_same_shape(result: dict) -> None:
    assert result["new"] == result["baseline"], result
    for vp in result["new"]:
        assert vp["status"] == "ok"


def test_air6_009_live_r3_normal_report_matches_unisolated_baseline(tmp_path):
    result = scenario_r3(tmp_path, _normal_report())

    _assert_same_shape(result)
    assert all(vp["tiles"] >= 2 for vp in result["new"]), result["new"]  # 타일이 둘 이상이어야 의미가 있다

@pytest.mark.skipif(not os.environ.get(_ENV_R3_DRAFT), reason=f"{_ENV_R3_DRAFT}(라이브 초안 사본 경로)가 없다")
def test_air6_009_live_r3_live_draft_copy_matches_unisolated_baseline(tmp_path):
    draft = Path(os.environ[_ENV_R3_DRAFT])
    result = scenario_r3(tmp_path, draft.read_bytes())

    _assert_same_shape(result)
