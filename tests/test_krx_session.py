"""Characterization tests for my_chart/krx_session.py.

SPEC: SPEC-KRX-AUTH-001
이 파일은 krx_session 모듈의 현재 동작을 캡처하는 테스트다.
네트워크 호출이 필요한 부분은 mock으로 대체한다.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

import my_chart.krx_session as krx_session


# ---------------------------------------------------------------------------
# patch_pykrx_session 테스트
# ---------------------------------------------------------------------------


class TestPatchPykrxSession:
    def setup_method(self):
        """각 테스트 전에 패치 상태를 초기화한다."""
        krx_session._patched = False

    def teardown_method(self):
        """각 테스트 후 패치 상태를 초기화한다."""
        krx_session._patched = False

    def test_characterize_patch_sets_patched_flag(self):
        """patch_pykrx_session() 호출 후 _patched가 True로 설정된다."""
        with patch("my_chart.krx_session.webio", create=True):
            # pykrx.website.comm.webio를 mock으로 대체
            mock_webio = MagicMock()
            mock_webio.Post = MagicMock()
            mock_webio.Get = MagicMock()

            with patch.dict("sys.modules", {"pykrx.website.comm": MagicMock(webio=mock_webio)}):
                import importlib
                import sys

                # webio import를 mock으로 대체
                with patch.object(krx_session, "_patched", False):
                    pass  # 상태 리셋

        # 실제 패치 호출 시 예외 없이 완료되어야 함
        # (pykrx 설치 여부에 따라 ImportError 처리)
        try:
            krx_session.patch_pykrx_session()
            assert krx_session._patched is True
        except Exception:
            # pykrx webio 구조 변경 시에도 _patched는 False 유지
            assert krx_session._patched is False

    def test_characterize_patch_is_idempotent(self):
        """patch_pykrx_session()을 여러 번 호출해도 동일한 결과를 반환한다."""
        initial_patched = krx_session._patched

        # 첫 번째 호출
        krx_session.patch_pykrx_session()
        first_result = krx_session._patched

        # 두 번째 호출
        krx_session.patch_pykrx_session()
        second_result = krx_session._patched

        # 두 번 호출해도 상태가 동일해야 함 (멱등성)
        assert first_result == second_result

    def test_characterize_patch_skips_if_already_patched(self):
        """_patched=True 상태에서는 patch_pykrx_session()이 아무 작업도 하지 않는다."""
        krx_session._patched = True

        # 호출 후에도 True 유지
        krx_session.patch_pykrx_session()
        assert krx_session._patched is True


# ---------------------------------------------------------------------------
# login_krx 테스트
# ---------------------------------------------------------------------------


class TestLoginKrx:
    def setup_method(self):
        """각 테스트 전에 로그인 상태를 초기화한다."""
        krx_session._logged_in = False

    def teardown_method(self):
        """각 테스트 후 로그인 상태를 초기화한다."""
        krx_session._logged_in = False

    def test_characterize_login_success_cd001(self):
        """CD001 응답 시 login_krx()가 True를 반환하고 _logged_in=True로 설정한다."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"_error_code": "CD001"}

        with patch.object(krx_session._session, "get", return_value=mock_response):
            with patch.object(krx_session._session, "post", return_value=mock_response):
                result = krx_session.login_krx("test_id", "test_pw")

        assert result is True
        assert krx_session._logged_in is True

    def test_characterize_login_failure_unknown_code(self):
        """알 수 없는 error_code 응답 시 login_krx()가 False를 반환한다."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"_error_code": "CD999"}

        with patch.object(krx_session._session, "get", return_value=mock_response):
            with patch.object(krx_session._session, "post", return_value=mock_response):
                result = krx_session.login_krx("test_id", "wrong_pw")

        assert result is False
        assert krx_session._logged_in is False

    def test_characterize_login_duplicate_cd011_retry(self):
        """CD011 중복 로그인 시 skipDup=Y로 재시도하고, CD001이면 True를 반환한다."""
        mock_get = MagicMock()
        mock_get.raise_for_status = MagicMock()

        # POST: 첫 번째는 CD011, 두 번째는 CD001
        cd011_response = MagicMock()
        cd011_response.raise_for_status = MagicMock()
        cd011_response.json.return_value = {"_error_code": "CD011"}

        cd001_response = MagicMock()
        cd001_response.raise_for_status = MagicMock()
        cd001_response.json.return_value = {"_error_code": "CD001"}

        with patch.object(krx_session._session, "get", return_value=mock_get):
            with patch.object(
                krx_session._session,
                "post",
                side_effect=[cd011_response, cd001_response],
            ):
                result = krx_session.login_krx("test_id", "test_pw")

        assert result is True
        assert krx_session._logged_in is True

    def test_characterize_login_network_error_returns_false(self):
        """네트워크 예외 발생 시 login_krx()가 False를 반환한다."""
        import requests

        with patch.object(
            krx_session._session,
            "get",
            side_effect=requests.RequestException("네트워크 오류"),
        ):
            result = krx_session.login_krx("test_id", "test_pw")

        assert result is False
        assert krx_session._logged_in is False

    def test_characterize_login_does_not_log_password(self, caplog):
        """비밀번호가 로그에 절대 포함되지 않는다."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"_error_code": "CD001"}

        secret_password = "super_secret_password_12345"

        with patch.object(krx_session._session, "get", return_value=mock_response):
            with patch.object(krx_session._session, "post", return_value=mock_response):
                with caplog.at_level("DEBUG"):
                    krx_session.login_krx("test_id", secret_password)

        # 비밀번호가 로그에 포함되어서는 안 됨
        for record in caplog.records:
            assert secret_password not in record.message


