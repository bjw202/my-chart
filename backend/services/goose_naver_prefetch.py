"""SPEC-AI-REPORT-007 M2 — goose 네이버 최신 뉴스 사전 수집.

goose 실행 직전에 서버가 네이버 증권 모바일 뉴스 JSON을 한 번 받아 `runs/<job_id>/naver/`에
기사별 텍스트 파일(`NN_article.txt`)·원본 응답(`response.json`)·`index.json`으로 저장한다.
goose 권한은 넓히지 않는다(spec D1). 구조는 SPEC-AI-REPORT-005의 `goose_dart_prefetch.py`를 따르되
공용 헬퍼는 뽑아내지 않는다(plan T8).

흐름: 종목코드 검사·요청 1회(REQ-AIR7-005) → 응답 해석(그룹 펼침·모양 오류 기록·평문 변환, 006)
→ 저장·색인(007) → `outcome` 판정(014). 어떤 실패도 색인에 기록하고 정상 반환한다(008, fail-open).
취소(CancelledError)는 실패가 아니므로 그대로 전파한다.

경계:
- 받는 것은 기사 전문이 아니라 API가 주는 제목과 약 150자 요약 본문이다(spec D3). 원문 페이지는 받지 않는다.
- 응답의 다른 키(`titleFull`, `mobileNewsUrl` 등)는 무시하고, 기사 주소는 검증된 식별자로만 만든다.
- 작업 서비스 연결(생성자 주입, 끄기 스위치, `code_validated` 전달)은 M3 몫이다. 이 모듈은 수집기와
  끄기 상태 색인 작성 함수(`write_disabled_index`)만 제공한다.
"""

from __future__ import annotations

import asyncio
import hashlib
import html
import json
import logging
import re
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))

NAVER_HOST = "m.stock.naver.com"
PAGE_SIZE = 10
PAGE = 1
ARTICLE_URL = "https://n.news.naver.com/mnews/article/{office_id}/{article_id}"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)

INDEX_FILE = "index.json"
RESPONSE_FILE = "response.json"
SCHEMA_VERSION = 1
CHANNEL = "naver"

# @MX:NOTE: [AUTO] 상한 수치(spec REQ-AIR7-005). 테스트는 REQUEST_TIMEOUT_S를 낮춰 시간 상한을 관측한다
REQUEST_TIMEOUT_S = 10.0  # 요청 전체(전송 + 본문 읽기) 상한 — asyncio.wait_for로 전송 계층과 무관하게 보장
MAX_RESPONSE_BYTES = 2 * 1024 * 1024  # 응답 크기 상한(2 MB)
MAX_ARTICLES = 10  # 펼친 기사 목록 중 앞 10건만 저장

CODE_RE = re.compile(r"[0-9]{6}")  # ASCII 숫자만(전각 숫자 거부)
ID_RE = re.compile(r"[0-9]{1,12}")  # officeId·articleId
DATETIME_RE = re.compile(r"[0-9]{12}")  # YYYYMMDDHHMM
_TAG_RE = re.compile(r"<[^>]+>")


# ─────────────────────────────────────────────────────────────────────────────
# 검증·평문 변환


def news_url(code: str) -> str:
    return f"https://{NAVER_HOST}/api/news/stock/{code}?pageSize={PAGE_SIZE}&page={PAGE}"


def check_url(url: str) -> None:
    """https + 호스트 완전 일치(`m.stock.naver.com`)가 아니면 ValueError. 부분 문자열 검사 금지."""
    parts = urlsplit(url)
    if (
        parts.scheme != "https"
        or parts.hostname != NAVER_HOST
        or parts.username is not None
        or parts.password is not None
        or parts.port not in (None, 443)
    ):
        raise ValueError(f"disallowed url: {url!r}")


def to_plain(text: str) -> str:
    """(1) 태그 제거 → (2) HTML 문자 참조 해제(이름·10진·16진) → (3) 앞뒤 공백 정리(REQ-AIR7-006).

    순서가 중요하다: 해제를 먼저 하면 `&lt;b&gt;`가 태그로 바뀐 뒤 지워져 글자가 사라진다.
    """
    return html.unescape(_TAG_RE.sub("", text)).strip()


def to_published_at(value: Any) -> str | None:
    """`YYYYMMDDHHMM`을 `+09:00`이 붙은 ISO-8601로. 형식이 틀리면 None."""
    if not isinstance(value, str) or not DATETIME_RE.fullmatch(value):
        return None
    try:
        dt = datetime.strptime(value, "%Y%m%d%H%M").replace(tzinfo=KST)
    except ValueError:
        return None
    return dt.isoformat(timespec="seconds")


# ─────────────────────────────────────────────────────────────────────────────
# 응답 해석


class _ParseError(Exception):
    """응답 전체를 쓸 수 없음 — 색인 `outcome`은 `failed`."""


def _null_entry(status: str, error: str | None) -> dict[str, Any]:
    return {
        "article_ref": None,
        "office_id": None,
        "article_id": None,
        "office_name": None,
        "title": None,
        "published_at": None,
        "article_url": None,
        "text_file": None,
        "body_chars": None,
        "status": status,
        "error": error,
    }


