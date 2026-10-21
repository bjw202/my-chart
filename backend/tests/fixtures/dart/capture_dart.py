"""SPEC-AI-REPORT-005 M1 DART 픽스처 1회 수집 스크립트 (테스트에서 실행하지 않음).

요청 10회 이하, 요청 시작 간격 1.1초 이상, dart.fss.or.kr 공개 페이지만 읽는다.
실행: /Users/byunjungwon/Dev/my_chart/.venv/bin/python -I backend/tests/fixtures/dart/capture_dart.py backend/tests/fixtures/dart/recorded
"""
import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
KST = timezone(timedelta(hours=9))
BASE = "https://dart.fss.or.kr"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
# 1차 실행(2026-10-21 11:45 KST)에서 본문 직렬화 오류로 요청 1건이 중단됨 → 그 1건을 상한에 포함
MAX_REQ = 9
log = []
last = [0.0]
client = httpx.Client(headers={"User-Agent": UA}, follow_redirects=False, timeout=20)


def req(method, url, fname, data=None):
    assert len(log) < MAX_REQ, "요청 상한 초과"
    p = urlparse(url)
    assert p.scheme == "https" and p.hostname == "dart.fss.or.kr", url
    wait = 1.1 - (time.monotonic() - last[0])
    if wait > 0:
        time.sleep(wait)
    started = datetime.now(KST).isoformat(timespec="milliseconds")
    t0 = time.monotonic()
    last[0] = t0
    r = client.request(method, url, data=data)
    el = time.monotonic() - t0
    (OUT / fname).write_bytes(r.content)
    entry = {"n": len(log) + 1, "started_at": started, "method": method, "url": url,
             "form": data, "status": r.status_code, "bytes": len(r.content),
             "content_type": r.headers.get("content-type"), "elapsed_s": round(el, 3),
             "file": fname}
    log.append(entry)
    print(json.dumps(entry, ensure_ascii=False), flush=True)
    return r.text


def nodes(html):
    out = []
    for _, text, rest in re.findall(
            r"(node\d)\['text'\] = \"(.*?)\";(.*?)(?=node\d\['text'\]|$)", html, re.S):
        d = {"text": text}
        for k in ("rcpNo", "dcmNo", "eleId", "offset", "length", "dtd"):
            m = re.search(r"\['%s'\] = \"(.*?)\"" % k, rest)
            d[k] = m.group(1) if m else None
        out.append(d)
    return out


def attachments(html):
    return re.findall(
        r'<option value="(rcpNo=\d+&(?:amp;)?dcmNo=\d+)"[^>]*>\s*([^<]*?)\s*</option>', html)


def list_form(code, recent):
    # httpx 0.28은 튜플 목록을 받지 않는다 — 같은 키 반복은 리스트 값으로 준다
    f = {"currentPage": "1", "maxResults": "100", "maxLinks": "10", "sort": "date",
         "series": "desc", "textCrpNm": code, "startDate": "20231021", "endDate": "20261021",
         "publicType": ["A001", "A002", "A003"]}
    if recent:
        f["finalReport"] = "recent"
    return f


def viewer(n):
    return (f"{BASE}/report/viewer.do?rcpNo={n['rcpNo']}&dcmNo={n['dcmNo']}&eleId={n['eleId']}"
            f"&offset={n['offset']}&length={n['length']}&dtd={n['dtd']}")


def pick(ns, title):
    m = [n for n in ns if n["text"].strip() == title]
    assert m, (title, [n["text"] for n in ns])
    return m[0]


HALF, ANNUAL = "20260814000373", "20260310002974"
try:
    # 1. 020150 정기보고서 목록 (운영 형태, finalReport=recent)
    req("POST", f"{BASE}/dsab007/detailSearch.ax", "list_020150_recent.html",
        list_form("020150", True))
    # 2. 반기보고서 본문 목차
    hn = nodes(req("GET", f"{BASE}/dsaf001/main.do?rcpNo={HALF}", f"main_{HALF}.html"))
    # 3. 반기연결검토보고서 첨부 목차
    req("GET", f"{BASE}/dsaf001/main.do?rcpNo={HALF}&dcmNo=11527105",
        f"main_{HALF}_11527105.html")
    # 4. 연결재무제표, 5. 연결재무제표 주석 (반기)
    req("GET", viewer(pick(hn, "2. 연결재무제표")), f"viewer_{HALF}_fs_consolidated.html")
    req("GET", viewer(pick(hn, "3. 연결재무제표 주석")), f"viewer_{HALF}_notes_consolidated.html")
    # 6. 최신 사업보고서 목차
    a = req("GET", f"{BASE}/dsaf001/main.do?rcpNo={ANNUAL}", f"main_{ANNUAL}.html")
    an = nodes(a)
    # 7. 사업보고서 요약재무정보
    req("GET", viewer(pick(an, "1. 요약재무정보")), f"viewer_{ANNUAL}_summary.html")
    # 8. 사업보고서 첨부 감사보고서 목차 (연결 우선)
    atts = [(v.replace("&amp;", "&"), t) for v, t in attachments(a)]
    print("ANNUAL_ATTACHMENTS", json.dumps(atts, ensure_ascii=False), flush=True)
    aud = ([x for x in atts if "연결" in x[1] and "감사" in x[1]]
           or [x for x in atts if "감사" in x[1]])
    assert aud, atts
    dcm = re.search(r"dcmNo=(\d+)", aud[0][0]).group(1)
    tn = nodes(req("GET", f"{BASE}/dsaf001/main.do?{aud[0][0]}", f"main_{ANNUAL}_{dcm}.html"))
    print("AUDIT_TOC", json.dumps(tn, ensure_ascii=False), flush=True)
    # 감사보고서 본문 구간은 요청 상한(중단 1건 포함 10회) 때문에 받지 않았다 (README 참조)
    # 9. F4 확인: 299030(하나기술, [기재정정] 사업보고서 (2025.12) 이력)을 finalReport=recent로
    req("POST", f"{BASE}/dsab007/detailSearch.ax", "list_299030_recent.html",
        list_form("299030", True))
finally:
    (OUT / "request_log.json").write_text(json.dumps(log, ensure_ascii=False, indent=1) + "\n")
    print("DONE", len(log))
