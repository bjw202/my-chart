# SPEC-FNGUIDE-WCOMP-001: read_fs(wcomp JSON) 오프라인 테스트 — AC-WC-002 ~ AC-WC-010
"""신사이트 재무제표 리더 테스트.

실제 HTTP는 보내지 않는다. ``requests.Session.request``를 가로채
``tests/fnguide/fixtures/wcomp/``의 실응답 축소본을 돌려준다. 대조 테스트
(``_contrast``)는 검증 대상 단위 하나만 순진한 구현으로 바꾼 뒤 프로덕션 경로
(``read_fs`` → ``fs_analysis`` / ``_calc_business_performance``)를 그대로 부른다.
기대값은 acceptance.md에 고정된 값이다.
"""

from __future__ import annotations

import copy
import json
import logging
import re
from pathlib import Path

import pytest
import requests

from fnguide import account_alias as aa
from fnguide import crawler
from fnguide.analysis import calc_weight_coeff, fs_analysis
from fnguide.crawler import read_fs
from fnguide.dashboard import _calc_business_performance

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "wcomp"
# 응답이 하나뿐인 코드: 모든 요청에 같은 실응답을 돌려준다(README 참조)
SINGLE_BODY = {
    "005935": FIXTURE_DIR / "getFinIncome_005935_Y_C.json",
    "999999": FIXTURE_DIR / "getFinIncome_999999_Y_C.html",
}
TOL = 0.01


def _norm(name: str) -> str:
    return name.replace(" ", "").replace("\xa0", "")


def _raw(ep: str, code: str, freq: str, consol: str) -> dict:
    """fixture JSON을 dict로 읽는다(조작본을 만들 때 쓴다)."""
    return json.loads((FIXTURE_DIR / f"{ep}_{code}_{freq}_{consol}.json").read_text(encoding="utf-8"))


def _raw_value(ep, code, freq, consol, label, val):
    """fixture에서 정규화 이름 label인 첫 행의 val 값을 float로 읽는다."""
    for r in _raw(ep, code, freq, consol)["dataset"]["data"]:
        if _norm(r["NAME"]) == label:
            return float(r[val])
    raise KeyError(label)


def _resp(body: bytes, url: str, status: int = 200) -> requests.Response:
    r = requests.Response()
    r.status_code = status
    r._content = body
    r.encoding = "utf-8"
    r.url = url
    return r


@pytest.fixture
def site(monkeypatch):
    """fixture 응답을 돌려주는 가짜 사이트. 요청을 기록하고 조작본을 끼워 넣을 수 있다.

    site["calls"]: 요청 기록(url, kwargs)
    site["override"][(ep, code, freq, consol)]: dict를 받아 고친 dict를 돌려주는 함수,
        또는 (status, bytes) 튜플, 또는 예외 인스턴스
    """
    state = {"calls": [], "override": {}}

    def fake_request(self, method, url, **kwargs):
        state["calls"].append({"url": url, **kwargs})
        p = kwargs.get("params") or {}
        key = (url.rsplit("/", 1)[-1], p.get("cmp_cd"), p.get("freq_typ"), p.get("consol_typ"))
        ov = state["override"].get(key)
        if isinstance(ov, BaseException):
            raise ov
        if isinstance(ov, tuple):
            return _resp(ov[1], url, ov[0])
        if key[1] in SINGLE_BODY:
            return _resp(SINGLE_BODY[key[1]].read_bytes(), url)
        path = FIXTURE_DIR / "{}_{}_{}_{}.json".format(*key)
        assert path.exists(), f"fixture 없음: {path.name}"
        if ov is None:
            return _resp(path.read_bytes(), url)
        data = ov(copy.deepcopy(json.loads(path.read_text(encoding="utf-8"))))
        return _resp(json.dumps(data, ensure_ascii=False).encode("utf-8"), url)

    monkeypatch.setattr(requests.Session, "request", fake_request)
    return state


def _edit_rows(label, fn):
    """정규화 이름이 label인 행마다 fn(row)를 적용하는 조작 함수를 만든다."""

    def edit(d):
        for r in d["dataset"]["data"]:
            if _norm(r["NAME"]) == label:
                fn(r)
        return d

    return edit