def parse_articles(data: Any) -> tuple[list[tuple[str, Any]], int]:
    """응답 JSON을 응답 순서의 칸 목록과 펼친 기사 수(상한 전)로 바꾼다.

    칸: `("group_error", "<사유>")` 또는 `("article", 기사 값)`. 기사는 앞 MAX_ARTICLES건만 남긴다.
    그룹 `total`은 쓰지 않는다(M1 관측 — 기사 수가 아니다). 최상위가 배열이 아니거나, 비어 있지 않은
    배열인데 `items` 배열을 가진 그룹이 하나도 없으면 _ParseError(REQ-AIR7-008).
    """
    if not isinstance(data, list):
        raise _ParseError("top-level JSON value is not an array")
    if data and not any(isinstance(g, dict) and isinstance(g.get("items"), list) for g in data):
        raise _ParseError("no group has an items array")
    slots: list[tuple[str, Any]] = []
    flattened = 0
    for no, group in enumerate(data, 1):
        if not isinstance(group, dict):
            slots.append(("group_error", f"group {no}: group not an object"))
            continue
        if "items" not in group:
            slots.append(("group_error", f"group {no}: items missing"))
            continue
        items = group["items"]
        if not isinstance(items, list):
            slots.append(("group_error", f"group {no}: items not a list"))
            continue
        for item in items:
            flattened += 1
            if flattened <= MAX_ARTICLES:
                slots.append(("article", (no, item)))
    return slots, flattened


def _article_entry(group_no: int, item: Any) -> tuple[dict[str, Any], str | None]:
    """기사 하나의 색인 항목과 (ok일 때) 텍스트 파일 본문."""
    if not isinstance(item, dict):
        return _null_entry("error", f"group {group_no}: article not an object"), None
    office_id, article_id = item.get("officeId"), item.get("articleId")
    if not (isinstance(office_id, str) and ID_RE.fullmatch(office_id)):
        return _null_entry("error", "invalid officeId"), None
    if not (isinstance(article_id, str) and ID_RE.fullmatch(article_id)):
        return _null_entry("error", "invalid articleId"), None
    published_at = to_published_at(item.get("datetime"))
    if published_at is None:
        return _null_entry("error", "invalid datetime (YYYYMMDDHHMM required)"), None
    title, body = item.get("title"), item.get("body")
    if not isinstance(title, str):
        return _null_entry("error", "title not a string"), None
    if body is not None and not isinstance(body, str):
        return _null_entry("error", "body not a string"), None
    office_name = item.get("officeName")
    office_name = to_plain(office_name) if isinstance(office_name, str) else None
    title_text, body_text = to_plain(title), to_plain(body or "")
    entry = _null_entry("ok" if body_text else "metadata_only", None)
    entry.update(
        article_ref=f"{office_id}/{article_id}",
        office_id=office_id,
        article_id=article_id,
        office_name=office_name,
        title=title_text,
        published_at=published_at,
        article_url=ARTICLE_URL.format(office_id=office_id, article_id=article_id),
        body_chars=len(body_text),
    )
    if not body_text:
        return entry, None
    text = (
        f"제목: {title_text}\n"
        f"언론사: {office_name or ''}\n"
        f"게시 시각: {published_at}\n"
        f"본문(모바일 뉴스 API 요약본, 약 150자 — 기사 전문 아님):\n{body_text}\n"
    )
    return entry, text


def derive_outcome(statuses: list[str]) -> str:
    """REQ-AIR7-014 판정(요청·응답 처리 실패와 끄기 상태는 호출부가 정한다)."""
    if not statuses:
        return "no_results"
    if all(s == "ok" for s in statuses):
        return "complete"
    if "ok" in statuses:
        return "partial"
    return "failed"


# ─────────────────────────────────────────────────────────────────────────────
# 색인


def _iso(dt: datetime) -> str:
    return dt.astimezone(KST).isoformat(timespec="milliseconds")


def _now_kst() -> datetime:
    return datetime.now(KST)


def _describe(exc: BaseException) -> str:
    msg = str(exc).strip()
    return f"{type(exc).__name__}: {msg}" if msg else type(exc).__name__


def _empty_index(code: str, code_validated: bool, started: datetime) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "code": code,
        "code_validated": bool(code_validated),
        "channel": CHANNEL,
        "search": {
            "url": None,
            "query": None,
            "searched_at": None,
            "status": "skipped",
            "item_count": None,
            "error": None,
        },
        "outcome": "failed",
        "started_at": _iso(started),
        "finished_at": None,
        "request_count": 0,
        "response_file": None,
        "response_sha256": None,
        "response_bytes": None,
        "articles": [],
    }


