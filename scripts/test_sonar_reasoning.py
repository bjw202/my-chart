"""sonar-reasoning-pro 모델 실측 테스트.

현재 v1.1.2 payload에서 모델만 sonar-reasoning-pro로 교체하여 품질/시간/포맷 검증.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
import time
import types
from pathlib import Path

env_path = Path("/Users/byunjungwon/Dev/my-project-01/my_chart/.env")
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

sys.modules["my_chart.registry"] = types.SimpleNamespace(_name=lambda x: "대한광통신")
spec = importlib.util.spec_from_file_location(
    "svc", "/Users/byunjungwon/Dev/my-project-01/my_chart/backend/services/ai_report_service.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

import httpx

API_KEY = os.environ["PERPLEXITY_API_KEY"]
URL = "https://api.perplexity.ai/chat/completions"
prompt = mod.load_prompt("대한광통신")


def test(model: str, extra: dict | None = None):
    payload = {
        "model": model,
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
    if extra:
        payload.update(extra)

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    print(f"\n{'='*60}")
    print(f"MODEL: {model} | extra: {extra}")
    print(f"{'='*60}")
    start = time.time()
    first_at = None
    chunks = []
    try:
        with httpx.Client(timeout=300.0) as c:
            with c.stream("POST", URL, headers=headers, json=payload) as r:
                elapsed = time.time() - start
                print(f"HTTP {r.status_code} ({elapsed:.2f}s)")
                if r.status_code >= 400:
                    print("ERROR:", r.read().decode(errors="replace")[:500])
                    return None

                for line in r.iter_lines():
                    if line.startswith("data: "):
                        raw = line[6:].strip()
                        if raw == "[DONE]":
                            break
                        try:
                            d = json.loads(raw)
                            content = d.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if content:
                                if first_at is None:
                                    first_at = time.time() - start
                                    print(f"First chunk at: {first_at:.2f}s")
                                chunks.append(content)
                        except json.JSONDecodeError:
                            pass
    except Exception as e:
        print(f"EXCEPTION: {type(e).__name__}: {e}")
        return None

    full = "".join(chunks)
    total_time = time.time() - start

    # Thinking 블록 검출
    think_blocks = re.findall(r"<think>.*?</think>", full, re.DOTALL)

    # 품질 지표
    citations = re.findall(r"\[(\d+)\]", full)
    unique_cites = len(set(citations))
    tables = full.count("|---")
    headers = full.count("##")

    print(f"\nSUMMARY:")
    print(f"  total time: {total_time:.1f}s")
    print(f"  chars: {len(full)}")
    print(f"  <think> blocks: {len(think_blocks)}")
    if think_blocks:
        print(f"  <think> total chars: {sum(len(t) for t in think_blocks)}")
    print(f"  unique citations: {unique_cites}")
    print(f"  tables: {tables}")
    print(f"  ##: {headers}")

    # 저장
    out = Path(f"/tmp/sonar_test_{model.replace('-', '_')}.md")
    out.write_text(full)
    print(f"  saved: {out}")

    return full


if __name__ == "__main__":
    # 1. sonar-reasoning-pro (with reasoning_effort if supported)
    test("sonar-reasoning-pro")
