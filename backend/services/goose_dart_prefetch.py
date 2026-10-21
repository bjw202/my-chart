"""SPEC-AI-REPORT-005 M2 — goose DART 원문 사전 수집.

goose 실행 직전에 서버가 DART 공개 화면에서 정기보고서 구간을 받아 `runs/<job_id>/dart/`에
원본 HTML·텍스트판·`index.json`으로 저장한다. goose 권한은 넓히지 않는다(spec D2).

흐름: 회사 확인(REQ-AIR5-005) → 보고서 선택(006) → 목차 해석·구간 선택(007·008, plan T4·T5)
→ 저장·색인(009). 어떤 실패도 색인에 기록하고 정상 반환한다(010, fail-open). 취소(CancelledError)는
실패가 아니므로 그대로 전파한다. 요청 예의·예산(011)과 주소·인자 검증(012)은 `_Session`이 맡는다.

경계:
- 서버는 원문만 공급하고 숫자를 해석하지 않는다(spec D5). 색인에는 재무 수치를 넣지 않는다.
- 작업 서비스 연결(생성자 주입, 끄기 스위치, 진행 이벤트)은 M3 몫이다. 이 모듈은 수집기와
  끄기 상태 색인 작성 함수(`write_disabled_index`)만 제공한다.
- 작업 간 캐시·재시도 큐 없음(spec D7).
"""

from __future__ import annotations

import asyncio
import hashlib
import html as html_lib
import json
import logging
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))

DART_HOST = "dart.fss.or.kr"
SEARCH_URL = f"https://{DART_HOST}/dsab007/detailSearch.ax"
TOC_URL = f"https://{DART_HOST}/dsaf001/main.do"
VIEWER_URL = f"https://{DART_HOST}/report/viewer.do"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)

INDEX_FILE = "index.json"
SCHEMA_VERSION = 1

# @MX:NOTE: [AUTO] 예산 수치(plan T9). 환경 변수로 바꾸지 않는다 — 끄기 스위치 하나만 둔다(REQ-AIR5-004)
MIN_INTERVAL_S = 1.0  # 요청 시작 간 최소 간격
REQUEST_TIMEOUT_S = 20.0  # 요청당 상한(남은 예산이 더 작으면 그 값)
MAX_REQUESTS = 40  # 작업당 요청 수 상한
TOTAL_BUDGET_S = 120.0  # 수집 전체 시간 예산
MAX_RESPONSE_BYTES = 8 * 1024 * 1024  # 응답 크기 상한

MAX_REPORTS = 9  # 최신 9개 기간(plan T3)
SEARCH_YEARS = 3
PUBLIC_TYPES = ("A001", "A002", "A003")  # 사업·반기·분기보고서

CODE_RE = re.compile(r"[0-9]{6}")  # ASCII 숫자만(전각 숫자 거부)
VIEWER_PARAMS = ("rcpNo", "dcmNo", "eleId", "offset", "length", "dtd")
# 목차 노드 값의 엄격한 형태(REQ-AIR5-012). 하나라도 어긋나면 그 노드는 쓰지 않는다
NODE_PATTERNS = {
    "rcpNo": re.compile(r"[0-9]{14}"),
    "dcmNo": re.compile(r"[0-9]{1,10}"),
    "eleId": re.compile(r"[0-9]{1,6}"),
    "offset": re.compile(r"[0-9]{1,10}"),
    "length": re.compile(r"[0-9]{1,10}"),
    "dtd": re.compile(r"[A-Za-z0-9_-]{1,32}\.xsd"),
}

# 목차 제목(앞 번호·공백 제거 후) 완전 일치 판정 — 부분 일치 금지(plan T5)
TITLE_FS = {"consolidated": "연결재무제표", "separate": "재무제표"}
TITLE_NOTES = {"consolidated": "연결재무제표주석", "separate": "재무제표주석"}
TITLE_SUMMARY = "요약재무정보"
ATTACHED_COPY_PREFIX = "(첨부)"  # 첨부 문서에서 이 노드부터는 재무제표 사본이라 받지 않는다(REQ-AIR5-008)

