# SPEC-FNGUIDE-WCOMP-001: AC-WC-001 재현 테스트 (오프라인)
"""옛 호스트 안내 페이지 재현 테스트.

옛 호스트 ``comp.fnguide.com``은 어떤 URL에도 HTTP 200과 함께 1,829바이트
"페이지가 없습니다" 안내 페이지(표 1개)를 돌려준다. 리더는 이 응답을 2xx라는
이유로 성공으로 받아들이지 말고 ``ValueError``(라우터에서 404)를 내야 한다.

실제 HTTP는 보내지 않는다. ``requests.Session.request``를 가로채
``requests.get``과 세션의 ``get`` 모두 fixture 응답을 받게 한다.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import requests

from fnguide.crawler import read_fs

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "wcomp"
LEGACY_STUB = FIXTURE_DIR / "legacy_stub_1829.html"


def _stub_response(url: str) -> requests.Response:
    """옛 안내 페이지 본문을 HTTP 200으로 담은 응답을 만든다."""
    resp = requests.Response()
    resp.status_code = 200
    resp._content = LEGACY_STUB.read_bytes()
    resp.encoding = "utf-8"
    resp.headers["Content-Type"] = "text/html; charset=utf-8"
    resp.url = url
    return resp


@pytest.fixture
def legacy_stub_everywhere(monkeypatch):
    """모든 HTTP 요청에 옛 안내 페이지를 돌려주고 요청 URL을 기록한다."""
    calls: list[str] = []

    def fake_request(self, method, url, *args, **kwargs):
        calls.append(url)
        return _stub_response(url)

    monkeypatch.setattr(requests.Session, "request", fake_request)
    return calls


def test_legacy_stub_fixture_is_the_observed_page():
    """fixture가 관측한 안내 페이지 그대로인지 확인한다(1,829바이트, 표 1개)."""
    body = LEGACY_STUB.read_bytes()
    assert len(body) == 1829
    assert body.count(b"<table") == 1


def test_ac_wc_001_legacy_stub_raises_value_error_with_code(legacy_stub_everywhere):
    """옛 안내 페이지를 받으면 read_fs가 종목 코드를 담은 ValueError를 낸다."""
    with pytest.raises(ValueError) as excinfo:
        read_fs("005930")

    assert "005930" in str(excinfo.value)
    # 가짜 응답이 실제로 쓰였는지(실제 HTTP가 나가지 않았는지) 확인한다.
    assert legacy_stub_everywhere, "요청이 가로채지지 않았다"
