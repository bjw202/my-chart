"""Perplexity 응답 메모리 캐시 (SPEC-AI-REPORT-002 v1.0.3 — 시나리오 C 비용 절감).

빠른 분석(SPEC-001 stream_perplexity)이 종료될 때 full markdown을 종목 코드별로
캐시한다. 같은 종목으로 심층 분석(SPEC-002 deep mode)이 호출될 때
deep_research_collector._collect_perplexity가 이 캐시를 먼저 조회하여
HTTP 재호출을 스킵한다.

설계:
- TTL 600초 (10분) — 빠른분석 결과를 보고 사용자가 심층 분석을 결정하는 평균 시간
- 메모리 dict (단일 프로세스 uvicorn 전제, ai_report_service의 _active_analyses와 동일 패턴)
- thread-safe 보장 안 함 (Python GIL + 단순 dict ops로 실용 충분)
- 멀티워커 환경에서는 Redis 등으로 교체 필요 (@MX:WARN)
"""

from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)

# @MX:WARN [AUTO] _perplexity_full_cache — 모듈 레벨 가변 상태, 멀티워커 비호환.
# @MX:REASON 단일 프로세스 uvicorn 전제. 멀티워커 전환 시 Redis로 교체 필요.
_perplexity_full_cache: dict[str, tuple[float, str]] = {}

# TTL: 10분. 빠른분석 후 사용자가 심층 분석으로 결정하는 평균 시간을 고려.
TTL_SECONDS: float = 600.0


def put(code: str, full_markdown: str) -> None:
    """빠른 분석 종료 시 호출. 종목 코드를 키로 full markdown을 캐시한다.

    Args:
        code: 종목 코드 6자리 (예: "010170")
        full_markdown: stream_perplexity가 yield한 모든 청크의 합본
    """
    if not code or not full_markdown:
        return
    _perplexity_full_cache[code] = (time.monotonic(), full_markdown)
    logger.info(
        "perplexity_cache put: code=%s, chars=%d (TTL=%ds)",
        code,
        len(full_markdown),
        int(TTL_SECONDS),
    )


def get(code: str) -> str | None:
    """심층 분석 시작 시 호출. 신선한 캐시가 있으면 반환, 없거나 만료면 None.

    Args:
        code: 종목 코드

    Returns:
        캐시된 full markdown 또는 None (cache miss / expired)
    """
    entry = _perplexity_full_cache.get(code)
    if entry is None:
        return None
    ts, content = entry
    age = time.monotonic() - ts
    if age > TTL_SECONDS:
        # 만료된 엔트리 정리
        _perplexity_full_cache.pop(code, None)
        logger.info("perplexity_cache expired: code=%s, age=%.1fs", code, age)
        return None
    logger.info("perplexity_cache HIT: code=%s, age=%.1fs (재사용으로 HTTP 호출 스킵)", code, age)
    return content


def clear() -> None:
    """테스트 격리용. 전체 캐시 초기화."""
    _perplexity_full_cache.clear()


def size() -> int:
    """현재 캐시 크기 (관찰성)."""
    return len(_perplexity_full_cache)
