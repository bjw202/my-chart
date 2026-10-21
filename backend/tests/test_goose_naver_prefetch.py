"""SPEC-AI-REPORT-007 M2 — goose 네이버 최신 뉴스 사전 수집 모듈 단위 테스트.

네트워크 없음: 모든 요청은 `httpx.MockTransport`가 녹화 픽스처(`fixtures/naver/recorded`)와
합성 픽스처(`fixtures/naver/synthetic`)로 답한다. 파일 이름이 `test_goose_`로 시작하므로
conftest.py의 네트워크 가드가 적용된다(REQ-AIR7-012).

기대값 원칙(lessons #10): 기사 수·제목·본문은 손으로 옮겨 적지 않고 픽스처에서 테스트 실행 중에
추출한다. 기사 수는 펼친 목록 길이이며 그룹 `total`을 쓰지 않는다. 평문 기대값은
`html.unescape(re.sub(r"<[^>]+>", "", 원문)).strip()`으로 만든다. 리터럴은 형식 규칙과 합성 값뿐이다.

요청을 기다리는 테스트는 모두 바깥 `asyncio.wait_for` 상한 안에서 돌린다 — `MockTransport`는
httpx 시간 상한을 적용하지 않으므로, 구현이 틀려도 테스트가 멈추지 않고 TimeoutError로 RED가 된다.
"""

from __future__ import annotations

import asyncio
import hashlib
import html
import importlib.util
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

from backend.services import goose_naver_prefetch as gnp

FIX = Path(__file__).parent / "fixtures" / "naver"
REC = FIX / "recorded"
SYN = FIX / "synthetic"
AUDIT_SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "goose_harness_src" / "skills" / "goose" / "workflows" / "fact-check" / "scripts" / "audit_report.py"
)

KST = timezone(timedelta(hours=9))
FIXED_NOW = datetime(2026, 10, 21, 18, 0, 0, tzinfo=KST)
CEILING = 2  # 바깥 상한(초)

# acceptance.md §B — 집합 동등으로 검사
TOP_KEYS = {
    "schema_version", "code", "code_validated", "channel", "search", "outcome", "started_at",
    "finished_at", "request_count", "response_file", "response_sha256", "response_bytes", "articles",
}
SEARCH_KEYS = {"url", "query", "searched_at", "status", "item_count", "error"}
ARTICLE_KEYS = {
    "article_ref", "office_id", "article_id", "office_name", "title", "published_at", "article_url",
    "text_file", "body_chars", "status", "error",
}
ENTITY_RE = re.compile(r"&[a-zA-Z#0-9]+;")
TEXT_FILE_RE = re.compile(r"^[0-9]{2}_article\.txt$")


@pytest.fixture(autouse=True)
def _isolate_home(tmp_path, monkeypatch):
    # 실제 홈·설치 하네스를 건드리지 않는다(REQ-AIR7-012)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("AI_REPORT_GOOSE_HARNESS_DIR", str(tmp_path / "harness"))


# ─────────────────────────────────────────────────────────────────────────────
# 도우미


def load(path: Path):
    return json.loads(path.read_bytes().decode("utf-8"))


def flatten(data) -> list:
    """픽스처의 펼친 기사 목록(그룹 `total`을 쓰지 않는다)."""
    return [it for g in data for it in g["items"]]


def plain(text: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", text)).strip()


class Recorder:
    """모든 요청을 기록하는 MockTransport 처리기. 응답 바이트 또는 처리 함수를 받는다."""

    def __init__(self, body: bytes | None = None, *, status: int = 200, respond=None) -> None:
        self.body = body
        self.status = status
        self.respond = respond
        self.requests: list[httpx.Request] = []

    async def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.respond is not None:
            resp = self.respond(request)
            if asyncio.iscoroutine(resp):
                resp = await resp
            return resp
        return httpx.Response(
            self.status, content=self.body or b"", headers={"content-type": "application/json;charset=UTF-8"}
        )

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handle)


async def run(tmp_path: Path, recorder: Recorder, code: str = "020150", **kw):
    out = tmp_path / "runs" / "job1" / "naver"
    prefetcher = gnp.NaverPrefetcher(transport=recorder.transport(), now=lambda: FIXED_NOW)
    index = await asyncio.wait_for(prefetcher(code, out, **kw), CEILING)
    return index, out


