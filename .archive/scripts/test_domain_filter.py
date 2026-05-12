"""search_domain_filter 세부 테스트: whitelist-only, blacklist-only, 크기, 포맷."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

import httpx

API_KEY = os.environ["PERPLEXITY_API_KEY"]
URL = "https://api.perplexity.ai/chat/completions"
PROMPT = "대한광통신(010170) 최근 7일 주가 핵심 모멘텀을 한 문단으로 알려주세요. 출처 포함."


def run(label: str, domain_filter):
    payload = {
        "model": "sonar-pro",
        "stream": True,
        "messages": [
            {"role": "system", "content": "You are a Korean stock market analyst."},
            {"role": "user", "content": PROMPT},
        ],
    }
    if domain_filter is not None:
        payload["search_domain_filter"] = domain_filter

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    start = time.time()
    chunks = 0
    chars = 0
    err = None
    http_body = None
    try:
        with httpx.Client(timeout=45.0) as c:
            with c.stream("POST", URL, headers=headers, json=payload) as r:
                if r.status_code != 200:
                    http_body = r.read().decode(errors="replace")[:300]
                else:
                    for line in r.iter_lines():
                        if line.startswith("data: "):
                            raw = line[6:].strip()
                            if raw == "[DONE]":
                                break
                            try:
                                d = json.loads(raw)
                                content = d.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if content:
                                    chunks += 1
                                    chars += len(content)
                            except json.JSONDecodeError:
                                pass
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
    elapsed = time.time() - start
    status = "OK" if chunks > 0 else ("EMPTY" if not err and not http_body else "ERR")
    body_snip = f" | body={http_body}" if http_body else ""
    err_snip = f" | err={err}" if err else ""
    print(f"[{status:5}] {label:50} | chunks={chunks:4} chars={chars:5} time={elapsed:.2f}s{body_snip}{err_snip}")


# Test cases
cases = [
    ("None (baseline)", None),
    ("single whitelist: dart.fss.or.kr", ["dart.fss.or.kr"]),
    ("single whitelist: naver.com", ["naver.com"]),
    ("single blacklist: -youtube.com", ["-youtube.com"]),
    ("2 mixed: dart + -youtube", ["dart.fss.or.kr", "-youtube.com"]),
    ("3 major dailies", ["hankyung.com", "mk.co.kr", "chosun.com"]),
    ("5 whitelist", ["dart.fss.or.kr", "kind.krx.co.kr", "hankyung.com", "mk.co.kr", "chosun.com"]),
    ("10 whitelist", ["dart.fss.or.kr", "kind.krx.co.kr", "hankyung.com", "mk.co.kr",
                       "chosun.com", "newsis.com", "naver.com", "daum.net", "fnguide.com", "wisereport.co.kr"]),
    ("17 whitelist only (no blacklist)", [
        "dart.fss.or.kr", "kind.krx.co.kr",
        "hankyung.com", "mk.co.kr", "chosun.com", "biz.chosun.com",
        "newsis.com", "news.nate.com",
        "finance.naver.com", "stock.naver.com", "m.finance.daum.net",
        "wisereport.co.kr", "comp.wisereport.co.kr",
        "fnguide.com", "comp.fnguide.com",
        "stockplus.com", "alphasquare.co.kr",
    ]),
    ("5 blacklist only", ["-youtube.com", "-tistory.com", "-blog.naver.com", "-instagram.com", "-x.com"]),
    ("broad domains (top-level only)", [
        "dart.fss.or.kr", "krx.co.kr",
        "hankyung.com", "mk.co.kr", "chosun.com",
        "newsis.com", "naver.com", "daum.net", "fnguide.com",
    ]),
    ("v1.1.0 full (22 entries)", [
        "dart.fss.or.kr", "kind.krx.co.kr",
        "hankyung.com", "mk.co.kr", "chosun.com", "biz.chosun.com",
        "newsis.com", "news.nate.com",
        "finance.naver.com", "stock.naver.com", "m.finance.daum.net",
        "wisereport.co.kr", "comp.wisereport.co.kr",
        "fnguide.com", "comp.fnguide.com",
        "stockplus.com", "alphasquare.co.kr",
        "-youtube.com", "-tistory.com", "-blog.naver.com", "-instagram.com", "-x.com",
    ]),
]

for label, flt in cases:
    run(label, flt)
