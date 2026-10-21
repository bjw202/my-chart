"""SPEC-AI-REPORT-005 M2 — goose DART 사전 수집 모듈 단위 테스트.

네트워크 없음: 모든 요청은 `httpx.MockTransport`가 녹화 픽스처(`fixtures/dart/recorded`)와
합성 픽스처(`fixtures/dart/synthetic`) 또는 테스트 안에서 만든 작은 합성 바이트로 답한다.
시계·대기 함수는 가짜를 주입해 실제로 기다리지 않는다.

녹화가 없는 응답(반기보고서 외 보고서의 목차·재무제표 구간, 감사·검토보고서 본문 — progress.md G-M1-1)은
아래 `FakeDart`가 합성 바이트로 만든다.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from backend.services import goose_dart_prefetch as gdp

FIX = Path(__file__).parent / "fixtures" / "dart"
REC = FIX / "recorded"
SYN = FIX / "synthetic"
KEYS = json.loads((FIX / "index_keys.json").read_text(encoding="utf-8"))

KST = timezone(timedelta(hours=9))
LATEST = "20260814000373"  # 반기보고서 (2026.06)
ANNUAL = "20260310002974"  # 사업보고서 (2025.12)
SELECTED = [
    "20260814000373",
    "20260515000387",
    "20260310002974",
    "20251114002397",
    "20250814003923",
    "20250515002590",
    "20250314001597",
    "20241113000761",
    "20240814000979",
]

# 녹화된 viewer 구간: (rcpNo, eleId) → 파일
RECORDED_VIEWER = {
    (LATEST, "19"): REC / "viewer_20260814000373_fs_consolidated.html",
    (LATEST, "24"): REC / "viewer_20260814000373_notes_consolidated.html",
    (ANNUAL, "18"): REC / "viewer_20260310002974_summary.html",
}
RECORDED_ATT_TOC = {
    (LATEST, "11527105"): REC / "main_20260814000373_11527105.html",
    (ANNUAL, "11105314"): REC / "main_20260310002974_11105314.html",
}
AUDITOR_DCM = {"11527104", "11527105", "11105293", "11105314"}


@pytest.fixture(autouse=True)
def _isolate_home(tmp_path, monkeypatch):
    # 실제 홈·설치 하네스를 건드리지 않는다(REQ-AIR5-015)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("AI_REPORT_GOOSE_HARNESS_DIR", str(tmp_path / "harness"))


class FakeClock:
    """가짜 단조 시계 + 가짜 대기 + 가짜 KST 벽시계(같은 시간축)."""

    def __init__(self) -> None:
        self.t = 0.0
        self.slept: list[float] = []

    def monotonic(self) -> float:
        return self.t

    async def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.t += max(0.0, seconds)

    def now(self) -> datetime:
        return datetime(2026, 10, 21, 12, 0, 0, tzinfo=KST) + timedelta(seconds=self.t)


class FakeDart:
    """경로별로 픽스처를 돌려주는 비동기 MockTransport 처리기. 모든 요청을 기록한다."""

    def __init__(self, clock: FakeClock, overrides=None, list_file: Path | None = None) -> None:
        self.clock = clock
        self.overrides = overrides or []  # [(predicate(request) -> bool, responder(request))]
        self.list_file = list_file or (REC / "list_020150_recent.html")
        self.requests: list[dict] = []
        self.in_flight = 0
        self.max_in_flight = 0
        self.served: dict[str, bytes] = {}
        self._toc_template = (REC / "main_20260814000373.html").read_bytes()

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handle)

    async def handle(self, request: httpx.Request) -> httpx.Response:
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        try:
            self.requests.append(
                {
                    "method": request.method,
                    "url": str(request.url),
                    "body": request.content.decode("utf-8", "replace"),
                    "start": self.clock.t,
                    "timeout": (request.extensions.get("timeout") or {}).get("read"),
                }
            )
            await asyncio.sleep(0)
            for predicate, responder in self.overrides:
                if predicate(request):
                    resp = responder(request)
                    if asyncio.iscoroutine(resp):
                        resp = await resp
                    if resp.status_code == 200:
                        self.served[str(request.url)] = resp.content
                    return resp
            body = self.route(request)
            if body is None:
                return httpx.Response(404, content=b"not found")
            self.served[str(request.url)] = body
            return httpx.Response(200, content=body, headers={"content-type": "text/html; charset=utf-8"})
        finally:
            self.in_flight -= 1

    def route(self, request: httpx.Request) -> bytes | None:
        q = {k: v[0] for k, v in parse_qs(request.url.query.decode()).items()}
        path = request.url.path
        if request.method == "POST" and path == "/dsab007/detailSearch.ax":
            return self.list_file.read_bytes()
        if path == "/dsaf001/main.do":
            rcp = q.get("rcpNo", "")
            dcm = q.get("dcmNo")
            if dcm:
                f = RECORDED_ATT_TOC.get((rcp, dcm))
                return f.read_bytes() if f else None
            if rcp == LATEST:
                return (REC / "main_20260814000373.html").read_bytes()
            if rcp == ANNUAL:
                return (REC / "main_20260310002974.html").read_bytes()
            # 녹화 없는 보고서 목차: 반기보고서 목차의 접수번호만 바꾼 합성본
            return self._toc_template.replace(LATEST.encode(), rcp.encode())
        if path == "/report/viewer.do":
            f = RECORDED_VIEWER.get((q.get("rcpNo"), q.get("eleId")))
            if f:
                return f.read_bytes()
            if q.get("dcmNo") in AUDITOR_DCM:
                return (
                    "<html><body><p>감사인 보고서 본문 합성 "
                    f"{q.get('rcpNo')} {q.get('eleId')}</p></body></html>"
                ).encode()
            return (
                "<html><body><table><tr><td>영업이익</td><td>1</td></tr></table>"
                f"<p>합성 구간 {q.get('rcpNo')} {q.get('eleId')}</p></body></html>"
            ).encode()
        return None


def make(clock: FakeClock, fake: FakeDart) -> gdp.DartPrefetcher:
    return gdp.DartPrefetcher(
        transport=fake.transport(), clock=clock.monotonic, sleep=clock.sleep, now=clock.now
    )


async def run(tmp_path: Path, fake: FakeDart | None = None, code: str = "020150", clock: FakeClock | None = None):
    clock = clock or (fake.clock if fake else FakeClock())
    fake = fake or FakeDart(clock)
    out = tmp_path / "runs" / "job1" / "dart"
    index = await make(clock, fake)(code, out)
    on_disk = json.loads((out / "index.json").read_text(encoding="utf-8"))
    assert on_disk == index
    return index, fake, out


def entries(index, section=None, rcp=None, document=None):
    return [
        f
        for f in index["files"]
        if (section is None or f["section"] == section)
        and (rcp is None or f["rcp_no"] == rcp)
        and (document is None or f["document"] == document)
    ]


def vq(entry) -> dict:
    return {k: v[0] for k, v in parse_qs(urlparse(entry["viewer_url"]).query).items()}


def on_path(fake: FakeDart, path: str) -> list[dict]:
    return [r for r in fake.requests if urlparse(r["url"]).path == path]


# ─────────────────────────────────────────────────────────────────────────────
# AC-AIR5-005 — 회사 확인


async def test_air5_005_resolves_company_and_first_request_is_detail_search(tmp_path):
    index, fake, _ = await run(tmp_path)
    assert index["company"] == {"name": "롯데에너지머티리얼즈", "corp_code": "00113997"}
    first = fake.requests[0]
    assert first["method"] == "POST"
    assert first["url"] == "https://dart.fss.or.kr/dsab007/detailSearch.ax"
    form = parse_qs(first["body"])
    assert form["textCrpNm"] == ["020150"]
    assert set(form["publicType"]) >= {"A001", "A002", "A003"}
    assert index["search"]["row_count"] == 12
    assert index["search"]["status"] == "ok"


@pytest.mark.parametrize("list_file", [SYN / "list_020150_mixed_corp.html", SYN / "list_empty.html"])
async def test_air5_005_unresolved_company_stops_after_search(tmp_path, list_file):
    clock = FakeClock()
    fake = FakeDart(clock, list_file=list_file)
    index, fake, _ = await run(tmp_path, fake)
    assert index["outcome"] == "company_unresolved"
    assert index["company"] is None
    assert len(fake.requests) == 1
    assert index["request_count"] == 1
    assert index["files"] == []


# ─────────────────────────────────────────────────────────────────────────────
# AC-AIR5-006 — 보고서 선택


async def test_air5_006_selects_nine_latest_periods_in_order(tmp_path):
    index, _, _ = await run(tmp_path)
    fs = entries(index, section="financial_statements")
    assert [f["rcp_no"] for f in fs] == SELECTED
    assert fs[0]["report_type"] == "반기보고서" and fs[0]["period"] == "2026.06"
    assert fs[2]["report_type"] == "사업보고서" and fs[2]["period"] == "2025.12"


async def test_air5_006_same_period_keeps_latest_submission(tmp_path):
    clock = FakeClock()
    fake = FakeDart(clock, list_file=SYN / "list_020150_correction.html")
    index, _, _ = await run(tmp_path, fake)
    fs = entries(index, section="financial_statements")
    by_period = {}
    for f in fs:
        by_period.setdefault(f["period"], []).append(f["rcp_no"])
    assert by_period["2025.06"] == ["20250902000123"]
    assert "20250814003923" not in [f["rcp_no"] for f in fs]
    assert len(by_period) == 9
    assert "[기재정정]" in [f for f in fs if f["period"] == "2025.06"][0]["report_name"]


# ─────────────────────────────────────────────────────────────────────────────
# AC-AIR5-007 — 구간 선택


async def test_air5_007_consolidated_sections_of_latest_report(tmp_path):
    index, _, _ = await run(tmp_path)
    fs = entries(index, section="financial_statements", rcp=LATEST)
    assert len(fs) == 1
    assert vq(fs[0]) == {
        "rcpNo": LATEST,
        "dcmNo": "11527102",
        "eleId": "19",
        "offset": "259834",
        "length": "178344",
        "dtd": "dart4.xsd",
    }
    assert fs[0]["basis"] == "consolidated"
    assert fs[0]["section_title"] == "2. 연결재무제표"
    notes = entries(index, section="notes")
    assert len(notes) == 1  # 최신 보고서만
    assert notes[0]["rcp_no"] == LATEST
    assert (vq(notes[0])["eleId"], vq(notes[0])["offset"], vq(notes[0])["length"]) == ("24", "438182", "1703030")
    assert notes[0]["section_title"] == "3. 연결재무제표 주석"
    assert notes[0]["basis"] == "consolidated"


async def test_air5_007_separate_basis_when_no_consolidated(tmp_path):
    clock = FakeClock()
    no_cons = (SYN / "main_20260814000373_no_consolidated.html").read_bytes()
    fake = FakeDart(
        clock,
        overrides=[
            (
                lambda r: r.url.path == "/dsaf001/main.do" and r.url.params.get("rcpNo") == LATEST
                and "dcmNo" not in r.url.params,
                lambda r: httpx.Response(200, content=no_cons),
            )
        ],
    )
    index, _, _ = await run(tmp_path, fake)
    fs = entries(index, section="financial_statements", rcp=LATEST)[0]
    assert (vq(fs)["eleId"], vq(fs)["offset"]) == ("58", "2141216")
    assert fs["basis"] == "separate"
    assert fs["section_title"] == "4. 재무제표"
    notes = entries(index, section="notes")[0]
    assert vq(notes)["eleId"] == "63"
    assert notes["basis"] == "separate"
    assert notes["section_title"] == "5. 재무제표 주석"


async def test_air5_007_summary_only_from_latest_annual_report(tmp_path):
    index, _, _ = await run(tmp_path)
    summary = entries(index, section="summary")
    assert len(summary) == 1
    assert summary[0]["rcp_no"] == ANNUAL
    assert summary[0]["report_type"] == "사업보고서"
    assert summary[0]["section_title"] == "1. 요약재무정보"
    assert (vq(summary[0])["eleId"], vq(summary[0])["offset"], vq(summary[0])["length"]) == ("18", "250218", "25415")


async def test_air5_007_exact_title_match_survives_reordered_toc(tmp_path):
    clock = FakeClock()
    reordered = (SYN / "main_20260814000373_reordered.html").read_bytes()
    fake = FakeDart(
        clock,
        overrides=[
            (
                lambda r: r.url.path == "/dsaf001/main.do" and r.url.params.get("rcpNo") == LATEST
                and "dcmNo" not in r.url.params,
                lambda r: httpx.Response(200, content=reordered),
            )
        ],
    )
    index, _, _ = await run(tmp_path, fake)
    fs = entries(index, section="financial_statements", rcp=LATEST)[0]
    assert vq(fs)["eleId"] == "19"
    assert fs["section_title"] == "2. 연결재무제표"
    assert vq(entries(index, section="notes")[0])["eleId"] == "24"


def test_air5_007_normalize_title_strips_numbering_and_spaces():
    assert gdp.normalize_title("2. 연결재무제표") == "연결재무제표"
    assert gdp.normalize_title("3. 연결재무제표 주석") == "연결재무제표주석"
    assert gdp.normalize_title("III. 재무에 관한 사항") == "재무에관한사항"
    assert gdp.normalize_title("2-1. 연결 재무상태표") == "연결재무상태표"
    assert gdp.normalize_title("(첨부)반 기 연 결 재 무 제 표") == "(첨부)반기연결재무제표"


# ─────────────────────────────────────────────────────────────────────────────
# AC-AIR5-008 — 첨부 검토·감사보고서 (+ plan 부채 R3-3)


async def test_air5_008_attachment_review_and_audit_reports(tmp_path):
    index, fake, _ = await run(tmp_path)
    att_latest = entries(index, rcp=LATEST, document="attachment")
    # 연결 첨부(11527105)를 고르고, (첨부) 앞 노드 eleId 1·2만 받는다
    assert sorted(vq(e)["eleId"] for e in att_latest) == ["1", "2"]
    assert {vq(e)["dcmNo"] for e in att_latest} == {"11527105"}
    for e in att_latest:
        # R3-3: eleId 1·2 항목의 section·document 단언
        assert e["section"] == "auditor_report"
        assert e["document"] == "attachment"
        assert e["attachment_name"] == "반기연결검토보고서"
        assert e["basis"] == "consolidated"
        assert e["status"] == "ok"
    assert [e["section_title"] for e in sorted(att_latest, key=lambda e: vq(e)["eleId"])] == [
        "검  토  보  고  서",
        "반기연결재무제표 검토보고서",
    ]
    att_annual = entries(index, rcp=ANNUAL, document="attachment")
    assert len(att_annual) >= 1
    assert {vq(e)["dcmNo"] for e in att_annual} == {"11105314"}  # 감사의감사보고서(11105318) 아님
    assert sorted(vq(e)["eleId"] for e in att_annual) == ["1", "2"]
    assert all(e["attachment_name"] == "연결감사보고서" for e in att_annual)
    # 다른 보고서의 첨부는 받지 않는다
    assert {e["rcp_no"] for e in entries(index, document="attachment")} == {LATEST, ANNUAL}
    # 첨부 노드 3·4(5)는 요청하지 않는다
    viewer = [parse_qs(urlparse(r["url"]).query) for r in on_path(fake, "/report/viewer.do")]
    att_req = [q for q in viewer if q["dcmNo"][0] in AUDITOR_DCM]
    assert sorted((q["dcmNo"][0], q["eleId"][0]) for q in att_req) == [
        ("11105314", "1"),
        ("11105314", "2"),
        ("11527105", "1"),
        ("11527105", "2"),
    ]


def test_air5_008_attachment_choice_prefers_exact_consolidated_name():
    html = (REC / "main_20260310002974.html").read_text(encoding="utf-8")
    options = gdp.parse_attachments(html)
    names = [o.name for o in options]
    assert "감사의감사보고서" in names and "연결감사보고서" in names
    chosen = gdp.choose_attachment(options, ANNUAL)
    assert (chosen.name, chosen.dcm_no, chosen.basis) == ("연결감사보고서", "11105314", "consolidated")
    only_separate = [o for o in options if o.name != "연결감사보고서"]
    fallback = gdp.choose_attachment(only_separate, ANNUAL)
    assert (fallback.name, fallback.dcm_no, fallback.basis) == ("감사보고서", "11105293", "separate")
    assert gdp.choose_attachment([o for o in options if o.name == "감사의감사보고서"], ANNUAL) is None


# ─────────────────────────────────────────────────────────────────────────────
# AC-AIR5-009 — 저장과 색인


async def test_air5_009_index_schema_hashes_and_files(tmp_path):
    index, fake, out = await run(tmp_path)
    assert set(index) == set(KEYS["top"])
    assert set(index["company"]) == set(KEYS["company"])
    assert set(index["search"]) == set(KEYS["search"])
    assert index["outcome"] == "complete"
    assert index["request_count"] == len(fake.requests)
    assert index["files"]
    for f in index["files"]:
        assert set(f) == set(KEYS["files_item"])
        assert f["section"] in KEYS["enums"]["files.section"]
        assert f["document"] in KEYS["enums"]["files.document"]
        assert f["status"] in KEYS["enums"]["files.status"]
        ints = [k for k, v in f.items() if isinstance(v, (int, float)) and not isinstance(v, bool)]
        assert ints == ["bytes"]
    ok = [f for f in index["files"] if f["status"] == "ok"]
    assert len(ok) == len(index["files"])
    for f in ok:
        served = fake.served[f["viewer_url"]]
        assert f["sha256"] == hashlib.sha256(served).hexdigest()
        assert f["bytes"] == len(served)
        u = urlparse(f["viewer_url"])
        assert u.scheme == "https" and u.hostname == "dart.fss.or.kr"
        assert set(vq(f)) == set(KEYS["viewer_url_params"])
        for name in (f["html_file"], f["text_file"]):
            assert re.fullmatch(r"[a-z0-9_.-]+", name)
            assert (out / name).is_file()
        assert (out / f["html_file"]).read_bytes() == served
        assert f["basis"] in KEYS["enums"]["files.basis"] + [None]
    assert {f["section"] for f in index["files"]} == set(KEYS["enums"]["files.section"])
    fs_text = (out / entries(index, section="financial_statements", rcp=LATEST)[0]["text_file"]).read_text(
        encoding="utf-8"
    )
    assert "영업이익" in fs_text
    assert not re.search(r"<[A-Za-z/!]", fs_text)
    stamps = [index["search"]["searched_at"], index["started_at"], index["finished_at"]] + [
        f["fetched_at"] for f in index["files"]
    ]
    for s in stamps:
        dt = datetime.fromisoformat(s)
        assert dt.tzinfo is not None
        assert dt.utcoffset() == timedelta(hours=9)
        assert s.endswith("+09:00")


def test_air5_009_text_rendition_one_row_per_line():
    html = (
        "<html><head><style>p{}</style><script>var x='<b>';</script></head><body>"
        "<p>첫 문단</p><table><tr><th>항목</th><th>당기</th></tr>"
        "<tr><td>영업이익</td><td>1,234</td></tr></table><p>둘째&nbsp;문단<br>셋째</p></body></html>"
    ).encode()
    text = gdp.html_to_text(html)
    lines = text.splitlines()
    assert lines == ["첫 문단", "항목 | 당기", "영업이익 | 1,234", "둘째 문단", "셋째"]


# ─────────────────────────────────────────────────────────────────────────────
# AC-AIR5-010 — 실패해도 진행 (수집기 부분)


async def test_air5_010_list_500_is_failed_without_raising(tmp_path):
    clock = FakeClock()
    fake = FakeDart(
        clock,
        overrides=[(lambda r: r.method == "POST", lambda r: httpx.Response(500, content=b"err"))],
    )
    index, fake, _ = await run(tmp_path, fake)
    assert index["outcome"] == "failed"
    assert index["search"]["status"] == "error"
    assert index["search"]["error"]
    assert index["files"] == []
    assert len(fake.requests) == 1


def _raise(exc):
    def responder(request):
        raise exc

    return responder


@pytest.mark.parametrize(
    "case",
    ["toc_connect_error", "section_timeout", "toc_without_nodes"],
)
async def test_air5_010_one_failure_marks_partial_and_others_ok(tmp_path, case):
    clock = FakeClock()
    target = "20250515002590"
    if case == "toc_connect_error":
        overrides = [
            (
                lambda r: r.url.path == "/dsaf001/main.do" and r.url.params.get("rcpNo") == target,
                _raise(httpx.ConnectError("boom")),
            )
        ]
    elif case == "section_timeout":
        overrides = [
            (
                lambda r: r.url.path == "/report/viewer.do" and r.url.params.get("rcpNo") == target,
                _raise(httpx.ReadTimeout("slow")),
            )
        ]
    else:
        overrides = [
            (
                lambda r: r.url.path == "/dsaf001/main.do" and r.url.params.get("rcpNo") == target,
                lambda r: httpx.Response(200, content=b"<html><body>no toc</body></html>"),
            )
        ]
    fake = FakeDart(clock, overrides=overrides)
    index, _, _ = await run(tmp_path, fake)
    assert index["outcome"] == "partial"
    bad = entries(index, section="financial_statements", rcp=target)
    assert len(bad) == 1
    assert bad[0]["status"] == "error"
    assert bad[0]["error"]
    others = [f for f in entries(index, section="financial_statements") if f["rcp_no"] != target]
    assert len(others) == 8
    assert all(f["status"] == "ok" for f in others)


async def test_air5_010_unexpected_exception_is_recorded_as_failed(tmp_path, monkeypatch):
    def explode(*a, **k):
        raise RuntimeError("parser exploded")

    monkeypatch.setattr(gdp, "parse_search_rows", explode)
    index, _, _ = await run(tmp_path)
    assert index["outcome"] == "failed"
    assert "parser exploded" in (index["search"]["error"] or "")


# ─────────────────────────────────────────────────────────────────────────────
# AC-AIR5-011 — 요청 예의와 예산


async def test_air5_011_spacing_serial_count_and_timeouts(tmp_path):
    clock = FakeClock()
    jump_at = 10

    class Jump:
        n = 0

    def predicate(request):
        Jump.n += 1
        if Jump.n == jump_at:
            clock.t = 110.0
        return False

    fake = FakeDart(clock, overrides=[(predicate, None)])
    index, fake, _ = await run(tmp_path, fake)
    starts = [r["start"] for r in fake.requests]
    assert all(b - a >= 1.0 for a, b in zip(starts, starts[1:]))
    assert fake.max_in_flight == 1
    assert len(fake.requests) <= 40
    assert fake.requests[0]["timeout"] == pytest.approx(20.0)
    after = [r for r in fake.requests if r["start"] >= 110.0]
    assert after, "clock jump did not take effect"
    assert all(r["timeout"] <= 10.0 for r in after)
    assert all(r["timeout"] == pytest.approx(min(20.0, 120.0 - r["start"])) for r in fake.requests)


async def test_air5_011_total_budget_stops_requests_and_skips_rest(tmp_path):
    clock = FakeClock()

    def slow(request):
        clock.t += 30.0
        return False

    fake = FakeDart(clock, overrides=[(slow, None)])
    index, fake, _ = await run(tmp_path, fake)
    assert all(r["start"] < 120.0 for r in fake.requests)
    assert len(fake.requests) <= 5
    skipped = [f for f in index["files"] if f["status"] == "skipped"]
    assert skipped
    assert all(f["error"] for f in skipped)
    assert index["outcome"] == "partial"
    assert datetime.fromisoformat(index["finished_at"]) - datetime.fromisoformat(index["started_at"]) <= timedelta(
        seconds=150
    )


async def test_air5_011_request_cap_forty(tmp_path, monkeypatch):
    monkeypatch.setattr(gdp, "MAX_REQUESTS", 5)
    index, fake, _ = await run(tmp_path)
    assert len(fake.requests) == 5
    assert index["request_count"] == 5
    assert [f for f in index["files"] if f["status"] == "skipped"]
    assert gdp.MAX_REQUESTS == 5
    monkeypatch.undo()
    assert gdp.MAX_REQUESTS == 40
    assert gdp.TOTAL_BUDGET_S == 120.0
    assert gdp.MIN_INTERVAL_S == 1.0
    assert gdp.REQUEST_TIMEOUT_S == 20.0
    assert gdp.MAX_RESPONSE_BYTES == 8 * 1024 * 1024


async def test_air5_011_oversized_response_is_error_without_file(tmp_path):
    clock = FakeClock()
    big = b"<p>" + b"x" * (9 * 1024 * 1024) + b"</p>"
    fake = FakeDart(
        clock,
        overrides=[
            (
                lambda r: r.url.path == "/report/viewer.do" and r.url.params.get("eleId") == "24"
                and r.url.params.get("rcpNo") == LATEST,
                lambda r: httpx.Response(200, content=big),
            )
        ],
    )
    index, _, out = await run(tmp_path, fake)
    notes = entries(index, section="notes")[0]
    assert notes["status"] == "error"
    assert "too large" in notes["error"]
    assert notes["html_file"] is None and notes["text_file"] is None
    ok = [f for f in index["files"] if f["status"] == "ok"]
    assert sorted(p.name for p in out.iterdir()) == sorted(
        ["index.json"] + [f["html_file"] for f in ok] + [f["text_file"] for f in ok]
    )
    assert index["outcome"] == "partial"


# ─────────────────────────────────────────────────────────────────────────────
# AC-AIR5-012 — 주소·입력 검증


@pytest.mark.parametrize("code", ["02015", "0201500", "02015a", "", "０２０１５０"])
async def test_air5_012_invalid_code_sends_nothing(tmp_path, code):
    index, fake, _ = await run(tmp_path, code=code)
    assert fake.requests == []
    assert index["outcome"] == "failed"
    assert index["request_count"] == 0


async def test_air5_012_polluted_toc_node_is_not_used(tmp_path):
    clock = FakeClock()
    polluted = (SYN / "main_20260814000373_polluted.html").read_bytes()
    fake = FakeDart(
        clock,
        overrides=[
            (
                lambda r: r.url.path == "/dsaf001/main.do" and r.url.params.get("rcpNo") == LATEST
                and "dcmNo" not in r.url.params,
                lambda r: httpx.Response(200, content=polluted),
            )
        ],
    )
    index, fake, _ = await run(tmp_path, fake)
    fs = entries(index, section="financial_statements", rcp=LATEST)[0]
    assert fs["status"] == "error"
    assert fs["error"]
    assert fs["viewer_url"] is None
    for r in fake.requests:
        raw = r["url"] + r["body"]
        assert "../1" not in raw and "..%2F1" not in raw
        assert "x=y" not in raw and "1%26x" not in raw
        assert "a/b" not in raw and "a%2Fb" not in raw


async def test_air5_012_redirects_are_not_followed(tmp_path):
    clock = FakeClock()
    fake = FakeDart(
        clock,
        overrides=[
            (
                lambda r: r.url.path == "/report/viewer.do" and r.url.params.get("eleId") == "19"
                and r.url.params.get("rcpNo") == LATEST,
                lambda r: httpx.Response(302, headers={"location": "https://evil.example/x"}),
            ),
            (
                lambda r: r.url.path == "/report/viewer.do" and r.url.params.get("eleId") == "24",
                lambda r: httpx.Response(302, headers={"location": "https://dart.fss.or.kr.evil.example/x"}),
            ),
        ],
    )
    index, fake, _ = await run(tmp_path, fake)
    assert entries(index, section="financial_statements", rcp=LATEST)[0]["status"] == "error"
    assert entries(index, section="notes")[0]["status"] == "error"
    for r in fake.requests:
        u = urlparse(r["url"])
        assert u.scheme == "https"
        assert u.hostname == "dart.fss.or.kr"


@pytest.mark.parametrize(
    "url,ok",
    [
        ("https://dart.fss.or.kr/report/viewer.do?rcpNo=1", True),
        ("http://dart.fss.or.kr/report/viewer.do", False),
        ("https://dart.fss.or.kr.evil.example/x", False),
        ("https://evil.example/dart.fss.or.kr", False),
        ("https://user@evil.example/", False),
        ("https://sub.dart.fss.or.kr/", False),
    ],
)
def test_air5_012_url_guard_requires_exact_host(url, ok):
    if ok:
        gdp.check_url(url)
    else:
        with pytest.raises(ValueError):
            gdp.check_url(url)


def test_air5_012_toc_node_value_patterns():
    good = {"rcpNo": LATEST, "dcmNo": "11527102", "eleId": "19", "offset": "259834", "length": "178344", "dtd": "dart4.xsd"}
    assert gdp.valid_node_params(good)
    for key, bad in [("offset", "1&x=y"), ("dcmNo", "../1"), ("dtd", "a/b"), ("rcpNo", "2026"), ("eleId", "")]:
        assert not gdp.valid_node_params({**good, key: bad})


# ─────────────────────────────────────────────────────────────────────────────
# AC-AIR5-002 — 수집 중 취소 (수집기 부분)


async def test_air5_002_cancellation_propagates_from_request(tmp_path):
    clock = FakeClock()
    gate = asyncio.Event()
    entered = asyncio.Event()

    async def hang(request):
        entered.set()
        await gate.wait()
        return httpx.Response(200, content=b"")

    fake = FakeDart(clock, overrides=[(lambda r: True, hang)])
    task = asyncio.create_task(make(clock, fake)("020150", tmp_path / "dart"))

    async def scenario():
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    await asyncio.wait_for(scenario(), 5)
    assert task.cancelled()


# 감사 부채 F1 — 검색·목록은 정상으로 답하고, 보고서 안쪽 단계에서 멈춘 채 취소한다.
# 첫 요청(검색)에서 멈추는 위 테스트로는 구간·목차·첨부 단계의 `except Exception`이
# `except BaseException`으로 넓어져 취소를 삼켜도 잡히지 않는다(AC-002 대조 (b)).
# 멈춤은 처음 일치한 요청 한 번뿐이다 — 취소를 삼키는 변이라면 이후 요청은 정상 응답으로
# 끝까지 진행해 정상 반환하므로 `CancelledError` 단언이 즉시 실패한다.
CANCEL_STAGES = {
    # fetch_section(:523) — 최신 반기보고서 주석 구간 본문
    "section_viewer": lambda r: r.url.path == "/report/viewer.do" and r.url.params.get("eleId") == "24"
    and r.url.params.get("rcpNo") == LATEST,
    # report() 목차(:552) — 본문 목차
    "report_toc": lambda r: r.url.path == "/dsaf001/main.do" and "dcmNo" not in r.url.params,
    # attachment() 목차(:611) — 감사·검토보고서 첨부 목차
    "attachment_toc": lambda r: r.url.path == "/dsaf001/main.do" and "dcmNo" in r.url.params,
}


@pytest.mark.parametrize("stage", sorted(CANCEL_STAGES))
async def test_air5_002_cancellation_inside_report_stage_propagates(tmp_path, stage):
    clock = FakeClock()
    entered = asyncio.Event()
    never = asyncio.Event()
    target = CANCEL_STAGES[stage]

    async def hang(request):
        entered.set()
        await never.wait()
        return httpx.Response(200, content=b"")

    fake = FakeDart(clock, overrides=[(lambda r: not entered.is_set() and target(r), hang)])
    out = tmp_path / "dart"
    task = asyncio.create_task(make(clock, fake)("020150", out))

    async def scenario():
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    await asyncio.wait_for(scenario(), 5)
    assert task.cancelled()
    # 멈춘 단계 앞의 검색 요청은 정상으로 처리됐다 — 취소가 보고서 안쪽에서 일어났다
    paths = [urlparse(r["url"]).path for r in fake.requests]
    assert paths[0] == "/dsab007/detailSearch.ax"
    assert len(paths) >= 2
    assert target(httpx.Request("GET", fake.requests[-1]["url"]))


# ─────────────────────────────────────────────────────────────────────────────
# 감사 부채 F2 — 길이 머리글 없이 흘려보내는 응답의 8 MB 상한(:394-398)


class _ChunkedBody(httpx.AsyncByteStream):
    """content-length 없이 1 MiB 조각을 흘려보내는 본문."""

    def __init__(self, chunks: int) -> None:
        self.chunks = chunks
        self.sent = 0

    async def __aiter__(self):
        for _ in range(self.chunks):
            self.sent += 1
            yield b"x" * (1024 * 1024)

    async def aclose(self) -> None:
        pass


async def test_air5_011_streamed_oversized_response_without_length_is_error(tmp_path):
    clock = FakeClock()
    fake = FakeDart(clock)
    body = _ChunkedBody(chunks=9)  # 9 MiB > 8 MiB
    seen_headers: list[httpx.Headers] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        if (
            request.url.path == "/report/viewer.do" and request.url.params.get("eleId") == "24"
            and request.url.params.get("rcpNo") == LATEST
        ):
            resp = httpx.Response(200, stream=body)
            seen_headers.append(resp.headers)
            return resp
        return await fake.handle(request)

    out = tmp_path / "runs" / "job1" / "dart"
    prefetcher = gdp.DartPrefetcher(
        transport=httpx.MockTransport(handler), clock=clock.monotonic, sleep=clock.sleep, now=clock.now
    )
    index = await prefetcher("020150", out)
    assert json.loads((out / "index.json").read_text(encoding="utf-8")) == index

    # 전제: 길이 머리글이 없어 선언 길이 검사(:391-393)는 걸리지 않는다
    assert len(seen_headers) == 1
    assert "content-length" not in seen_headers[0]
    notes = entries(index, section="notes")[0]
    assert notes["status"] == "error"
    assert "too large" in notes["error"]
    assert notes["html_file"] is None and notes["text_file"] is None
    # 8 MiB까지는 경계 이하라 계속 읽고, 9번째 조각에서 초과하자마자 멈춘다
    assert body.sent == 9
    ok = [f for f in index["files"] if f["status"] == "ok"]
    assert sorted(p.name for p in out.iterdir()) == sorted(
        ["index.json"] + [f["html_file"] for f in ok] + [f["text_file"] for f in ok]
    )
    assert index["outcome"] == "partial"


# ─────────────────────────────────────────────────────────────────────────────
# REQ-AIR5-004 — 끄기 스위치 색인 모양 (작업 서비스가 이 함수로 쓴다, M3에서 연결)


def test_air5_004_disabled_index_shape(tmp_path):
    out = tmp_path / "dart"
    clock = FakeClock()
    index = gdp.write_disabled_index(out, "020150", now=clock.now)
    assert json.loads((out / "index.json").read_text(encoding="utf-8")) == index
    assert set(index) == set(KEYS["top"])
    assert set(index["search"]) == set(KEYS["search"])
    assert index["outcome"] == "disabled"
    assert index["files"] == []
    assert index["request_count"] == 0
    assert index["company"] is None
    assert index["started_at"].endswith("+09:00")


# ─────────────────────────────────────────────────────────────────────────────
# AC-AIR5-014 #4 — 네트워크 가드 자체 검사 (conftest.py, REQ-AIR5-015)


def test_air5_014_guard_records_attempt(goose_network_attempts):
    import socket

    # 로컬 주소만 쓴다. 가드는 원래 함수를 부르지 않으므로 실제 연결은 일어나지 않는다
    try:
        socket.create_connection(("127.0.0.1", 9), timeout=1)
    except Exception:  # noqa: BLE001 — 일부러 삼켜 fail-open 코드를 흉내 낸다
        pass
    assert [a for a in goose_network_attempts if a == ("127.0.0.1", 9)] == [("127.0.0.1", 9)]
    assert len(goose_network_attempts) == 1
    goose_network_attempts.clear()  # 비워야 종료 단언이 통과한다
