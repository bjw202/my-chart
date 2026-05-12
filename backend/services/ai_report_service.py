"""AI 리포트 서비스: Codex CLI 기반 Fast Mode + 리포트 영속화 (SPEC-AI-REPORT-003)."""

from __future__ import annotations

import logging
import os
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator

from my_chart.registry import _name

logger = logging.getLogger(__name__)

# 현재 진행 중인 분석 요청을 추적하는 집합 (종목 코드)
# @MX:WARN: [AUTO] v1.1.4 - 모듈 레벨 가변 전역 상태. 멀티 워커 환경에서 일관성 보장 불가.
# @MX:REASON: 로컬 단일 프로세스 uvicorn 전제. 프로덕션 멀티워커 전환 시 Redis로 교체 필요.
_active_analyses: set[str] = set()

# @MX:NOTE: [AUTO] v1.1.4 - Rate limiting: 일일 쿼터 + 분당 버스트 방지 (CRITICAL 보안)
# Perplexity API 비용 폭주 방지. 단일 프로세스 로컬 앱 전제 (멀티워커면 Redis 권장).
_daily_call_count: int = 0
_daily_reset_date: str = ""
_recent_call_timestamps: list[float] = []

# 환경변수 기반 제한 (기본값은 개인 사용 기준)
AI_REPORT_DAILY_QUOTA = int(os.environ.get("AI_REPORT_DAILY_QUOTA", "50"))
AI_REPORT_BURST_LIMIT = int(os.environ.get("AI_REPORT_BURST_LIMIT", "3"))  # 분당 최대
AI_REPORT_BURST_WINDOW_SEC = 60


class RateLimitError(Exception):
    """Rate limit 초과 예외. HTTP 429로 변환됨."""


# @MX:ANCHOR: [AUTO] v1.1.4 - 비용 폭주 방지 게이트. fan_in >= 2 (router + tests).
# @MX:REASON: Perplexity API 호출 전 모든 경로가 이 함수를 통과해야 하는 invariant.
# 일일 쿼터/분당 버스트 제한을 강제하며, 제거/우회 시 비용 통제 불가.
def check_rate_limit() -> None:
    """AI 리포트 요청의 rate limit 검사. 위반 시 RateLimitError 발생.

    일일 쿼터와 분당 버스트 제한을 동시에 검사. 검사 통과 시 카운터 증가.

    Raises:
        RateLimitError: 쿼터 초과 또는 분당 버스트 초과.
    """
    import time

    global _daily_call_count, _daily_reset_date, _recent_call_timestamps

    today = datetime.now().strftime("%Y-%m-%d")

    # 일일 카운터 자정 리셋
    if _daily_reset_date != today:
        _daily_call_count = 0
        _daily_reset_date = today
        logger.info("일일 AI 리포트 쿼터 리셋: %s", today)

    # 일일 쿼터 초과 검사
    if _daily_call_count >= AI_REPORT_DAILY_QUOTA:
        raise RateLimitError(
            f"일일 쿼터 초과 ({AI_REPORT_DAILY_QUOTA}회). 내일 다시 시도해 주세요."
        )

    # 분당 버스트 검사: 윈도우 밖 타임스탬프 제거
    now = time.time()
    cutoff = now - AI_REPORT_BURST_WINDOW_SEC
    _recent_call_timestamps = [t for t in _recent_call_timestamps if t > cutoff]

    if len(_recent_call_timestamps) >= AI_REPORT_BURST_LIMIT:
        oldest = _recent_call_timestamps[0]
        wait_sec = int(AI_REPORT_BURST_WINDOW_SEC - (now - oldest))
        raise RateLimitError(
            f"분당 요청 한도 초과 ({AI_REPORT_BURST_LIMIT}회/분). "
            f"{wait_sec}초 후 다시 시도해 주세요."
        )

    # 통과: 카운터 증가
    _daily_call_count += 1
    _recent_call_timestamps.append(now)
    logger.info(
        "rate limit 통과: daily=%d/%d, burst=%d/%d",
        _daily_call_count, AI_REPORT_DAILY_QUOTA,
        len(_recent_call_timestamps), AI_REPORT_BURST_LIMIT,
    )

# 리포트 저장 기본 경로
_REPORTS_BASE = Path(__file__).parent.parent / "reports"

# @MX:NOTE: [AUTO] v1.1.4 - 파일 경로 안전성 강화 (CRITICAL 보안)
# 기본 파일시스템 금지 문자 + 경로 조작 문자 + 제어 문자
_UNSAFE_CHARS = re.compile(r'[/\\:*?"<>|\x00-\x1f\x7f]')