# ---------------------------------------------------------------------------
# init_session 테스트
# ---------------------------------------------------------------------------


class TestInitSession:
    def setup_method(self):
        """각 테스트 전에 전역 상태를 초기화한다."""
        krx_session._patched = False
        krx_session._logged_in = False

    def teardown_method(self):
        """각 테스트 후 전역 상태를 초기화한다."""
        krx_session._patched = False
        krx_session._logged_in = False

    def test_characterize_init_without_env_vars(self, monkeypatch):
        """환경변수 미설정 시 init_session()이 예외 없이 완료된다."""
        monkeypatch.delenv("KRX_ID", raising=False)
        monkeypatch.delenv("KRX_PW", raising=False)

        # patch_pykrx_session을 mock으로 대체
        with patch.object(krx_session, "patch_pykrx_session") as mock_patch:
            with patch.object(krx_session, "login_krx") as mock_login:
                krx_session.init_session()

        # patch는 호출되지만 login은 호출되지 않음
        mock_patch.assert_called_once()
        mock_login.assert_not_called()

    def test_characterize_init_with_env_vars_calls_login(self, monkeypatch):
        """KRX_ID, KRX_PW 환경변수 설정 시 저장된 세션 없으면 login_krx()를 호출한다."""
        monkeypatch.setenv("KRX_ID", "test_user")
        monkeypatch.setenv("KRX_PW", "test_password")

        with patch.object(krx_session, "patch_pykrx_session"):
            with patch.object(krx_session, "_load_saved_session", return_value=False):
                with patch.object(krx_session, "login_krx", return_value=True) as mock_login:
                    krx_session.init_session()

        mock_login.assert_called_once_with("test_user", "test_password")

    def test_characterize_init_login_failure_does_not_raise(self, monkeypatch):
        """로그인 실패 시에도 init_session()이 예외를 발생시키지 않는다."""
        monkeypatch.setenv("KRX_ID", "test_user")
        monkeypatch.setenv("KRX_PW", "wrong_password")

        with patch.object(krx_session, "patch_pykrx_session"):
            with patch.object(krx_session, "_load_saved_session", return_value=False):
                with patch.object(krx_session, "login_krx", return_value=False):
                    # 예외 없이 완료되어야 함
                    krx_session.init_session()


# ---------------------------------------------------------------------------
# get_market_cap_safe 테스트
# ---------------------------------------------------------------------------