async def run_file(tmp_path: Path, path: Path, code: str = "020150", **kw):
    rec = Recorder(path.read_bytes())
    index, out = await run(tmp_path, rec, code, **kw)
    return index, out, rec


def ok_entries(index) -> list:
    return [a for a in index["articles"] if a["status"] == "ok"]


# ─────────────────────────────────────────────────────────────────────────────
# AC-AIR7-005 — 요청 모양, 입력 검증, 크기·시간 상한 (REQ-AIR7-005)


async def test_air7_005_valid_code_sends_exactly_one_get(tmp_path):
    index, _, rec = await run_file(tmp_path, REC / "020150_p1.json")
    assert len(rec.requests) == 1
    assert rec.requests[0].method == "GET"
    assert str(rec.requests[0].url) == "https://m.stock.naver.com/api/news/stock/020150?pageSize=10&page=1"
    assert index["request_count"] == 1


@pytest.mark.parametrize("code", ["02015a", "０２０１５０", "0201500"])
async def test_air7_005_invalid_code_sends_nothing(tmp_path, code):
    rec = Recorder((REC / "020150_p1.json").read_bytes())
    index, _ = await run(tmp_path, rec, code)
    assert rec.requests == []
    assert index["search"]["status"] == "error"
    assert index["outcome"] == "failed"
    assert index["request_count"] == 0


async def test_air7_005_redirect_to_other_host_is_not_followed(tmp_path):
    def respond(request):
        if request.url.host == "m.stock.naver.com":
            return httpx.Response(302, headers={"location": "https://evil.example.com/x"})
        return httpx.Response(200, content=(REC / "020150_p1.json").read_bytes())

    rec = Recorder(respond=respond)
    index, _ = await run(tmp_path, rec)
    assert len(rec.requests) == 1  # 리디렉트 대상으로 두 번째 요청 없음
    assert "HTTP 302" in index["search"]["error"]
    assert index["outcome"] == "failed"


class _CountingStream(httpx.AsyncByteStream):
    """읽힌 조각 수를 세는 본문. 1 MiB 조각을 ``chunks``개, 마지막에 ``tail`` 바이트를 흘려보낸다."""

    def __init__(self, chunks: int, tail: int = 0) -> None:
        self.chunks = chunks
        self.tail = tail
        self.read = 0

    async def __aiter__(self):
        for _ in range(self.chunks):
            self.read += 1
            yield b"x" * (1024 * 1024)
        if self.tail:
            self.read += 1
            yield b"x" * self.tail

    async def aclose(self) -> None:
        pass


async def test_air7_005_declared_oversize_rejected_before_reading_body(tmp_path):
    body = _CountingStream(chunks=2, tail=1)  # 2 MiB + 1 바이트
    rec = Recorder(respond=lambda r: httpx.Response(200, headers={"content-length": "2097153"}, stream=body))
    index, out = await run(tmp_path, rec)
    assert index["outcome"] == "failed"
    assert "too large" in index["search"]["error"]
    assert body.read == 0  # 선언 길이만 보고 본문을 읽기 전에 거부
    assert not (out / "response.json").exists()


async def test_air7_005_streamed_oversize_without_length_rejected(tmp_path):
    body = _CountingStream(chunks=2, tail=1)  # 2 MiB + 1 바이트, content-length 없음
    seen: list[httpx.Headers] = []

    def respond(request):
        resp = httpx.Response(200, stream=body)
        seen.append(resp.headers)
        return resp

    rec = Recorder(respond=respond)
    index, out = await run(tmp_path, rec)
    assert "content-length" not in seen[0]  # 전제: 선언 길이 검사는 걸리지 않는다
    assert index["outcome"] == "failed"
    assert "too large" in index["search"]["error"]
    assert not (out / "response.json").exists()


async def test_air7_005_hanging_response_times_out(tmp_path, monkeypatch):
    monkeypatch.setattr(gnp, "REQUEST_TIMEOUT_S", 0.05)
    never = asyncio.Event()

    async def hang(request):  # 비동기 처리기 — 응답하지 않는다
        await never.wait()
        return httpx.Response(200, content=b"[]")

    rec = Recorder(respond=hang)
    index, _ = await run(tmp_path, rec)  # 바깥 2초 상한 안에서 반환해야 한다
    assert index["outcome"] == "failed"
    assert "Timeout" in index["search"]["error"]
    assert len(rec.requests) == 1