def _drop_rows(label):
    def edit(d):
        d["dataset"]["data"] = [r for r in d["dataset"]["data"] if _norm(r["NAME"]) != label]
        return d

    return edit


def _set_headers(periods, line0=False):
    """머리글 VAL1..VAL4의 YYMM을 periods로 바꾼다."""

    def edit(d):
        for h in d["dataset"]["header"]:
            i = int(h["CD"][3:])
            if i <= len(periods):
                h["YYMM"] = periods[i - 1]
                if line0:
                    h["LINE"] = 0
        return d

    return edit


def _warnings(caplog):
    return [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]


def _key(call):
    p = call["params"]
    return (call["url"].rsplit("/", 1)[-1], p["freq_typ"], p["consol_typ"])


# ───────────────────────── AC-WC-002 ─────────────────────────


def test_ac_wc_002_alias_layer_and_shareholder_equity(site):
    _, ann, quar, _ = read_fs("005930")
    df_anal, _, _ = fs_analysis(ann, quar)
    expected = _raw_value("getFinBalance", "005930", "Y", "C", "지배주주지분", "VAL1")
    assert df_anal.loc["주주몫", "2023/12"] == pytest.approx(3532337.75, abs=TOL)
    assert df_anal.loc["주주몫", "2023/12"] == pytest.approx(expected, abs=TOL)
    for label in ("매출액", "자산", "유동금융자산", "이익잉여금(결손금)"):
        assert label in ann.index
    for label in ("매출액(수익)", "자산총계"):
        assert label not in ann.index


def test_ac_wc_002_name_and_value_normalization(site):
    def edit(r):
        r["NAME"] = "\xa0\xa0  재고자산"
        r["VAL2"] = "N/A"

    site["override"][("getFinBalance", "005930", "Y", "C")] = _edit_rows("재고자산", edit)
    _, ann, _, _ = read_fs("005930")
    assert "재고자산" in ann.index
    assert ann.loc["재고자산", "2024/12"] == 0.0


def test_ac_wc_002_contrast_empty_alias_table_breaks_fs_analysis(site, monkeypatch):
    monkeypatch.setattr(aa, "ALIASES", {})
    _, ann, quar, _ = read_fs("005930")
    with pytest.raises(KeyError, match="매입채무및기타유동채무"):
        fs_analysis(ann, quar)


# ───────────────────────── AC-WC-003 ─────────────────────────


def _null_val4_selection_row(d):
    for r in d["dataset"]["data"]:
        if r["LVL"] == 0 and _norm(r["NAME"]) == aa.CONSOL_SELECTION_LABEL:
            r["VAL4"] = None
    return d


CASES_003 = {
    "a": ("403870", "IFRS(별도)", "매출액", 1729.65),
    "b": ("001750", "IFRS(별도)", "당기순이익", 565.71),
    "c": ("005930", "IFRS(연결)", "지배주주순이익", 442609.56),
    "d": ("005930", "IFRS(연결)", "지배주주순이익", 442609.56),
}


def _prepare_003(site, case):
    if case == "d":
        for consol in ("C", "B"):
            site["override"][("getFinIncome", "005930", "Y", consol)] = _null_val4_selection_row


@pytest.mark.parametrize("case", ["a", "b", "c", "d"])
def test_ac_wc_003_consolidation_selection(site, case):
    code, account_type, label, value = CASES_003[case]
    _prepare_003(site, case)
    got_type, ann, _, _ = read_fs(code)
    assert got_type == account_type
    assert ann.loc[label, "2025/12"] == pytest.approx(value, abs=TOL)
    decided = "C" if account_type == "IFRS(연결)" else "B"
    keys = [_key(c) for c in site["calls"]]
    others = [k for k in keys if k[:2] != ("getFinIncome", "Y")]
    assert others and all(k[2] == decided for k in others)
    inc_y = [k[2] for k in keys if k[:2] == ("getFinIncome", "Y")]
    assert set(inc_y) <= {"C", "B"} and decided in inc_y
    assert len(keys) <= 7  # 판정 2 + 나머지 재무 5 (스냅샷 1은 get_fnguide 몫)


