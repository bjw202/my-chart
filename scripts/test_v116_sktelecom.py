"""v1.1.6 시스템 프롬프트로 SK텔레콤 실측 테스트 (대형주 품질 개선 검증)."""
import asyncio, importlib.util, os, sys, time, types, re
from pathlib import Path

env = Path("/Users/byunjungwon/Dev/my-project-01/my_chart/.env")
for line in env.read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

sys.modules["my_chart.registry"] = types.SimpleNamespace(_name=lambda x: "SK텔레콤")

spec = importlib.util.spec_from_file_location(
    "svc", "/Users/byunjungwon/Dev/my-project-01/my_chart/backend/services/ai_report_service.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


async def main():
    start = time.time()
    chunks = []
    async for chunk in mod.stream_perplexity("SK텔레콤"):
        chunks.append(chunk)
    full = "".join(chunks)
    elapsed = time.time() - start

    unique_cites = len(set(re.findall(r'\[(\d+)\]', full)))
    print(f"time: {elapsed:.1f}s | chars: {len(full)} | tables: {full.count('|---')} | unique_cites: {unique_cites}")
    print(f"'데이터 부재' 언급: {full.count('데이터 부재') + full.count('부재')}")
    print(f"'검색 결과' 언급: {full.count('검색 결과')}")
    print(f"\n--- FIRST 600 CHARS ---\n{full[:600]}")
    print(f"\n--- LAST 400 CHARS ---\n{full[-400:]}")


asyncio.run(main())
