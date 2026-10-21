"""SPEC-AI-REPORT-004 M3 — goose 실행기(goose_runner) 단위·통합 테스트.

테스트 대상: backend/services/goose_runner.py
- argv·cwd·프롬프트 구성(AC-AIR4-002, design §3.1·§3.2)
- 환경 변수 허용 목록(AC-AIR4-004, design §3.3)
- 시간 초과 시 프로세스 그룹 종료(AC-AIR4-005, design §3.4)
- 종료 사유 분류(AC-AIR4-006, design §4.1)
- stream-json → 진행 단계(AC-AIR4-012, design §3.5)

격리 원칙:
- 실제 `claude` 바이너리를 띄우지 않는다. tmp_path 안의 가짜 실행 스크립트만 쓴다.
- 실제 홈·실제 ~/.goose-harness를 건드리지 않는다. HOME·하네스 경로는 environ 인자로 주입한다.
- 프로세스 그룹 시험은 짧은 시간 상한으로 묶고, 끝나면 남은 PID를 SIGKILL로 정리한다.
- AC-012 기대 순서는 녹화 픽스처를 사람이 읽어 도출한 리터럴이다(plan-audit R5-8).
  테스트 실행 중에 시험 대상 파서로 기대값을 계산하지 않는다.
"""

from __future__ import annotations

import asyncio
import importlib
import json
import os
import signal
import sys
import time
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_FIXTURE = Path(__file__).parent / "fixtures" / "goose_stream_299030.jsonl"
_SETTINGS_SOURCE = _REPO_ROOT / "backend" / "goose_harness_src" / "claude-settings.json"


@pytest.fixture(scope="module")
def gr():
    """실제 모듈로 goose_runner를 불러온다.

    다른 테스트 모듈(test_ai_report_router_deep_mode)이 import 시점에 `my_chart`를
    sys.modules 스텁으로 바꿔 두므로 `my_chart*`·`backend*` 항목을 잠시 비우고 불러온 뒤
    원래대로 되돌린다(test_main_goose_lifespan과 같은 방식).
    """
    saved = {name: mod for name, mod in sys.modules.items() if _ours(name)}
    for name in saved:
        del sys.modules[name]
    try:
        yield importlib.import_module("backend.services.goose_runner")
    finally:
        # `my_chart*`·`backend*`만 되돌린다. sys.modules 전체를 되돌리면 이 픽스처 안에서 처음
        # 불러온 numpy 같은 C 확장이 빠지고, 다음 파일(test_main_goose_lifespan)이 다시 불러올 때
        # `ImportError: cannot load module more than once per process`가 난다.
        for name in [n for n in sys.modules if _ours(n)]:
            del sys.modules[name]
        sys.modules.update(saved)


def _ours(name: str) -> bool:
    return name in ("my_chart", "backend") or name.startswith(("my_chart.", "backend."))


def _base_environ(tmp_path: Path) -> dict[str, str]:
    """테스트용 부모 환경: 실제 홈 대신 tmp_path, 하네스 경로도 tmp_path 아래."""
    harness = tmp_path / "harness"
    (harness / "runs").mkdir(parents=True, exist_ok=True)
    return {
        "PATH": "/usr/bin:/bin",
        "HOME": str(tmp_path / "home"),
        "AI_REPORT_GOOSE_HARNESS_DIR": str(harness),
    }


