# SPEC-FNGUIDE-WCOMP-001: read_snapshot(wcomp Snapshot HTML) 오프라인 테스트 — AC-WC-011, AC-WC-012
"""신사이트 스냅샷 리더 테스트.

실제 HTTP는 보내지 않는다. ``requests.Session.request``를 가로채
``tests/fnguide/fixtures/wcomp/``의 실응답 축소본을 돌려준다.
"""

from __future__ import annotations

import inspect
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import pytest
import requests
from bs4 import BeautifulSoup

from fnguide import crawler
from fnguide.crawler import read_snapshot

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "wcomp"
# 스냅샷 요청 코드 → fixture. 005935는 사이트가 005930 페이지를 내준 실응답이다.
SNAPSHOT_FILE = {
    "005935": "snapshot_005935_served_as_005930.html",
    "999999": "snapshot_999999_object_moved.html",
}
REPORT_KEYS = {
    "시가총액(상장예정포함,억원)",
    "발행주식수(보통주)",
    "발행주식수(우선주)",
    "자기주식",
    "베타(1년)",
    "PER",
    "12M PER",
    "업종 PER",
    "PBR",
    "배당수익률",
    "Summary",
    "종목명",
}


def _resp(body: bytes, url: str) -> requests.Response:
    r = requests.Response()
    r.status_code = 200
    r._content = body
    r.encoding = "utf-8"
    r.url = url
    return r


@pytest.fixture
def site(monkeypatch):
    """스냅샷·재무제표 fixture를 돌려주는 가짜 사이트. state["snapshot_html"]로 본문을 바꿀 수 있다."""
    state = {"calls": [], "snapshot_html": {}}

    def fake_request(self, method, url, **kwargs):
        state["calls"].append({"url": url, **kwargs})
        if urlparse(url).hostname != "wcomp.fnguide.com":
            # 옛 호스트는 어떤 URL에도 1,829바이트 안내 페이지를 돌려준다(AC-WC-001 fixture)
            return _resp((FIXTURE_DIR / "legacy_stub_1829.html").read_bytes(), url)
        p = kwargs.get("params") or {}
        endpoint, code = url.rsplit("/", 1)[-1], p.get("cmp_cd")
        if endpoint == "Snapshot":
            if code in state["snapshot_html"]:
                return _resp(state["snapshot_html"][code].encode("utf-8"), url)
            name = SNAPSHOT_FILE.get(code, f"Snapshot_{code}.html")
            return _resp((FIXTURE_DIR / name).read_bytes(), url)
        path = FIXTURE_DIR / f"{endpoint}_{code}_{p.get('freq_typ')}_{p.get('consol_typ')}.json"
        assert path.exists(), f"fixture 없음: {path.name}"
        return _resp(path.read_bytes(), url)

    monkeypatch.setattr(requests.Session, "request", fake_request)
    return state


def _without_exact_treasury_row(code: str) -> str:
    """정확히 '자사주'인 주주 표 행만 지운 조작본. '자사주(자사주+자사주신탁)' 행은 남긴다."""
    soup = BeautifulSoup((FIXTURE_DIR / f"Snapshot_{code}.html").read_text(encoding="utf-8"), "html.parser")
    rows = [th.find_parent("tr") for th in soup.find_all("th") if th.get_text(strip=True) == "자사주"]
    assert len(rows) == 1
    rows[0].decompose()
    assert "자사주(자사주+자사주신탁)" in str(soup)
    return str(soup)


# ───────────────────────── AC-WC-011 ─────────────────────────


def test_ac_wc_011_served_as_other_company_raises(site):
    with pytest.raises(ValueError, match="005935"):
        read_snapshot("005935")


def test_ac_wc_011_missing_cmp_cd_raises(site):
    with pytest.raises(ValueError, match="999999"):
        read_snapshot("999999")


def test_ac_wc_011_contrast_no_cmp_cd_check(site, monkeypatch):
    monkeypatch.setattr(crawler, "_check_snapshot_code", lambda *a, **k: None)
    report, _, _ = read_snapshot("005935")
    assert report["종목명"] == "삼성전자"


def test_snapshot_code_validation_no_request(site):
    """REQ-WC-001: 코드 형식이 틀리면 요청 없이 ValueError."""
    with pytest.raises(ValueError):
        read_snapshot("00593a")
    assert site["calls"] == []


# ───────────────────────── AC-WC-012 ─────────────────────────


def test_ac_wc_012_report_values_005930(site):
    report, df_snap, df_snap_ann = read_snapshot("005930")
    assert set(report) >= REPORT_KEYS
    assert report["시가총액(상장예정포함,억원)"] == 17748495
    assert report["발행주식수(보통주)"] == 5846278608
    assert report["발행주식수(우선주)"] == 802371203
    assert report["자기주식"] == 133670794
    assert report["베타(1년)"] == pytest.approx(1.27893)
    assert report["종목명"] == "삼성전자"
    assert "1969년" in report["Summary"]
    for frame in (df_snap, df_snap_ann):
        assert isinstance(frame, pd.DataFrame) and frame.empty
    # account_type 인자는 받되 무시한다(REQ-WC-013)
    assert read_snapshot("005930", "IFRS(별도)")[0] == report
    assert len(site["calls"]) == 2  # 호출마다 스냅샷 1회