# Windows 예약 파일명 (macOS/Linux에서도 호환성 위해 차단)
_WINDOWS_RESERVED_NAMES = frozenset({
    "con", "prn", "aux", "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
})

# 파일명 최대 길이 (대부분 파일시스템의 안전 한도)
_MAX_FILENAME_LENGTH = 100

def get_stock_name(code: str) -> str | None:
    """종목 코드로 종목명 조회.

    Args:
        code: 6자리 KRX 종목 코드.

    Returns:
        종목명 문자열, 존재하지 않으면 None.
    """
    name = _name(code)
    if name == "NonName":
        return None
    return name


# SPEC-AI-REPORT-003: Perplexity 전용 자산 (SYSTEM_PROMPT, SEARCH_DOMAIN_FILTER,
# _PROMPT_TEMPLATE_PATH, _load_prompt_template, load_prompt, stream_perplexity) 은
# 모두 제거됨. Fast/Deep Mode 양쪽 Codex CLI 기반으로 전환 완료.


# ─────────────────────────────────────────────────────────────────────────────
# SPEC-AI-REPORT-003 Step 4: Fast Mode Codex 전환 + 30s heartbeat
# ─────────────────────────────────────────────────────────────────────────────

# heartbeat 주기 (NFR: 사용자 대기 UX) — 30s 간격으로 phase 이벤트 emit
_CODEX_FAST_HEARTBEAT_SEC: float = 30.0

# 완료 시 markdown 청크 크기 (SSE data 이벤트 단위)
_CODEX_FAST_CHUNK_SIZE: int = 256

# heartbeat 이벤트 메시지 순환 — Codex 내부 단계 추정에 기반한 사용자 친화 표현
_CODEX_FAST_HEARTBEAT_MESSAGES: tuple[str, ...] = (
    "웹 검색 진행 중",
    "자료 교차 검증 중",
    "시장 데이터 분석 중",
    "리포트 작성 중",
    "최종 검수 진행 중",
)


