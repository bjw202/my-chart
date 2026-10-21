"""SPEC-AI-REPORT-006 M2 — 서버 화면 캡처 모듈(goose_screenshot) 단위 시험.

대상: backend/services/goose_screenshot.py (AC-AIR6-006~010, AC-AIR6-002의 캡처 모듈 몫)

격리 원칙:
- 실제 브라우저·실제 네트워크·실제 `claude`를 쓰지 않는다. DevTools 구동은 가짜 ``FakeDriver``로 바꾸고,
  브라우저 프로세스는 tmp_path 안의 셸 스크립트(argv를 파일에 남기고 오래 잠)로 대신한다.
- 이 파일 이름은 `test_goose_` 접두어라 공용 네트워크 가드(conftest)가 자동 적용된다. 그 가드가
  루프백 연결도 막으므로 실제 브라우저 시험은 이 파일에 둘 수 없다(M2 증거 폴더의 수동 실행으로 대신).
- 기댓값 리터럴(타일 높이 목록 등)은 acceptance.md에서 가져왔고 시험 대상 코드로 계산하지 않는다.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import re
import signal
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.services import goose_screenshot as gs
from backend.services.goose_runner import ENV_ALLOWLIST

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
# 보고서 내용에서 온 문자열(브라우저 인자·파일 이름으로 새면 안 된다) — AC-009
_HOSTILE = ["--evil-flag", "$(touch x)", "</script>", "A; rm -rf /"]
_REPORT_HTML = (
    "<html><head><title>--evil-flag $(touch x) </script></title></head>"
    "<body><h1>A; rm -rf /</h1><link href='https://cdn.jsdelivr.net/x.css'></body></html>"
)
_FAKE_BROWSER = """#!/bin/sh
printf '%s\\n' "$@" > "$0.argv.tmp" && mv "$0.argv.tmp" "$0.argv"
env > "$0.env.tmp" && mv "$0.env.tmp" "$0.env"
echo "$$ {ident}" >> "{runlog}"
sleep 300 &
wait
"""
_KST_STAMP = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\+09:00$")


# ─────────────────────────────────────────────────────────────────────────────
# 시험 도구
# ─────────────────────────────────────────────────────────────────────────────


def _make_exe(path: Path, ident: str, runlog: Path, executable: bool = True) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_FAKE_BROWSER.format(ident=ident, runlog=runlog))
    path.chmod(0o755 if executable else 0o644)
    return path


def _runlog_lines(runlog: Path) -> list[list[str]]:
    return [line.split() for line in runlog.read_text().splitlines()] if runlog.exists() else []


def _assert_group_gone(pid: int) -> None:
    """가짜 브라우저의 프로세스 그룹이 사라졌는지 본다(좀비 회수까지 잠깐 기다림)."""
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        try:
            os.killpg(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.05)
    raise AssertionError(f"process group {pid} still alive")


class FakeDriver:
    """호출 인자를 기록하고 결정적 PNG 바이트와 지표를 돌려주는 가짜 BrowserDriver."""

    def __init__(self, heights=None, metrics=None, errors=(), delay=None, tile_size=None, ready=None):
        self.heights = heights or {"desktop": 3200, "mobile": 4000}
        self.metrics = metrics or {}
        self.errors = set(errors)
        self.delay = delay or {}
        self.tile_size = tile_size or {}
        self.ready = ready
        self.calls: list[tuple] = []
        self._now = "desktop"

    async def connect(self, port):
        self.calls.append(("connect",))
        deadline = time.monotonic() + 3
        while self.ready and not (self.ready.exists() and self.ready.read_text()):
            assert time.monotonic() < deadline, "fake browser never started"
            await asyncio.sleep(0.02)
        return "FakeChrome", "1.0"

    async def block_network(self, patterns):
        self.calls.append(("block", list(patterns)))

    async def disable_scripts(self):
        self.calls.append(("scripts_off",))

    async def isolate(self, url, body):
        self.calls.append(("isolate", url, body))

    async def open(self, url, width, height, mobile):
        self.calls.append(("open", url, width, height, mobile))
        self._now = "mobile" if mobile else "desktop"
        if self._now in self.delay:
            await asyncio.sleep(self.delay[self._now])
        if self._now in self.errors:
            raise RuntimeError("boom")
        scroll_w, client_w = self.metrics.get(self._now, (width, width))
        return {"scroll_width": scroll_w, "client_width": client_w, "scroll_height": self.heights[self._now]}

    async def capture_tile(self, width, y, height):
        self.calls.append(("tile", width, y, height))
        body = _PNG_MAGIC + f"{self._now}:{y}:{height}".encode()
        # 크기 지정은 둘째 타일부터 적용한다 — 앞 타일이 이미 디스크에 쓰인 뒤의 정리를 보기 위해서다
        return body.ljust(self.tile_size.get(self._now, 0) if y > 0 else 0, b"\0")

    async def close(self):
        self.calls.append(("close",))


@pytest.fixture
def job(tmp_path):
    job_dir = tmp_path / "job"
    (job_dir / "draft").mkdir(parents=True)
    (job_dir / "draft" / "report.html").write_text(_REPORT_HTML)
    (job_dir / "draft" / "report-input.json").write_text('{"input": 1}')
    return job_dir


@pytest.fixture
def browser(tmp_path):
    """AI_REPORT_GOOSE_BROWSER로 지정할 가짜 브라우저 실행 파일."""
    runlog = tmp_path / "runlog.txt"
    exe = _make_exe(tmp_path / "bin" / "fake-browser", "A", runlog)
    environ = {gs.ENV_BROWSER: str(exe), "PATH": os.environ["PATH"]}
    yield SimpleNamespace(exe=exe, runlog=runlog, environ=environ)
    for fields in _runlog_lines(runlog):  # 시험이 실패해도 잔류 프로세스를 남기지 않는다
        try:
            os.killpg(int(fields[0]), signal.SIGKILL)
        except (ProcessLookupError, ValueError):
            pass


async def _capture(job_dir, environ, driver, cap=20):
    return await asyncio.wait_for(
        gs.capture(job_dir, environ=environ, driver_factory=lambda: driver), cap
    )


def _argv(browser) -> list[str]:
    return Path(f"{browser.exe}.argv").read_text().splitlines()


def _child_env(browser) -> dict[str, str]:
    lines = Path(f"{browser.exe}.env").read_text().splitlines()
    return dict(line.split("=", 1) for line in lines if "=" in line)


def _profile(browser) -> Path:
    return Path(next(a for a in _argv(browser) if a.startswith("--user-data-dir=")).split("=", 1)[1])


def _viewport(index, name):
    return next(v for v in index["viewports"] if v["name"] == name)


# ─────────────────────────────────────────────────────────────────────────────
# AC-AIR6-006 — 캡처 대상·뷰포트·타일
# ─────────────────────────────────────────────────────────────────────────────


async def test_air6_006_target_viewports_and_tiles(job, browser):
    driver = FakeDriver(heights={"desktop": 3200, "mobile": 4000}, ready=browser.runlog)
    index = await _capture(job, browser.environ, driver)

    url = (job / "draft" / "report.html").resolve().as_uri()
    opens = [c for c in driver.calls if c[0] == "open"]
    assert [(c[1], c[2], c[4]) for c in opens] == [(url, 1280, False), (url, 390, True)]
    assert driver.calls.index(("scripts_off",)) < driver.calls.index(opens[0])
    desktop, mobile = _viewport(index, "desktop"), _viewport(index, "mobile")
    assert [t["height"] for t in desktop["tiles"]] == [1568, 1568, 64]
    assert [t["height"] for t in mobile["tiles"]] == [1568, 1568, 864]
    assert [t["y"] for t in desktop["tiles"]] == [0, 1568, 3136]
    assert [t["y"] for t in mobile["tiles"]] == [0, 1568, 3136]
    assert [c[1] for c in driver.calls if c[0] == "tile"] == [1280] * 3 + [390] * 3
    expected = {f"{v}-{n:02d}.png" for v in ("desktop", "mobile") for n in (1, 2, 3)}
    assert {p.name for p in (job / "screens").iterdir()} == expected | {"index.json"}
    assert [t["file"] for t in desktop["tiles"]] == [f"desktop-0{n}.png" for n in (1, 2, 3)]


async def test_air6_006_symlinked_draft_is_refused(job, browser, tmp_path):
    outside = tmp_path / "outside.html"
    outside.write_text("<html>secret</html>")
    (job / "draft" / "report.html").unlink()
    (job / "draft" / "report.html").symlink_to(outside)
    driver = FakeDriver(ready=browser.runlog)
    index = await _capture(job, browser.environ, driver)

    assert driver.calls == []
    assert not browser.runlog.exists()  # 브라우저도 띄우지 않는다
    assert index["outcome"] == "failed"
    assert {v["error"] for v in index["viewports"]} == {"draft_not_regular_file"}
    assert [p.name for p in (job / "screens").iterdir()] == ["index.json"]


async def test_air6_006_draft_resolving_outside_job_is_refused(job, browser, tmp_path):
    real = tmp_path / "elsewhere"
    real.mkdir()
    (real / "report.html").write_text("<html></html>")
    (job / "draft").rename(tmp_path / "moved")
    (job / "draft").symlink_to(real)  # 폴더 심볼릭 링크: 파일 자체는 링크가 아니다
    driver = FakeDriver(ready=browser.runlog)
    index = await _capture(job, browser.environ, driver)

    assert driver.calls == []
    assert {v["error"] for v in index["viewports"]} == {"draft_outside_job_dir"}


# ─────────────────────────────────────────────────────────────────────────────
# AC-AIR6-007 — screens/index.json
# ─────────────────────────────────────────────────────────────────────────────

_TOP = {"schema_version", "source", "preview_sha256", "started_at", "finished_at", "outcome", "browser", "viewports"}
_VP = {"name", "width", "status", "error", "metrics", "tiles"}
_METRICS = {"scroll_width", "client_width", "scroll_height", "horizontal_overflow"}
_TILE = {"file", "y", "width", "height", "bytes", "sha256"}


def _assert_schema(index):
    assert set(index) == _TOP
    assert set(index["browser"]) == {"name", "version", "path_kind"}
    for vp in index["viewports"]:
        assert set(vp) == _VP
        assert set(vp["metrics"]) == _METRICS
        for tile in vp["tiles"]:
            assert set(tile) == _TILE
    assert _KST_STAMP.match(index["started_at"]) and _KST_STAMP.match(index["finished_at"])


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


async def test_air6_007_complete_index_matches_disk(job, browser):
    driver = FakeDriver(ready=browser.runlog)
    index = await _capture(job, browser.environ, driver)

    _assert_schema(index)
    assert json.loads((job / "screens" / "index.json").read_text()) == index
    assert index["outcome"] == "complete"
    assert index["preview_sha256"] == _sha((job / "draft" / "report.html").read_bytes())
    assert index["source"] == "draft/report.html"
    assert index["browser"] == {"name": "FakeChrome", "version": "1.0", "path_kind": "env"}
    for vp in index["viewports"]:
        assert vp["status"] == "ok" and vp["error"] is None
        for tile in vp["tiles"]:
            data = (job / "screens" / tile["file"]).read_bytes()
            assert (tile["bytes"], tile["sha256"]) == (len(data), _sha(data))
    assert _viewport(index, "desktop")["metrics"] == {
        "scroll_width": 1280, "client_width": 1280, "scroll_height": 3200, "horizontal_overflow": False}


@pytest.mark.parametrize(
    ("errors", "outcome", "statuses"),
    [
        (("mobile",), "partial", ["ok", "error"]),
        (("desktop", "mobile"), "failed", ["error", "error"]),
    ],
)
async def test_air6_007_outcome_by_viewport_status(job, browser, errors, outcome, statuses):
    index = await _capture(job, browser.environ, FakeDriver(errors=errors, ready=browser.runlog))

    _assert_schema(index)
    assert index["outcome"] == outcome
    assert [v["status"] for v in index["viewports"]] == statuses
    for vp in index["viewports"]:
        if vp["status"] == "error":
            assert vp["error"] == "RuntimeError" and vp["tiles"] == []


async def test_air6_007_no_browser_is_unavailable(job, tmp_path, monkeypatch):
    monkeypatch.setattr(gs, "PLAYWRIGHT_CACHE_ROOTS", (tmp_path / "empty-cache",))
    driver = FakeDriver()
    index = await _capture(job, {}, driver)

    _assert_schema(index)
    assert index["outcome"] == "unavailable" and driver.calls == []
    assert index["browser"] == {"name": None, "version": None, "path_kind": "none"}
    assert {v["error"] for v in index["viewports"]} == {"browser_not_found"}


@pytest.mark.parametrize(("scroll_w", "overflow"), [(390, False), (391, True)])
async def test_air6_007_horizontal_overflow_is_strictly_greater(job, browser, scroll_w, overflow):
    driver = FakeDriver(metrics={"mobile": (scroll_w, 390)}, ready=browser.runlog)
    index = await _capture(job, browser.environ, driver)
    assert _viewport(index, "mobile")["metrics"]["horizontal_overflow"] is overflow
    assert _viewport(index, "desktop")["metrics"]["horizontal_overflow"] is False


async def test_air6_007_tile_hash_is_computed_from_disk(job, browser, monkeypatch):
    """쓰기 뒤 파일이 메모리 사본과 달라지는 상황(마지막 바이트 유실)에서도 색인은 디스크 값을 적는다."""
    real = Path.write_bytes
    monkeypatch.setattr(Path, "write_bytes", lambda self, data: real(self, data[:-1]))
    index = await _capture(job, browser.environ, FakeDriver(ready=browser.runlog))

    tile = _viewport(index, "desktop")["tiles"][0]
    on_disk = (job / "screens" / tile["file"]).read_bytes()
    assert on_disk.startswith(_PNG_MAGIC) and (tile["bytes"], tile["sha256"]) == (len(on_disk), _sha(on_disk))


async def test_air6_007_preview_hash_is_of_draft_not_input(job, browser):
    index = await _capture(job, browser.environ, FakeDriver(ready=browser.runlog))
    assert index["preview_sha256"] != _sha((job / "draft" / "report-input.json").read_bytes())


# ─────────────────────────────────────────────────────────────────────────────
# AC-AIR6-008 — 한도와 정리
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("height", "status", "tiles"),
    [
        (gs.TILE_CAP * gs.TILE_HEIGHT, "ok", gs.TILE_CAP),
        (gs.TILE_CAP * gs.TILE_HEIGHT + 1, "too_tall", 0),
        (100000, "too_tall", 0),
    ],
)
async def test_air6_008_tile_cap_boundary(job, browser, height, status, tiles):
    driver = FakeDriver(heights={"desktop": 3200, "mobile": height}, ready=browser.runlog)
    index = await _capture(job, browser.environ, driver)

    mobile = _viewport(index, "mobile")
    assert (mobile["status"], len(mobile["tiles"])) == (status, tiles)
    assert len(list((job / "screens").glob("mobile-*.png"))) == tiles  # 일부만 저장하지 않는다
    assert _viewport(index, "desktop")["status"] == "ok"
    assert index["outcome"] == ("complete" if status == "ok" else "partial")
    if status == "too_tall":
        assert mobile["error"] is None and mobile["metrics"]["scroll_height"] == height


async def test_air6_008_tile_over_size_limit_fails_viewport(job, browser):
    driver = FakeDriver(tile_size={"mobile": gs.MAX_TILE_BYTES + 1}, ready=browser.runlog)
    index = await _capture(job, browser.environ, driver)

    mobile = _viewport(index, "mobile")
    assert (mobile["status"], mobile["error"], mobile["tiles"]) == ("error", "tile_too_large", [])
    assert list((job / "screens").glob("mobile-*.png")) == []  # 첫 타일은 이미 썼지만 부분 출력은 정리된다
    assert _viewport(index, "desktop")["status"] == "ok"


async def test_air6_008_tile_at_size_limit_is_accepted(job, browser):
    driver = FakeDriver(tile_size={"mobile": gs.MAX_TILE_BYTES}, ready=browser.runlog)
    index = await _capture(job, browser.environ, driver)
    assert _viewport(index, "mobile")["status"] == "ok"


@pytest.mark.parametrize(
    ("slow", "statuses", "outcome"),
    [("desktop", ["error", "skipped"], "failed"), ("mobile", ["ok", "error"], "partial")],
)
async def test_air6_008_budget_exceeded(job, browser, monkeypatch, slow, statuses, outcome):
    monkeypatch.setattr(gs, "CAPTURE_BUDGET_SEC", 0.5)
    driver = FakeDriver(delay={slow: 30}, ready=browser.runlog)
    started = time.monotonic()
    index = await _capture(job, browser.environ, driver, cap=10)

    assert time.monotonic() - started < 5
    assert [v["status"] for v in index["viewports"]] == statuses
    assert index["outcome"] == outcome
    slow_vp = _viewport(index, slow)
    assert (slow_vp["error"], slow_vp["tiles"]) == ("budget_exceeded", [])
    pid = int(_runlog_lines(browser.runlog)[0][0])
    _assert_group_gone(pid)
    assert not _profile(browser).exists()


@pytest.mark.parametrize("scenario", ["ok", "viewport_error", "too_tall"])
async def test_air6_008_group_and_profile_cleaned_on_every_path(job, browser, scenario):
    kwargs = {
        "ok": {},
        "viewport_error": {"errors": ("desktop", "mobile")},
        "too_tall": {"heights": {"desktop": 3200, "mobile": 100000}},
    }[scenario]
    await _capture(job, browser.environ, FakeDriver(ready=browser.runlog, **kwargs))

    _assert_group_gone(int(_runlog_lines(browser.runlog)[0][0]))
    assert not _profile(browser).exists()


async def test_air6_008_driver_start_failure_is_recorded_and_cleaned(job, browser):
    class Broken(FakeDriver):
        async def connect(self, port):
            await super().connect(port)
            raise OSError("no devtools")

    index = await _capture(job, browser.environ, Broken(ready=browser.runlog))

    assert index["outcome"] == "failed"
    assert {v["error"] for v in index["viewports"]} == {"browser_start_failed:OSError"}
    _assert_group_gone(int(_runlog_lines(browser.runlog)[0][0]))
    assert not _profile(browser).exists()


async def test_air6_008_unlaunchable_browser_is_failed(job, tmp_path):
    bad = tmp_path / "bin" / "not-an-executable-format"
    bad.parent.mkdir()
    bad.write_bytes(b"\x00\x01\x02")
    bad.chmod(0o755)
    index = await _capture(job, {gs.ENV_BROWSER: str(bad)}, FakeDriver())
    assert index["outcome"] == "failed"
    assert {v["error"] for v in index["viewports"]} == {"browser_start_failed:OSError"}


# AC-AIR6-002 (캡처 모듈 몫): 취소하면 브라우저 프로세스 그룹과 임시 프로필이 남지 않는다
async def test_air6_002_cancel_kills_browser_group_and_profile(job, browser):
    driver = FakeDriver(delay={"desktop": 60}, ready=browser.runlog)
    task = asyncio.create_task(gs.capture(job, environ=browser.environ, driver_factory=lambda: driver))
    for _ in range(100):  # 첫 open(=브라우저 기동·연결 끝)까지 기다린다
        if any(c[0] == "open" for c in driver.calls):
            break
        await asyncio.sleep(0.02)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(task, 5)

    _assert_group_gone(int(_runlog_lines(browser.runlog)[0][0]))
    assert not _profile(browser).exists()
    assert ("close",) in driver.calls
    index = json.loads((job / "screens" / "index.json").read_text())
    assert _viewport(index, "desktop")["error"] == "cancelled"


# ─────────────────────────────────────────────────────────────────────────────
# AC-AIR6-009 — 격리
# ─────────────────────────────────────────────────────────────────────────────


async def test_air6_009_argv_only_fixed_strings_and_server_values(job, browser):
    driver = FakeDriver(ready=browser.runlog)
    await _capture(job, browser.environ, driver)

    safety_net = {"--proxy-server=127.0.0.1:1", "--proxy-bypass-list=<-loopback>", "--host-resolver-rules=MAP * ~NOTFOUND"}
    fixed = {"--headless", "--disable-gpu", "--hide-scrollbars", "about:blank"} | safety_net
    argv = _argv(browser)
    assert safety_net <= set(argv)  # 셋 중 하나라도 빠지면 실패(v0.3.4, 층 A2)
    for arg in argv:
        assert (
            arg in fixed
            or re.fullmatch(r"--remote-debugging-port=\d+", arg)
            or re.fullmatch(r"--user-data-dir=.*goose-shot-[^/]+", arg)
        ), arg
    for hostile in _HOSTILE:
        assert not any(hostile in arg for arg in argv)
        assert hostile not in repr(driver.calls[:3])
    assert "--remote-debugging-address=0.0.0.0" not in argv
    assert all(not a.startswith("--remote-debugging-address") or a.endswith("=127.0.0.1") for a in argv)


async def test_air6_009_scripts_off_and_all_network_blocked(job, browser):
    driver = FakeDriver(ready=browser.runlog)
    await _capture(job, browser.environ, driver)

    assert ("block", ["*"]) in driver.calls and [c for c in driver.calls if c[0] == "block"] == [("block", ["*"])]
    first_open = next(i for i, c in enumerate(driver.calls) if c[0] == "open")
    assert driver.calls.index(("scripts_off",)) < first_open
    assert driver.calls.index(("block", ["*"])) < first_open
    text = repr([c for c in driver.calls if c[0] != "isolate"])  # isolate는 초안 바이트를 받는다(초안 안의 링크는 차단 대상)
    assert "cdn.jsdelivr.net" not in text and "fonts.googleapis.com" not in text


async def test_air6_009_isolation_is_applied_before_first_open_with_the_hashed_draft_bytes(job, browser):
    driver = FakeDriver(ready=browser.runlog)
    index = await _capture(job, browser.environ, driver)

    draft = job / "draft" / "report.html"
    isolate = [c for c in driver.calls if c[0] == "isolate"]
    assert isolate == [("isolate", draft.resolve().as_uri(), draft.read_bytes())]  # 정확히 한 번, 디스크 바이트 그대로
    assert driver.calls.index(isolate[0]) < next(i for i, c in enumerate(driver.calls) if c[0] == "open")
    assert index["preview_sha256"] == _sha(isolate[0][2])  # 해시한 바이트 == 렌더에 쓸 바이트


async def test_air6_009_isolation_failure_closes_both_viewports_without_open(job, browser):
    class NoIsolation(FakeDriver):
        async def isolate(self, url, body):
            raise RuntimeError("fetch.enable refused")

    driver = NoIsolation(ready=browser.runlog)
    index = await _capture(job, browser.environ, driver)

    assert not any(c[0] in ("open", "tile") for c in driver.calls)
    assert index["outcome"] == "failed"
    for vp in index["viewports"]:
        assert vp["status"] == "error" and vp["tiles"] == []
        assert vp["error"].startswith("browser_start_failed:")
    _assert_group_gone(int(_runlog_lines(browser.runlog)[0][0]))


async def test_air6_009_child_env_is_an_allowlist_without_server_secrets(job, browser, monkeypatch):
    monkeypatch.setenv("SPEC_SENTINEL_SECRET", "canary")  # 서버 프로세스 환경에만 있는 표지
    environ = {**browser.environ, "SPEC_SENTINEL_SECRET": "canary", "HOME": "/home/server-user", "OPENAI_API_KEY": "k"}
    await _capture(job, environ, FakeDriver(ready=browser.runlog))

    child = _child_env(browser)
    assert "SPEC_SENTINEL_SECRET" not in child and "OPENAI_API_KEY" not in child
    assert gs.ENV_BROWSER not in child
    assert set(child) - {"PWD", "SHLVL", "_", "OLDPWD"} <= set(ENV_ALLOWLIST)  # 셸이 더하는 변수만 예외
    assert child["HOME"] == "/home/server-user" and child["PATH"] == environ["PATH"]  # 목록 변수는 부모 값 그대로


async def test_air6_009_tile_names_are_server_generated(job, browser):
    await _capture(job, browser.environ, FakeDriver(ready=browser.runlog))
    names = " ".join(p.name for p in (job / "screens").iterdir())
    assert not any(h in names for h in _HOSTILE)


# CdpDriver 자체: 가짜 전송로로 DevTools 호출 형태만 확인한다(실제 브라우저 구동은 증거 폴더 수동 실행)
class FakeWs:
    def __init__(self, fail=(), nav_error=None):
        self.sent: list[dict] = []
        self.queue: asyncio.Queue = asyncio.Queue()
        self.fail, self.nav_error, self.closed = set(fail), nav_error, False

    async def send(self, raw):
        msg = json.loads(raw)
        self.sent.append(msg)
        method = msg["method"]
        if method in self.fail:
            await self.queue.put(json.dumps({"id": msg["id"], "error": {"message": "x"}}))
            return
        result = {
            "Browser.getVersion": {"product": "HeadlessChrome/153.0.1"},
            "Page.navigate": {"errorText": self.nav_error} if self.nav_error else {},
            "Runtime.evaluate": {"result": {"value": json.dumps({"sw": 390, "cw": 390, "sh": 4000})}},
            "Page.captureScreenshot": {"data": base64.b64encode(b"PNGDATA").decode()},
        }.get(method, {})
        await self.queue.put(json.dumps({"method": "Noise.event"}))
        await self.queue.put(json.dumps({"id": msg["id"], "result": result}))
        if method == "Page.navigate":
            await self.queue.put(json.dumps({"method": "Page.loadEventFired"}))

    async def recv(self):
        return await self.queue.get()

    async def close(self):
        self.closed = True


def _cdp(ws):
    class Driver(gs.CdpDriver):
        async def _open_transport(self, port):
            return ws

    return Driver()


async def test_air6_009_cdp_driver_calls_block_all_and_disable_scripts():
    ws = FakeWs()
    driver = _cdp(ws)
    assert await driver.connect(9) == ("HeadlessChrome", "153.0.1")
    await driver.block_network(["*"])
    await driver.disable_scripts()
    sent = {m["method"]: m["params"] for m in ws.sent}
    assert sent["Network.setBlockedURLs"] == {"urls": ["*"]}
    assert sent["Emulation.setScriptExecutionDisabled"] == {"value": True}
    await driver.close()
    assert ws.closed


async def test_air6_006_cdp_driver_open_and_clip_tile():
    ws = FakeWs()
    driver = _cdp(ws)
    await driver.connect(9)
    metrics = await asyncio.wait_for(driver.open("file:///x/report.html", 390, 844, True), 5)
    assert metrics == {"scroll_width": 390, "client_width": 390, "scroll_height": 4000}
    assert await driver.capture_tile(390, 1568, 1568) == b"PNGDATA"
    by_method = {m["method"]: m["params"] for m in ws.sent}
    assert by_method["Emulation.setDeviceMetricsOverride"] == {
        "width": 390, "height": 844, "deviceScaleFactor": 1, "mobile": True}
    assert by_method["Page.navigate"] == {"url": "file:///x/report.html"}
    shot = by_method["Page.captureScreenshot"]
    assert shot["clip"] == {"x": 0, "y": 1568, "width": 390, "height": 1568, "scale": 1}
    assert shot["captureBeyondViewport"] is True and shot["format"] == "png"


async def test_air6_006_cdp_driver_reports_protocol_errors():
    driver = _cdp(FakeWs(fail={"Network.enable"}))
    with pytest.raises(gs.CaptureError, match="cdp_error:Network.enable"):
        await driver.connect(9)
    driver = _cdp(FakeWs(nav_error="net::ERR_FILE_NOT_FOUND"))
    await driver.connect(9)
    with pytest.raises(gs.CaptureError, match="navigate_failed"):
        await driver.open("file:///nope", 1280, 800, False)


# ─────────────────────────────────────────────────────────────────────────────
# AC-AIR6-010 — 브라우저 탐색
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def world(tmp_path, monkeypatch):
    """env 후보 A(실행 가능)·B(실행 불가), 캐시 빌드 9·12, PATH의 D·E 가짜 브라우저."""
    runlog = tmp_path / "runlog.txt"
    cache = tmp_path / "ms-playwright"
    monkeypatch.setattr(gs, "PLAYWRIGHT_CACHE_ROOTS", (cache,))
    path_dir = tmp_path / "pathbin"
    for name in ("chromium", "google-chrome", "Google Chrome"):
        _make_exe(path_dir / name, "D", runlog)
    return SimpleNamespace(
        runlog=runlog,
        cache=cache,
        a=_make_exe(tmp_path / "A" / "browser", "A", runlog),
        b=_make_exe(tmp_path / "B" / "browser", "B", runlog, executable=False),
        path_dir=path_dir,
        build=lambda n: _make_exe(cache / f"chromium_headless_shell-{n}" / "plat" / "chrome-headless-shell", f"build{n}", runlog),
    )


async def _run_with(job, world, environ):
    driver = FakeDriver(ready=world.runlog)
    index = await _capture(job, environ, driver)
    ran = [fields[1] for fields in _runlog_lines(world.runlog)]
    for fields in _runlog_lines(world.runlog):
        try:
            os.killpg(int(fields[0]), signal.SIGKILL)
        except ProcessLookupError:
            pass
    return index, ran


async def test_air6_010_env_variable_has_precedence(job, world):
    world.build(9), world.build(12)
    index, ran = await _run_with(job, world, {gs.ENV_BROWSER: str(world.a)})
    assert ran == ["A"] and index["browser"]["path_kind"] == "env"


async def test_air6_010_bad_env_variable_does_not_fall_back(job, world, tmp_path):
    world.build(12)
    index, ran = await _run_with(job, world, {gs.ENV_BROWSER: str(world.b)})
    assert ran == [] and index["outcome"] == "unavailable"
    assert {v["error"] for v in index["viewports"]} == {"browser_env_not_executable"}
    assert str(tmp_path) not in json.dumps(index)


async def test_air6_010_highest_numeric_build_in_playwright_cache(job, world):
    world.build(9), world.build(12)
    index, ran = await _run_with(job, world, {})
    assert ran == ["build12"] and index["browser"]["path_kind"] == "playwright_cache"


async def test_air6_010_path_and_chrome_app_are_not_searched(job, world, tmp_path):
    index, ran = await _run_with(job, world, {"PATH": str(world.path_dir)})
    assert ran == [] and index["outcome"] == "unavailable"
    assert {v["error"] for v in index["viewports"]} == {"browser_not_found"}
    assert str(tmp_path) not in json.dumps(index)


# ─────────────────────────────────────────────────────────────────────────────
# AC-AIR6-009 (3)(4) — 요청 차단 핸들러 계약 (가짜 DevTools 전송, 브라우저 없음)
# ─────────────────────────────────────────────────────────────────────────────

_CSP_DIRECTIVES = ("default-src 'none'", "frame-src 'none'", "object-src 'none'")
_ANSWERS = ("Fetch.continueRequest", "Fetch.fulfillRequest", "Fetch.failRequest")
_PIXEL = "data:image/png;base64,iVBORw0KGgo="


class DevtoolsWs:
    """보낸 명령을 (방법·세션·순서)로 기록하고, Page.navigate마다 스크립트된 이벤트를 load 이벤트 앞에 주입한다."""

    def __init__(self, events=None, fail=()):
        self.sent: list[dict] = []
        self.queue: asyncio.Queue = asyncio.Queue()
        self.events = events or (lambda nav: [])
        self.fail = set(fail)  # (방법, 세션 ID 또는 None)
        self.navs = 0
        self.closed = False

    async def send(self, raw):
        msg = json.loads(raw)
        self.sent.append(msg)
        reply = {"id": msg["id"]}
        if msg.get("sessionId"):
            reply["sessionId"] = msg["sessionId"]
        if (msg["method"], msg.get("sessionId")) in self.fail:
            reply["error"] = {"message": "refused"}
        else:
            reply["result"] = {
                "Browser.getVersion": {"product": "HeadlessChrome/153.0.1"},
                "Runtime.evaluate": {"result": {"value": json.dumps({"sw": 390, "cw": 390, "sh": 1000})}},
                "Page.captureScreenshot": {"data": base64.b64encode(b"PNGDATA").decode()},
            }.get(msg["method"], {})
        await self.queue.put(json.dumps(reply))
        if msg["method"] == "Page.navigate":
            self.navs += 1
            for event in self.events(self.navs):
                await self.queue.put(json.dumps(event))
            await self.queue.put(json.dumps({"method": "Page.loadEventFired", "params": {}}))

    async def recv(self):
        return await self.queue.get()

    async def close(self):
        self.closed = True

    def methods(self, session=None):
        return [m["method"] for m in self.sent if m.get("sessionId") == session]

    def answers(self):
        """requestId → [(방법, 세션, 매개변수)]. 일시 정지 요청 하나에 응답이 정확히 하나여야 한다."""
        out: dict[str, list] = {}
        for m in self.sent:
            if m["method"] in _ANSWERS:
                out.setdefault(m["params"]["requestId"], []).append((m["method"], m.get("sessionId"), m["params"]))
        return out


def _attached(session_id, parent=None):
    event = {"method": "Target.attachedToTarget",
             "params": {"sessionId": session_id, "waitingForDebugger": True,
                        "targetInfo": {"targetId": f"T-{session_id}", "type": "iframe", "url": ""}}}
    if parent:
        event["sessionId"] = parent
    return event


def _paused(request_id, url, session=None):
    event = {"method": "Fetch.requestPaused",
             "params": {"requestId": request_id, "request": {"url": url, "method": "GET"},
                        "frameId": "F", "resourceType": "Document"}}
    if session:
        event["sessionId"] = session
    return event


def _contract_urls(draft_url):
    """(이름, 주입 URL, 기대 응답 방법) — acceptance AC-AIR6-009 (3) 표."""
    path = draft_url.removeprefix("file://")
    return [
        ("draft", draft_url, "Fetch.fulfillRequest"),
        ("data-png", _PIXEL, "Fetch.continueRequest"),
        ("etc-hosts", "file:///etc/hosts", "Fetch.failRequest"),
        ("secret-shaped", "file:///Users/someone/.ssh/id_rsa", "Fetch.failRequest"),
        ("localhost-form", "file://localhost" + path, "Fetch.failRequest"),
        ("fragment", draft_url + "#x", "Fetch.failRequest"),
        ("query", draft_url + "?x=1", "Fetch.failRequest"),
        ("case", draft_url.replace("report.html", "Report.html"), "Fetch.failRequest"),
        ("bak", draft_url + ".bak", "Fetch.failRequest"),
        ("http-loopback", "http://127.0.0.1:9/iframe", "Fetch.failRequest"),
        ("https", "https://example.com/a.css", "Fetch.failRequest"),
        ("ws", "ws://127.0.0.1:1/", "Fetch.failRequest"),
        ("ftp", "ftp://example.com/", "Fetch.failRequest"),
        ("blob", "blob:null/0f0f", "Fetch.failRequest"),
        ("about-blank", "about:blank", "Fetch.failRequest"),
    ]


async def _capture_over_ws(job, browser, ws):
    class Driver(gs.CdpDriver):
        async def _open_transport(self, port):
            deadline = time.monotonic() + 3  # 가짜 브라우저가 떠서 기록을 남긴 뒤에야 연결한다(정리 확인을 위해)
            while not (browser.runlog.exists() and browser.runlog.read_text()):
                assert time.monotonic() < deadline, "fake browser never started"
                await asyncio.sleep(0.02)
            return ws

    return await asyncio.wait_for(gs.capture(job, environ=browser.environ, driver_factory=Driver), 20)


def _draft_url(job) -> str:
    return (job / "draft" / "report.html").resolve().as_uri()


async def test_air6_009_3_handler_contract_attach_order_and_per_request_answers(job, browser):
    url = _draft_url(job)
    table = _contract_urls(url)

    def events(nav):
        out = []
        if nav == 1:
            out += [_attached("S2"), _attached("S3", parent="S2")]
        for session in (None, "S2", "S3"):
            out += [_paused(f"{nav}-{name}-{session}", u, session) for name, u, _m in table]
        return out

    ws = DevtoolsWs(events)
    index = await _capture_over_ws(job, browser, ws)
    assert index["outcome"] == "complete"

    # 1. 페이지 세션: setAutoAttach·Fetch.enable이 한 번씩, 첫 Page.navigate보다 앞
    page = ws.methods(None)
    first_nav = page.index("Page.navigate")
    assert page.count("Target.setAutoAttach") == 1 and page.count("Fetch.enable") == 1
    assert page.index("Target.setAutoAttach") < first_nav and page.index("Fetch.enable") < first_nav
    by_method = {m["method"]: m["params"] for m in ws.sent if not m.get("sessionId")}
    assert by_method["Target.setAutoAttach"] == {"autoAttach": True, "waitForDebuggerOnStart": True, "flatten": True}
    assert by_method["Fetch.enable"] == {"patterns": [{"urlPattern": "*"}]}
    assert by_method["Network.setBlockedURLs"] == {"urls": ["*"]}  # 심층 방어는 그대로
    # 2. S2·S3: 두 명령이 정확히 한 번씩, runIfWaitingForDebugger는 그 둘 뒤에만
    for session in ("S2", "S3"):
        sess = ws.methods(session)
        assert sess.count("Fetch.enable") == 1 and sess.count("Target.setAutoAttach") == 1
        assert sess.count("Runtime.runIfWaitingForDebugger") == 1
        resume = sess.index("Runtime.runIfWaitingForDebugger")
        assert sess.index("Fetch.enable") < resume and sess.index("Target.setAutoAttach") < resume
    # 3·4. 요청마다 응답 정확히 하나, 대상 종류와 무관하게 같은 방식
    answers = ws.answers()
    for nav in (1, 2):
        for session in (None, "S2", "S3"):
            for name, _u, expected in table:
                got = answers[f"{nav}-{name}-{session}"]
                assert len(got) == 1, (name, session, got)
                method, sent_session, params = got[0]
                assert method == expected and sent_session == session, (name, session, method)
                if expected == "Fetch.fulfillRequest":
                    assert base64.b64decode(params["body"]) == (job / "draft" / "report.html").read_bytes()
                    csp = next(h["value"] for h in params["responseHeaders"] if h["name"] == "Content-Security-Policy")
                    assert all(d in csp for d in _CSP_DIRECTIVES)
                    assert params["responseCode"] == 200


async def test_air6_009_3_isolation_commands_precede_the_first_navigation(job, browser):
    """Fetch.enable보다 Page.navigate가 먼저 가면 첫 요청이 방어 없이 나간다 — 순서만 따로 한 번 더 본다."""
    ws = DevtoolsWs()
    await _capture_over_ws(job, browser, ws)
    methods = [m["method"] for m in ws.sent if not m.get("sessionId")]
    assert methods.index("Fetch.enable") < methods.index("Page.navigate")
    assert methods.index("Emulation.setScriptExecutionDisabled") < methods.index("Page.navigate")


async def test_air6_009_4_fetch_enable_error_on_page_session_closes_without_navigating(job, browser):
    ws = DevtoolsWs(fail={("Fetch.enable", None)})
    index = await _capture_over_ws(job, browser, ws)

    assert "Page.navigate" not in ws.methods(None)
    assert ws.answers() == {}
    for vp in index["viewports"]:
        assert vp["status"] == "error" and vp["tiles"] == []
    _assert_group_gone(int(_runlog_lines(browser.runlog)[0][0]))


async def test_air6_009_4_fetch_enable_error_on_attached_target_closes_the_viewport(job, browser):
    ws = DevtoolsWs(lambda nav: [_attached("S2")], fail={("Fetch.enable", "S2")})
    index = await _capture_over_ws(job, browser, ws)

    assert ws.navs == 1  # 방어가 깨진 뒤에는 두 번째 뷰포트도 열지 않는다
    for vp in index["viewports"]:
        assert vp["status"] == "error" and vp["tiles"] == []
    assert ws.answers() == {}  # 어떤 요청도 통과시키지 않았다
    assert "Runtime.runIfWaitingForDebugger" not in ws.methods("S2")  # 방어 없이 풀어 주지 않는다
    _assert_group_gone(int(_runlog_lines(browser.runlog)[0][0]))


async def test_air6_009_4_malformed_paused_event_closes_the_viewport_without_passing_anything(job, browser):
    malformed = {"method": "Fetch.requestPaused", "params": {"requestId": "r1"}}  # request 키가 없다
    ws = DevtoolsWs(lambda nav: [malformed])
    index = await _capture_over_ws(job, browser, ws)

    assert ws.navs == 1
    for vp in index["viewports"]:
        assert vp["status"] == "error" and vp["tiles"] == []
    assert ws.answers() == {}
    _assert_group_gone(int(_runlog_lines(browser.runlog)[0][0]))