# 첨부 검토·감사보고서 이름(공백 제거 후 완전 일치). `감사의감사보고서` 같은 다른 첨부를 잡지 않는다
CONSOLIDATED_ATTACHMENTS = ("연결감사보고서", "반기연결검토보고서", "분기연결검토보고서")
SEPARATE_ATTACHMENTS = ("감사보고서", "반기검토보고서", "분기검토보고서")

_NUM_PREFIX = re.compile(r"^\s*(?:[IVXLC]+|[0-9]+(?:-[0-9]+)*)\s*\.\s*")
_NODE_START = re.compile(r"var\s+(node\d+)\s*=\s*\{\s*\}\s*;")
_NODE_ASSIGN = re.compile(r"(node\d+)\[\s*'(\w+)'\s*\]\s*=\s*\"((?:[^\"\\]|\\.)*)\"")
_CORP_RE = re.compile(r"openCorpInfoNew\('([0-9]{8})'")
_RCP_HREF_RE = re.compile(r"rcpNo=([0-9]{14})")
_TYPE_RE = re.compile(r"(사업|반기|분기)보고서")
_PERIOD_RE = re.compile(r"\(([0-9]{4}\.[0-9]{2})\)")
_DATE_PREFIX = re.compile(r"^[0-9]{4}\.[0-9]{2}\.[0-9]{2}")


# ─────────────────────────────────────────────────────────────────────────────
# 검증


def check_url(url: str) -> None:
    """https + 호스트 완전 일치(`dart.fss.or.kr`)가 아니면 ValueError. 부분 문자열 검사 금지."""
    parts = urlsplit(url)
    if (
        parts.scheme != "https"
        or parts.hostname != DART_HOST
        or parts.username is not None
        or parts.password is not None
        or parts.port not in (None, 443)
    ):
        raise ValueError(f"disallowed url: {url!r}")


def valid_node_params(params: dict[str, Any]) -> bool:
    """목차 노드 값 6개가 각각 엄격한 형태에 맞는지."""
    return all(isinstance(params.get(k), str) and p.fullmatch(params[k]) for k, p in NODE_PATTERNS.items())


# ─────────────────────────────────────────────────────────────────────────────
# 파싱


@dataclass(frozen=True)
class SearchRow:
    rcp_no: str | None
    corp_code: str | None
    company: str
    report_name: str
    report_type: str | None
    period: str | None


@dataclass(frozen=True)
class Attachment:
    name: str
    rcp_no: str
    dcm_no: str
    basis: str | None


def normalize_title(title: str) -> str:
    """목차 제목에서 앞 번호(`2.`, `III.`, `2-1.`)와 모든 공백을 지운다(글자 사이 공백 포함)."""
    return re.sub(r"\s+", "", _NUM_PREFIX.sub("", title, count=1))


def parse_search_rows(html_text: str) -> list[SearchRow]:
    """상세검색 결과 표의 행. 표 자체가 없으면 ValueError(해석 불가 페이지)."""
    soup = BeautifulSoup(html_text, "html.parser")
    table = soup.find("table", class_="tbList")
    tbody = table.find("tbody") if table else None
    if tbody is None:
        raise ValueError("search result table not found")
    rows: list[SearchRow] = []
    for tr in tbody.find_all("tr"):
        corp_a = tr.find("a", href=_CORP_RE)
        rep_a = tr.find("a", href=_RCP_HREF_RE)
        if rep_a is None and corp_a is None:
            continue
        name = " ".join(rep_a.get_text().split()) if rep_a else ""
        rcp = _RCP_HREF_RE.search(rep_a["href"]) if rep_a else None
        corp = _CORP_RE.search(corp_a["href"]) if corp_a else None
        rtype = _TYPE_RE.search(name)
        period = _PERIOD_RE.search(name)
        rows.append(
            SearchRow(
                rcp_no=rcp.group(1) if rcp else None,
                corp_code=corp.group(1) if corp else None,
                company=" ".join(corp_a.get_text().split()) if corp_a else "",
                report_name=name,
                report_type=rtype.group(0) if rtype else None,
                period=period.group(1) if period else None,
            )
        )
    return rows


