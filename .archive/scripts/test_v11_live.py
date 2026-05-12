"""수정된 v1.1.0 payload로 실제 엔드-투-엔드 스트리밍 테스트."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
import types
from pathlib import Path

# .env 로드
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

# my_chart.registry 스텁 (실제 등록소 의존 회피)
sys.modules["my_chart.registry"] = types.SimpleNamespace(_name=lambda x: "대한광통신")

# 서비스 모듈 직접 로드
spec = importlib.util.spec_from_file_location("svc", "backend/services/ai_report_service.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

import httpx

API_KEY = os.environ["PERPLEXITY_API_KEY"]
URL = "https://api.perplexity.ai/chat/completions"

# 서비스의 실제 payload 구성 사용 (load_prompt + SYSTEM_PROMPT + domain filter)
prompt = mod.load_prompt("대한광통신")
print(f"Prompt length: {len(prompt)} chars")
print(f"Domain count: {len(mod.SEARCH_DOMAIN_FILTER)}")

payload = {
    "model": "sonar-pro",
    "stream": True,
    "temperature": 0.2,
    "max_tokens": 8000,
    "web_search_options": {"search_context_size": "high"},
    "search_recency_filter": "month",
    "search_domain_filter": mod.SEARCH_DOMAIN_FILTER,
    "return_related_questions": True,
    "messages": [
        {"role": "system", "content": mod.SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ],
}

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "Accept": "text/event-stream",
}

print("\n--- Streaming test ---")
start = time.time()
first_chunk_at = None
chunks = 0
total = 0
sample = []

with httpx.Client(timeout=180.0) as c:
    with c.stream("POST", URL, headers=headers, json=payload) as r:
        print(f"HTTP {r.status_code} ({time.time()-start:.2f}s)")
        if r.status_code >= 400:
            print("ERROR:", r.read().decode(errors="replace")[:400])
            sys.exit(1)

        for line in r.iter_lines():
            if not line.startswith("data: "):
                continue
            raw = line[6:].strip()
            if raw == "[DONE]":
                break
            try:
                d = json.loads(raw)
            except json.JSONDecodeError:
                continue
            content = d.get("choices", [{}])[0].get("delta", {}).get("content", "")
            if content:
                if first_chunk_at is None:
                    first_chunk_at = time.time() - start
                    print(f"First chunk at: {first_chunk_at:.2f}s")
                chunks += 1
                total += len(content)
                sample.append(content)

elapsed = time.time() - start
full = "".join(sample)

print(f"\n--- SUMMARY ---")
print(f"  chunks: {chunks}")
print(f"  total chars: {total}")
print(f"  first chunk: {first_chunk_at:.2f}s")
print(f"  total time: {elapsed:.2f}s")

# 품질 체크
import re
citations = re.findall(r"\[(\d+)\]", full)
unique_cites = set(citations)
print(f"\n--- QUALITY CHECK ---")
print(f"  citations total: {len(citations)}")
print(f"  unique citations: {len(unique_cites)} (NFR-005 target: >=15)")
print(f"  headers (##): {full.count('##')}")
print(f"  tables (|...|): {full.count('|---')}")

# 저품질 도메인 체크
bad_domains = ["youtube.com", "tistory.com", "blog.naver.com", "instagram.com"]
bad_hits = {d: full.count(d) for d in bad_domains if d in full}
print(f"  blocked domain hits (should be 0): {bad_hits}")

# 샘플 출력
print(f"\n--- OUTPUT SAMPLE (first 500 chars) ---")
print(full[:500])
print("\n--- OUTPUT SAMPLE (last 300 chars) ---")
print(full[-300:])
