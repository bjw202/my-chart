"""SPEC-PRESET-001 AC-8 — backend/schemas/screen.py patterns.max_length=5 회귀 테스트.

Group E: Pydantic 검증 회귀 테스트
- E1: 5개 patterns 포함 요청 → Pydantic 검증 통과 (max_length=5 허용)
- E2: 6개 patterns 포함 요청 → ValidationError 발생 (max_length=5 초과 거부)

참고:
- SPEC-MINERVINI-001 REQ-MIN-005에서 max_length=5가 이미 적용됨 (idempotent).
- 본 테스트는 회귀 방어용이며, 백엔드 코드 변경 없이 통과해야 한다.
- Pydantic 스키마 레이어만 직접 검증하여 DB/서비스 의존성 없이 격리 실행한다.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.schemas.screen import ScreenRequest


# ─────────────────────────────────────────────────────────────────────────────
# 유효한 PatternCondition 헬퍼
# ─────────────────────────────────────────────────────────────────────────────

def _pattern_dict(indicator_b: str = "SMA50") -> dict:
    """단일 PatternCondition 딕셔너리 생성 헬퍼."""
    return {
        "indicator_a": "Close",
        "operator": "gt",
        "indicator_b": indicator_b,
        "multiplier": 1.0,
    }


def _patterns(count: int) -> list[dict]:
    """count개의 PatternCondition 딕셔너리 리스트 생성."""
    indicators = ["EMA10", "EMA20", "SMA50", "SMA100", "SMA200", "SMA200"]
    return [
        {"indicator_a": "Close", "operator": "gt", "indicator_b": indicators[i], "multiplier": 1.0}
        for i in range(count)
    ]


def _base_payload(num_patterns: int) -> dict:
    """ScreenRequest 딕셔너리 생성 (num_patterns개 패턴 포함)."""
    return {
        "market_cap_min": None,
        "chg_1d_min": None,
        "chg_1w_min": None,
        "chg_1m_min": None,
        "chg_3m_min": None,
        "patterns": _patterns(num_patterns),
        "pattern_logic": "AND",
        "rs_min": None,
        "markets": [],
        "sectors": [],
        "codes": [],
        "minervini_trend_template": None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Group E 테스트
# ─────────────────────────────────────────────────────────────────────────────

class TestScreenPatternsLimit:
    """AC-8 (REQ-PST-009): patterns max_length=5 Pydantic 검증 회귀 테스트."""

    def test_e1_five_patterns_validates_ok(self) -> None:
        """E1: 5개 patterns를 포함한 ScreenRequest는 Pydantic 검증을 통과한다."""
        payload = _base_payload(5)
        req = ScreenRequest(**payload)
        assert len(req.patterns) == 5, (
            f"5개 patterns가 Pydantic 검증에서 거부됨. "
            f"max_length=5 이내여야 함."
        )

    def test_e2_six_patterns_raises_validation_error(self) -> None:
        """E2: 6개 patterns를 포함한 ScreenRequest는 ValidationError를 발생시킨다."""
        payload = _base_payload(6)
        with pytest.raises(ValidationError) as exc_info:
            ScreenRequest(**payload)
        # Pydantic 에러 상세에 patterns 관련 메시지 포함 확인
        errors = exc_info.value.errors()
        assert any(
            "patterns" in str(e.get("loc", "")) or "patterns" in str(e.get("msg", ""))
            for e in errors
        ), f"ValidationError에 patterns 관련 에러가 없음: {errors}"

    def test_e1_existing_three_patterns_ok(self) -> None:
        """기존 3개 patterns 요청은 여전히 수용된다 (회귀 없음, A7)."""
        payload = _base_payload(3)
        req = ScreenRequest(**payload)
        assert len(req.patterns) == 3

    def test_e1_empty_patterns_ok(self) -> None:
        """0개 patterns (빈 배열) 요청도 수용된다 (회귀 없음)."""
        payload = _base_payload(0)
        req = ScreenRequest(**payload)
        assert len(req.patterns) == 0

    def test_e1_one_pattern_ok(self) -> None:
        """1개 patterns 요청도 수용된다 (기존 동작 회귀 없음)."""
        payload = _base_payload(1)
        req = ScreenRequest(**payload)
        assert len(req.patterns) == 1