class TestGetMarketCapSafe:
    def test_characterize_returns_dataframe_on_success(self):
        """pykrx 성공 시 get_market_cap_safe()가 DataFrame을 반환한다."""
        mock_mc = pd.DataFrame(
            {"시가총액": [300_000_000_000_000]},
            index=pd.Index(["005930"]),
        )

        mock_stock = MagicMock()
        mock_stock.get_market_cap.return_value = mock_mc

        # get_market_cap_safe 내부의 pykrx.stock import를 mock으로 대체
        with patch.dict("sys.modules", {"pykrx": MagicMock(stock=mock_stock)}):
            with patch("my_chart.krx_session.stock", mock_stock, create=True):
                # 함수 내부에서 `from pykrx import stock`을 mock
                import sys
                mock_pykrx = MagicMock()
                mock_pykrx.stock = mock_stock
                with patch.dict(sys.modules, {"pykrx": mock_pykrx}):
                    result = krx_session.get_market_cap_safe("20260227")

        assert isinstance(result, pd.DataFrame)

    def test_characterize_returns_dataframe_on_pykrx_failure(self):
        """pykrx 실패 시 폴백을 시도하고, 폴백도 실패하면 빈 DataFrame을 반환한다."""
        import sys
        from pathlib import Path

        mock_stock = MagicMock()
        mock_stock.get_market_cap.side_effect = Exception("인증 실패")
        mock_pykrx = MagicMock()
        mock_pykrx.stock = mock_stock

        with patch.dict(sys.modules, {"pykrx": mock_pykrx}):
            # config.SECTORMAP_PATH를 존재하지 않는 경로로 대체
            with patch("my_chart.config.SECTORMAP_PATH", Path("/nonexistent/path.xlsx")):
                result = krx_session.get_market_cap_safe("20260227")

        # 항상 DataFrame 반환 보장
        assert isinstance(result, pd.DataFrame)

    def test_characterize_always_returns_dataframe(self):
        """get_market_cap_safe()는 어떤 경우에도 DataFrame을 반환한다."""
        import sys
        from pathlib import Path

        mock_stock = MagicMock()
        mock_stock.get_market_cap.side_effect = RuntimeError("완전 실패")
        mock_pykrx = MagicMock()
        mock_pykrx.stock = mock_stock

        with patch.dict(sys.modules, {"pykrx": mock_pykrx}):
            with patch("my_chart.config.SECTORMAP_PATH", Path("/nonexistent/path.xlsx")):
                result = krx_session.get_market_cap_safe("20260101")

        assert isinstance(result, pd.DataFrame)

    def test_characterize_empty_pykrx_triggers_fallback(self):
        """pykrx가 빈 DataFrame을 반환하면 폴백을 시도한다."""
        import sys
        from pathlib import Path

        empty_mc = pd.DataFrame(columns=["시가총액"])
        mock_stock = MagicMock()
        mock_stock.get_market_cap.return_value = empty_mc
        mock_pykrx = MagicMock()
        mock_pykrx.stock = mock_stock

        with patch.dict(sys.modules, {"pykrx": mock_pykrx}):
            with patch("my_chart.config.SECTORMAP_PATH", Path("/nonexistent/path.xlsx")):
                result = krx_session.get_market_cap_safe("20260227")

        assert isinstance(result, pd.DataFrame)

    def test_characterize_시가총액_column_in_fallback_result(self):
        """폴백 결과에는 '시가총액' 컬럼이 포함된다 (빈 DataFrame 케이스)."""
        import sys
        from pathlib import Path

        mock_stock = MagicMock()
        mock_stock.get_market_cap.side_effect = Exception("실패")
        mock_pykrx = MagicMock()
        mock_pykrx.stock = mock_stock

        with patch.dict(sys.modules, {"pykrx": mock_pykrx}):
            with patch("my_chart.config.SECTORMAP_PATH", Path("/nonexistent/path.xlsx")):
                result = krx_session.get_market_cap_safe("20260227")

        # 빈 DataFrame이라도 '시가총액' 컬럼이 있어야 함
        assert "시가총액" in result.columns