# ─────────────────────────────────────────────────────────────────────────────
# AC-AIR7-006 — 응답 해석과 기사 파일 (REQ-AIR7-006)


@pytest.mark.parametrize("name", ["020150_p1.json", "000040_p1.json"])
async def test_air7_006_recorded_flattened_articles_and_text_files(tmp_path, name):
    data = load(REC / name)
    flat = flatten(data)
    index, out, _ = await run_file(tmp_path, REC / name)
    arts = index["articles"]
    assert len(arts) == min(10, len(flat))
    assert [a["article_ref"] for a in arts] == [f"{it['officeId']}/{it['articleId']}" for it in flat[:10]]
    for a, it in zip(arts, flat):
        assert a["status"] == "ok", a
        text = (out / a["text_file"]).read_text(encoding="utf-8")
        assert plain(it["title"]) in text
        assert plain(it["body"]) in text
        assert a["title"] == plain(it["title"])
        assert a["body_chars"] == len(plain(it["body"]))
    # 2: 서버가 만든 파일 이름만, 폴더의 파일 집합이 정확히 색인 + 원본 + ok 텍스트
    assert all(TEXT_FILE_RE.fullmatch(a["text_file"]) for a in arts)
    assert {p.name for p in out.iterdir()} == {"index.json", "response.json"} | {a["text_file"] for a in ok_entries(index)}


async def test_air7_006_parse_cases(tmp_path):
    data = load(SYN / "parse_cases.json")
    flat = flatten(data)
    index, out, _ = await run_file(tmp_path, SYN / "parse_cases.json")
    empty, traversal, short_dt, good = index["articles"]
    assert empty["status"] == "metadata_only" and empty["text_file"] is None
    assert traversal["status"] == "error" and traversal["text_file"] is None
    assert short_dt["status"] == "error" and short_dt["text_file"] is None
    assert good["status"] == "ok"
    assert good["published_at"] == "2026-10-21T13:52:00+09:00"
    text = (out / good["text_file"]).read_text(encoding="utf-8")
    assert "강조" in text and "<b>" not in text
    assert plain(flat[3]["body"]) in text
    # 폴더 밖에 파일이 없고, 폴더 안 파일은 색인 + 원본 + ok 텍스트뿐
    assert sorted(p.name for p in out.parent.iterdir()) == ["naver"]
    assert {p.name for p in out.iterdir()} == {"index.json", "response.json", good["text_file"]}


async def test_air7_006_two_items_in_one_group(tmp_path):
    data = load(SYN / "two_items_group.json")
    flat = flatten(data)
    index, _, _ = await run_file(tmp_path, SYN / "two_items_group.json")
    assert len(flat) == len(data) + 1
    assert len(index["articles"]) == len(flat)
    assert [a["article_ref"] for a in index["articles"]] == [f"{it['officeId']}/{it['articleId']}" for it in flat]
    assert all(a["status"] == "ok" for a in index["articles"])


async def test_air7_006_malformed_groups_become_error_entries(tmp_path):
    data = load(SYN / "mixed_malformed_groups.json")
    index, out, _ = await run_file(tmp_path, SYN / "mixed_malformed_groups.json")  # 예외 없이 반환
    arts = index["articles"]
    good = [g["items"][0] for g in data if isinstance(g, dict) and isinstance(g.get("items"), list)]
    assert [a["article_ref"] for a in arts if a["status"] == "ok"] == [
        f"{it['officeId']}/{it['articleId']}" for it in good
    ]
    errors = [a for a in arts if a["status"] == "error"]
    reasons = ["items missing", "items not a list", "group not an object", "article not an object"]
    assert len(errors) == len(reasons)
    for e, reason, group_no in zip(errors, reasons, (2, 3, 4, 5)):
        assert reason in e["error"] and f"group {group_no}" in e["error"], e
        assert e["text_file"] is None
        for key in ARTICLE_KEYS - {"status", "error"}:
            assert e[key] is None, (key, e)
    assert {p.name for p in out.iterdir()} == {"index.json", "response.json"} | {a["text_file"] for a in ok_entries(index)}