def _sel_row(rows):
    for r in rows or []:
        if r["LVL"] == 0 and _norm(r["NAME"]) == aa.CONSOL_SELECTION_LABEL:
            return r
    return {}


NAIVE_003 = {
    # (가) 항상 C
    "a": lambda c_rows, b_rows: "C",
    # (나) C에 값이 하나라도 있으면 C
    "b": lambda c_rows, b_rows: "C" if any(_sel_row(c_rows).get(f"VAL{i}") is not None for i in range(1, 5)) else "B",
    # (다) 항상 B
    "c": lambda c_rows, b_rows: "B",
    # (라) C의 VAL4가 null이 아니면 C
    "d": lambda c_rows, b_rows: "C" if _sel_row(c_rows).get("VAL4") is not None else "B",
}


@pytest.mark.parametrize("case", ["a", "b", "c", "d"])
def test_ac_wc_003_contrast_naive_selection(site, monkeypatch, case):
    monkeypatch.setattr(crawler, "_choose_consol", NAIVE_003[case])
    code, _, label, _ = CASES_003[case]
    _prepare_003(site, case)
    got_type, ann, _, _ = read_fs(code)
    if case == "a":
        assert got_type == "IFRS(연결)" and ann.loc["매출액", "2025/12"] == 0.0
    elif case == "b":
        assert got_type == "IFRS(연결)" and ann.loc["당기순이익", "2025/12"] == 0.0
    elif case == "c":
        assert got_type == "IFRS(별도)"
        assert ann.loc["지배주주순이익", "2025/12"] == pytest.approx(336866.01, abs=TOL)
    else:
        assert got_type == "IFRS(별도)"


# ───────────────────────── AC-WC-004 ─────────────────────────


def test_ac_wc_004_net_income_single_row(site):
    _, ann, _, yoy = read_fs("005930")
    bp = _calc_business_performance(ann, yoy)
    idx = bp.periods.index("2025/12")
    assert bp.net_income[idx] == pytest.approx(452068.05, abs=TOL)
    assert list(ann.index).count("당기순이익") == 1
    assert list(ann.index).count("당기순손익") == 1


def test_ac_wc_004_contrast_no_cashflow_rename(site, monkeypatch):
    monkeypatch.setattr(aa, "CASHFLOW_RENAMES", {})
    _, ann, _, yoy = read_fs("005930")
    with pytest.raises(TypeError, match="float\\(\\) argument"):
        _calc_business_performance(ann, yoy)


# ───────────────────────── AC-WC-005 ─────────────────────────


def test_ac_wc_005_tax_and_interest_multi_row(site):
    _, ann, quar, _ = read_fs("005930")
    df_anal, _, _ = fs_analysis(ann, quar)
    assert df_anal.loc["법인세비용", "2024/12"] == pytest.approx(30783.83, abs=TOL)
    assert df_anal.loc["법인세비용", "2026/06"] == pytest.approx(371247.80, abs=TOL)
    assert df_anal.loc["이자비용", "2024/12"] == pytest.approx(9039.18, abs=TOL)
    assert df_anal.loc["이자비용", "2026/06"] == pytest.approx(7558.38, abs=TOL)
    for frame, freq in ((ann, "Y"), (quar, "Q")):
        for label in aa.MULTI_ROW_LABELS:
            rows = frame.loc[[label]]
            assert len(rows) >= 2
            assert rows.iloc[0, 0] == pytest.approx(
                _raw_value("getFinIncome", "005930", freq, "C", label, "VAL1"), abs=TOL
            )


def test_ac_wc_005_contrast_no_zero_row_padding(site, monkeypatch):
    monkeypatch.setattr(aa, "MULTI_ROW_LABELS", ())
    _, ann, quar, _ = read_fs("005930")
    df_anal, _, _ = fs_analysis(ann, quar)
    assert df_anal.loc["법인세비용", "2024/12"] == pytest.approx(-44808.35, abs=TOL)
    assert df_anal.loc["법인세비용", "2026/06"] == pytest.approx(13198.16, abs=TOL)


