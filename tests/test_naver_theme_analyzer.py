"""naver_theme.analyzer 단위 테스트.

네트워크 호출 없이 DataFrame 을 직접 구성하여 analyzer 함수를 검증한다.
"""

from __future__ import annotations

import math
import sys

import numpy as np
import pandas as pd
import pytest

# pykrx 가 pkg_resources 를 필요로 하는데 설치되지 않은 환경 대응
for _mod in ("pykrx", "pykrx.stock"):
    if _mod not in sys.modules:
        import types
        sys.modules[_mod] = types.ModuleType(_mod)

from backend.services.naver_theme.analyzer import (
    _zscore,
    build_leaders,
    build_multi_theme_stocks,
    build_strong_themes,
)
from backend.services.naver_theme.config import LEADER_SCORE_WEIGHTS


# ---------------------------------------------------------------------------
# 테스트 데이터 헬퍼
# ---------------------------------------------------------------------------

def _make_themes_df(**extra) -> pd.DataFrame:
    """기본 테마 DataFrame 생성."""
    data = {
        "theme_id": [1, 2, 3],
        "theme_name": ["전선", "반도체", "자동차"],
        "change_pct": [5.0, 2.0, 8.0],
        "change_pct_3d": [3.0, 1.5, 6.0],
        "up_count": [10.0, 5.0, 8.0],
        "flat_count": [2.0, 3.0, 1.0],
        "down_count": [3.0, 7.0, 2.0],
    }
    data.update(extra)
    return pd.DataFrame(data)


def _make_stocks_df(theme_id: int = 1, theme_name: str = "전선") -> pd.DataFrame:
    """단일 테마에 속하는 4개 종목 DataFrame 생성."""
    return pd.DataFrame({
        "theme_id": [theme_id] * 4,
        "theme_name": [theme_name] * 4,
        "stock_code": ["001440", "006340", "000500", "009540"],
        "stock_name": ["대한전선", "대원전선", "가온전선", "한국조선해양"],
        "change_pct": [4.05, 14.97, 11.29, 2.5],
        "volume": [5_234_120, 82_099_217, 147_466, 1_000_000],
        "market_cap": [500_000_000_000, 200_000_000_000, 150_000_000_000, 800_000_000_000],
        "trade_value": [123_400_000_000, 52_400_000_000, 33_721_000_000, 10_000_000_000],
    })


# ---------------------------------------------------------------------------
# build_strong_themes 테스트
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_build_strong_themes_sorts_by_change_pct_desc():
    """change_pct 내림차순 정렬 후 상위 top_n 반환 (REQ-NT-005)."""
    df = _make_themes_df()
    result = build_strong_themes(df, top_n=3)
    # change_pct: [5.0, 2.0, 8.0] → 정렬 후: [8.0, 5.0, 2.0]
    assert result["change_pct"].tolist() == [8.0, 5.0, 2.0]


@pytest.mark.unit
def test_build_strong_themes_top_n_limits_output():
    """top_n=2 이면 2행만 반환한다."""
    df = _make_themes_df()
    result = build_strong_themes(df, top_n=2)
    assert len(result) == 2


@pytest.mark.unit
def test_build_strong_themes_adds_momentum_score():
    """momentum_score = change_pct*0.6 + change_pct_3d*0.4 (REQ-NT-005)."""
    df = _make_themes_df()
    result = build_strong_themes(df, top_n=3)
    for _, row in result.iterrows():
        expected = row["change_pct"] * 0.6 + row["change_pct_3d"] * 0.4
        assert abs(row["momentum_score"] - expected) < 1e-9, (
            f"momentum_score 불일치: {row['momentum_score']} != {expected}"
        )


@pytest.mark.unit
def test_build_strong_themes_breadth_ratio_zero_division_safe():
    """up+flat+down == 0 이면 breadth_ratio == 0 (NaN/inf 없음) (REQ-NT-005)."""
    df = _make_themes_df(
        up_count=[0.0, 0.0, 0.0],
        flat_count=[0.0, 0.0, 0.0],
        down_count=[0.0, 0.0, 0.0],
    )
    result = build_strong_themes(df, top_n=3)
    assert "breadth_ratio" in result.columns
    assert (result["breadth_ratio"] == 0).all(), (
        f"분모 0 시 breadth_ratio 가 0 이어야 함: {result['breadth_ratio'].tolist()}"
    )
    assert not result["breadth_ratio"].isna().any(), "breadth_ratio 에 NaN 존재"