def select_reports(rows: list[SearchRow], limit: int = MAX_REPORTS) -> list[SearchRow]:
    """최신 `limit`개 기간, 기간마다 가장 늦은 접수(접수번호가 큰 것) 하나. 기간 내림차순.

    목록은 접수 순이지 기간 순이 아니므로(M1 관측) 행 순서에 기대지 않는다.
    """
    best: dict[str, SearchRow] = {}
    for row in rows:
        if not (row.rcp_no and row.report_type and row.period):
            continue
        kept = best.get(row.period)
        if kept is None or row.rcp_no > kept.rcp_no:
            best[row.period] = row
    return [best[p] for p in sorted(best, reverse=True)][:limit]


def parse_toc(html_text: str) -> list[dict[str, str]]:
    """`makeToc()` 자바스크립트의 노드 정의(`nodeN['키'] = "값"`)를 문서 순서대로 읽는다."""
    start = html_text.find("function makeToc")
    text = html_text[start:] if start >= 0 else html_text
    starts = list(_NODE_START.finditer(text))
    nodes: list[dict[str, str]] = []
    for i, m in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(text)
        node: dict[str, str] = {}
        for a in _NODE_ASSIGN.finditer(text, m.end(), end):
            if a.group(1) == m.group(1) and a.group(2) not in node:
                node[a.group(2)] = a.group(3)
        if "text" in node:
            nodes.append(node)
    return nodes


def find_node(nodes: list[dict[str, str]], title: str) -> dict[str, str] | None:
    return next((n for n in nodes if normalize_title(n["text"]) == title), None)


def parse_attachments(html_text: str) -> list[Attachment]:
    """본문 목차 페이지의 첨부 선택 목록. 값은 HTML 엔티티로 이스케이프되어 있다(M1 관측)."""
    soup = BeautifulSoup(html_text, "html.parser")
    select = soup.find("select", id="att")
    out: list[Attachment] = []
    if select is None:
        return out
    for opt in select.find_all("option"):
        value = opt.get("value") or ""
        for _ in range(3):  # 이중 이스케이프(`&amp;amp;`)까지 푼다
            unescaped = html_lib.unescape(value)
            if unescaped == value:
                break
            value = unescaped
        q = parse_qs(value)
        rcp, dcm = (q.get("rcpNo") or [""])[0], (q.get("dcmNo") or [""])[0]
        if not (NODE_PATTERNS["rcpNo"].fullmatch(rcp) and NODE_PATTERNS["dcmNo"].fullmatch(dcm)):
            continue
        name = _DATE_PREFIX.sub("", re.sub(r"\s+", "", opt.get_text()))
        if name in CONSOLIDATED_ATTACHMENTS:
            basis = "consolidated"
        elif name in SEPARATE_ATTACHMENTS:
            basis = "separate"
        else:
            basis = None
        out.append(Attachment(name=name, rcp_no=rcp, dcm_no=dcm, basis=basis))
    return out


def choose_attachment(options: list[Attachment], rcp_no: str) -> Attachment | None:
    """연결 검토·감사보고서 우선, 없으면 별도. 이름 완전 일치만."""
    for names in (CONSOLIDATED_ATTACHMENTS, SEPARATE_ATTACHMENTS):
        for name in names:
            for opt in options:
                if opt.name == name and opt.rcp_no == rcp_no:
                    return opt
    return None