def test_ac_wc_005_contrast_cashflow_before_income(site, monkeypatch):
    monkeypatch.setattr(
        crawler, "_STATEMENT_ORDER", ("getFinCashFlow", "getFinBalance", "getFinIncome")
    )
    _, ann, quar, _ = read_fs("005930")
    df_anal, _, _ = fs_analysis(ann, quar)
    assert df_anal.loc["이자비용", "2024/12"] == 0.0


# ───────────────────────── AC-WC-006 ─────────────────────────


def test_ac_wc_006_a_columns_and_yoy_base(site):
    _, ann, quar, yoy = read_fs("005930")
    assert list(ann.columns) == ["2023/12", "2024/12", "2025/12", "2026/06"]
    assert list(quar.columns) == ["2025/09", "2025/12", "2026/03", "2026/06"]
    assert yoy is not None and yoy.shape[1] == 1 and "전년동기" in str(yoy.columns[0])
    assert yoy.iloc[:, 0]["매출액"] == pytest.approx(1537068.20, abs=TOL)
    bp = _calc_business_performance(ann, yoy)
    assert bp.yoy_revenue[-1] == pytest.approx(0.98672, abs=1e-4)


def test_ac_wc_006_b_semiannual_reit(site):
    _, ann, _, yoy = read_fs("330590")
    assert list(ann.columns) == ["2024/12", "2025/06", "2025/12", "2026/06"]
    assert yoy is None


DEC_PERIODS = ["2022/12", "2023/12", "2024/12", "2025/12"]


def _prepare_dec(site):
    for ep in ("getFinIncome", "getFinBalance", "getFinCashFlow"):
        for consol in ("C", "B"):
            site["override"][(ep, "005930", "Y", consol)] = _set_headers(DEC_PERIODS, line0=True)


def test_ac_wc_006_c_dec_close_columns(site):
    _prepare_dec(site)
    _, ann, _, yoy = read_fs("005930")
    assert list(ann.columns) == DEC_PERIODS
    assert yoy is None
    assert calc_weight_coeff(ann.columns) == (1.0, 2.0, 3.0, 6.0)


def _prepare_misaligned(site):
    site["override"][("getFinBalance", "005930", "Y", "C")] = _set_headers(
        ["2023/12", "2024/09", "2025/12", "2026/06"]
    )


def test_ac_wc_006_d_period_misalignment_is_runtime_error(site):
    _prepare_misaligned(site)
    with pytest.raises(RuntimeError) as excinfo:
        read_fs("005930")
    assert not isinstance(excinfo.value, (ValueError, OSError))


def test_ac_wc_006_e_quarter_annual_mismatch_warns_once(site, caplog):
    caplog.set_level(logging.WARNING, logger="fnguide.crawler")
    shifted = ["2025/06", "2025/09", "2025/12", "2026/03"]
    for ep in ("getFinIncome", "getFinBalance", "getFinCashFlow"):
        site["override"][(ep, "005930", "Q", "C")] = _set_headers(shifted)
    read_fs("005930")
    msgs = _warnings(caplog)
    assert len(msgs) == 1 and "005930" in msgs[0]


def test_ac_wc_006_contrast_yoy_base_always_none(site, monkeypatch):
    monkeypatch.setattr(crawler, "_yoy_base", lambda *a, **k: None)
    _, ann, _, yoy = read_fs("005930")
    bp = _calc_business_performance(ann, yoy)
    assert bp.yoy_revenue[-1] == pytest.approx(-0.08463, abs=1e-4)


def test_ac_wc_006_contrast_yoy_base_ignores_marker(site, monkeypatch):
    monkeypatch.setattr(crawler, "_RECENT_MARK", "")
    _, _, _, yoy_b = read_fs("330590")
    assert yoy_b is not None


def test_ac_wc_006_contrast_no_alignment_check(site, monkeypatch):
    monkeypatch.setattr(crawler, "_check_alignment", lambda *a, **k: None)
    _prepare_misaligned(site)
    read_fs("005930")  # 예외 없이 반환된다


# ───────────────────────── AC-WC-007 ─────────────────────────

GUARD = "정합성 불일치"


def _guard_warnings(caplog):
    return [m for m in _warnings(caplog) if GUARD in m]