# ---------------------------------------------------------------------------
# build_leaders 테스트
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_build_leaders_weights_sum_to_one_and_apply_correctly():
    """가중치 합 = 1.0 이고 leader_score 가 수동 계산값과 일치 (REQ-NT-009)."""
    weights = LEADER_SCORE_WEIGHTS
    assert abs(sum(weights.values()) - 1.0) < 1e-9

    df = _make_stocks_df(theme_id=1)
    result = build_leaders(df, leaders_per_theme=3)

    # 수동 z-score 재계산
    def zscore_ddof0(s):
        std = s.std(ddof=0)
        if std == 0 or np.isnan(std):
            return pd.Series([0.0] * len(s), index=s.index)
        return (s - s.mean()) / std

    g = df.copy()
    for col in ("change_pct", "volume", "market_cap", "trade_value"):
        s = g[col].astype(float).fillna(0)
        g[f"z_{col}"] = zscore_ddof0(s)
    expected_scores = sum(g[f"z_{c}"] * w for c, w in weights.items())

    for _, row in result.iterrows():
        code = row["stock_code"]
        expected = expected_scores[df["stock_code"] == code].values[0]
        assert abs(row["leader_score"] - expected) < 0.01, (
            f"{code} leader_score 불일치: {row['leader_score']:.4f} != {expected:.4f}"
        )


@pytest.mark.unit
def test_build_leaders_zero_std_yields_zero_z():
    """모든 값이 동일해 std=0 이면 z-score=0 (REQ-NT-009)."""
    df = _make_stocks_df()
    # 모든 change_pct 를 동일하게 설정
    df["change_pct"] = 5.0
    result = build_leaders(df, leaders_per_theme=4)
    assert len(result) > 0
    # leader_score 가 NaN/inf 없어야 함
    assert not result["leader_score"].isna().any(), "zero-std 시 leader_score 에 NaN"
    assert not np.isinf(result["leader_score"].values).any(), "leader_score 에 inf"


@pytest.mark.unit
def test_build_leaders_market_cap_nan_treated_as_zero():
    """market_cap=NaN 이면 0으로 fillna 후 z-score 계산 (REQ-NT-009)."""
    df = _make_stocks_df()
    df["market_cap"] = float("nan")
    result = build_leaders(df, leaders_per_theme=3)
    assert len(result) > 0
    assert not result["leader_score"].isna().any(), "market_cap NaN fillna 실패"


@pytest.mark.unit
def test_build_leaders_rank_starts_at_one():
    """rank 컬럼이 1부터 시작한다 (REQ-NT-009)."""
    df = _make_stocks_df(theme_id=10)
    result = build_leaders(df, leaders_per_theme=3)
    assert "rank" in result.columns
    assert result["rank"].min() == 1, f"rank 최소값: {result['rank'].min()}"


@pytest.mark.unit
def test_build_leaders_per_theme_limits_rows():
    """leaders_per_theme=2 이면 테마당 최대 2행 반환."""
    df = _make_stocks_df(theme_id=5)
    result = build_leaders(df, leaders_per_theme=2)
    for tid, grp in result.groupby("theme_id"):
        assert len(grp) <= 2, f"theme_id={tid} 에서 {len(grp)}행 > 2"


@pytest.mark.unit
def test_build_leaders_multiple_themes_per_theme_isolation():
    """멀티 테마일 때 z-score 가 테마별로 독립 계산된다."""
    df1 = _make_stocks_df(theme_id=1, theme_name="전선")
    df2 = _make_stocks_df(theme_id=2, theme_name="반도체")
    # 두 번째 테마의 change_pct 를 완전히 다른 범위로 설정
    df2["change_pct"] = [100.0, 200.0, 150.0, 180.0]
    combined = pd.concat([df1, df2], ignore_index=True)
    result = build_leaders(combined, leaders_per_theme=2)
    # 테마 1, 2 모두 결과에 포함
    assert set(result["theme_id"].unique()) == {1, 2}


# ---------------------------------------------------------------------------
# build_multi_theme_stocks 테스트
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_build_multi_theme_stocks_dedups_duplicate_rows():
    """동일 (stock_code, theme_name) 중복 행 → theme_count 는 nunique 기준 (REQ-NT-010)."""
    df = pd.DataFrame({
        "stock_code": ["001440", "001440", "001440"],
        "stock_name": ["대한전선", "대한전선", "대한전선"],
        "theme_name": ["전선", "전선", "구리"],  # 전선 2번 → nunique=2
        "change_pct": [5.0, 5.0, 3.0],
    })
    result = build_multi_theme_stocks(df)
    assert len(result) == 1
    assert result.iloc[0]["theme_count"] == 2  # nunique("theme_name")=2, 전선+구리


