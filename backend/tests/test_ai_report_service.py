"""SPEC-AI-REPORT-001 v1.1.4 회귀 테스트.

테스트 대상:
- _sanitize_name(): 파일 경로 조작 방지 보안 (CRITICAL)
- get_report_content(): path traversal 차단
- save_report(): 동일 날짜 시퀀스 처리
- load_prompt(): 프롬프트 로드 + 종목명 치환
- check_rate_limit(): 일일 쿼터 + 분당 버스트
"""

from __future__ import annotations

import importlib
import os
import sys
import time
import types
from pathlib import Path

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def service_module(monkeypatch, tmp_path):
    """깨끗한 상태의 ai_report_service 모듈 직접 로드.

    backend.services.__init__.py가 다른 서비스들을 연쇄 import하므로,
    importlib.util.spec_from_file_location으로 격리 로드하여 my_chart 전체 로드 회피.

    - my_chart.registry 스텁 (실제 DB 의존 회피)
    - _REPORTS_BASE를 tmp_path로 패치
    - 모듈 레벨 상태(_active_analyses, rate limiter) 초기화
    """
    import importlib.util

    # registry 스텁 (ai_report_service가 from my_chart.registry import _name)
    sys.modules["my_chart.registry"] = types.SimpleNamespace(
        _name=lambda code: "테스트종목" if code == "000000" else "NonName"
    )

    # 서비스 파일 직접 로드
    svc_path = Path(__file__).parent.parent / "services" / "ai_report_service.py"
    spec = importlib.util.spec_from_file_location("_test_ai_report_service", svc_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # 보관 경로를 임시 디렉토리로
    monkeypatch.setattr(mod, "_REPORTS_BASE", tmp_path)
    # 모듈 레벨 상태 초기화
    mod._active_analyses.clear()
    mod._daily_call_count = 0
    mod._daily_reset_date = ""
    mod._recent_call_timestamps.clear()
    # 테스트용 완화된 제한 설정
    monkeypatch.setattr(mod, "AI_REPORT_DAILY_QUOTA", 5)
    monkeypatch.setattr(mod, "AI_REPORT_BURST_LIMIT", 2)
    monkeypatch.setattr(mod, "AI_REPORT_BURST_WINDOW_SEC", 2)

    yield mod


# ─────────────────────────────────────────────────────────────────────────────
# _sanitize_name 보안 테스트 (CRITICAL)
# ─────────────────────────────────────────────────────────────────────────────


class TestSanitizeName:
    """경로 조작 공격 방지 검증."""

    def test_normal_korean_name(self, service_module):
        assert service_module._sanitize_name("삼성전자") == "삼성전자"

    def test_normal_mixed_name(self, service_module):
        assert service_module._sanitize_name("LG에너지솔루션") == "LG에너지솔루션"

    def test_forbidden_path_chars_removed(self, service_module):
        """/, \\, :, *, ?, ", <, >, | 제거."""
        assert service_module._sanitize_name('evil/path\\:name*?"<>|') == "evilpathname"

    def test_parent_directory_traversal_blocked(self, service_module):
        """`..` 시퀀스는 `_`로 치환되어 경로 이탈 불가."""
        result = service_module._sanitize_name("../../../etc/passwd")
        assert ".." not in result
        assert "/" not in result

    def test_leading_dot_stripped(self, service_module):
        """선행 점은 제거됨 (숨김 파일 방지)."""
        assert service_module._sanitize_name(".hidden") == "hidden"

    def test_multiple_dots_collapsed(self, service_module):
        """연속된 점은 단일 언더스코어로."""
        result = service_module._sanitize_name("a...b")
        assert ".." not in result

    def test_windows_reserved_name_prefixed(self, service_module):
        """Windows 예약명은 `_` 접두사 부여."""
        for reserved in ("CON", "NUL", "COM1", "LPT9", "aux"):
            result = service_module._sanitize_name(reserved)
            assert result.startswith("_"), f"{reserved} should be prefixed"

    def test_control_chars_removed(self, service_module):
        """제어 문자(\\x00-\\x1f) 제거."""
        assert service_module._sanitize_name("name\x00\x01\x1ftest") == "nametest"

    def test_null_byte_removed(self, service_module):
        """널 바이트 제거 (poisoning 방지)."""
        assert "\x00" not in service_module._sanitize_name("a\x00b")

    def test_empty_string_fallback(self, service_module):
        """빈 문자열은 `report`로 폴백."""
        assert service_module._sanitize_name("") == "report"
        assert service_module._sanitize_name("...") == "report"
        assert service_module._sanitize_name("   ") == "report"

    def test_length_limit(self, service_module):
        """100자 초과 시 자름."""
        long_name = "가" * 200
        result = service_module._sanitize_name(long_name)
        assert len(result) <= 100

    def test_nfkc_normalization(self, service_module):
        """NFKC 정규화로 전각/반각 통일."""
        # 전각 영문 A → 반각 A
        result = service_module._sanitize_name("Ａ")
        assert result == "A"


# ─────────────────────────────────────────────────────────────────────────────
# get_report_content: path traversal 방지
# ─────────────────────────────────────────────────────────────────────────────


class TestGetReportContent:
    def test_rejects_invalid_filename_format(self, service_module):
        """YYYY-MM-DD(_N).md 형식 아닌 것 거부."""
        assert service_module.get_report_content("테스트", "../../etc/passwd") is None
        assert service_module.get_report_content("테스트", "arbitrary.md") is None
        assert service_module.get_report_content("테스트", "2026-04-12.txt") is None

    def test_accepts_valid_filename_but_not_exists(self, service_module):
        """형식은 맞으나 파일 없으면 None."""
        assert service_module.get_report_content("테스트", "2026-04-12.md") is None

    def test_accepts_sequence_filename(self, service_module, tmp_path):
        """시퀀스 포함 파일명 허용."""
        (tmp_path / "테스트").mkdir()
        content_file = tmp_path / "테스트" / "2026-04-12_3.md"
        content_file.write_text("테스트 내용", encoding="utf-8")

        result = service_module.get_report_content("테스트", "2026-04-12_3.md")
        assert result == "테스트 내용"

    def test_path_traversal_in_stock_name_blocked(self, service_module):
        """stock_name에 경로 조작 시도해도 sanitize 후 안전."""
        # stock_name에 ".." 포함 시 sanitize로 제거되므로 파일이 있을 수 없음
        assert service_module.get_report_content("../../etc", "2026-04-12.md") is None


# ─────────────────────────────────────────────────────────────────────────────
# save_report: 동일 날짜 시퀀스
# ─────────────────────────────────────────────────────────────────────────────


class TestSaveReport:
    def test_saves_basic_report(self, service_module, tmp_path):
        filename = service_module.save_report("테스트", "# 내용")
        assert filename.endswith(".md")
        saved = tmp_path / "테스트" / filename
        assert saved.exists()
        assert saved.read_text(encoding="utf-8") == "# 내용"

    def test_same_day_sequence_increment(self, service_module, tmp_path):
        """같은 날 중복 호출 시 _2, _3 시퀀스."""
        f1 = service_module.save_report("종목", "첫번째")
        f2 = service_module.save_report("종목", "두번째")
        f3 = service_module.save_report("종목", "세번째")

        assert "_2" in f2 or f2 != f1
        assert "_3" in f3 or f3 != f2
        # 모든 파일이 존재해야 함
        assert (tmp_path / "종목" / f1).exists()
        assert (tmp_path / "종목" / f2).exists()
        assert (tmp_path / "종목" / f3).exists()


# ─────────────────────────────────────────────────────────────────────────────
# load_prompt: 프롬프트 치환
# ─────────────────────────────────────────────────────────────────────────────


class TestLoadPrompt:
    def test_replaces_placeholder(self, service_module):
        result = service_module.load_prompt("삼성전자")
        assert "삼성전자" in result
        assert "〈종목명〉" not in result  # placeholder 모두 치환됨

    def test_preserves_other_content(self, service_module):
        """프롬프트 템플릿의 다른 마커들은 유지."""
        result = service_module.load_prompt("현대차")
        assert "🔥" in result  # Executive Summary 마커
        assert "0단계" in result


# ─────────────────────────────────────────────────────────────────────────────
# Rate limiting (CRITICAL 보안)
# ─────────────────────────────────────────────────────────────────────────────


class TestRateLimit:
    def test_allows_within_burst_limit(self, service_module):
        """분당 한도(2회) 내에서는 통과."""
        service_module.check_rate_limit()
        service_module.check_rate_limit()

    def test_blocks_burst_exceeded(self, service_module):
        """분당 한도 초과 시 RateLimitError."""
        service_module.check_rate_limit()
        service_module.check_rate_limit()
        with pytest.raises(service_module.RateLimitError) as exc_info:
            service_module.check_rate_limit()
        assert "분당" in str(exc_info.value) or "한도" in str(exc_info.value)

    def test_burst_window_resets(self, service_module):
        """버스트 윈도우 경과 후 재허용."""
        service_module.check_rate_limit()
        service_module.check_rate_limit()
        # 윈도우(2초) 경과
        time.sleep(2.1)
        # 재호출 가능해야 함
        service_module.check_rate_limit()

    def test_blocks_daily_quota(self, service_module):
        """일일 쿼터(5회) 초과 시 RateLimitError."""
        # 윈도우 충분히 기다리며 5회 호출
        for _ in range(5):
            service_module.check_rate_limit()
            time.sleep(2.1)  # 버스트 윈도우 회피

        with pytest.raises(service_module.RateLimitError) as exc_info:
            service_module.check_rate_limit()
        assert "일일" in str(exc_info.value) or "쿼터" in str(exc_info.value)


# ─────────────────────────────────────────────────────────────────────────────
# get_stock_name
# ─────────────────────────────────────────────────────────────────────────────


class TestGetStockName:
    def test_valid_code_returns_name(self, service_module):
        assert service_module.get_stock_name("000000") == "테스트종목"

    def test_invalid_code_returns_none(self, service_module):
        assert service_module.get_stock_name("999999") is None