def _plus_one_2024(d):
    for r in d["dataset"]["data"]:
        if _norm(r["NAME"]) == "기타유동자산":
            r["VAL2"] = f"{float(r['VAL2']) + 1.0:.2f}"
    return d


def test_ac_wc_007_fold_keeps_balance_guard_silent(site, caplog):
    caplog.set_level(logging.WARNING, logger="fnguide.crawler")
    read_fs("005930")
    assert _guard_warnings(caplog) == []


def test_ac_wc_007_fold_values(site):
    _, ann, _, _ = read_fs("005930")
    assert list(ann.loc["기타유동자산"]) == pytest.approx(
        [90403.61, 94464.41, 106174.16, 137745.49], abs=TOL
    )
    assert ann.loc["유동금융자산", "2023/12"] == pytest.approx(226909.24, abs=TOL)


def test_ac_wc_007_manipulated_other_asset_warns_once(site, caplog):
    caplog.set_level(logging.WARNING, logger="fnguide.crawler")
    site["override"][("getFinBalance", "005930", "Y", "C")] = _plus_one_2024
    read_fs("005930")
    msgs = _guard_warnings(caplog)
    assert len(msgs) == 1
    assert "005930" in msgs[0] and "2024/12" in msgs[0] and "-1.0" in msgs[0]


def test_ac_wc_007_missing_fold_destination_warns(site, caplog):
    caplog.set_level(logging.WARNING, logger="fnguide.crawler")
    for freq in ("Y", "Q"):
        site["override"][("getFinBalance", "005930", freq, "C")] = _drop_rows("기타유동자산")
    read_fs("005930")
    assert any("005930" in m and "기타유동자산" in m and "행 없음" in m for m in _warnings(caplog))


WORD_ASSET = re.compile(r"(^|[^가-힣A-Za-z0-9_])자산([^가-힣A-Za-z0-9_]|$)")


def test_ac_wc_007_missing_asset_total_warns(site, caplog):
    caplog.set_level(logging.WARNING, logger="fnguide.crawler")
    site["override"][("getFinBalance", "005930", "Y", "C")] = _drop_rows("자산총계")
    read_fs("005930")
    assert any(
        "005930" in m and WORD_ASSET.search(m) and "행 없음" in m for m in _warnings(caplog)
    )


def test_ac_wc_007_contrast_no_fold_gives_eight_warnings(site, caplog, monkeypatch):
    caplog.set_level(logging.WARNING, logger="fnguide.crawler")
    monkeypatch.setattr(aa, "FOLD_PARENT_TO_OTHER", {})
    read_fs("005930")
    msgs = _guard_warnings(caplog)
    assert len(msgs) == 8
    assert any("6353.93" in m for m in msgs)


def test_ac_wc_007_contrast_no_guard_misses_manipulation(site, caplog, monkeypatch):
    caplog.set_level(logging.WARNING, logger="fnguide.crawler")
    monkeypatch.setattr(crawler, "_check_balance", lambda *a, **k: None)
    site["override"][("getFinBalance", "005930", "Y", "C")] = _plus_one_2024
    read_fs("005930")
    assert _guard_warnings(caplog) == []


def test_ac_wc_007_contrast_naive_row_lookup_leaks(site, monkeypatch):
    # 순진한 조회: 부재를 검사하지 않고 바로 위치를 찾는다
    monkeypatch.setattr(crawler, "_first_row", lambda frame, label: frame.index.get_loc(label))
    for freq in ("Y", "Q"):
        site["override"][("getFinBalance", "005930", freq, "C")] = _drop_rows("기타유동자산")
    with pytest.raises((KeyError, IndexError)):
        read_fs("005930")


# ───────────────────────── AC-WC-008 ─────────────────────────


def test_ac_wc_008_a_zero_row_supplement(site):
    _, ann, quar, _ = read_fs("005930")
    for frame in (ann, quar):
        assert (frame.loc["관계기업등지분관련투자자산"] == 0.0).all()


def _rename_inventory(site):
    def ren(r):
        r["NAME"] = "        재고"

    for freq in ("Y", "Q"):
        site["override"][("getFinBalance", "005930", freq, "C")] = _edit_rows("재고자산", ren)