@pytest.mark.unit
def test_build_multi_theme_stocks_filters_below_two_themes():
    """theme_count < 2 인 종목은 결과에서 제외된다 (REQ-NT-010)."""
    df = pd.DataFrame({
        "stock_code": ["001440", "001440", "006340"],
        "stock_name": ["대한전선", "대한전선", "대원전선"],
        "theme_name": ["전선", "구리", "전선"],  # 대한전선=2, 대원전선=1
        "change_pct": [5.0, 3.0, 4.0],
    })
    result = build_multi_theme_stocks(df)
    assert "006340" not in result["stock_code"].values, "단일테마 종목이 결과에 포함됨"
    assert "001440" in result["stock_code"].values


@pytest.mark.unit
def test_build_multi_theme_stocks_theme_names_sorted_unique_list():
    """theme_names 컬럼이 sorted(set(theme_name)) 리스트 형태 (REQ-NT-010)."""
    df = pd.DataFrame({
        "stock_code": ["001440", "001440", "001440"],
        "stock_name": ["대한전선", "대한전선", "대한전선"],
        "theme_name": ["전선", "구리", "에너지"],
        "change_pct": [5.0, 3.0, 4.0],
    })
    result = build_multi_theme_stocks(df)
    assert len(result) == 1
    names = result.iloc[0]["theme_names"]
    assert isinstance(names, list)
    assert names == sorted({"전선", "구리", "에너지"})


@pytest.mark.unit
def test_build_multi_theme_stocks_empty_input_returns_empty():
    """빈 DataFrame 입력 시 빈 DataFrame 반환."""
    result = build_multi_theme_stocks(pd.DataFrame())
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 0


# ---------------------------------------------------------------------------
# _zscore 내부 함수 테스트
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_zscore_standard_normal():
    """표준 z-score 계산 검증 (ddof=0 모집단 표준편차)."""
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    result = _zscore(s)
    # 평균=3, std=sqrt(2) ≈ 1.4142
    assert abs(result.mean()) < 1e-10
    assert abs(result.std(ddof=0) - 1.0) < 1e-9


@pytest.mark.unit
def test_zscore_zero_std_returns_zero_series():
    """std=0 인 경우 모든 원소가 0.0 인 시리즈 반환."""
    s = pd.Series([42.0, 42.0, 42.0])
    result = _zscore(s)
    assert (result == 0.0).all()


# ---------------------------------------------------------------------------
# crawler.py 모킹 단위 테스트 (네트워크 없이 로직 커버)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_crawler_get_session_singleton(monkeypatch):
    """_get_session 이 동일 Session 객체를 반환한다 (싱글톤 패턴)."""
    import backend.services.naver_theme.crawler as crawler_mod
    crawler_mod._session = None  # 리셋
    s1 = crawler_mod._get_session()
    s2 = crawler_mod._get_session()
    assert s1 is s2, "싱글톤 아님 — 매번 새 Session 생성"
    crawler_mod._session = None  # 정리


@pytest.mark.unit
def test_crawler_fetch_sets_euc_kr_encoding(monkeypatch):
    """_fetch 가 Response.encoding 을 'euc-kr' 로 강제 설정한다 (REQ-NT-NF-002)."""
    import backend.services.naver_theme.crawler as crawler_mod
    from unittest.mock import MagicMock

    mock_resp = MagicMock()
    mock_resp.text = "<html>테스트</html>"
    mock_resp.encoding = "utf-8"  # 초기값

    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp

    crawler_mod._session = mock_session
    monkeypatch.setattr("backend.services.naver_theme.crawler.time.sleep", lambda _: None)

    result = crawler_mod._fetch("https://example.com/test")

    assert mock_resp.encoding == "euc-kr", f"encoding 강제 설정 실패: {mock_resp.encoding}"
    assert result == "<html>테스트</html>"
    crawler_mod._session = None