@pytest.mark.parametrize(
    "code,name", [("403870", "HPSP"), ("105560", "KB금융"), ("001750", "한양증권"), ("330590", "롯데리츠")]
)
def test_ac_wc_012_company_name(site, code, name):
    report, _, _ = read_snapshot(code)
    assert report["종목명"] == name
    assert set(report) >= REPORT_KEYS


def test_ac_wc_012_treasury_exact_row_only(site):
    site["snapshot_html"]["005930"] = _without_exact_treasury_row("005930")
    report, _, _ = read_snapshot("005930")
    assert report["자기주식"] == 0


def test_ac_wc_012_analyze_dashboard_company_name(site):
    from fnguide.dashboard import analyze_dashboard

    assert analyze_dashboard("005930").company_name == "삼성전자"


def test_ac_wc_012_contrast_prefix_match_treasury(site, monkeypatch):
    def prefix_value(soup, label):
        for th in soup.find_all("th"):
            if crawler._label(th).startswith(label):
                td = th.find_next_sibling("td")
                return td.get_text(strip=True) if td else ""
        return None

    monkeypatch.setattr(crawler, "_row_value", prefix_value)
    site["snapshot_html"]["005930"] = _without_exact_treasury_row("005930")
    report, _, _ = read_snapshot("005930")
    assert report["자기주식"] in (133670794, 1)


def test_ac_wc_012_contrast_no_company_name(site, monkeypatch):
    from fnguide.dashboard import analyze_dashboard

    monkeypatch.setattr(crawler, "_NAME_ID", "__absent__")
    assert analyze_dashboard("005930").company_name == "005930"


# ───────────────────────── AC-WC-013 ─────────────────────────

OLD_HOST = "comp.fnguide.com"
NEW_HOST = "wcomp.fnguide.com"


def _host_violations(calls):
    """옛 호스트·컨센서스 경로·새 호스트 밖 요청을 찾는다. 호스트는 파싱한 이름을 정확히
    비교한다 — 'wcomp.fnguide.com'은 문자열 'comp.fnguide.com'을 품고 있어 부분 문자열
    판정은 정상 요청을 모두 위반으로 잡는다(plan-audit iteration 4 D2)."""
    urls = [c["url"] for c in calls]
    return {
        "old_host": [u for u in urls if urlparse(u).hostname == OLD_HOST],
        "01_06": [u for u in urls if "01_06" in u],
        "not_new_host": [u for u in urls if urlparse(u).hostname != NEW_HOST],
    }


def test_ac_wc_013_eight_tuple_and_no_consensus_request(site):
    from fnguide.crawler import get_fnguide

    assert list(inspect.signature(get_fnguide).parameters) == ["code"]
    error: Exception | None = None
    try:
        result = get_fnguide("005930")
    except Exception as e:  # noqa: BLE001 — 요청 기록 판정을 먼저 보고 아래에서 다시 던진다
        error = e
    # 호스트 판정은 예외 여부와 무관하게 먼저 본다: 옛 호스트 요청이 끼면 그 응답을
    # 파싱하다 예외가 나기 쉬워, 예외부터 보면 URL 단언이 가려진다.
    assert _host_violations(site["calls"]) == {"old_host": [], "01_06": [], "not_new_host": []}
    assert len(site["calls"]) <= 8
    if error is not None:
        raise error
    assert len(result) == 8
    for pos in (2, 3, 4):
        assert isinstance(result[pos], pd.DataFrame) and result[pos].empty
    assert result[6] == "IFRS(연결)"
    assert isinstance(result[7], pd.DataFrame)


def test_ac_wc_013_contrast_consensus_request_is_caught(site, monkeypatch):
    """대조: 실제 get_fnguide가 컨센서스를 다시 요청하게 되돌리면 같은 판정이
    옛 호스트와 01_06 경로를 잡는다. get_fnguide가 부르는 read_snapshot을 감싸
    원래 스냅샷 뒤에 read_consensus를 부르게 한다(sync-audit F9)."""
    from fnguide.crawler import get_fnguide

    original = crawler.read_snapshot

    def snapshot_then_consensus(code, account_type="IFRS(연결)"):
        result = original(code, account_type)
        crawler.read_consensus(code, account_type)
        return result

    monkeypatch.setattr(crawler, "read_snapshot", snapshot_then_consensus)
    try:
        get_fnguide("005930")
    except Exception:  # noqa: BLE001 — 옛 호스트는 안내 페이지라 파싱에서 실패한다. 판정은 요청 기록으로 한다
        pass
    found = _host_violations(site["calls"])
    assert len(found["old_host"]) == 1 and len(found["01_06"]) == 1, found