# @MX:ANCHOR stream_codex_fast — SPEC-AI-REPORT-003 FR-001/FR-004. fan_in >= 2 (router + tests).
# @MX:REASON Codex CLI non-streaming 한계를 30s heartbeat SSE 로 UX 보완. 라우터 계약:
#             yield dict (SSE 이벤트) — 상위 스트리밍 핸들러가 EventSourceResponse 로 변환.
#             전체 응답 종료 시 save_report 로 영속화 (stream_perplexity 호환 계약 유지).
async def stream_codex_fast(
    stock_name: str,
    code: str,
) -> AsyncGenerator[dict, None]:
    """Codex CLI 를 비스트리밍 서브프로세스로 실행하고 30s heartbeat + 완료 시 청크 스트림.

    SPEC-AI-REPORT-003 FR-001 / FR-004. Codex 는 non-streaming 이므로 heartbeat SSE 로
    UX 연속성을 보완하고, 완료 시 markdown 을 256자 청크로 분할해 순차 yield 한다.

    Args:
        stock_name: 종목명 (예: "삼성전자").
        code: 종목 코드 (예: "005930").

    Yields:
        - {"event": "phase", "data": json-str} — phase 이벤트 (시작/heartbeat)
        - {"data": str} — markdown 청크 (256자 단위)
        - {"event": "done", "data": ""} — 정상 완료
        - {"event": "error", "data": str} — 실패

    Note:
        save_report 는 정상 완료 직전에 자동 호출 (stream_perplexity 와 계약 동일).
    """
    import asyncio
    import json
    import tempfile
    from pathlib import Path

    # Lazy import — codex_cli_runner 는 독립 모듈이지만 순환 import 방지 및
    # 테스트 격리 환경 (importlib.util.spec_from_file_location) 호환을 위해 지연 로드
    from backend.services.codex_cli_runner import (
        load_codex_prompt,
        run_codex_research,
    )

    # 시작 phase 이벤트
    yield {
        "event": "phase",
        "data": json.dumps({"phase": "codex_fast_start"}),
    }

    # 프롬프트 로드 — 실패 시 즉시 error 이벤트 (재시도 없음)
    try:
        prompt = load_codex_prompt(code=code, stock_name=stock_name)
    except (FileNotFoundError, ValueError) as exc:
        logger.error("Codex 프롬프트 로드 실패 [%s]: %s", code, exc)
        yield {
            "event": "error",
            "data": f"Codex 프롬프트 로드 실패: {exc}",
        }
        return

    # 임시 디렉토리에 output 파일 경로 준비
    with tempfile.TemporaryDirectory(prefix=f"fast_{code}_") as tmp_dir:
        output_path = Path(tmp_dir) / "codex.md"

        # Codex 호출을 background task 로 시작 → heartbeat 루프에서 완료 대기
        codex_task: asyncio.Task = asyncio.create_task(
            run_codex_research(
                code=code,
                stock_name=stock_name,
                output_path=output_path,
                prompt=prompt,
            )
        )

        try:
            msg_idx = 0
            while not codex_task.done():
                try:
                    # heartbeat 간격 만큼 대기 — shield 로 timeout 에도 codex_task 유지
                    await asyncio.wait_for(
                        asyncio.shield(codex_task),
                        timeout=_CODEX_FAST_HEARTBEAT_SEC,
                    )
                    break  # codex 완료 (정상/에러 모두 여기서 break)
                except asyncio.TimeoutError:
                    # 아직 진행 중 — heartbeat phase 이벤트 emit
                    message = _CODEX_FAST_HEARTBEAT_MESSAGES[
                        msg_idx % len(_CODEX_FAST_HEARTBEAT_MESSAGES)
                    ]
                    msg_idx += 1
                    yield {
                        "event": "phase",
                        "data": json.dumps(
                            {"phase": "codex_fast_progress", "message": message}
                        ),
                    }

            codex_result = await codex_task

        except asyncio.CancelledError:
            # 상위 요청 취소 — codex_task 정리 후 re-raise
            codex_task.cancel()
            try:
                await codex_task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
            logger.info("Codex Fast Mode 취소됨 (CancelledError): code=%s", code)
            raise

        if not codex_result.success:
            logger.error(
                "Codex Fast Mode 실패 [%s]: %s — %s",
                code,
                codex_result.error_type,
                codex_result.error_message,
            )
            yield {
                "event": "error",
                "data": (
                    f"Codex 호출 실패 ({codex_result.error_type}): "
                    f"{codex_result.error_message}"
                ),
            }
            return

        # 마크다운 읽어서 검증 → 저장 → 청크 스트리밍
        try:
            markdown = output_path.read_text(encoding="utf-8")
        except OSError as exc:
            logger.error("Codex output 파일 읽기 실패 [%s]: %s", code, exc)
            yield {"event": "error", "data": f"Codex output 파일 읽기 실패: {exc}"}
            return

        if not markdown.strip():
            yield {"event": "error", "data": "Codex 응답이 비어 있습니다"}
            return

        # 리포트 영속화 (stream_perplexity 와 동일한 save_report 계약)
        filename = save_report(stock_name, markdown)
        logger.info(
            "Codex Fast 리포트 저장: %s / %s (%d chars)",
            stock_name,
            filename,
            len(markdown),
        )

        # 256자 청크로 분할해 SSE data 이벤트 발행
        for i in range(0, len(markdown), _CODEX_FAST_CHUNK_SIZE):
            yield {"data": markdown[i : i + _CODEX_FAST_CHUNK_SIZE]}

        yield {"event": "done", "data": ""}


# @MX:ANCHOR: [AUTO] v1.1.4 - 경로 조작 방지 보안 게이트. fan_in = 3.
# @MX:REASON: save_report, get_history, get_report_content에서 모두 사용되는 유일한 정규화 경로.
# 우회 시 path traversal / 파일시스템 손상 / Windows 예약명 충돌 발생. 7단계 처리 순서 변경 금지.
def _sanitize_name(stock_name: str) -> str:
    """파일시스템 안전 문자열로 변환. 경로 조작 공격 방지.

    다음을 차단/정리:
    - 금지 문자 (/ \\ : * ? " < > |)
    - 제어 문자 (\\x00-\\x1f, \\x7f)
    - 경로 조작: `..`, 선행/후행 점
    - Windows 예약명 (CON, NUL, COM1-9, LPT1-9 등)
    - 공백 / 선행·후행 공백
    - 길이 100자 초과
    - 빈 문자열 (→ "report" 폴백)

    Args:
        stock_name: 원본 종목명.

    Returns:
        파일명에 사용 가능한 문자열 (경로 조작 불가).
    """
    # 1) Unicode 정규화 (NFKC: 전각/반각, 합성문자 통일)
    safe = unicodedata.normalize("NFKC", stock_name)

    # 2) 금지 문자 + 제어 문자 제거
    safe = _UNSAFE_CHARS.sub("", safe)

    # 3) 경로 조작 제거: `..` → "_" 치환, 모든 `.` 시퀀스 단일화
    safe = re.sub(r"\.{2,}", "_", safe)

    # 4) 선행·후행 점·공백·밑줄 제거
    safe = safe.strip(". _\t")

    # 5) Windows 예약명 차단 (확장자 앞부분만 검사)
    stem = safe.split(".", 1)[0].lower()
    if stem in _WINDOWS_RESERVED_NAMES:
        safe = f"_{safe}"

    # 6) 길이 제한 (앞에서 자르기)
    if len(safe) > _MAX_FILENAME_LENGTH:
        safe = safe[:_MAX_FILENAME_LENGTH]

    # 7) 빈 문자열 폴백
    if not safe:
        safe = "report"

    return safe