class _TextExtractor(HTMLParser):
    """표의 행 하나·문단 하나를 한 줄로(plan T7). 셀은 ` | `로 잇는다."""

    BLOCK = {"p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6", "li", "title", "caption", "table", "pre"}
    SKIP = {"script", "style"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lines: list[str] = []
        self._buf: list[str] = []
        self._rows: list[list[str]] = []
        self._cells: list[list[str]] = []
        self._skip = 0

    def _flush(self) -> None:
        line = " ".join("".join(self._buf).split())
        self._buf = []
        if line:
            self.lines.append(line)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.SKIP:
            self._skip += 1
        elif tag == "tr":
            self._flush()
            self._rows.append([])
        elif tag in ("td", "th"):
            if not self._rows:
                self._rows.append([])
            self._cells.append([])
        elif tag in self.BLOCK:
            if self._cells:
                self._cells[-1].append(" ")
            else:
                self._flush()

    def handle_endtag(self, tag: str) -> None:
        if tag in self.SKIP:
            self._skip = max(0, self._skip - 1)
        elif tag in ("td", "th"):
            if self._cells:
                cell = " ".join("".join(self._cells.pop()).split())
                if self._rows:
                    self._rows[-1].append(cell)
        elif tag == "tr":
            if self._rows:
                cells = self._rows.pop()
                if any(cells):
                    self.lines.append(" | ".join(cells))
        elif tag in self.BLOCK and not self._cells:
            self._flush()

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        if self._cells:
            self._cells[-1].append(data)
        else:
            self._buf.append(data)

    def close(self) -> None:
        super().close()
        self._flush()


def html_to_text(raw: bytes) -> str:
    parser = _TextExtractor()
    parser.feed(raw.decode("utf-8", "replace"))
    parser.close()
    return "\n".join(parser.lines) + "\n"


# ─────────────────────────────────────────────────────────────────────────────
# 요청 세션: 순차 요청·간격·예산·크기·주소 검증


class _BudgetExhausted(Exception):
    """요청 수·시간 예산이 다 됨 — 남은 항목은 `skipped`."""


class _FetchError(Exception):
    pass


def _describe(exc: BaseException) -> str:
    msg = str(exc).strip()
    return f"{type(exc).__name__}: {msg}" if msg else type(exc).__name__


# @MX:WARN: [AUTO] 외부 시스템(DART) 진입점 — 네트워크·시간 예산이 여기서만 지켜진다
# @MX:REASON: 모든 요청이 이 메서드를 지나야 간격(1.0초)·요청 수(40)·총 예산(120초)·크기(8MB)·
#             호스트 완전 일치·리디렉트 비추적이 보장된다. 우회 경로를 만들지 말 것. 취소는 삼키지 않는다
class _Session:
    def __init__(
        self,
        client: httpx.AsyncClient,
        clock: Callable[[], float],
        sleep: Callable[[float], Awaitable[None]],
    ) -> None:
        self._client = client
        self._clock = clock
        self._sleep = sleep
        self._started = clock()
        self._last_start: float | None = None
        self.count = 0
        self.stopped: str | None = None

    def _remaining(self) -> float:
        return TOTAL_BUDGET_S - (self._clock() - self._started)

    async def fetch(self, method: str, url: str, form: list[tuple[str, str]] | None = None) -> bytes:
        check_url(url)
        if self.stopped is None and self.count >= MAX_REQUESTS:
            self.stopped = f"request limit {MAX_REQUESTS} reached"
        if self.stopped is None and self._last_start is not None:
            wait = self._last_start + MIN_INTERVAL_S - self._clock()
            if wait > 0:
                await self._sleep(wait)
        if self.stopped is None and self._remaining() <= 0:
            self.stopped = f"total budget {TOTAL_BUDGET_S:g}s exhausted"
        if self.stopped is not None:
            raise _BudgetExhausted(self.stopped)
        timeout = min(REQUEST_TIMEOUT_S, self._remaining())
        self.count += 1
        self._last_start = self._clock()
        return await asyncio.wait_for(self._send(method, url, form, timeout), timeout)

    async def _send(self, method: str, url: str, form: list[tuple[str, str]] | None, timeout: float) -> bytes:
        headers = {"User-Agent": USER_AGENT}
        content = None
        if form is not None:
            content = urlencode(form).encode("ascii")
            headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        request = self._client.build_request(
            method, url, content=content, headers=headers, timeout=httpx.Timeout(timeout)
        )
        response = await self._client.send(request, stream=True, follow_redirects=False)
        try:
            if response.status_code != 200:  # 3xx 포함 — 리디렉트는 따라가지 않는다
                raise _FetchError(f"HTTP {response.status_code}")
            declared = response.headers.get("content-length", "")
            if declared.isdigit() and int(declared) > MAX_RESPONSE_BYTES:
                raise _FetchError(f"response too large ({declared} bytes > {MAX_RESPONSE_BYTES})")
            buf = bytearray()
            async for chunk in response.aiter_bytes():
                buf.extend(chunk)
                if len(buf) > MAX_RESPONSE_BYTES:
                    raise _FetchError(f"response too large (> {MAX_RESPONSE_BYTES} bytes)")
            return bytes(buf)
        finally:
            await response.aclose()


# ─────────────────────────────────────────────────────────────────────────────
# 색인


def _iso(dt: datetime) -> str:
    return dt.astimezone(KST).isoformat(timespec="milliseconds")


def _now_kst() -> datetime:
    return datetime.now(KST)


def _empty_index(code: str, started: datetime) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "code": code,
        "company": None,
        "search": {
            "url": SEARCH_URL,
            "query": None,
            "searched_at": None,
            "status": "skipped",
            "row_count": None,
            "error": None,
        },
        "outcome": "failed",
        "started_at": _iso(started),
        "finished_at": None,
        "request_count": 0,
        "files": [],
    }