def _fake_bin(tmp_path: Path, body: str, name: str = "fake-claude") -> Path:
    path = tmp_path / name
    path.write_text("#!/bin/bash\n" + body)
    path.chmod(0o755)
    return path


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _force_kill(pids: list[int]) -> None:
    for pid in pids:
        try:
            os.kill(pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass


async def _run(gr, tmp_path: Path, claude_bin: str, **kwargs):
    events: list = []
    environ = kwargs.pop("environ", None) or _base_environ(tmp_path)
    result = await gr.run_goose(
        job_id=kwargs.pop("job_id", "j1"),
        stock_name="하나기술",
        code="299030",
        on_event=events.append,
        environ=environ,
        claude_bin=claude_bin,
        **kwargs,
    )
    return result, events


# ─────────────────────────────────────────────────────────────────────────────
# AC-AIR4-002 — argv·cwd 구성, 설정 원본
# ─────────────────────────────────────────────────────────────────────────────


def _value_after(argv: list[str], flag: str) -> str:
    assert flag in argv, f"{flag} 없음: {argv}"
    return argv[argv.index(flag) + 1]


@pytest.mark.parametrize(
    ("model_env", "expected_model"),
    [(None, "sonnet"), ("opus", "opus")],
)
@pytest.mark.parametrize("harness_env", [None, "/tmp/h2"])
def test_ac002_argv_and_cwd(gr, tmp_path, model_env, expected_model, harness_env):
    home = tmp_path / "T"
    environ = {"PATH": "/usr/bin:/bin", "HOME": str(home)}
    if model_env is not None:
        environ["AI_REPORT_GOOSE_MODEL"] = model_env
    if harness_env is not None:
        environ["AI_REPORT_GOOSE_HARNESS_DIR"] = harness_env

    inv = gr.build_invocation("프롬프트", environ=environ)

    expected_cwd = Path(harness_env) if harness_env else home / ".goose-harness"
    assert Path(inv.cwd) == expected_cwd
    assert not Path(inv.cwd).resolve().is_relative_to(_REPO_ROOT)

    argv = inv.argv
    assert argv[0] == "claude"
    for token in ("-p", "--setting-sources", "project", "--strict-mcp-config",
                  "--output-format", "stream-json", "--permission-mode", "dontAsk",
                  "--verbose", "--no-session-persistence"):
        assert token in argv, f"{token} 없음"
    assert _value_after(argv, "-p") == "프롬프트"
    assert _value_after(argv, "--setting-sources") == "project"
    assert _value_after(argv, "--output-format") == "stream-json"
    assert _value_after(argv, "--permission-mode") == "dontAsk"
    assert _value_after(argv, "--settings") == str(expected_cwd / ".claude" / "settings.json")
    assert _value_after(argv, "--model") == expected_model

    joined = " ".join(argv)
    for forbidden in ("bypassPermissions", "--dangerously-skip-permissions", "--restricted", "--bare"):
        assert forbidden not in joined


def test_ac002_settings_source_keys():
    data = json.loads(_SETTINGS_SOURCE.read_text())
    assert data["disableAllHooks"] is True
    assert data["autoMemoryEnabled"] is False
    path_parts = data["env"]["PATH"].split(":")
    assert "/usr/bin" in path_parts
    assert "/bin" in path_parts
    # v0.4.2: 사용자 전역 ~/.claude/CLAUDE.md 제외(하네스 CLAUDE.md는 유지)
    assert "**/.claude/CLAUDE.md" in data["claudeMdExcludes"]


def test_build_prompt_follows_design_template(gr):
    from datetime import datetime, timedelta, timezone

    as_of = datetime(2026, 10, 20, 9, 30, tzinfo=timezone(timedelta(hours=9)))
    prompt = gr.build_prompt("하나기술", "299030", "j1", as_of)
    assert prompt.splitlines() == [
        "/goose 하나기술(299030) 종목을 분석해줘.",
        "기준일: 2026-10-20T09:30:00+09:00. 범위: 전체 기업 보고서(company_report).",
        "작업 디렉터리: runs/j1. 질문 없이 진행하고 가정은 runs/j1/assumptions.md에 기록하세요.",
    ]


@pytest.mark.parametrize(
    ("code", "job_id"),
    [("12AB56", "j1"), ("29903", "j1"), ("299030", "../x"), ("299030", "a/b"), ("299030", "")],
)
def test_build_prompt_rejects_unsafe_values(gr, code, job_id):
    with pytest.raises(ValueError):
        gr.build_prompt("하나기술", code, job_id)


def test_timeout_env_resolution(gr):
    assert gr.resolve_timeout({}) == 900.0
    assert gr.resolve_timeout({"AI_REPORT_GOOSE_TIMEOUT": "120"}) == 120.0
    # 잘못된 값은 기본값으로
    assert gr.resolve_timeout({"AI_REPORT_GOOSE_TIMEOUT": "abc"}) == 900.0
    assert gr.resolve_timeout({"AI_REPORT_GOOSE_TIMEOUT": "-5"}) == 900.0


async def test_ac002_subprocess_gets_cwd_and_argv(gr, tmp_path):
    """가짜 claude가 실제로 받은 cwd·argv를 기록하게 해 실행 경로 배선을 확인."""
    log = tmp_path / "invocation.txt"
    fake = _fake_bin(tmp_path, f'pwd > "{log}"\nfor a in "$@"; do echo "$a" >> "{log}"; done\nexit 0\n')
    environ = _base_environ(tmp_path)
    result, _ = await _run(gr, tmp_path, str(fake), environ=environ)
    lines = log.read_text().splitlines()
    assert Path(lines[0]).resolve() == Path(environ["AI_REPORT_GOOSE_HARNESS_DIR"]).resolve()
    assert "--strict-mcp-config" in lines
    assert lines[lines.index("--settings") + 1] == str(
        Path(environ["AI_REPORT_GOOSE_HARNESS_DIR"]) / ".claude" / "settings.json"
    )
    assert result.status == "error" and result.error_kind == "empty_output"


# ─────────────────────────────────────────────────────────────────────────────
# AC-AIR4-004 — 환경 변수 허용 목록
# ─────────────────────────────────────────────────────────────────────────────

_ALLOWED = {"PATH", "HOME", "USER", "LANG", "LC_ALL", "TZ", "TMPDIR", "SHELL"}


def test_ac004_env_allowlist(gr):
    parent = {
        "KRX_PW": "canary-4f2",
        "BRAVE_API_KEY": "canary-9a1",
        "ANTHROPIC_API_KEY": "canary-7c3",
        "PATH": "/usr/bin:/bin",
        "HOME": "/tmp/home-x",
        "NAVER_CLIENT_SECRET": "canary-n",
    }
    env = gr.build_env(parent)
    assert set(env) <= _ALLOWED
    for key in ("KRX_PW", "BRAVE_API_KEY", "ANTHROPIC_API_KEY", "NAVER_CLIENT_SECRET"):
        assert key not in env
    assert env["PATH"] == "/usr/bin:/bin"
    assert env["HOME"] == "/tmp/home-x"


def test_ac004_env_only_existing_keys(gr):
    env = gr.build_env({"PATH": "/bin", "HOME": "/h", "LANG": "ko_KR.UTF-8"})
    assert env == {"PATH": "/bin", "HOME": "/h", "LANG": "ko_KR.UTF-8"}


async def test_ac004_subprocess_env_is_allowlisted(gr, tmp_path):
    dump = tmp_path / "env.txt"
    fake = _fake_bin(tmp_path, f'/usr/bin/env > "{dump}"\nexit 0\n')
    environ = _base_environ(tmp_path) | {"KRX_PW": "canary-4f2", "ANTHROPIC_API_KEY": "canary-7c3"}
    await _run(gr, tmp_path, str(fake), environ=environ)
    keys = {line.split("=", 1)[0] for line in dump.read_text().splitlines() if "=" in line}
    # 셸이 스스로 더하는 변수(PWD·SHLVL·_)는 실행기가 넘긴 값이 아니다
    keys -= {"PWD", "SHLVL", "_", "OLDPWD"}
    assert keys <= _ALLOWED, keys
    assert "canary" not in dump.read_text()


# ─────────────────────────────────────────────────────────────────────────────
# AC-AIR4-005 — 시간 초과 시 프로세스 그룹 종료
# ─────────────────────────────────────────────────────────────────────────────


def _tree_script(tmp_path: Path, ignore_term: bool) -> tuple[Path, Path, Path]:
    leader_pid = tmp_path / "leader.pid"
    child_pid = tmp_path / "child.pid"
    trap = "trap '' TERM\n" if ignore_term else ""
    body = (
        f"{trap}"
        f'echo $$ > "{leader_pid}"\n'
        "sleep 30 &\n"
        f'echo $! > "{child_pid}"\n'
        "wait\n"
    )
    return _fake_bin(tmp_path, body), leader_pid, child_pid


@pytest.mark.parametrize("ignore_term", [False, True], ids=["sigterm", "sigkill-after-grace"])
async def test_ac005_timeout_kills_whole_group(gr, tmp_path, ignore_term):
    fake, leader_file, child_file = _tree_script(tmp_path, ignore_term)
    pids: list[int] = []
    started = time.monotonic()
    try:
        result, _ = await _run(gr, tmp_path, str(fake), timeout_sec=1.0, grace_sec=0.5)
        pids = [int(leader_file.read_text()), int(child_file.read_text())]
        assert result.status == "error"
        assert result.error_kind == "timeout"
        deadline = started + 3.0
        while any(_pid_alive(p) for p in pids) and time.monotonic() < deadline:
            await asyncio.sleep(0.05)
        alive = [p for p in pids if _pid_alive(p)]
        assert alive == [], f"3초 안에 종료되지 않은 PID: {alive}"
        assert time.monotonic() - started <= 3.0
    finally:
        if not pids and leader_file.exists() and child_file.exists():
            pids = [int(leader_file.read_text()), int(child_file.read_text())]
        _force_kill(pids)


async def test_cancel_kills_group_and_reraises(gr, tmp_path):
    """취소(서비스의 cancel·서버 종료)는 그룹을 죽이고 CancelledError를 다시 던진다."""
    fake, leader_file, child_file = _tree_script(tmp_path, ignore_term=False)
    pids: list[int] = []
    try:
        task = asyncio.create_task(_run(gr, tmp_path, str(fake), timeout_sec=30.0, grace_sec=0.5))
        for _ in range(100):
            if leader_file.exists() and child_file.exists() and child_file.read_text().strip():
                break
            await asyncio.sleep(0.05)
        pids = [int(leader_file.read_text()), int(child_file.read_text())]
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        deadline = time.monotonic() + 2.0
        while any(_pid_alive(p) for p in pids) and time.monotonic() < deadline:
            await asyncio.sleep(0.05)
        assert [p for p in pids if _pid_alive(p)] == []
    finally:
        _force_kill(pids)


async def test_leader_exit_with_orphan_holding_pipe_is_not_timeout(gr, tmp_path):
    """claude가 exit 0으로 끝났는데 손자가 stdout 파이프를 쥐고 있어도 시간 초과로 보지 않고,
    남은 손자는 그룹 종료로 정리한다."""
    child_file = tmp_path / "child.pid"
    fake = _fake_bin(
        tmp_path,
        "mkdir -p runs/j1/draft && echo '<html>' > runs/j1/draft/report.html\n"
        f'sleep 30 &\necho $! > "{child_file}"\n'
        "echo '{\"type\":\"result\"}'\nexit 0\n",
    )
    pids: list[int] = []
    started = time.monotonic()
    try:
        result, events = await _run(gr, tmp_path, str(fake), timeout_sec=20.0, grace_sec=0.5)
        pids = [int(child_file.read_text())]
        assert (result.status, result.error_kind) == ("done", None)
        assert result.exit_code == 0
        assert [e.stage for e in events] == ["session_end"]
        assert time.monotonic() - started < 10.0
        deadline = time.monotonic() + 2.0
        while _pid_alive(pids[0]) and time.monotonic() < deadline:
            await asyncio.sleep(0.05)
        assert not _pid_alive(pids[0])
    finally:
        _force_kill(pids)


async def test_terminate_group_tolerates_missing_group(gr):
    # 이미 없는 그룹: ProcessLookupError는 종료로 본다
    await gr.terminate_group(999_999_9, grace_sec=0.1)


# ─────────────────────────────────────────────────────────────────────────────
# AC-AIR4-006 — 종료 사유 분류
# ─────────────────────────────────────────────────────────────────────────────


async def test_ac006_binary_missing(gr, tmp_path):
    result, _ = await _run(gr, tmp_path, str(tmp_path / "no-such-claude"))
    assert (result.status, result.error_kind) == ("error", "binary_missing")


async def test_ac006_auth_failure(gr, tmp_path):
    fake = _fake_bin(tmp_path, "echo 'Error: not logged in · Please run /login' >&2\nexit 1\n")
    result, _ = await _run(gr, tmp_path, str(fake))
    assert (result.status, result.error_kind) == ("error", "auth")
    assert any("not logged in" in line for line in result.stderr_tail)


async def test_ac006_exit0_without_report_is_empty_output(gr, tmp_path):
    fake = _fake_bin(tmp_path, "exit 0\n")
    result, _ = await _run(gr, tmp_path, str(fake))
    assert (result.status, result.error_kind) == ("error", "empty_output")


async def test_ac006_exit7_is_exit_error(gr, tmp_path):
    fake = _fake_bin(tmp_path, "echo 'boom' >&2\nexit 7\n")
    result, _ = await _run(gr, tmp_path, str(fake))
    assert (result.status, result.error_kind) == ("error", "exit_error")
    assert result.exit_code == 7


async def test_exit0_with_draft_report_is_done_draft(gr, tmp_path):
    fake = _fake_bin(tmp_path, "mkdir -p runs/j1/draft && echo '<html>' > runs/j1/draft/report.html\nexit 0\n")
    result, _ = await _run(gr, tmp_path, str(fake))
    assert (result.status, result.error_kind) == ("done", None)
    assert result.delivery_status == "draft"
    assert result.report_dir.name == "draft"


async def test_timeout_keeps_kind_but_reports_selectable_draft(gr, tmp_path):
    """결정 T10: 시간 초과는 error/timeout 그대로, 선택 가능한 초안 정보는 함께 돌려준다."""
    fake = _fake_bin(
        tmp_path,
        "mkdir -p runs/j1/draft && echo '<html>' > runs/j1/draft/report.html\nexec sleep 30\n",
    )
    result, _ = await _run(gr, tmp_path, str(fake), timeout_sec=0.5, grace_sec=0.2)
    assert (result.status, result.error_kind) == ("error", "timeout")
    assert result.delivery_status == "draft"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_select_report_rules(gr, tmp_path):
    job = tmp_path / "job"
    assert gr.select_report(job) is None
    _write(job / "draft" / "report.html", "<d>")
    assert gr.select_report(job) == ("draft", job / "draft")
    # final 폴더가 있어도 delivery_allowed가 참이 아니면 draft
    _write(job / "final" / "report.html", "<f>")
    _write(job / "final" / "render-validation.json", '{"delivery_allowed": false}')
    assert gr.select_report(job) == ("draft", job / "draft")
    _write(job / "final" / "render-validation.json", "{broken")
    assert gr.select_report(job) == ("draft", job / "draft")
    _write(job / "final" / "render-validation.json", '{"delivery_allowed": "true"}')
    assert gr.select_report(job) == ("draft", job / "draft")
    _write(job / "final" / "render-validation.json", '{"delivery_allowed": true}')
    assert gr.select_report(job) == ("final", job / "final")


def test_select_report_ignores_symlinked_report(gr, tmp_path):
    outside = tmp_path / "outside.html"
    outside.write_text("<x>")
    job = tmp_path / "job"
    (job / "draft").mkdir(parents=True)
    (job / "draft" / "report.html").symlink_to(outside)
    assert gr.select_report(job) is None


async def test_stderr_tail_keeps_last_50_lines(gr, tmp_path):
    fake = _fake_bin(tmp_path, "for i in $(seq 1 120); do echo \"err $i\" >&2; done\nexit 3\n")
    result, _ = await _run(gr, tmp_path, str(fake))
    assert len(result.stderr_tail) == 50
    assert result.stderr_tail[0] == "err 71"
    assert result.stderr_tail[-1] == "err 120"


# ─────────────────────────────────────────────────────────────────────────────
# AC-AIR4-012 — stream-json → 진행 단계
# ─────────────────────────────────────────────────────────────────────────────

# 녹화 픽스처(196줄)를 design §3.5 표로 사람이 읽어 도출한 기대 순서(R5-8, 리터럴 고정).
# 괄호 안은 픽스처 줄 번호.
_EXPECTED_STAGES = [
    "goose_start",  # 1 system/init
    "plan", "plan", "plan", "plan", "plan", "plan",  # 4,6,8,11,13,15 Read workflows/**
    # 20 ToolSearch, 22 Bash ls → 단계 없음
    "research_tick", "research_tick", "research_tick",  # 25,26,27 WebSearch
    "fetch_start",  # 34 Agent web-fetch (35 task_started는 단계 없음)
    "research_tick",  # 38 서브에이전트 WebFetch
    "fetch_start",  # 40 Agent web-fetch
    "research_tick",  # 44 서브에이전트 WebFetch
    "research_tick",  # 45 메인 WebSearch
    "research_tick", "research_tick", "research_tick", "research_tick",  # 48,51,54,57
    "research_tick", "research_tick", "research_tick",  # 59,62,66
    "fetch_done",  # 70 task_notification
    "research_tick",  # 74
    "fetch_done",  # 78 task_notification
    "fetch_start",  # 84 Agent web-fetch
    "research_tick", "research_tick", "research_tick", "research_tick",  # 88,91,94,97
    "research_tick", "research_tick", "research_tick", "research_tick",  # 100,103,106,109
    "fetch_done",  # 112 task_notification
    # 118 Bash curl → 단계 없음, 119 permission_denied → 단계 없음
    # 125 render_report.py --help → 단계 없음
    # 177 Write assumptions.md → 단계 없음
    "compose",  # 180 Write runs/m1p4/input.json
    "render_draft",  # 183 render_report.py (--final 없음)
    # 188 Edit → 단계 없음
    "render_draft",  # 190 render_report.py (--final 없음)
    "session_end",  # 196 result
]
_EXPECTED_FETCH_DETAILS = [
    "DART 하나기술 공시 열람",
    "하나기술 실적·IR·뉴스 열람",
    "DART rcpNo 및 본문 접근 재시도",
]
_EXTRA_LINES = [
    '{"type": "brand_new_event", "payload": {"x": 1}}',
    '{"type": "assistant", "message": {"content": [',
]


def _fixture_lines() -> list[str]:
    lines = _FIXTURE.read_text().splitlines()
    assert len(lines) == 196
    # 알 수 없는 타입·깨진 JSON을 중간과 끝에 넣는다
    return lines[:50] + [_EXTRA_LINES[0]] + lines[50:150] + [_EXTRA_LINES[1]] + lines[150:]


def test_ac012_fixture_stage_sequence(gr):
    mapper = gr.StageMapper(job_id="m1p4")
    events = []
    for line in _fixture_lines():
        events.extend(mapper.feed(line))
    stages = [e.stage for e in events]
    assert stages == _EXPECTED_STAGES
    assert stages[0] == "goose_start" and stages[-1] == "session_end"
    assert stages.count("fetch_start") == 3 and stages.count("fetch_done") == 3
    assert stages.count("render_draft") >= 1
    assert "role_start" not in stages
    assert [e.detail for e in events if e.stage == "fetch_start"] == _EXPECTED_FETCH_DETAILS


def test_ac012_permission_denied_makes_no_stage(gr, caplog):
    mapper = gr.StageMapper(job_id="m1p4")
    line = json.dumps({"type": "system", "subtype": "permission_denied", "tool_name": "Bash"})
    with caplog.at_level("WARNING"):
        assert mapper.feed(line) == []
    assert any("permission_denied" in r.getMessage() for r in caplog.records)


# 라이브 결함(2026-10-20, job bb4c0b2d): permission_denied 이벤트에는 명령이 없어
# 로그만으로 거부된 명령을 알 수 없었다. 직전 assistant tool_use를 tool_use_id로 맞춰 기록한다.
def _denied_records(caplog) -> list[str]:
    return [
        r.getMessage() for r in caplog.records
        if r.levelname == "WARNING" and "permission_denied" in r.getMessage()
    ]


def test_permission_denied_logs_correlated_command_from_fixture(gr, caplog):
    """녹화 118줄(Bash curl tool_use) → 119줄(permission_denied): 거부된 명령이 로그에 남는다."""
    lines = _FIXTURE.read_text().splitlines()
    mapper = gr.StageMapper(job_id="m1p4")
    with caplog.at_level("WARNING"):
        for line in lines[:119]:
            mapper.feed(line)
    records = _denied_records(caplog)
    assert len(records) == 1
    assert "Bash" in records[0]
    assert 'curl -s -m 20 "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260814003482"' in records[0]


def test_permission_denied_command_truncated(gr, caplog):
    mapper = gr.StageMapper(job_id="m1p4")
    command = "mkdir -p runs/x/draft && " + "A" * 1000
    mapper.feed(json.dumps({
        "type": "assistant",
        "parent_tool_use_id": None,
        "message": {"content": [
            {"type": "tool_use", "id": "toolu_long", "name": "Bash", "input": {"command": command}},
        ]},
    }))
    with caplog.at_level("WARNING"):
        mapper.feed(json.dumps({
            "type": "system", "subtype": "permission_denied",
            "tool_name": "Bash", "tool_use_id": "toolu_long", "decision_reason_type": "mode",
        }))
    records = _denied_records(caplog)
    assert len(records) == 1
    assert "mkdir -p runs/x/draft" in records[0]
    assert "A" * 301 not in records[0]
    assert "A" * 250 in records[0]


def test_permission_denied_uncorrelated_still_logs_tool(gr, caplog):
    mapper = gr.StageMapper(job_id="m1p4")
    with caplog.at_level("WARNING"):
        assert mapper.feed(json.dumps({
            "type": "system", "subtype": "permission_denied",
            "tool_name": "Bash", "tool_use_id": "toolu_unknown", "decision_reason_type": "mode",
        })) == []
    records = _denied_records(caplog)
    assert len(records) == 1 and "Bash" in records[0] and "mode" in records[0]


def _tool_use(name: str, inp: dict, parent: str | None = None) -> str:
    return json.dumps({
        "type": "assistant",
        "parent_tool_use_id": parent,
        "message": {"content": [{"type": "tool_use", "name": name, "input": inp}]},
    })


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        (_tool_use("Bash", {"command": "python3 .claude/skills/goose/workflows/fact-check/scripts/audit_report.py --input x"}), ["audit"]),
        (_tool_use("Bash", {"command": "python3 .claude/skills/goose/workflows/stock-report/scripts/render_report.py --input runs/j/input.json --output-dir runs/j/final --final"}), ["render_final"]),
        (_tool_use("Bash", {"command": "python3 .claude/skills/goose/workflows/stock-report/scripts/render_report.py --help"}), []),
        (_tool_use("Write", {"file_path": "/H/runs/other/input.json", "content": "{}"}), []),
        (_tool_use("Write", {"file_path": "/H/runs/m1p4/input.json.bak", "content": "{}"}), []),
        (_tool_use("Read", {"file_path": "/H/.claude/skills/goose/SKILL.md"}), []),
        (_tool_use("Read", {"file_path": "/H/.claude/skills/goose/workflows/x.md"}, parent="toolu_sub"), []),
        (_tool_use("WebSearch", {"query": "q"}, parent="toolu_sub"), []),
        (_tool_use("WebFetch", {"url": "https://x"}), []),
        (_tool_use("Agent", {"description": "역할", "subagent_type": "general-purpose"}), []),
        (json.dumps({"type": "system", "subtype": "task_started", "description": "x"}), []),
        (json.dumps({"type": "assistant", "message": "not-a-dict"}), []),
        (json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": "str"}]}}), []),
        (json.dumps([1, 2, 3]), []),
        ("", []),
        ("null", []),
    ],
)
def test_ac012_mapping_edges(gr, line, expected):
    mapper = gr.StageMapper(job_id="m1p4")
    assert [e.stage for e in mapper.feed(line)] == expected