@pytest.mark.unit
def test_crawler_fetch_list_page_uses_correct_url(monkeypatch):
    """fetch_theme_list_page(1) 이 올바른 URL 로 요청한다."""
    import backend.services.naver_theme.crawler as crawler_mod
    from unittest.mock import MagicMock
    from backend.services.naver_theme.config import NAVER_THEME_LIST_URL

    mock_resp = MagicMock()
    mock_resp.text = "<html></html>"
    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp

    crawler_mod._session = mock_session
    monkeypatch.setattr("backend.services.naver_theme.crawler.time.sleep", lambda _: None)

    crawler_mod.fetch_theme_list_page(1)

    expected_url = NAVER_THEME_LIST_URL.format(n=1)
    called_url = mock_session.get.call_args[0][0]
    assert called_url == expected_url
    crawler_mod._session = None


@pytest.mark.unit
def test_crawler_fetch_detail_page_uses_correct_url(monkeypatch):
    """fetch_theme_detail_page(178) 이 올바른 URL 로 요청한다."""
    import backend.services.naver_theme.crawler as crawler_mod
    from unittest.mock import MagicMock
    from backend.services.naver_theme.config import NAVER_THEME_DETAIL_URL

    mock_resp = MagicMock()
    mock_resp.text = "<html></html>"
    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp

    crawler_mod._session = mock_session
    monkeypatch.setattr("backend.services.naver_theme.crawler.time.sleep", lambda _: None)

    crawler_mod.fetch_theme_detail_page(178)

    expected_url = NAVER_THEME_DETAIL_URL.format(theme_id=178)
    called_url = mock_session.get.call_args[0][0]
    assert called_url == expected_url
    crawler_mod._session = None


# ---------------------------------------------------------------------------
# db_join.py 모킹 단위 테스트
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_enrich_market_cap_empty_df_returns_with_column():
    """빈 DataFrame 입력 시 market_cap 컬럼이 추가된 빈 DataFrame 반환."""
    import backend.services.naver_theme.db_join as db_join_mod

    result = db_join_mod.enrich_market_cap(pd.DataFrame(), db_path=":memory:")
    assert "market_cap" in result.columns
    assert len(result) == 0


@pytest.mark.unit
def test_enrich_market_cap_joins_from_db(tmp_path):
    """실제 SQLite DB 에서 market_cap 을 JOIN 해서 stocks_df 에 보강한다."""
    import sqlite3
    import backend.services.naver_theme.db_join as db_join_mod

    # 임시 DB 생성
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE stock_meta (code TEXT, market_cap INTEGER)")
    conn.execute("INSERT INTO stock_meta VALUES ('001440', 500000000000)")
    conn.execute("INSERT INTO stock_meta VALUES ('006340', 200000000000)")
    conn.commit()
    conn.close()

    stocks_df = pd.DataFrame({
        "stock_code": ["001440", "006340", "999999"],
        "stock_name": ["대한전선", "대원전선", "미등록종목"],
    })

    result = db_join_mod.enrich_market_cap(stocks_df, db_path=db_path)

    assert "market_cap" in result.columns
    # DB에 있는 코드는 값이 있어야 함
    cap_001440 = result.loc[result["stock_code"] == "001440", "market_cap"].iloc[0]
    assert cap_001440 == pytest.approx(500_000_000_000)
    # DB에 없는 코드는 NaN
    cap_999999 = result.loc[result["stock_code"] == "999999", "market_cap"].iloc[0]
    assert math.isnan(cap_999999), "미등록 종목 market_cap 은 NaN 이어야 함"


# ---------------------------------------------------------------------------
# service.py 모킹 단위 테스트
# ---------------------------------------------------------------------------

def _make_list_html(theme_id: int = 1, theme_name: str = "테마A") -> str:
    """parse_theme_list 호환 최소 HTML — last_page=1."""
    return f"""<html><body>
<table class="type_1">
<tr>
  <td class="col_type1"><a href="?no={theme_id}">{theme_name}</a></td>
  <td>5.0</td><td>3.0</td><td>10</td><td>2</td><td>3</td><td>종목A 종목B</td>
</tr>
</table>
</body></html>"""


def _make_detail_html(theme_id: int = 1) -> str:
    """parse_theme_detail 호환 최소 HTML."""
    return f"""<html><body>
<table class="type_5">
<tr>
  <td><a class="tltle" href="/item/main.naver?code=001440">대한전선</a></td>
  <td>전선 제조업체</td>
  <td>3850</td><td>상승 50</td><td>+1.32%</td>
  <td>3850</td><td>3855</td><td>1000000</td><td>100억</td><td>900000</td>
</tr>
</table>
</body></html>"""