# @MX:ANCHOR: [AUTO] v1.1.4 - 리포트 영속화 진입점. fan_in >= 2 (stream_perplexity + tests).
# @MX:REASON: 동일 날짜 시퀀스 충돌 해결 로직(seq 증가)이 파일명 규칙을 결정.
# 변경 시 get_history / get_report_content의 파일명 파싱과 일관성 유지 필요.
def save_report(stock_name: str, content: str) -> str:
    """분석 리포트를 파일로 저장.

    Args:
        stock_name: 종목명 (디렉토리명으로 사용).
        content: 저장할 마크다운 내용.

    Returns:
        저장된 파일명 (예: "2026-04-12.md" 또는 "2026-04-12_2.md").
    """
    safe_name = _sanitize_name(stock_name)
    report_dir = _REPORTS_BASE / safe_name
    os.makedirs(report_dir, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    base_filename = f"{today}.md"
    target = report_dir / base_filename

    # 같은 날짜 파일이 이미 존재하면 시퀀스 번호 부여
    if target.exists():
        seq = 2
        while True:
            candidate = report_dir / f"{today}_{seq}.md"
            if not candidate.exists():
                target = candidate
                break
            seq += 1

    target.write_text(content, encoding="utf-8")
    logger.info("리포트 저장: %s", target)
    return target.name


def get_history(stock_name: str) -> list[dict[str, str]]:
    """저장된 리포트 히스토리 조회.

    Args:
        stock_name: 종목명.

    Returns:
        날짜 내림차순 정렬된 리포트 목록.
        각 항목: {"filename": str, "date": str, "created_at": str}
    """
    safe_name = _sanitize_name(stock_name)
    report_dir = _REPORTS_BASE / safe_name

    if not report_dir.exists():
        return []

    items = []
    for path in report_dir.glob("*.md"):
        # 파일명에서 날짜 추출 (예: "2026-04-12.md" → "2026-04-12")
        stem = path.stem
        # 시퀀스 번호가 있으면 제거 (예: "2026-04-12_2" → "2026-04-12")
        date_part = stem.split("_")[0] if "_" in stem else stem

        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        items.append(
            {
                "filename": path.name,
                "date": date_part,
                "created_at": mtime.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

    # 날짜 내림차순 정렬 (파일명 기준)
    items.sort(key=lambda x: x["filename"], reverse=True)
    return items


# @MX:ANCHOR: [AUTO] v1.1.4 - 외부 입력(filename) path traversal 방지 게이트. fan_in >= 2.
# @MX:REASON: API 엔드포인트 /api/ai-report/{code}/{filename}이 직접 호출. filename 정규식 검증 +
# resolve() 후 보관 디렉토리 이탈 체크의 2중 방어를 제거하면 임의 파일 읽기 취약점 발생.
def get_report_content(stock_name: str, filename: str) -> str | None:
    """저장된 리포트 내용 조회.

    Args:
        stock_name: 종목명.
        filename: 조회할 파일명 (예: "2026-04-12.md"). 외부 입력이므로 검증 필수.

    Returns:
        리포트 마크다운 내용, 파일이 없거나 안전하지 않은 경로면 None.
    """
    # v1.1.4 - YYYY-MM-DD.md 또는 YYYY-MM-DD_N.md 형식만 허용
    if not re.match(r"^\d{4}-\d{2}-\d{2}(_\d+)?\.md$", filename):
        logger.warning("잘못된 파일명 형식 거부: %s", filename)
        return None

    safe_name = _sanitize_name(stock_name)
    safe_dir = (_REPORTS_BASE / safe_name).resolve()
    target = (safe_dir / filename).resolve()

    # resolve 후 보관 디렉토리 밖을 참조하면 거부
    try:
        target.relative_to(_REPORTS_BASE.resolve())
    except ValueError:
        logger.warning("경로 이탈 차단: %s", target)
        return None

    if not target.exists() or not target.is_file():
        return None

    return target.read_text(encoding="utf-8")