@pytest.mark.parametrize("name", ["020150_p1.json", "000040_p1.json"])
async def test_air7_006_recorded_entities_are_decoded(tmp_path, name):
    flat = flatten(load(REC / name))
    index, out, _ = await run_file(tmp_path, REC / name)
    # 엔티티가 든 기사를 런타임에 고른다 — 0건이면 검사가 빈 것이므로 실패
    picked = [
        (i, field) for i, it in enumerate(flat[:10]) for field in ("title", "body") if ENTITY_RE.search(it[field])
    ]
    assert picked, "녹화 픽스처에 엔티티가 든 기사가 없다 — 검사가 비었다"
    for i, field in picked:
        text = (out / index["articles"][i]["text_file"]).read_text(encoding="utf-8")
        for ent in ENTITY_RE.findall(flat[i][field]):
            assert ent not in text, (i, field, ent)
        assert plain(flat[i][field]) in text


async def test_air7_006_tags_removed_before_entities_decoded(tmp_path):
    index, out, _ = await run_file(tmp_path, SYN / "entity_body.json")
    (art,) = index["articles"]
    text = (out / art["text_file"]).read_text(encoding="utf-8")
    assert "a'b'c & <b>리터럴</b> 태그" in text  # 두 참조 모두 해제, 리터럴 <b>는 글자로 남음
    for absent in ("<i>", "&#39;", "&#x27;", "&amp;", "&lt;"):
        assert absent not in text, absent


# ─────────────────────────────────────────────────────────────────────────────
# AC-AIR7-007 — 색인 키 집합과 원본 보존 (REQ-AIR7-007)


@pytest.mark.parametrize("name", ["020150_p1.json", "000040_p1.json"])
async def test_air7_007_index_keys_raw_response_and_urls(tmp_path, name):
    raw = (REC / name).read_bytes()
    flat = flatten(load(REC / name))
    index, out, _ = await run_file(tmp_path, REC / name)
    assert json.loads((out / "index.json").read_text(encoding="utf-8")) == index
    assert set(index) == TOP_KEYS
    assert set(index["search"]) == SEARCH_KEYS
    assert index["articles"] and all(set(a) == ARTICLE_KEYS for a in index["articles"])
    assert index["channel"] == "naver"
    assert index["search"]["status"] == "ok"
    assert index["search"]["item_count"] == len(flat)
    saved = (out / "response.json").read_bytes()
    assert saved == raw
    assert index["response_file"] == "response.json"
    assert index["response_sha256"] == hashlib.sha256(saved).hexdigest()
    assert index["response_bytes"] == len(saved)
    for stamp in (index["search"]["searched_at"], index["started_at"], index["finished_at"]):
        assert stamp.endswith("+09:00"), stamp
    for a, it in zip(index["articles"], flat):
        assert a["published_at"].endswith("+09:00")
        assert a["article_ref"] == f"{a['office_id']}/{a['article_id']}"
        # V5 교차 확인: 서버가 검증된 식별자로 만든 주소가 응답의 mobileNewsUrl과 같다
        assert a["article_url"] == it["mobileNewsUrl"]


# ─────────────────────────────────────────────────────────────────────────────
# AC-AIR7-008 — 실패해도 진행, 0건은 0건 (REQ-AIR7-008, REQ-AIR7-009)


def _connect_error(request):
    raise httpx.ConnectError("refused", request=request)


FAILURES = {
    "connect_error": lambda: Recorder(respond=_connect_error),
    "http_410": lambda: Recorder(b"gone", status=410),
    "http_500": lambda: Recorder(b"down", status=500),
    "not_json": lambda: Recorder((SYN / "not_json.txt").read_bytes()),
    "missing_items_path": lambda: Recorder((SYN / "missing_items_path.json").read_bytes()),
    "top_level_object": lambda: Recorder((SYN / "top_level_object.json").read_bytes()),
}


@pytest.mark.parametrize("case", sorted(FAILURES))
async def test_air7_008_failures_are_recorded_without_raising(tmp_path, case):
    index, out = await run(tmp_path, FAILURES[case]())
    assert index["outcome"] == "failed"
    assert index["search"]["error"]
    assert json.loads((out / "index.json").read_text(encoding="utf-8")) == index