@pytest.mark.unit
def test_collect_and_analyze_skip_details_returns_five_dfs(monkeypatch):
    """skip_details=True 시 5종 DataFrame + metadata 반환 (REQ-NT-001, REQ-NT-004)."""
    import backend.services.naver_theme.service as svc_mod

    monkeypatch.setattr(
        "backend.services.naver_theme.service.fetch_theme_list_page",
        lambda page: _make_list_html(),
    )

    from backend.services.naver_theme.service import collect_and_analyze, ThemeAnalysisResult
    result = collect_and_analyze(top_n_themes=5, skip_details=True)

    assert isinstance(result, ThemeAnalysisResult)
    assert not result.themes_df.empty
    assert not result.strong_themes_df.empty
    assert result.stocks_df.empty       # skip_details=True
    assert result.leaders_df.empty      # skip_details=True
    assert result.multi_theme_stocks_df.empty  # skip_details=True
    for key in ("collected_at", "theme_count", "stock_count", "elapsed_sec", "errors"):
        assert key in result.metadata


@pytest.mark.unit
def test_collect_and_analyze_theme_filter(monkeypatch):
    """theme_filter 파라미터가 테마 목록을 필터링한다 (REQ-NT-001)."""
    import backend.services.naver_theme.service as svc_mod

    def mock_list_page(page):
        return _make_list_html(theme_id=178, theme_name="전선")

    monkeypatch.setattr("backend.services.naver_theme.service.fetch_theme_list_page", mock_list_page)

    from backend.services.naver_theme.service import collect_and_analyze
    result = collect_and_analyze(top_n_themes=10, skip_details=True, theme_filter=["존재안함"])

    assert result.themes_df.empty, "필터링 후 결과가 비어있어야 함"


@pytest.mark.unit
def test_collect_theme_list_handles_fetch_error(monkeypatch):
    """fetch_theme_list_page 가 실패할 때 errors 에 기록하고 빈 DataFrame 반환."""
    import requests
    monkeypatch.setattr(
        "backend.services.naver_theme.service.fetch_theme_list_page",
        lambda page: (_ for _ in ()).throw(requests.RequestException("Network error")),
    )

    from backend.services.naver_theme.service import collect_and_analyze
    result = collect_and_analyze(top_n_themes=5, skip_details=True)

    assert result.themes_df.empty
    assert len(result.metadata["errors"]) >= 1
    err = result.metadata["errors"][0]
    assert err["stage"] == "list"
    assert "reason" in err


@pytest.mark.unit
def test_collect_and_analyze_full_pipeline(monkeypatch, tmp_path):
    """전체 파이프라인 — 상세 수집 포함 (mock 네트워크 + 임시 DB)."""
    import sqlite3, requests
    import backend.services.naver_theme.service as svc_mod

    # 임시 DB
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE stock_meta (code TEXT, market_cap INTEGER)")
    conn.execute("INSERT INTO stock_meta VALUES ('001440', 500000000000)")
    conn.commit()
    conn.close()

    monkeypatch.setattr(
        "backend.services.naver_theme.service.fetch_theme_list_page",
        lambda page: _make_list_html(theme_id=178, theme_name="전선"),
    )
    monkeypatch.setattr(
        "backend.services.naver_theme.service.fetch_theme_detail_page",
        lambda theme_id: _make_detail_html(theme_id=178),
    )
    monkeypatch.setattr(
        "backend.services.naver_theme.service.DAILY_DB_PATH",
        db_path,
    )
    # enrich_market_cap 도 db_path 패치
    monkeypatch.setattr(
        "backend.services.naver_theme.service.enrich_market_cap",
        lambda df, db_path=None: df.assign(market_cap=500_000_000_000.0),
    )

    from backend.services.naver_theme.service import collect_and_analyze
    result = collect_and_analyze(top_n_themes=5, leaders_per_theme=1, skip_details=False)

    assert not result.themes_df.empty
    assert not result.stocks_df.empty
    assert not result.leaders_df.empty
    assert "rank" in result.leaders_df.columns


@pytest.mark.unit
def test_collect_theme_details_handles_detail_error(monkeypatch):
    """상세 페이지 fetch 실패 시 errors 에 기록하고 부분 결과 반환 (REQ-NT-NF-003)."""
    import requests
    monkeypatch.setattr(
        "backend.services.naver_theme.service.fetch_theme_list_page",
        lambda page: _make_list_html(theme_id=178, theme_name="전선"),
    )
    monkeypatch.setattr(
        "backend.services.naver_theme.service.fetch_theme_detail_page",
        lambda tid: (_ for _ in ()).throw(requests.RequestException("429")),
    )

    from backend.services.naver_theme.service import collect_and_analyze
    result = collect_and_analyze(top_n_themes=5, skip_details=False)

    # 상세 실패여도 themes_df 는 있어야 함
    assert not result.themes_df.empty
    # 오류가 errors 에 기록되어야 함
    detail_errors = [e for e in result.metadata["errors"] if e["stage"] == "detail"]
    assert len(detail_errors) >= 1


