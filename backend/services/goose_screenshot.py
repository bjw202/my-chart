"""SPEC-AI-REPORT-006 M2 — 서버 화면 캡처: 초안 `draft/report.html`을 두 뷰포트 PNG 타일로 저장.

설계: design.md §3(브라우저 실행·캡처 절차), §4.1(`screens/index.json` 스키마), §9(보안).
결정 T9: 지원 브라우저는 Playwright 캐시의 `chrome-headless-shell`뿐이고(환경 변수가 우선),
캡처 중 외부 네트워크는 예외 없이 전부 차단하며 스크립트는 실행하지 않는다.

경계: 이 모듈은 브라우저 프로세스 수명(실행·그룹 종료·임시 프로필 삭제)과 타일 파일·색인을
책임진다. DevTools 통신은 ``BrowserDriver`` 뒤에 두어 테스트가 가짜를 꽂는다. 감수·영수증·
전달 판정은 이 모듈의 일이 아니다(M3 이후).
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import hashlib
import json
import logging
import os
import re
import shutil
import signal
import socket
import subprocess
import tempfile
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Protocol

import httpx
import websockets

logger = logging.getLogger(__name__)

ENV_BROWSER = "AI_REPORT_GOOSE_BROWSER"
SCHEMA_VERSION = 1
SCREENS_DIR = "screens"
INDEX_NAME = "index.json"
TILE_HEIGHT = 1568
# research P26: 기존 초안 중 가장 무거운 것이 모바일 20타일 — 그 1.5배(M1 재측정으로 유지 확인)
TILE_CAP = 30
MAX_TILE_BYTES = 8 * 1024 * 1024
# 브라우저 시작부터 정리까지의 벽시계 예산(REQ-AIR6-008)
CAPTURE_BUDGET_SEC = 60.0
LOAD_TIMEOUT_SEC = 20.0
DISCOVERY_TRIES = 100
# (이름, 폭, 높이, 모바일 에뮬레이션) — design §3.2
VIEWPORTS = (("desktop", 1280, 800, False), ("mobile", 390, 844, True))
# 외부 네트워크 전면 차단. 글꼴 호스트 예외는 없다(운영자 결정 2026-10-21)
BLOCK_ALL_PATTERNS = ("*",)
PLAYWRIGHT_CACHE_ROOTS = (
    Path.home() / "Library" / "Caches" / "ms-playwright",
    Path.home() / ".cache" / "ms-playwright",
)

_KST = timezone(timedelta(hours=9))
_BUILD_PATTERN = re.compile(r"^chromium_headless_shell-(\d+)$")


class CaptureError(Exception):
    """사유 코드를 ``args[0]``에 담는 캡처 실패. 보고서·경로 문자열은 담지 않는다."""


class BrowserDriver(Protocol):
    """브라우저 구동 인터페이스. 실제 구현은 ``CdpDriver``, 테스트는 가짜를 쓴다."""

    async def connect(self, port: int) -> tuple[str, str]: ...

    async def block_network(self, patterns: list[str]) -> None: ...

    async def disable_scripts(self) -> None: ...

    async def open(self, url: str, width: int, height: int, mobile: bool) -> dict: ...

    async def capture_tile(self, width: int, y: int, height: int) -> bytes: ...

    async def close(self) -> None: ...


# ─────────────────────────────────────────────────────────────────────────────
# DevTools 구동 (M1 스파이크 방식을 옮김)
# ─────────────────────────────────────────────────────────────────────────────


class CdpDriver:
    """루프백 DevTools 프로토콜로 헤드리스 셸을 구동한다(plan T8)."""

    def __init__(self) -> None:
        self._ws = None
        self._seq = 0
        self._loaded = False

    async def _open_transport(self, port: int):
        """`/json/list`에서 page 대상을 찾아 WebSocket을 연다. 테스트가 가짜 전송로로 바꾼다."""
        async with httpx.AsyncClient(timeout=1.0) as client:
            for _ in range(DISCOVERY_TRIES):
                try:
                    reply = await client.get(f"http://127.0.0.1:{port}/json/list")
                    pages = [p for p in reply.json() if p.get("type") == "page"]
                    if pages:
                        return await websockets.connect(
                            pages[0]["webSocketDebuggerUrl"], max_size=2 * MAX_TILE_BYTES
                        )
                except (httpx.HTTPError, ValueError, OSError):
                    pass
                await asyncio.sleep(0.1)
        raise CaptureError("devtools_unreachable")

    def _note(self, msg: dict) -> None:
        if msg.get("method") == "Page.loadEventFired":
            self._loaded = True

    async def _call(self, method: str, params: dict | None = None) -> dict:
        self._seq += 1
        await self._ws.send(json.dumps({"id": self._seq, "method": method, "params": params or {}}))
        while True:
            msg = json.loads(await self._ws.recv())
            self._note(msg)
            if msg.get("id") == self._seq:
                if "error" in msg:
                    raise CaptureError(f"cdp_error:{method}")
                return msg.get("result", {})

    async def connect(self, port: int) -> tuple[str, str]:
        self._ws = await self._open_transport(port)
        await self._call("Page.enable")
        await self._call("Network.enable")
        product = (await self._call("Browser.getVersion")).get("product", "")
        name, _, version = product.partition("/")
        return name, version

    async def block_network(self, patterns: list[str]) -> None:
        await self._call("Network.setBlockedURLs", {"urls": patterns})

    async def disable_scripts(self) -> None:
        await self._call("Emulation.setScriptExecutionDisabled", {"value": True})

    async def _wait_load(self) -> None:
        while not self._loaded:
            self._note(json.loads(await self._ws.recv()))

    async def open(self, url: str, width: int, height: int, mobile: bool) -> dict:
        await self._call(
            "Emulation.setDeviceMetricsOverride",
            {"width": width, "height": height, "deviceScaleFactor": 1, "mobile": mobile},
        )
        self._loaded = False
        nav = await self._call("Page.navigate", {"url": url})
        if nav.get("errorText"):
            raise CaptureError("navigate_failed")
        await asyncio.wait_for(self._wait_load(), LOAD_TIMEOUT_SEC)
        probe = await self._call(
            "Runtime.evaluate",
            {
                "expression": "JSON.stringify({sw:document.documentElement.scrollWidth,"
                "cw:document.documentElement.clientWidth,sh:document.documentElement.scrollHeight})",
                "returnByValue": True,
            },
        )
        raw = json.loads(probe["result"]["value"])
        return {"scroll_width": raw["sw"], "client_width": raw["cw"], "scroll_height": raw["sh"]}

    async def capture_tile(self, width: int, y: int, height: int) -> bytes:
        shot = await self._call(
            "Page.captureScreenshot",
            {
                "format": "png",
                "captureBeyondViewport": True,
                "clip": {"x": 0, "y": y, "width": width, "height": height, "scale": 1},
            },
        )
        return base64.b64decode(shot["data"])

    async def close(self) -> None:
        if self._ws is not None:
            await self._ws.close()


# ─────────────────────────────────────────────────────────────────────────────
# 브라우저 탐색·프로세스 수명
# ─────────────────────────────────────────────────────────────────────────────


def _executable(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)


def find_browser(environ: Mapping[str, str]) -> tuple[Path | None, str, str | None]:
    """(실행 파일, path_kind, 실패 사유). design §3.1: 환경 변수 → Playwright 캐시 최고 빌드.

    ``PATH``와 ``Google Chrome.app``은 찾지 않는다. 환경 변수가 있는데 실행할 수 없으면
    캐시로 폴백하지 않는다(무엇으로 찍었는지 잃지 않게).
    """
    configured = environ.get(ENV_BROWSER)
    if configured:
        exe = Path(configured)
        if _executable(exe):
            return exe, "env", None
        return None, "none", "browser_env_not_executable"
    best: tuple[int, Path] | None = None
    for root in PLAYWRIGHT_CACHE_ROOTS:
        for build_dir in root.glob("chromium_headless_shell-*"):
            match = _BUILD_PATTERN.match(build_dir.name)
            if not match:
                continue
            for exe in build_dir.glob("*/chrome-headless-shell"):
                if _executable(exe) and (best is None or int(match.group(1)) > best[0]):
                    best = (int(match.group(1)), exe)
    if best:
        return best[1], "playwright_cache", None
    return None, "none", "browser_not_found"


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


# @MX:WARN: [AUTO] 브라우저를 새 프로세스 그룹으로 띄우고 그룹 전체에 SIGKILL을 보낸다.
# @MX:REASON: 헤드리스 셸은 렌더러·GPU 손자 프로세스를 띄운다(직계만 죽이면 남는다, AC-AIR6-002/008).
#             pgid는 start_new_session으로 만든 그룹이어야 한다 — 서버 자신의 그룹을 넘기면 서버가 죽는다.
def _launch(exe: Path, port: int, profile: Path) -> subprocess.Popen:
    """인자는 고정 문자열 + 서버가 만든 포트·임시 프로필뿐이다(REQ-AIR6-009)."""
    argv = [
        str(exe),
        "--headless",
        "--disable-gpu",
        "--hide-scrollbars",
        f"--remote-debugging-port={port}",
        f"--user-data-dir={profile}",
        "about:blank",
    ]
    return subprocess.Popen(
        argv,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def _kill_group(proc: subprocess.Popen) -> None:
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(proc.pid, signal.SIGKILL)
    proc.wait()  # 좀비를 회수해야 그룹이 완전히 사라진다


# ─────────────────────────────────────────────────────────────────────────────
# 색인·뷰포트
# ─────────────────────────────────────────────────────────────────────────────


def _now() -> str:
    return datetime.now(_KST).isoformat(timespec="seconds")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _new_viewport(name: str, width: int) -> dict:
    metrics = dict.fromkeys(("scroll_width", "client_width", "scroll_height", "horizontal_overflow"))
    return {"name": name, "width": width, "status": "skipped", "error": None, "metrics": metrics, "tiles": []}


def _reason(exc: BaseException) -> str:
    return str(exc.args[0]) if isinstance(exc, CaptureError) else type(exc).__name__


def _fail(viewports: list[dict], reason: str, screens: Path) -> None:
    """뷰포트를 ``error``로 기록하고, 이미 쓴 타일은 지운다(일부만 남기지 않는다)."""
    for vp in viewports:
        vp["status"], vp["error"], vp["tiles"] = "error", reason, []
        for stale in screens.glob(f"{vp['name']}-*.png"):
            stale.unlink(missing_ok=True)


def _check_draft(job_dir: Path, draft: Path) -> str | None:
    """정규 파일이고 심볼릭 링크가 아니며 해석 경로가 작업 폴더 안일 때만 통과(design §9)."""
    if draft.is_symlink() or not draft.is_file():
        return "draft_not_regular_file"
    if not draft.resolve().is_relative_to(job_dir.resolve()):
        return "draft_outside_job_dir"
    return None


async def _capture_viewport(
    driver: BrowserDriver, url: str, spec: tuple, vp: dict, screens: Path
) -> None:
    name, width, height, mobile = spec
    try:
        raw = await driver.open(url, width, height, mobile)
        vp["metrics"] = {
            "scroll_width": raw["scroll_width"],
            "client_width": raw["client_width"],
            "scroll_height": raw["scroll_height"],
            "horizontal_overflow": raw["scroll_width"] > raw["client_width"],
        }
        total = raw["scroll_height"]
        count = -(-total // TILE_HEIGHT)
        if count > TILE_CAP:  # 일부만 저장하지 않는다
            vp["status"] = "too_tall"
            return
        if count == 0:
            raise CaptureError("empty_page")
        for index in range(count):
            y = index * TILE_HEIGHT
            tile_h = min(TILE_HEIGHT, total - y)
            png = await driver.capture_tile(width, y, tile_h)
            if len(png) > MAX_TILE_BYTES:
                raise CaptureError("tile_too_large")
            file = f"{name}-{index + 1:02d}.png"
            (screens / file).write_bytes(png)
            written = (screens / file).read_bytes()  # 해시는 쓴 뒤 디스크에서 계산한다
            vp["tiles"].append(
                {"file": file, "y": y, "width": width, "height": tile_h,
                 "bytes": len(written), "sha256": _sha256(written)}
            )
        vp["status"] = "ok"
    except Exception as exc:  # noqa: BLE001 - 뷰포트 하나의 실패가 다른 뷰포트를 막지 않는다
        logger.warning("goose screenshot viewport %s failed: %s", name, _reason(exc))
        _fail([vp], _reason(exc), screens)


async def _run(job_dir: Path, screens: Path, index: dict, current: list, environ, driver_factory) -> None:
    draft = job_dir / "draft" / "report.html"
    viewports = index["viewports"]
    bad = _check_draft(job_dir, draft)
    if bad:
        _fail(viewports, bad, screens)
        return
    index["preview_sha256"] = _sha256(draft.read_bytes())
    exe, kind, why = find_browser(environ)
    index["browser"]["path_kind"] = kind
    if exe is None:
        for vp in viewports:
            vp["error"] = why
        index["outcome"] = "unavailable"
        return
    profile = Path(tempfile.mkdtemp(prefix="goose-shot-"))
    proc = driver = None
    try:
        current[:] = viewports  # 시작 단계에서 멈추면 두 뷰포트 모두 실패로 기록한다
        try:
            port = _free_port()
            proc = _launch(exe, port, profile)
            driver = driver_factory()
            name, version = await driver.connect(port)
            index["browser"].update(name=name, version=version)
            await driver.block_network(list(BLOCK_ALL_PATTERNS))
            await driver.disable_scripts()
        except Exception as exc:  # noqa: BLE001
            logger.warning("goose screenshot browser start failed: %s", _reason(exc))
            _fail(viewports, f"browser_start_failed:{_reason(exc)}", screens)
            return
        url = draft.resolve().as_uri()
        for spec, vp in zip(VIEWPORTS, viewports, strict=True):
            current[:] = [vp]
            await _capture_viewport(driver, url, spec, vp, screens)
            current[:] = []
    finally:
        if driver is not None:
            with contextlib.suppress(Exception):
                await driver.close()
        if proc is not None:
            _kill_group(proc)
        shutil.rmtree(profile, ignore_errors=True)


def _finish(index: dict, screens: Path) -> None:
    index["finished_at"] = _now()
    if index["outcome"] is None:
        ok = sum(vp["status"] == "ok" for vp in index["viewports"])
        index["outcome"] = {2: "complete", 1: "partial"}.get(ok, "failed")
    target = screens / INDEX_NAME
    tmp = screens / f".{INDEX_NAME}.tmp"
    tmp.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, target)


# @MX:ANCHOR: [AUTO] capture — 화면 캡처의 단일 진입점(REQ-AIR6-006~010, design §3).
# @MX:REASON: M3 감수 컨텍스트 작성, M4 작업 서비스 후처리, 이 모듈의 AC-AIR6-006~010 시험이 모두
#             색인 스키마(design §4.1)와 이 함수의 결과 dict에 의존한다(fan_in 3). 키 집합을 바꾸면 셋 다 깨진다.
async def capture(
    job_dir: Path,
    *,
    environ: Mapping[str, str] | None = None,
    driver_factory: Callable[[], BrowserDriver] | None = None,
) -> dict:
    """``job_dir/draft/report.html``을 찍어 ``job_dir/screens/``에 타일과 ``index.json``을 쓴다.

    실패는 예외가 아니라 색인의 ``outcome``/``status``로 기록한다. 취소(``CancelledError``)만
    다시 던지며, 어느 경로에서든 브라우저 프로세스 그룹과 임시 프로필은 정리된다.
    """
    screens = job_dir / SCREENS_DIR
    shutil.rmtree(screens, ignore_errors=True)  # 서버 소유 폴더: 이전 잔여물을 남기지 않는다
    screens.mkdir(parents=True)
    index = {
        "schema_version": SCHEMA_VERSION,
        "source": "draft/report.html",
        "preview_sha256": None,
        "started_at": _now(),
        "finished_at": None,
        "outcome": None,
        "browser": {"name": None, "version": None, "path_kind": "none"},
        "viewports": [_new_viewport(name, width) for name, width, _h, _m in VIEWPORTS],
    }
    current: list[dict] = []  # 지금 진행 중인 뷰포트(예산 초과·취소 때 실패로 기록)
    try:
        await asyncio.wait_for(
            _run(job_dir, screens, index, current,
                 os.environ if environ is None else environ, driver_factory or CdpDriver),
            timeout=CAPTURE_BUDGET_SEC,
        )
    except TimeoutError:
        _fail(current, "budget_exceeded", screens)
    except asyncio.CancelledError:
        _fail(current, "cancelled", screens)
        raise
    finally:
        _finish(index, screens)
    return index
