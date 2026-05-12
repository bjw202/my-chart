"""서비스 코드의 stream_perplexity() 직접 호출 - v1.1.3 실제 동작 검증."""
import asyncio, importlib.util, os, sys, time, types, re
from pathlib import Path

env = Path("/Users/byunjungwon/Dev/my-project-01/my_chart/.env")
for line in env.read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

sys.modules["my_chart.registry"] = types.SimpleNamespace(_name=lambda x: "대한광통신")
spec = importlib.util.spec_from_file_location(
    "svc", "/Users/byunjungwon/Dev/my-project-01/my_chart/backend/services/ai_report_service.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


async def main():
    start = time.time()
    chunks = []
    first_at = None
    async for chunk in mod.stream_perplexity("대한광통신"):
        if first_at is None:
            first_at = time.time() - start
        chunks.append(chunk)

    full = "".join(chunks)
    elapsed = time.time() - start

    print(f"Total time: {elapsed:.1f}s")
    print(f"First chunk: {first_at:.1f}s")
    print(f"Chars: {len(full)}")
    print(f"<think> in output: {'<think>' in full}")
    print(f"</think> in output: {'</think>' in full}")
    print(f"Unique citations: {len(set(re.findall(r'\\[(\\d+)\\]', full)))}")
    print(f"Tables: {full.count('|---')}")
    print(f"Headers (##): {full.count('##')}")
    print(f"\n--- FIRST 400 CHARS ---\n{full[:400]}")
    print(f"\n--- LAST 200 CHARS ---\n{full[-200:]}")


asyncio.run(main())