def _write_index(out_dir: Path, index: dict[str, Any]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = out_dir / (INDEX_FILE + ".tmp")
    tmp.write_text(json.dumps(index, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    tmp.replace(out_dir / INDEX_FILE)


def write_disabled_index(out_dir: Path, code: str, *, now: Callable[[], datetime] = _now_kst) -> dict[str, Any]:
    """끄기 스위치(`AI_REPORT_GOOSE_DART_PREFETCH=0`)일 때 작업 서비스가 쓰는 색인(REQ-AIR5-004)."""
    stamp = now()
    index = _empty_index(code, stamp)
    index["outcome"] = "disabled"
    index["finished_at"] = _iso(stamp)
    _write_index(Path(out_dir), index)
    return index


def _three_years_before(day: date) -> date:
    try:
        return day.replace(year=day.year - SEARCH_YEARS)
    except ValueError:  # 2월 29일
        return day.replace(year=day.year - SEARCH_YEARS, day=28)


# ─────────────────────────────────────────────────────────────────────────────
# 수집기


class _Run:
    """작업 1건의 수집 상태. 파일 이름은 서버가 만든다(순번 + 고정 키) — DART 문자열을 쓰지 않는다."""

    def __init__(self, session: _Session, out_dir: Path, now: Callable[[], datetime]) -> None:
        self.session = session
        self.out_dir = out_dir
        self.now = now
        self.files: list[dict[str, Any]] = []

    def entry(
        self,
        report: SearchRow,
        *,
        document: str,
        section: str,
        basis: str | None = None,
        attachment_name: str | None = None,
        section_title: str | None = None,
    ) -> dict[str, Any]:
        e = {
            "rcp_no": report.rcp_no,
            "report_type": report.report_type,
            "report_name": report.report_name,
            "period": report.period,
            "document": document,
            "attachment_name": attachment_name,
            "section": section,
            "section_title": section_title,
            "basis": basis,
            "viewer_url": None,
            "fetched_at": None,
            "html_file": None,
            "text_file": None,
            "sha256": None,
            "bytes": None,
            "status": "error",
            "error": None,
        }
        self.files.append(e)
        return e

    def fail(self, e: dict[str, Any], exc: BaseException | str) -> None:
        if isinstance(exc, _BudgetExhausted):
            e["status"], e["error"] = "skipped", str(exc)
            return
        e["status"] = "error"
        e["error"] = exc if isinstance(exc, str) else _describe(exc)
        e["fetched_at"] = _iso(self.now())

    async def fetch_section(self, e: dict[str, Any], node: dict[str, str], rcp_no: str, dcm_no: str | None = None):
        params = {k: node.get(k) for k in VIEWER_PARAMS}
        if not valid_node_params(params) or params["rcpNo"] != rcp_no or (dcm_no and params["dcmNo"] != dcm_no):
            self.fail(e, "invalid table-of-contents node values")
            return
        url = f"{VIEWER_URL}?{urlencode([(k, params[k]) for k in VIEWER_PARAMS])}"
        e["viewer_url"] = url
        try:
            raw = await self.session.fetch("GET", url)
        except Exception as exc:  # noqa: BLE001 — fail-open(REQ-AIR5-010). CancelledError는 Exception이 아니다
            self.fail(e, exc)
            return
        stem = f"{len([f for f in self.files if f['html_file']]) + 1:02d}_{e['section']}"
        html_name, text_name = f"{stem}.html", f"{stem}.txt"
        (self.out_dir / html_name).write_bytes(raw)
        (self.out_dir / text_name).write_text(html_to_text(raw), encoding="utf-8")
        e.update(
            fetched_at=_iso(self.now()),
            html_file=html_name,
            text_file=text_name,
            sha256=hashlib.sha256(raw).hexdigest(),
            bytes=len(raw),
            status="ok",
            error=None,
        )

    async def toc(self, url: str) -> tuple[str, list[dict[str, str]]]:
        text = (await self.session.fetch("GET", url)).decode("utf-8", "replace")
        nodes = parse_toc(text)
        if not nodes:
            raise _FetchError("table of contents not found")
        return text, nodes

    async def report(self, report: SearchRow, *, notes: bool, summary: bool, attachment: bool) -> None:
        rcp = report.rcp_no
        sections = ["financial_statements"] + (["notes"] if notes else []) + (["summary"] if summary else [])
        try:
            toc_html, nodes = await self.toc(f"{TOC_URL}?{urlencode({'rcpNo': rcp})}")
        except Exception as exc:  # noqa: BLE001 — 이 보고서만 실패로 적고 다른 보고서는 계속한다
            for section in sections:
                self.fail(self.entry(report, document="main", section=section), exc)
            if attachment:
                self.fail(self.entry(report, document="attachment", section="auditor_report"), exc)
            return

        fs_node, basis = None, None
        for b in ("consolidated", "separate"):
            fs_node = find_node(nodes, TITLE_FS[b])
            if fs_node is not None:
                basis = b
                break
        for section in sections:
            if section == "financial_statements":
                node, sec_basis = fs_node, basis
            elif section == "notes":
                order = (basis,) if basis else ("consolidated", "separate")
                node, sec_basis = None, None
                for b in order:
                    node = find_node(nodes, TITLE_NOTES[b])
                    if node is not None:
                        sec_basis = b
                        break
            else:
                node, sec_basis = find_node(nodes, TITLE_SUMMARY), None
            e = self.entry(
                report, document="main", section=section, basis=sec_basis,
                section_title=node["text"] if node else None,
            )
            if node is None:
                self.fail(e, "section not found in table of contents")
                continue
            await self.fetch_section(e, node, rcp)

        if attachment:
            await self.attachment(report, toc_html)

    async def attachment(self, report: SearchRow, toc_html: str) -> None:
        rcp = report.rcp_no
        chosen = choose_attachment(parse_attachments(toc_html), rcp)
        if chosen is None:
            self.fail(
                self.entry(report, document="attachment", section="auditor_report"),
                "review/audit report attachment not found",
            )
            return
        url = f"{TOC_URL}?{urlencode({'rcpNo': rcp, 'dcmNo': chosen.dcm_no})}"
        try:
            _, nodes = await self.toc(url)
            before: list[dict[str, str]] = []
            for node in nodes:
                if normalize_title(node["text"]).startswith(ATTACHED_COPY_PREFIX):
                    break
                before.append(node)
            else:
                raise _FetchError("attached financial statements marker not found")
            if not before:
                raise _FetchError("no auditor report node before attached financial statements")
        except Exception as exc:  # noqa: BLE001
            self.fail(
                self.entry(
                    report, document="attachment", section="auditor_report",
                    basis=chosen.basis, attachment_name=chosen.name,
                ),
                exc,
            )
            return
        for node in before:
            e = self.entry(
                report, document="attachment", section="auditor_report", basis=chosen.basis,
                attachment_name=chosen.name, section_title=node["text"],
            )
            await self.fetch_section(e, node, rcp, chosen.dcm_no)


# @MX:ANCHOR: [AUTO] 사전 수집기 공개 진입점 — 작업 서비스(M3)가 생성자 주입으로 부른다
# @MX:REASON: 호출 계약 `await prefetcher(code, out_dir) -> index`. 실패는 색인에 적고 정상 반환,
#             CancelledError만 전파(REQ-AIR5-002·010). 이 계약을 바꾸면 작업 서비스의 취소·fail-open이 깨진다
# @MX:SPEC: SPEC-AI-REPORT-005
class DartPrefetcher:
    """DART 정기보고서 원문 사전 수집기. 테스트는 전송 계층·시계·대기 함수를 주입한다."""

    def __init__(
        self,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        now: Callable[[], datetime] = _now_kst,
    ) -> None:
        self._transport = transport
        self._clock = clock
        self._sleep = sleep
        self._now = now

    async def __call__(self, code: str, out_dir: Path) -> dict[str, Any]:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        index = _empty_index(code, self._now())
        session: _Session | None = None
        try:
            if not isinstance(code, str) or not CODE_RE.fullmatch(code):
                index["search"].update(status="error", error="invalid stock code (six ASCII digits required)")
            else:
                async with httpx.AsyncClient(transport=self._transport, follow_redirects=False) as client:
                    session = _Session(client, self._clock, self._sleep)
                    await self._collect(code, _Run(session, out_dir, self._now), index)
        except Exception as exc:  # noqa: BLE001 — 예상 못 한 예외도 fail-open(REQ-AIR5-010)
            logger.exception("goose DART 사전 수집 중 예외 (code=%s)", code)
            index["outcome"] = "failed"
            if index["search"]["error"] is None:
                index["search"]["error"] = f"unexpected: {_describe(exc)}"
        index["request_count"] = session.count if session else 0
        index["finished_at"] = _iso(self._now())
        _write_index(out_dir, index)
        return index

    async def _collect(self, code: str, run: _Run, index: dict[str, Any]) -> None:
        today = self._now().astimezone(KST).date()
        form = [
            ("currentPage", "1"),
            ("maxResults", "100"),
            ("maxLinks", "10"),
            ("sort", "date"),
            ("series", "desc"),
            ("textCrpNm", code),
            ("startDate", _three_years_before(today).strftime("%Y%m%d")),
            ("endDate", today.strftime("%Y%m%d")),
            *[("publicType", t) for t in PUBLIC_TYPES],
            ("finalReport", "recent"),
        ]
        search = index["search"]
        search["query"] = urlencode(form)
        search["searched_at"] = _iso(self._now())
        try:
            raw = await run.session.fetch("POST", SEARCH_URL, form)
            rows = parse_search_rows(raw.decode("utf-8", "replace"))
        except Exception as exc:  # noqa: BLE001
            search.update(status="error", error=_describe(exc))
            index["outcome"] = "failed"
            return
        search.update(status="ok", row_count=len(rows))

        corp_codes = {r.corp_code for r in rows}
        if not rows or len(corp_codes) != 1 or None in corp_codes:
            # 결과 행이 정확히 한 회사에 속하지 않으면 더 요청하지 않는다(REQ-AIR5-005)
            index["outcome"] = "company_unresolved"
            return
        index["company"] = {"name": rows[0].company, "corp_code": rows[0].corp_code}

        reports = select_reports(rows)
        latest = reports[0] if reports else None
        annual = next((r for r in reports if r.report_type == "사업보고서"), None)
        index["files"] = run.files  # 같은 목록 — 중간 예외가 나도 이미 받은 항목은 색인에 남는다
        for report in reports:
            await run.report(
                report,
                notes=report is latest,
                summary=report is annual,
                attachment=report is latest or report is annual,
            )
        statuses = [f["status"] for f in run.files]
        if statuses and all(s == "ok" for s in statuses):
            index["outcome"] = "complete"
        elif "ok" in statuses:
            index["outcome"] = "partial"
        else:
            index["outcome"] = "failed"