def _write_index(out_dir: Path, index: dict[str, Any]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = out_dir / (INDEX_FILE + ".tmp")
    tmp.write_text(json.dumps(index, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    tmp.replace(out_dir / INDEX_FILE)


def write_disabled_index(
    out_dir: Path, code: str, *, code_validated: bool = False, now: Callable[[], datetime] = _now_kst
) -> dict[str, Any]:
    """끄기 스위치(`AI_REPORT_GOOSE_NAVER_PREFETCH=0`)일 때 작업 서비스가 쓰는 색인(REQ-AIR7-003·015)."""
    stamp = now()
    index = _empty_index(code, code_validated, stamp)
    index["outcome"] = "disabled"
    index["finished_at"] = _iso(stamp)
    _write_index(Path(out_dir), index)
    return index


# ─────────────────────────────────────────────────────────────────────────────
# 요청


class _FetchError(Exception):
    pass


# @MX:WARN: [AUTO] 외부 시스템(네이버 모바일 API) 진입점 — 요청은 이 함수 하나로만 나간다
# @MX:REASON: 호스트 완전 일치·리디렉트 비추적·선언 길이 선검사(본문 읽기 전)·스트리밍 누적 상한(2 MB)이
#             여기서만 지켜진다. 시간 상한은 호출부의 asyncio.wait_for가 맡는다(MockTransport는 httpx 상한 미적용)
async def _send(client: httpx.AsyncClient, url: str) -> bytes:
    check_url(url)
    request = client.build_request(
        "GET", url, headers={"User-Agent": USER_AGENT}, timeout=httpx.Timeout(REQUEST_TIMEOUT_S)
    )
    response = await client.send(request, stream=True, follow_redirects=False)
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
# 수집기


# @MX:ANCHOR: [AUTO] 네이버 사전 수집기 공개 진입점 — 작업 서비스(M3)가 생성자 주입으로 부른다
# @MX:REASON: 호출 계약 `await prefetcher(code, out_dir, code_validated=<bool>) -> index`. 실패는 색인에 적고
#             정상 반환, CancelledError만 전파(REQ-AIR7-002·008). 바꾸면 작업 서비스의 취소·fail-open이 깨진다
# @MX:SPEC: SPEC-AI-REPORT-007
class NaverPrefetcher:
    """네이버 증권 모바일 뉴스 사전 수집기. 테스트는 전송 계층과 벽시계를 주입한다."""

    def __init__(
        self,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        now: Callable[[], datetime] = _now_kst,
    ) -> None:
        self._transport = transport
        self._now = now

    async def __call__(self, code: str, out_dir: Path, *, code_validated: bool = False) -> dict[str, Any]:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        index = _empty_index(code, code_validated, self._now())
        try:
            if not isinstance(code, str) or not CODE_RE.fullmatch(code):
                index["search"].update(status="error", error="invalid stock code (six ASCII digits required)")
            else:
                await self._collect(code, out_dir, index)
        except Exception as exc:  # noqa: BLE001 — 예상 못 한 예외도 fail-open(REQ-AIR7-008)
            logger.exception("goose 네이버 사전 수집 중 예외 (code=%s)", code)
            index["outcome"] = "failed"
            index["articles"] = []
            if not index["search"]["error"]:
                index["search"].update(status="error", error=f"unexpected: {_describe(exc)}")
        index["finished_at"] = _iso(self._now())
        _write_index(out_dir, index)
        return index

    async def _collect(self, code: str, out_dir: Path, index: dict[str, Any]) -> None:
        url = news_url(code)
        search = index["search"]
        search.update(
            url=url,
            query=f"네이버 증권 모바일 뉴스 API 종목코드 {code} (pageSize={PAGE_SIZE}, page={PAGE})",
            searched_at=_iso(self._now()),
        )
        try:
            async with httpx.AsyncClient(transport=self._transport, follow_redirects=False) as client:
                index["request_count"] = 1
                raw = await asyncio.wait_for(_send(client, url), REQUEST_TIMEOUT_S)
        except Exception as exc:  # noqa: BLE001 — 연결·시간·상태·크기 실패. CancelledError는 Exception이 아니다
            search.update(status="error", error=_describe(exc))
            index["outcome"] = "failed"
            return

        (out_dir / RESPONSE_FILE).write_bytes(raw)
        index.update(
            response_file=RESPONSE_FILE,
            response_sha256=hashlib.sha256(raw).hexdigest(),
            response_bytes=len(raw),
        )
        try:
            slots, flattened = parse_articles(json.loads(raw.decode("utf-8")))
        except (_ParseError, ValueError) as exc:  # JSON·UTF-8 오류는 ValueError 하위
            search.update(status="error", error=_describe(exc))
            index["outcome"] = "failed"
            return
        search.update(status="ok", item_count=flattened)

        written = 0
        for kind, value in slots:
            if kind == "group_error":
                index["articles"].append(_null_entry("error", value))
                continue
            entry, text = _article_entry(*value)
            if text is not None:
                written += 1
                name = f"{written:02d}_article.txt"  # 서버가 만든 이름 — 응답 문자열을 쓰지 않는다
                (out_dir / name).write_text(text, encoding="utf-8")
                entry["text_file"] = name
            index["articles"].append(entry)
        index["outcome"] = derive_outcome([a["status"] for a in index["articles"]])
