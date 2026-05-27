"""도메인 필터 크기 한계 정밀 탐색."""

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
PROMPT = "대한광통신 최근 7일 주가 알려주세요."

ALL_WHITELIST = [
    "dart.fss.or.kr", "kind.krx.co.kr",
    "hankyung.com", "mk.co.kr", "chosun.com", "biz.chosun.com",
    "newsis.com", "news.nate.com",
    "finance.naver.com", "stock.naver.com", "m.finance.daum.net",
    "wisereport.co.kr", "comp.wisereport.co.kr",
    "fnguide.com", "comp.fnguide.com",
    "stockplus.com", "alphasquare.co.kr",
]
ALL_BLACKLIST = [
    "-youtube.com", "-tistory.com", "-blog.naver.com", "-instagram.com", "-x.com",
]


def run(label, domains):
    payload = {
        "model": "sonar-pro",
        "stream": False,
        "search_domain_filter": domains,
        "messages": [
            {"role": "system", "content": "Korean analyst."},
            {"role": "user", "content": PROMPT},
        ],
    }
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    start = time.time()
    try:
        r = httpx.post(URL, headers=headers, json=payload, timeout=30.0)
        elapsed = time.time() - start
        if r.status_code == 200:
            body = r.json()
            content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
            status = "OK" if content else "EMPTY"
            print(f"[{status:5}] {label:40} count={len(domains):3} time={elapsed:.2f}s chars={len(content)}")
            if status == "EMPTY":
                # empty 응답의 body 구조 확인
                print(f"          body keys: {list(body.keys())}")
                print(f"          body snippet: {str(body)[:200]}")
        else:
            body = r.text[:200]
            print(f"[HTTP{r.status_code}] {label:40} count={len(domains):3} body={body}")
    except Exception as e:
        print(f"[ERR] {label}: {type(e).__name__}: {e}")


# 크기별 테스트
run("w:17 only", ALL_WHITELIST[:17])
run("w:18", ALL_WHITELIST[:17] + ["google.com"])
run("w:19", ALL_WHITELIST[:17] + ["google.com", "bing.com"])
run("w:20", ALL_WHITELIST[:17] + ["google.com", "bing.com", "yahoo.com"])
run("w:5 + b:5 (10)", ALL_WHITELIST[:5] + ALL_BLACKLIST)
run("w:7 + b:5 (12)", ALL_WHITELIST[:7] + ALL_BLACKLIST)
run("w:10 + b:5 (15)", ALL_WHITELIST[:10] + ALL_BLACKLIST)
run("w:12 + b:5 (17)", ALL_WHITELIST[:12] + ALL_BLACKLIST)
run("w:15 + b:5 (20)", ALL_WHITELIST[:15] + ALL_BLACKLIST)
run("w:17 + b:5 (22) = FULL", ALL_WHITELIST[:17] + ALL_BLACKLIST)
run("w:17 + b:3 (20)", ALL_WHITELIST[:17] + ALL_BLACKLIST[:3])