def test_ac_wc_008_b_unlisted_required_label_warns_without_row(site, caplog):
    caplog.set_level(logging.WARNING, logger="fnguide.crawler")
    _rename_inventory(site)
    _, ann, _, _ = read_fs("005930")
    assert "재고자산" not in ann.index
    assert any("005930" in m and "재고자산" in m for m in _warnings(caplog))


def test_ac_wc_008_c_dashboard_only_label_warns(site, caplog):
    caplog.set_level(logging.WARNING, logger="fnguide.crawler")
    for freq in ("Y", "Q"):
        site["override"][("getFinIncome", "005930", freq, "C")] = _drop_rows("매출원가")
    _, ann, _, _ = read_fs("005930")
    assert "매출원가" not in ann.index
    assert any("005930" in m and "매출원가" in m for m in _warnings(caplog))


def test_ac_wc_008_contrast_zero_fill_all_required(site, monkeypatch):
    monkeypatch.setattr(aa, "ZERO_ROW_LABELS", aa.REQUIRED_LABELS)
    _rename_inventory(site)
    _, ann, _, _ = read_fs("005930")
    assert ann.loc["재고자산", "2024/12"] == 0.0


# ───────────────────────── AC-WC-009 ─────────────────────────


def test_ac_wc_009_a_error_html(site):
    with pytest.raises(ValueError, match="999999"):
        read_fs("999999")


def test_ac_wc_009_b_empty_dataset(site):
    with pytest.raises(ValueError, match="005935"):
        read_fs("005935")


def test_ac_wc_009_c_null_header_checked_before_alignment(site):
    def null_val3(d):
        for h in d["dataset"]["header"]:
            if h["CD"] == "VAL3":
                h["YYMM"] = None
        return d

    site["override"][("getFinCashFlow", "005930", "Y", "C")] = null_val3
    with pytest.raises(ValueError, match="005930"):
        read_fs("005930")


def test_ac_wc_009_d_fewer_than_four_periods(site):
    def drop_val1(d):
        for h in d["dataset"]["header"]:
            if h["CD"] == "VAL1":
                h["YYMM"] = None
        for r in d["dataset"]["data"]:
            r["VAL1"] = None
        return d

    for ep in ("getFinIncome", "getFinBalance", "getFinCashFlow"):
        site["override"][(ep, "403870", "Y", "B")] = drop_val1
    with pytest.raises(ValueError) as excinfo:
        read_fs("403870")
    assert "403870" in str(excinfo.value) and "기간" in str(excinfo.value)


@pytest.mark.parametrize("bad", ["00593a", "０05930", "5930"])
def test_ac_wc_009_e_code_validation_no_request(site, bad):
    with pytest.raises(ValueError):
        read_fs(bad)
    assert site["calls"] == []


def test_ac_wc_009_redirect_followed_error_html_is_value_error(monkeypatch):
    """없는 종목은 302 → /Error/InvalidCompany → 200 HTML. requests의 리디렉션 추종을
    실제로 거친 최종 본문이 ValueError(404)가 되는지 본다(M1 V-1)."""
    html = SINGLE_BODY["999999"].read_bytes()
    seen = []

    def fake_send(self, request, **kwargs):
        seen.append(request.url)
        if "/Error/InvalidCompany" in request.url:
            r = _resp(html, request.url, 200)
        else:
            r = _resp(b"<html>Object moved</html>", request.url, 302)
            r.headers["Location"] = "/Error/InvalidCompany?errorPath=x"
        r._content_consumed = True
        r.request = request
        return r

    monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", fake_send)
    with pytest.raises(ValueError, match="999999"):
        read_fs("999999")
    assert any("/Error/InvalidCompany" in u for u in seen), "리디렉션을 따라가지 않았다"