async def test_air7_008_top_level_object_reports_top_level_error(tmp_path):
    # 감사 부채 D-A: 형제 검사("items 배열을 가진 그룹 없음")가 같은 입력을 실패로 만들므로,
    # 최상위 배열 검사 자체를 지키려면 그 검사에만 있는 오류 문구를 단언한다
    index, _ = await run(tmp_path, FAILURES["top_level_object"]())
    assert index["outcome"] == "failed"
    assert "top-level JSON value is not an array" in index["search"]["error"]
    assert index["articles"] == []


async def test_air7_008_no_group_with_items_array_is_failed_with_error(tmp_path):
    index, _ = await run(tmp_path, FAILURES["missing_items_path"]())
    assert index["outcome"] == "failed"
    assert "no group has an items array" in index["search"]["error"]


async def test_air7_008_unexpected_exception_is_recorded_as_failed(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("parser exploded")

    monkeypatch.setattr(gnp, "parse_articles", boom)
    index, out = await run(tmp_path, Recorder((REC / "020150_p1.json").read_bytes()))
    assert index["outcome"] == "failed"
    assert "parser exploded" in index["search"]["error"]
    assert (out / "index.json").exists()


@pytest.mark.parametrize("path", [REC / "999999_p1.json", SYN / "zero_articles.json", SYN / "all_empty_items.json"])
async def test_air7_008_zero_articles_is_no_results(tmp_path, path):
    index, _, _ = await run_file(tmp_path, path)
    assert index["outcome"] == "no_results"
    assert index["search"]["status"] == "ok"
    assert index["search"]["item_count"] == 0
    assert index["articles"] == []


# ─────────────────────────────────────────────────────────────────────────────
# AC-AIR7-002 — 수집 중 취소 (수집기 부분)


async def test_air7_002_cancellation_propagates_from_request(tmp_path):
    entered = asyncio.Event()
    never = asyncio.Event()

    async def hang(request):
        entered.set()
        await never.wait()
        return httpx.Response(200, content=b"[]")

    rec = Recorder(respond=hang)
    prefetcher = gnp.NaverPrefetcher(transport=rec.transport(), now=lambda: FIXED_NOW)
    task = asyncio.create_task(prefetcher("020150", tmp_path / "naver"))

    async def scenario():
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    await asyncio.wait_for(scenario(), 5)
    assert task.cancelled()


# ─────────────────────────────────────────────────────────────────────────────
# AC-AIR7-014 — outcome 판정 (REQ-AIR7-014)


@pytest.mark.parametrize(
    "path,expected",
    [
        (SYN / "mixed_status.json", "partial"),
        (SYN / "all_metadata_only.json", "failed"),
        (REC / "020150_p1.json", "complete"),
        (SYN / "parse_cases.json", "partial"),
        (SYN / "mixed_malformed_groups.json", "partial"),
    ],
    ids=["a_mixed_status", "b_all_metadata_only", "c_recorded_020150", "d_parse_cases", "e_mixed_malformed"],
)
async def test_air7_014_outcome(tmp_path, path, expected):
    index, _, _ = await run_file(tmp_path, path)
    assert index["outcome"] == expected
    assert index["search"]["status"] == "ok"
    data = load(path)
    flat = [it for g in data if isinstance(g, dict) and isinstance(g.get("items"), list) for it in g["items"]]
    assert index["search"]["item_count"] == len(flat)


# ─────────────────────────────────────────────────────────────────────────────
# AC-AIR7-015 (수집기 부분) — code_validated 기록, 끄기 색인 모양


@pytest.mark.parametrize("flag", [True, False])
async def test_air7_015_code_validated_is_recorded(tmp_path, flag):
    index, _, rec = await run_file(tmp_path, REC / "999999_p1.json", code="999999", code_validated=flag)
    assert index["code_validated"] is flag
    assert index["outcome"] == "no_results"
    assert len(rec.requests) == 1


def test_air7_003_disabled_index_shape(tmp_path):
    out = tmp_path / "naver"
    index = gnp.write_disabled_index(out, "020150", code_validated=True, now=lambda: FIXED_NOW)
    assert json.loads((out / "index.json").read_text(encoding="utf-8")) == index
    assert set(index) == TOP_KEYS
    assert set(index["search"]) == SEARCH_KEYS
    assert index["outcome"] == "disabled"
    assert index["articles"] == []
    assert index["request_count"] == 0
    assert index["code_validated"] is True
    assert index["channel"] == "naver"
    assert index["started_at"].endswith("+09:00") and index["finished_at"].endswith("+09:00")


# ─────────────────────────────────────────────────────────────────────────────
# AC-AIR7-010 — 규칙(N-2·N-3)대로 만든 기록이 감사를 통과하는가 (감사 스크립트는 변경 없음)


def _audit_module():
    spec = importlib.util.spec_from_file_location("_air7_audit_report", AUDIT_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _report_input(index: dict, *, result: str, source: dict | None, note: str) -> dict:
    searched = datetime.fromisoformat(index["search"]["searched_at"])
    search = {
        "channel": "naver",
        "searched_at": index["search"]["searched_at"],
        "query": index["search"]["query"],
        "result": result,
        "note": note,
    }
    if source is not None:
        search["source_ids"] = [source["id"]]
    return {
        "document_type": "deep_report",
        "company": {"market": "KOSPI"},
        "research_window": {"cutoff": (searched + timedelta(minutes=10)).isoformat(), "searches": [search]},
        "sources": [source] if source is not None else [],
    }


def _naver_codes(audit_mod, data: dict) -> set:
    cutoff = datetime.fromisoformat(data["research_window"]["cutoff"])
    result = audit_mod.audit(data, json.dumps(data).encode("utf-8"), now=cutoff + timedelta(minutes=1))
    return {f["code"] for f in result["findings"] if f["code"].startswith("LATEST_SEARCH_NAVER")}


async def test_air7_010_rule_shaped_record_passes_audit_and_variants_fail(tmp_path):
    audit_mod = _audit_module()
    index, _, _ = await run_file(tmp_path, REC / "020150_p1.json")
    a = ok_entries(index)[0]
    source = {
        "id": "nv1",
        "title": a["title"],
        "publisher": a["office_name"],
        "url": a["article_url"],
        "published_at": a["published_at"],
        "accessed_at": (FIXED_NOW + timedelta(minutes=3)).isoformat(),
        "verification": "direct_read",
        "read_scope": f"{a['office_name']} · {a['published_at']} · 모바일 뉴스 API 응답의 제목·요약 본문 필드 · naver/{a['text_file']}",
        "limitations": "서버 사전 수집본으로 열람, 기사 원문 페이지와 대조하지 않음. API 요약본(약 150자), 원문 미확인",
    }
    note = "서버 사전 수집 네이버 모바일 뉴스 API 응답에서 기사 파일을 열람"
    base = _report_input(index, result="read", source=source, note=note)
    assert _naver_codes(audit_mod, base) == set()

    variants = {
        "v1_blocked": lambda d: d["research_window"]["searches"][0].update(result="blocked"),
        "v2_server_prefetch": lambda d: d["sources"][0].update(verification="server_prefetch"),
        "v3_empty_read_scope": lambda d: d["sources"][0].update(read_scope=""),
        "v4_stale_search": lambda d: d["research_window"]["searches"][0].update(
            searched_at=(datetime.fromisoformat(d["research_window"]["cutoff"]) - timedelta(hours=25)).isoformat()
        ),
    }
    for name, mutate in variants.items():
        d = json.loads(json.dumps(base))
        mutate(d)
        assert _naver_codes(audit_mod, d) == {"LATEST_SEARCH_NAVER"}, name


async def test_air7_010_no_results_record_passes_audit(tmp_path):
    audit_mod = _audit_module()
    index, _, _ = await run_file(tmp_path, REC / "999999_p1.json", code="999999")
    assert index["outcome"] == "no_results"
    note = f"종목코드 999999, pageSize=10, page=1, searched_at {index['search']['searched_at']} 기사 0건. 서버가 종목코드 유효성을 확인하지 못함"
    data = _report_input(index, result="no_results", source=None, note=note)
    assert _naver_codes(audit_mod, data) == set()