async def test_ac012_runner_emits_stages_from_stream(gr, tmp_path):
    """가짜 claude가 녹화를 stdout으로 내보내면 실행기가 같은 순서로 이벤트를 낸다."""
    stream = tmp_path / "stream.jsonl"
    stream.write_text("\n".join(_fixture_lines()) + "\n")
    fake = _fake_bin(tmp_path, f'cat "{stream}"\nexit 0\n')
    result, events = await _run(gr, tmp_path, str(fake), job_id="m1p4")
    assert [e.stage for e in events] == _EXPECTED_STAGES
    assert (result.status, result.error_kind) == ("error", "empty_output")


async def test_runner_accepts_async_event_callback(gr, tmp_path):
    fake = _fake_bin(tmp_path, 'echo \'{"type":"system","subtype":"init"}\'\necho \'{"type":"result"}\'\nexit 0\n')
    seen: list[str] = []

    async def on_event(event):
        await asyncio.sleep(0)
        seen.append(event.stage)

    await gr.run_goose(
        job_id="j1", stock_name="하나기술", code="299030", on_event=on_event,
        environ=_base_environ(tmp_path), claude_bin=str(fake),
    )
    assert seen == ["goose_start", "session_end"]


async def test_runner_survives_oversized_line(gr, tmp_path):
    """4MB 라인 버퍼를 넘는 줄은 버리고 계속 읽는다."""
    fake = _fake_bin(
        tmp_path,
        "head -c 5000000 /dev/zero | tr '\\0' 'a'\necho\n"
        'echo \'{"type":"result"}\'\nexit 0\n',
    )
    result, events = await _run(gr, tmp_path, str(fake))
    assert [e.stage for e in events] == ["session_end"]
    assert result.error_kind == "empty_output"


