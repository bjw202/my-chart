"""Perplexity API 호출 직접 테스트: v1.1.0 파라미터가 실제로 동작하는지 검증.

실행:
    python3 scripts/test_perplexity.py [--minimal|--v11|--domain-only|--recency-only|--ctx-only|--related-only]
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# .env 로드
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

import httpx

API_KEY = os.environ.get("PERPLEXITY_API_KEY")
if not API_KEY:
    print("ERROR: PERPLEXITY_API_KEY not set")
    sys.exit(1)

URL = "https://api.perplexity.ai/chat/completions"

SIMPLE_PROMPT = "대한광통신(010170) 최근 7일 주가 핵심 모멘텀을 한 문단으로 알려주세요. 출처 포함."

MINIMAL_PAYLOAD = {
    "model": "sonar-pro",
    "stream": True,
    "messages": [
        {"role": "system", "content": "You are a Korean stock market analyst."},
        {"role": "user", "content": SIMPLE_PROMPT},
    ],
}

# SPEC v1.1.0 도메인 필터
SEARCH_DOMAIN_FILTER = [
    "dart.fss.or.kr", "kind.krx.co.kr",
    "hankyung.com", "mk.co.kr", "chosun.com", "biz.chosun.com",
    "newsis.com", "news.nate.com",
    "finance.naver.com", "stock.naver.com", "m.finance.daum.net",
    "wisereport.co.kr", "comp.wisereport.co.kr",
    "fnguide.com", "comp.fnguide.com",
    "stockplus.com", "alphasquare.co.kr",
    "-youtube.com", "-tistory.com", "-blog.naver.com", "-instagram.com", "-x.com",
]

V11_PAYLOAD = {
    "model": "sonar-pro",
    "stream": True,
    "temperature": 0.2,
    "max_tokens": 8000,
    "web_search_options": {"search_context_size": "high"},
    "search_recency_filter": "month",
    "search_domain_filter": SEARCH_DOMAIN_FILTER,
    "return_related_questions": True,
    "messages": [
        {"role": "system", "content": "You are a Korean stock market analyst."},
        {"role": "user", "content": SIMPLE_PROMPT},
    ],
}


def build_variant(name: str) -> dict:
    """특정 파라미터만 추가하여 어떤 필드가 문제인지 이분 탐색."""
    base = dict(MINIMAL_PAYLOAD)
    if name == "minimal":
        return base
    if name == "v11":
        return V11_PAYLOAD
    if name == "ctx-only":
        base["web_search_options"] = {"search_context_size": "high"}
        return base
    if name == "recency-only":
        base["search_recency_filter"] = "month"
        return base
    if name == "domain-only":
        base["search_domain_filter"] = SEARCH_DOMAIN_FILTER
        return base
    if name == "related-only":
        base["return_related_questions"] = True
        return base
    if name == "max-tokens-only":
        base["max_tokens"] = 8000
        return base
    raise ValueError(f"unknown variant: {name}")


def test_stream(variant: str, timeout: float = 60.0) -> None:
    """스트리밍 테스트: 첫 청크 도달 시간 + 에러 감지."""
    payload = build_variant(variant)
    print(f"\n{'='*60}")
    print(f"VARIANT: {variant}")
    print(f"Payload keys: {list(payload.keys())}")
    print(f"{'='*60}")

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }

    start = time.time()
    first_chunk_at = None
    chunk_count = 0
    total_chars = 0
    error_msg = None

    try:
        with httpx.Client(timeout=timeout) as client:
            with client.stream("POST", URL, headers=headers, json=payload) as response:
                elapsed = time.time() - start
                print(f"HTTP status: {response.status_code} ({elapsed:.2f}s)")
                if response.status_code != 200:
                    body = response.read().decode(errors="replace")
                    print(f"ERROR BODY: {body[:500]}")
                    return

                for line in response.iter_lines():
                    if not line:
                        continue
                    if not line.startswith("data: "):
                        continue
                    raw = line[6:].strip()
                    if raw == "[DONE]":
                        break
                    try:
                        data = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    choices = data.get("choices", [])
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        if first_chunk_at is None:
                            first_chunk_at = time.time() - start
                            print(f"First chunk at: {first_chunk_at:.2f}s")
                        chunk_count += 1
                        total_chars += len(content)
                        # 처음 200자까지만 출력
                        if total_chars <= 200:
                            print(content, end="", flush=True)
    except httpx.TimeoutException as e:
        error_msg = f"TIMEOUT after {timeout}s"
    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}"

    total = time.time() - start
    print(f"\n--- SUMMARY ---")
    print(f"  chunks: {chunk_count}, chars: {total_chars}")
    print(f"  first chunk: {first_chunk_at}")
    print(f"  total time: {total:.2f}s")
    print(f"  error: {error_msg}")


if __name__ == "__main__":
    variant = sys.argv[1].lstrip("-") if len(sys.argv) > 1 else "v11"
    timeout = float(sys.argv[2]) if len(sys.argv) > 2 else 60.0
    test_stream(variant, timeout=timeout)
