"""SPEC-AI-REPORT-002 Phase C: 딥 리서치 오케스트레이터.

5-소스 수집(Phase B) + Claude CLI 합성(Phase A)을 결합하여
SSE 이벤트 스트림을 생성하는 최상위 오케스트레이터.

역할:
- 소스 수집 게이트 (2/5 이상 성공 필요)
- 스테이징 디렉토리 생성 및 사후 정리
- Claude CLI 호출 및 SSE 이벤트 변환
- Rate limit (일일 쿼터 + 버스트)
- 중복 분석 차단 (ER-006)
- 리포트 영속화 (save_report)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator

from backend.services.ai_report_service import save_report
from backend.services.claude_cli_streamer import (
    DoneSignal,
    ErrorSignal,
    TextDelta,
    stream_claude_synthesis,
)
from backend.services.deep_research_collector import (
    CollectionResult,
    SourceResult,
    collect_all_sources,
    finalize_staging_directory,
    prepare_staging_directory,
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# 한국어 에러 메시지 상수
# ─────────────────────────────────────────────────────────────────────────────

_MSG_ALREADY_RUNNING = "심층 분석이 이미 진행 중입니다. 완료 후 다시 시도해 주세요."
_MSG_COLLECTION_FAILED = "수집 실패: {n}/{total} 소스만 성공하여 합성 품질을 보장할 수 없습니다."
_MSG_TIMEOUT = "합성 시간 초과. 다시 시도하거나 빠른 분석을 사용해 주세요."
_MSG_DAILY_QUOTA = "딥 리서치 일일 쿼터 초과 ({quota}회). 내일 다시 시도해 주세요."
_MSG_BURST = "딥 리서치 분당 요청 한도 초과 ({limit}회/분). {wait}초 후 다시 시도해 주세요."

# ─────────────────────────────────────────────────────────────────────────────
# 합성 프롬프트 경로
# ─────────────────────────────────────────────────────────────────────────────

_SYNTHESIS_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "stock_synthesis_prompt.md"

# ─────────────────────────────────────────────────────────────────────────────
# 모듈 레벨 가변 상태
# ─────────────────────────────────────────────────────────────────────────────

# @MX:WARN: [AUTO] 모듈 레벨 가변 상태 — 멀티 워커 uvicorn 비호환.
# @MX:REASON: uvicorn >1 워커 환경에서 워커별로 별도 카운터가 생성되어 일관성 보장 불가.
#             단일 워커 로컬 배포 전제. 멀티 워커 전환 시 Redis 기반으로 교체 필요.
_deep_daily_call_count: dict[str, int] = {}   # key: YYYY-MM-DD
_deep_recent_timestamps: list[float] = []     # 60초 롤링 윈도우
_active_deep_analyses: set[str] = set()       # 진행 중인 종목 코드 집합

# ─────────────────────────────────────────────────────────────────────────────
# 예외 클래스
# ─────────────────────────────────────────────────────────────────────────────


class AlreadyRunningError(Exception):
    """동일 종목 코드로 딥 분석이 이미 진행 중인 경우."""


class DeepRateLimitError(Exception):
    """딥 리서치 rate limit 초과 예외."""


class CollectionFailedError(Exception):
    """소스 수집 게이트 실패 (2/5 미만 성공)."""


# ─────────────────────────────────────────────────────────────────────────────
# Rate limit
# ─────────────────────────────────────────────────────────────────────────────


# @MX:ANCHOR: [AUTO] check_deep_rate_limit — fan_in >= 2 (라우터 + 테스트).
# @MX:REASON: 일일 쿼터와 버스트 제한을 독립적으로 검사. 실패 시 DeepRateLimitError를 raise하며
#             Perplexity(ai_report_service) 카운터에는 일절 영향을 주지 않는 불변 조건.
def check_deep_rate_limit(now: datetime | None = None) -> None:
    """딥 리서치 rate limit 검사. 위반 시 DeepRateLimitError 발생.

    일일 쿼터와 분당 버스트 제한을 독립 검사. 통과 시 카운터 증가.

    Args:
        now: 테스트 주입용 현재 시각. None이면 datetime.now().

    Raises:
        DeepRateLimitError: 일일 쿼터 초과 또는 분당 버스트 초과.
    """
    global _deep_daily_call_count, _deep_recent_timestamps

    daily_quota = int(os.getenv("AI_REPORT_DEEP_DAILY_QUOTA", "15"))
    burst_limit = int(os.getenv("AI_REPORT_DEEP_BURST_LIMIT", "1"))
    burst_window = 60  # 초

    _now = now or datetime.now()
    today = _now.strftime("%Y-%m-%d")

    # 일일 카운터 초기화 (날짜 키 기반)
    today_count = _deep_daily_call_count.get(today, 0)

    # 일일 쿼터 검사
    if today_count >= daily_quota:
        raise DeepRateLimitError(_MSG_DAILY_QUOTA.format(quota=daily_quota))

    # 버스트 검사: 윈도우 밖 타임스탬프 제거
    ts_now = time.time()
    cutoff = ts_now - burst_window
    # 목록 내부 수정
    _deep_recent_timestamps[:] = [t for t in _deep_recent_timestamps if t > cutoff]

    if len(_deep_recent_timestamps) >= burst_limit:
        oldest = _deep_recent_timestamps[0]
        wait_sec = int(burst_window - (ts_now - oldest))
        raise DeepRateLimitError(_MSG_BURST.format(limit=burst_limit, wait=max(wait_sec, 1)))

    # 통과: 카운터 증가
    _deep_daily_call_count[today] = today_count + 1
    _deep_recent_timestamps.append(ts_now)
    logger.info(
        "딥 rate limit 통과: daily=%d/%d, burst=%d/%d",
        _deep_daily_call_count[today],
        daily_quota,
        len(_deep_recent_timestamps),
        burst_limit,
    )


# ─────────────────────────────────────────────────────────────────────────────
# SPEC-AI-REPORT-002 v1.0.4: 진행 상태 패널용 카운트 계산
# ─────────────────────────────────────────────────────────────────────────────


def _source_count(result: SourceResult) -> int:
    """source_done phase event의 count 필드 값 계산.

    - codex: char_count (파일 문자 수)
    - brave/naver/youtube: 정규화된 리스트 길이
    - tavily: results 리스트 길이

    실패 또는 데이터 없음이면 0 반환.
    """
    if not result.success or result.data is None:
        return 0
    data = result.data
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        # tavily
        if "results" in data and isinstance(data["results"], list):
            return len(data["results"])
        # codex (SPEC-AI-REPORT-003): markdown_path + char_count 스키마
        if "char_count" in data:
            try:
                return int(data.get("char_count") or 0)
            except (TypeError, ValueError):
                return 0
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# 합성 프롬프트 로더
# ─────────────────────────────────────────────────────────────────────────────


def _load_synthesis_prompt() -> str:
    """합성 시스템 프롬프트를 파일에서 읽어 반환.

    Returns:
        합성 프롬프트 전체 내용.

    Raises:
        FileNotFoundError: 프롬프트 파일 없음.
        ValueError: 파일이 비어 있음.
    """
    if not _SYNTHESIS_PROMPT_PATH.is_file():
        raise FileNotFoundError(
            f"합성 프롬프트 파일을 찾을 수 없습니다: {_SYNTHESIS_PROMPT_PATH}"
        )
    content = _SYNTHESIS_PROMPT_PATH.read_text(encoding="utf-8").strip()
    if not content:
        raise ValueError(
            f"합성 프롬프트 파일이 비어 있습니다: {_SYNTHESIS_PROMPT_PATH}"
        )
    return content


# ─────────────────────────────────────────────────────────────────────────────
# 메인 오케스트레이터
# ─────────────────────────────────────────────────────────────────────────────


# @MX:ANCHOR: [AUTO] stream_deep_analysis — fan_in >= 2 (라우터 + 테스트).
# @MX:REASON: finally 블록 불변 조건: _active_deep_analyses에서 코드 해제 + 스테이징 디렉토리 삭제.
#             CancelledError/TimeoutError 발생 시에도 반드시 정리 수행. 이 계약이 깨지면 코드가
#             영구적으로 active 집합에 남아 중복 요청 차단이 해제되지 않음.
async def stream_deep_analysis(
    code: str,
    stock_name: str,
    *,
    model: str | None = None,
) -> AsyncGenerator[dict, None]:
    """딥 리서치 오케스트레이터: 5-소스 수집 → 스테이징 → Claude 합성 → SSE 이벤트 스트림.

    Args:
        code: 종목 코드 (예: "005930").
        stock_name: 종목명 (예: "삼성전자").
        model: "opus"이면 Claude Opus 모델 사용. None이면 기본 Sonnet.

    Yields:
        SSE 이벤트 딕셔너리:
        - {"data": str} — 텍스트 청크 (기본 이벤트)
        - {"event": "phase", "data": json-str} — 단계 진행 알림
        - {"event": "done", "data": ""} — 합성 완료
        - {"event": "error", "data": str} — 오류

    Raises:
        asyncio.CancelledError: 클라이언트 연결 끊김 (재발생).
    """
    staging_dir: Path | None = None
    full_markdown_parts: list[str] = []
    # NFR-006 관찰성: end-to-end 소요시간 측정
    import time as _time
    _t_start = _time.monotonic()
    _outcome = "unknown"

    # Phase 1: 중복 분석 차단
    if code in _active_deep_analyses:
        yield {"event": "error", "data": _MSG_ALREADY_RUNNING}
        return

    # Phase 1a: 활성 세트 등록
    _active_deep_analyses.add(code)
    logger.info(
        "딥 리서치 시작: code=%s, stock_name=%s, model=%s",
        code,
        stock_name,
        model or os.getenv("AI_REPORT_DEEP_MODEL", "sonnet"),
    )

    try:
        # Phase 2a (SPEC-AI-REPORT-003 FR-006): 스테이징 디렉토리 선행 생성.
        # Codex CLI 의 --output-last-message 가 호출 시점에 경로 존재를 요구하므로
        # collect 이전에 staging 을 prepare 해야 한다.
        yield {"event": "phase", "data": json.dumps({"phase": "staging"})}
        staging_dir = prepare_staging_directory(code)
        staging_sources_dir = staging_dir / "sources"
        yield {"event": "phase", "data": json.dumps({"phase": "staging_prepared"})}

        # Phase 2b: 소스 수집 (per-source progress).
        # collect_all_sources를 task로 실행하면서 progress_callback이 asyncio.Queue에 phase
        # 이벤트를 put → 메인 async generator는 queue를 소비해서 yield. SENTINEL이 오면 종료.
        # 기존 "collecting" 이벤트는 backward compat 용으로 유지.
        yield {"event": "phase", "data": json.dumps({"phase": "collecting"})}

        event_queue: asyncio.Queue = asyncio.Queue()
        _SENTINEL = object()

        async def _progress_cb(evt: dict) -> None:
            phase_name = evt.get("phase")
            if phase_name == "source_start":
                await event_queue.put(
                    {
                        "event": "phase",
                        "data": json.dumps(
                            {"phase": "source_start", "source": evt["source"]}
                        ),
                    }
                )
            elif phase_name == "source_done":
                src: SourceResult = evt["result"]
                payload: dict = {
                    "phase": "source_done",
                    "source": src.name,
                    "success": src.success,
                    "duration_ms": src.duration_ms,
                    "count": _source_count(src),
                    "cached": src.cached,
                }
                if not src.success:
                    payload["error"] = src.error_type or "error"
                await event_queue.put(
                    {"event": "phase", "data": json.dumps(payload)}
                )

        async def _runner() -> CollectionResult:
            try:
                return await collect_all_sources(
                    code,
                    stock_name,
                    progress_callback=_progress_cb,
                    staging_sources_dir=staging_sources_dir,
                )
            finally:
                await event_queue.put(_SENTINEL)

        collect_task: asyncio.Task[CollectionResult] = asyncio.create_task(_runner())

        while True:
            item = await event_queue.get()
            if item is _SENTINEL:
                break
            yield item

        # collect_task 결과 수령 (예외는 재발생, 정상이면 CollectionResult)
        result: CollectionResult = await collect_task

        n_success = sum(1 for s in result.sources.values() if s.success)
        total = len(result.sources)

        yield {
            "event": "phase",
            "data": json.dumps(
                {"phase": "collecting_done", "successful": n_success, "total": total}
            ),
        }

        if not result.gate_passed:
            yield {
                "event": "error",
                "data": _MSG_COLLECTION_FAILED.format(n=n_success, total=total),
            }
            return

        # Phase 2c (SPEC-AI-REPORT-003 FR-006): 스테이징 finalize — summary.md + JSON 소스 파일.
        finalize_staging_directory(staging_dir, code, stock_name, result)
        yield {"event": "phase", "data": json.dumps({"phase": "staging_done"})}

        # Phase 4: 합성 프롬프트 로드
        system_prompt = _load_synthesis_prompt()
        deep_model_env = os.getenv("AI_REPORT_DEEP_MODEL", "sonnet")
        effective_model = model if model is not None else (
            "opus" if deep_model_env == "opus" else None
        )

        # 사용자 프롬프트: 종목 식별 + 명시적 Read 지시 + 학습 데이터 의존 차단.
        # 단순 "@summary.md 먼저 읽고..."는 Claude가 종종 Read tool을 무시하고 학습 데이터로
        # 직답하는 경향이 있어, 종목 코드 + 5개 파일을 명시적으로 모두 열도록 지시한다.
        user_prompt = (
            f"종목: {stock_name}({code}) — 한국 KOSPI/KOSDAQ 상장 종목 코드 {code}.\n\n"
            "지시:\n"
            "1) 먼저 Read tool로 ./summary.md를 읽고 어떤 소스가 성공했는지 확인하라.\n"
            "2) 다음 5개 파일을 Read tool로 모두 열어라 (존재하는 파일만):\n"
            "   - sources/codex.md\n"
            "   - sources/brave.json\n"
            "   - sources/tavily.json\n"
            "   - sources/naver.json\n"
            "   - sources/youtube.json\n"
            "3) 위 파일들의 내용만 사용해 한국 스윙 트레이딩 딥 리서치 리포트를 마크다운으로 생성하라.\n"
            "4) 당신의 사전 학습 지식을 사용하지 마라. \"학습 범위 벗어남\" / \"실시간 데이터 미접근\" / "
            "\"기업 식별 불가\" 같은 면책 사유로 리포트 작성을 거부하지 마라. "
            f"종목 코드 {code}는 위 파일에서 검증할 수 있다.\n"
            "5) 시스템 프롬프트의 출력 섹션 구조를 따르라."
        )

        # 기존 "synthesizing" phase는 backward compat 용으로 유지.
        # 신규 "synthesis_start"는 모델 정보 포함 — 프론트 진행 상태 패널이 이 이벤트로 합성 단계 전환.
        yield {"event": "phase", "data": json.dumps({"phase": "synthesizing"})}
        yield {
            "event": "phase",
            "data": json.dumps(
                {
                    "phase": "synthesis_start",
                    "model": effective_model or deep_model_env or "sonnet",
                }
            ),
        }

        # Phase 4a: 스트리밍 합성 (첫 청크 도착 시 synthesis_first_chunk phase 이벤트 발행)
        first_chunk_sent = False
        try:
            async for event in stream_claude_synthesis(
                cwd=staging_dir,
                prompt=user_prompt,
                system_prompt=system_prompt,
                model=effective_model,
            ):
                if isinstance(event, TextDelta):
                    if not first_chunk_sent:
                        yield {
                            "event": "phase",
                            "data": json.dumps({"phase": "synthesis_first_chunk"}),
                        }
                        first_chunk_sent = True
                    full_markdown_parts.append(event.text)
                    yield {"data": event.text}
                elif isinstance(event, DoneSignal):
                    full_markdown = "".join(full_markdown_parts)
                    if full_markdown:
                        save_report(stock_name, full_markdown)
                    _outcome = "done"
                    yield {"event": "done", "data": ""}
                elif isinstance(event, ErrorSignal):
                    _outcome = "error"
                    yield {"event": "error", "data": event.message}
        except asyncio.TimeoutError:
            _outcome = "timeout"
            yield {"event": "error", "data": _MSG_TIMEOUT}
        except asyncio.CancelledError:
            _outcome = "cancelled"
            logger.info("딥 리서치 스트리밍 취소됨 (CancelledError): code=%s", code)
            raise  # CancelledError는 삼키지 않고 재발생
        except Exception as exc:  # noqa: BLE001
            # SPEC-AI-REPORT-002 v1.0.5: 합성 단계 미처리 예외(LimitOverrunError 등) 방어.
            # 이전에는 async generator 밖으로 예외가 전파되면서 sse_starlette TaskGroup이
            # 500으로 처리했고, 프론트는 `event: error` 이벤트 없이 연결이 끊겨 "대기중"
            # 상태로 보였다. 여기서 명시적으로 error 이벤트 yield → 프론트가 onError 호출.
            _outcome = "error"
            logger.exception(
                "딥 리서치 합성 중 예외: code=%s, exc_type=%s",
                code,
                type(exc).__name__,
            )
            yield {
                "event": "error",
                "data": f"합성 중 오류가 발생했습니다: {type(exc).__name__}: {exc}",
            }

    finally:
        # Phase 5: 정리 (성공/실패/취소 모두)
        _active_deep_analyses.discard(code)
        if staging_dir is not None:
            shutil.rmtree(staging_dir, ignore_errors=True)
            logger.debug("스테이징 디렉토리 정리: %s", staging_dir)
        # NFR-006: end-to-end 소요시간 로깅
        _duration = _time.monotonic() - _t_start
        logger.info(
            "딥 리서치 종료: code=%s, outcome=%s, duration=%.2fs, chars=%d",
            code,
            _outcome,
            _duration,
            sum(len(p) for p in full_markdown_parts),
        )


# ─────────────────────────────────────────────────────────────────────────────
# 스테이징 디렉토리 정리 유틸리티
# ─────────────────────────────────────────────────────────────────────────────


def _cleanup_stale_staging_dirs(
    *,
    base_dir: Path = Path("/tmp"),
    max_age_days: int = 7,
) -> int:
    """오래된 스테이징 디렉토리를 정리.

    main.py lifespan에서 서버 시작 시 호출됨 (Phase D).

    Args:
        base_dir: 검색 기준 디렉토리 (기본 /tmp).
        max_age_days: 이 기간보다 오래된 디렉토리를 삭제 (기본 7일).

    Returns:
        삭제된 디렉토리 수.
    """
    threshold_sec = max_age_days * 86400
    now_ts = time.time()
    deleted = 0

    for candidate in base_dir.glob("analysis_*"):
        if not candidate.is_dir():
            continue
        try:
            age_sec = now_ts - candidate.stat().st_mtime
            if age_sec > threshold_sec:
                shutil.rmtree(candidate, ignore_errors=True)
                logger.info("오래된 스테이징 디렉토리 삭제: %s (%.0f일)", candidate, age_sec / 86400)
                deleted += 1
        except OSError as exc:
            logger.warning("스테이징 디렉토리 정리 실패: %s — %s", candidate, exc)

    logger.info("스테이징 정리 완료: %d개 삭제", deleted)
    return deleted