# 라이브 실행 a5becbb9(2026-10-21)에서 goose는 runs/{job_id}/company-input.json을 썼고,
# UI는 "리포트 입력 작성 — 건너뜀"을 보였다. 작업 폴더 바로 아래 *input.json은 모두 compose로 인식한다.
@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/H/runs/m1p4/company-input.json", ["compose"]),
        ("runs/m1p4/company-input.json", ["compose"]),
        ("/H/runs/m1p4/input.json", ["compose"]),
        ("runs/m1p4/input.json", ["compose"]),
        # 하위 폴더(render가 쓰는 draft/report-input.json)는 세지 않는다
        ("/H/runs/m1p4/draft/report-input.json", []),
        ("/H/runs/m1p4/draft/input.json", []),
        # 다른 작업·다른 이름·접미사가 붙은 파일은 세지 않는다
        ("/H/runs/other/company-input.json", []),
        ("/H/runs/m1p4/company-input.json.bak", []),
        ("/H/runs/m1p4/assumptions.md", []),
        ("/H/myruns/m1p4/input.json", []),
        ("/H/runs/xm1p4/input.json", []),
    ],
)
def test_compose_stage_recognizes_any_input_json_directly_under_job_dir(gr, path, expected):
    mapper = gr.StageMapper(job_id="m1p4")
    line = _tool_use("Write", {"file_path": path, "content": "{}"})
    assert [e.stage for e in mapper.feed(line)] == expected
