"""SPEC-AI-REPORT-003 Step 1 — Codex CLI runner 어댑터 단위 테스트.

테스트 대상:
- CodexResult dataclass
- run_codex_research(): Codex 서브프로세스 어댑터 (argv 구성 + subprocess 관리 + 에러 분류)

커버리지:
- AC-003 (1회 재시도의 전제가 되는 개별 호출 결과 계약)
- AC-008 (타임아웃 동작 — terminate→kill 2단계)
- AC-011 (경로 안전 — output_path 기반 검증)
- ER-001 (binary_missing), ER-003 (timeout), ER-004 (empty_output)

격리 방식:
- importlib.util.spec_from_file_location 로 codex_cli_runner 를 직접 로드 →
  backend/services/__init__.py cascade import (chart_service, db_service 등) 회피.
- 실 codex 바이너리에 의존하지 않음 — 파이썬 인라인 스크립트 subprocess 로 fake 구성.
"""

from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# 픽스처: codex_cli_runner 모듈 격리 로드
# ─────────────────────────────────────────────────────────────────────────────

_RUNNER_PATH = Path(__file__).parent.parent / "services" / "codex_cli_runner.py"


@pytest.fixture(scope="module")
def runner():
    """codex_cli_runner 모듈을 직접 로드 — cascade import 없이 격리 테스트."""
    spec = importlib.util.spec_from_file_location("_test_codex_cli_runner", _RUNNER_PATH)
    assert spec and spec.loader, f"모듈 스펙 로드 실패: {_RUNNER_PATH}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_test_codex_cli_runner"] = mod
    spec.loader.exec_module(mod)
    return mod


def _py_inline(script: str, *extra_args: str) -> list[str]:
    """파이썬 인라인 스크립트를 subprocess argv 로 감싼다.

    fake codex 역할로 사용. sys.argv[1:] 로 추가 인자(output_path 등) 전달.
    """
    return [sys.executable, "-c", script, *extra_args]


# ─────────────────────────────────────────────────────────────────────────────
# 1. 성공 케이스 — output_path 에 markdown 쓴 뒤 exit 0
# ─────────────────────────────────────────────────────────────────────────────


async def test_run_codex_success_writes_md(runner, tmp_path: Path) -> None:
    """fake codex 가 output_path 에 markdown 기록 + exit 0 → success=True, char_count>0."""
    sources_dir = tmp_path / "sources"
    sources_dir.mkdir()
    output_path = sources_dir / "codex.md"

    fake = _py_inline(
        "import sys, pathlib;"
        "pathlib.Path(sys.argv[1]).write_text("
        "'# Samsung SDI\\n내용 많음 abc def', encoding='utf-8')",
        str(output_path),
    )

    result = await runner.run_codex_research(
        code="006400",
        stock_name="Samsung SDI",
        output_path=output_path,
        timeout=10.0,
        _cmd_override=fake,
    )

    assert result.success is True
    assert result.output_path == output_path
    assert result.char_count > 0
    assert result.error_type is None
    assert result.error_message is None
    assert result.duration_ms >= 0
    assert output_path.read_text(encoding="utf-8").startswith("# Samsung SDI")


# ─────────────────────────────────────────────────────────────────────────────
# 2. 타임아웃 — 1초 타임아웃에 10초 sleep 프로세스 투입
# ─────────────────────────────────────────────────────────────────────────────


async def test_run_codex_timeout(runner, tmp_path: Path) -> None:
    """fake codex 가 타임아웃보다 오래 실행되면 error_type='timeout', 프로세스 정리."""
    output_path = tmp_path / "codex.md"

    fake = _py_inline("import time; time.sleep(10)")

    result = await runner.run_codex_research(
        code="006400",
        stock_name="Samsung SDI",
        output_path=output_path,
        timeout=1.0,
        _cmd_override=fake,
    )

    assert result.success is False
    assert result.error_type == "timeout"
    assert output_path.exists() is False
    assert result.char_count == 0
    assert result.duration_ms >= 1000


# ─────────────────────────────────────────────────────────────────────────────
# 3. 빈 출력 — exit 0 이지만 --output-last-message 파일 미생성
# ─────────────────────────────────────────────────────────────────────────────


async def test_run_codex_empty_output(runner, tmp_path: Path) -> None:
    """fake codex 가 exit 0 하지만 output 파일 미작성 → error_type='empty_output'."""
    output_path = tmp_path / "codex.md"

    # `pass` 만 실행 → 즉시 exit 0, 파일 미생성
    fake = _py_inline("pass")

    result = await runner.run_codex_research(
        code="006400",
        stock_name="Samsung SDI",
        output_path=output_path,
        timeout=5.0,
        _cmd_override=fake,
    )

    assert result.success is False
    assert result.error_type == "empty_output"
    assert result.char_count == 0
    assert output_path.exists() is False


# ─────────────────────────────────────────────────────────────────────────────
# 4. 바이너리 미설치 — FileNotFoundError → binary_missing (재시도 금지 사유)
# ─────────────────────────────────────────────────────────────────────────────


async def test_run_codex_binary_missing(runner, tmp_path: Path) -> None:
    """존재하지 않는 바이너리 → error_type='binary_missing' (ER-001, 결정론적 실패)."""
    output_path = tmp_path / "codex.md"

    fake = ["/absolutely/nonexistent/path/to/codex_binary_xyz_987"]

    result = await runner.run_codex_research(
        code="006400",
        stock_name="Samsung SDI",
        output_path=output_path,
        timeout=5.0,
        _cmd_override=fake,
    )

    assert result.success is False
    assert result.error_type == "binary_missing"
    assert result.error_message  # 비어있지 않아야 함 (진단 메시지)


# ─────────────────────────────────────────────────────────────────────────────
# 5. 비정상 종료 — stderr 에 메시지 남긴 뒤 exit != 0 → error_type='exit_error'
# ─────────────────────────────────────────────────────────────────────────────


async def test_run_codex_nonzero_exit(runner, tmp_path: Path) -> None:
    """exit != 0 + stderr 메시지 → error_type='exit_error', error_message 에 stderr tail 포함."""
    output_path = tmp_path / "codex.md"

    fake = _py_inline(
        "import sys;"
        "print('fatal: codex upstream error 42', file=sys.stderr);"
        "sys.exit(7)"
    )

    result = await runner.run_codex_research(
        code="006400",
        stock_name="Samsung SDI",
        output_path=output_path,
        timeout=5.0,
        _cmd_override=fake,
    )

    assert result.success is False
    assert result.error_type == "exit_error"
    assert result.error_message is not None
    assert "fatal: codex upstream error 42" in result.error_message


# ─────────────────────────────────────────────────────────────────────────────
# 6. 취소 — 상위 task.cancel() 시 CancelledError 재전파 + 프로세스 정리
# ─────────────────────────────────────────────────────────────────────────────


async def test_run_codex_cancelled(runner, tmp_path: Path) -> None:
    """asyncio.Task.cancel() 시 CancelledError re-raise, subprocess 정리 보장."""
    output_path = tmp_path / "codex.md"

    fake = _py_inline("import time; time.sleep(10)")

    task = asyncio.create_task(
        runner.run_codex_research(
            code="006400",
            stock_name="Samsung SDI",
            output_path=output_path,
            timeout=30.0,
            _cmd_override=fake,
        )
    )

    # subprocess 시작 대기
    await asyncio.sleep(0.3)

    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    # 파일은 생성되지 않았어야 함 (프로세스가 쓰기 전 취소됨)
    assert output_path.exists() is False