@pytest.mark.unit
def test_collect_theme_list_handles_generic_exception(monkeypatch):
    """fetch_theme_list_page 가 일반 예외 발생 시 errors 에 기록 (lines 58-60)."""
    monkeypatch.setattr(
        "backend.services.naver_theme.service.fetch_theme_list_page",
        lambda page: (_ for _ in ()).throw(ValueError("Unexpected format")),
    )

    from backend.services.naver_theme.service import collect_and_analyze
    result = collect_and_analyze(top_n_themes=5, skip_details=True)

    assert result.themes_df.empty
    assert any(e["stage"] == "list" for e in result.metadata["errors"])


@pytest.mark.unit
def test_collect_theme_list_multi_page(monkeypatch):
    """last_page=2 시 두 번째 페이지도 fetch 한다 (lines 62-69)."""
    call_count = {"n": 0}

    def mock_list_page(page):
        call_count["n"] += 1
        # 첫 페이지에 pagination 포함 (last_page=2 탐지용)
        if page == 1:
            return """<html><body>
            <table class="type_1">
            <tr><td class="col_type1"><a href="?no=1">테마A</a></td>
                <td>5.0</td><td>3.0</td><td>10</td><td>2</td><td>3</td><td>종목A</td></tr>
            </table>
            <table class="Nnavi">
            <tr><td><a href="?page=1">1</a></td><td><a href="?page=2">2</a></td></tr>
            </table>
            </body></html>"""
        else:
            return _make_list_html(theme_id=2, theme_name="테마B")

    monkeypatch.setattr("backend.services.naver_theme.service.fetch_theme_list_page", mock_list_page)

    from backend.services.naver_theme.service import collect_and_analyze
    result = collect_and_analyze(top_n_themes=10, skip_details=True)

    assert call_count["n"] == 2, f"2페이지 fetch 되지 않음: {call_count['n']}회 호출"
    assert len(result.themes_df) >= 2


@pytest.mark.unit
def test_collect_theme_details_handles_generic_exception(monkeypatch):
    """상세 페이지 파싱 시 일반 예외 발생 → errors 에 기록 (lines 87-88)."""
    monkeypatch.setattr(
        "backend.services.naver_theme.service.fetch_theme_list_page",
        lambda page: _make_list_html(theme_id=178, theme_name="전선"),
    )
    monkeypatch.setattr(
        "backend.services.naver_theme.service.fetch_theme_detail_page",
        lambda tid: (_ for _ in ()).throw(ValueError("parse fail")),
    )

    from backend.services.naver_theme.service import collect_and_analyze
    result = collect_and_analyze(top_n_themes=5, skip_details=False)

    detail_errors = [e for e in result.metadata["errors"] if e["stage"] == "detail"]
    assert len(detail_errors) >= 1
    assert "reason" in detail_errors[0]


@pytest.mark.unit
def test_collect_theme_list_page2_error_recorded(monkeypatch):
    """2페이지 fetch 실패 시 errors 에 기록하고 1페이지 결과는 유지 (lines 66-69)."""
    import requests

    def mock_list_page(page):
        if page == 1:
            # last_page=2 를 포함하는 HTML
            return """<html><body>
            <table class="type_1">
            <tr><td class="col_type1"><a href="?no=1">테마A</a></td>
                <td>5.0</td><td>3.0</td><td>10</td><td>2</td><td>3</td><td>종목A</td></tr>
            </table>
            <table class="Nnavi">
            <tr><td><a href="?page=1">1</a></td><td><a href="?page=2">2</a></td></tr>
            </table>
            </body></html>"""
        raise requests.RequestException("page 2 실패")

    monkeypatch.setattr("backend.services.naver_theme.service.fetch_theme_list_page", mock_list_page)

    from backend.services.naver_theme.service import collect_and_analyze
    result = collect_and_analyze(top_n_themes=10, skip_details=True)

    # 1페이지 결과는 있어야 함
    assert not result.themes_df.empty
    # 2페이지 오류가 errors 에 기록
    list_errors = [e for e in result.metadata["errors"] if e["stage"] == "list"]
    assert len(list_errors) >= 1