def test_ac_wc_010_redirect_to_other_host_is_connection_error(monkeypatch):
    """리디렉션이 wcomp.fnguide.com 밖으로 가면 그 본문을 믿지 않고 ConnectionError(503).
    최종 응답 URL의 호스트를 정확히 비교한다(sync-audit F1). 리디렉션 추종 자체는 유지한다."""
    seen = []

    def fake_send(self, request, **kwargs):
        seen.append(request.url)
        if request.url.startswith("https://wcomp.fnguide.com/"):
            r = _resp(b"<html>Object moved</html>", request.url, 302)
            r.headers["Location"] = "https://example.com/CompanyInfo/getFinIncome"
        else:
            # 다른 호스트가 정상처럼 보이는 실응답 본문을 돌려주는 경우
            r = _resp((FIXTURE_DIR / "getFinIncome_005930_Y_C.json").read_bytes(), request.url, 200)
        r._content_consumed = True
        r.request = request
        return r

    monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", fake_send)
    with pytest.raises(ConnectionError, match="005930"):
        read_fs("005930")
    assert any(u.startswith("https://example.com/") for u in seen), "리디렉션을 따라가지 않았다"


def test_ac_wc_009_malformed_json_body_is_value_error(site):
    """HTML이 아닌데 형식이 다른 본문(dataset 키 없음)도 ValueError(404)다."""
    for consol in ("C", "B"):
        site["override"][("getFinIncome", "005930", "Y", consol)] = (200, b'{"x": 1}')
    with pytest.raises(ValueError, match="005930"):
        read_fs("005930")


def test_ac_wc_009_contrast_no_dataset_check(site, monkeypatch):
    """대조: 빈 data·null 머리글 검사를 빼면 read_fs("005935")가 ValueError(404) 대신
    null 기간을 정규식에 넘기다 TypeError로 샌다(라우터 503). 그 TypeError만 인정한다 —
    fixture 누락 AssertionError나 ValueError로는 통과하지 않는다(sync-audit F10)."""
    monkeypatch.setattr(crawler, "_check_dataset", lambda *a, **k: None)
    with pytest.raises(TypeError):
        read_fs("005935")


# ───────────────────────── AC-WC-010 ─────────────────────────


def _hygiene_violations(calls, code):
    bad = []
    for c in calls:
        t = c.get("timeout")
        if not (isinstance(t, (int, float)) and 0 < t <= 10):
            bad.append(("timeout", t))
        h = c.get("headers") or {}
        for k in ("User-Agent", "X-Requested-With", "Referer"):
            if k not in h:
                bad.append(("header", k))
        if (c.get("params") or {}).get("cmp_cd") != code or code in c["url"]:
            bad.append(("params", c["url"]))
        if c.get("allow_redirects") is False:
            bad.append(("redirect", c["url"]))
    return bad


def test_ac_wc_010_request_hygiene(site):
    read_fs("005930")
    assert site["calls"]
    assert _hygiene_violations(site["calls"], "005930") == []
    assert all(c["url"].startswith("https://wcomp.fnguide.com/") for c in site["calls"])


def test_ac_wc_010_transport_timeout_is_connection_error(site):
    site["override"][("getFinIncome", "005930", "Y", "C")] = requests.exceptions.ConnectTimeout("t")
    with pytest.raises(OSError):  # ConnectionError는 OSError의 하위 클래스
        read_fs("005930")


def test_ac_wc_010_http_500_is_connection_error(site):
    body = (FIXTURE_DIR / "getFinBalance_005930_Y_C.json").read_bytes()
    site["override"][("getFinBalance", "005930", "Y", "C")] = (500, body)
    with pytest.raises(ConnectionError):
        read_fs("005930")


def test_ac_wc_010_contrast_no_timeout(site, monkeypatch):
    monkeypatch.setattr(crawler, "_TIMEOUT", None)
    read_fs("005930")
    assert ("timeout", None) in _hygiene_violations(site["calls"], "005930")


# ───────────────────────── AC-WC-014 (불변) ─────────────────────────


@pytest.mark.parametrize("code,account_type", [("105560", "IFRS(연결)"), ("001750", "IFRS(별도)")])
def test_ac_wc_014_financial_layout_reads_without_alias(site, code, account_type):
    result = read_fs(code)
    assert len(result) == 4 and result[0] == account_type
    assert "매출액" not in result[1].index  # 금융 레이아웃에는 별칭을 적용하지 않는다
