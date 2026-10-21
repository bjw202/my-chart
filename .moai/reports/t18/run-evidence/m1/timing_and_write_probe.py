"""M1 보조 관측(GO 판정 밖): (1) 라이브 초안 실제 타일 33장을 감수형 세션이 Read하는 시간(N10e, G5),
(2) 같은 인자·설정의 세션이 ./runs/<폴더>/에 Write/Edit 할 수 있는지(신뢰되지 않은 작업공간 경고 관측).
기존 goose_runner.build_invocation/build_env 재사용. 임시 폴더는 끝나면 삭제."""
import asyncio
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "..", "..")))
from cdp import Session, VIEWPORTS, png_wh, sha, tile_ranges  # noqa: E402
from backend.services.goose_runner import build_env, build_invocation  # noqa: E402

HARNESS = os.path.expanduser("~/.goose-harness")
LIVE = os.path.join(HARNESS, "runs", "a5becbb9b1a14483a1055c118d1b0be8", "draft", "report.html")
CLAUDE = os.path.expanduser("~/.local/bin/claude")


def run_claude(prompt, timeout, tag):
    inv = build_invocation(prompt, claude_bin=CLAUDE)
    t0 = time.monotonic()
    proc = subprocess.Popen(inv.argv, cwd=inv.cwd, env=build_env(os.environ), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            start_new_session=True, text=True, bufsize=1)
    lines, errs = [], []
    threading.Thread(target=lambda: errs.extend(proc.stderr.readlines()), daemon=True).start()
    rt = threading.Thread(target=lambda: [lines.append((round(time.monotonic() - t0, 2), l.rstrip("\n"))) for l in proc.stdout], daemon=True)
    rt.start()
    timed_out = False
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(proc.pid, 15)
        except Exception:
            pass
        proc.wait(15)
    rt.join(5)
    el = round(time.monotonic() - t0, 2)
    open(os.path.join(HERE, f"{tag}-stream.jsonl"), "w").write("\n".join(f"{t}\t{r}" for t, r in lines))
    return lines, proc.returncode, timed_out, el, errs


def pairs(lines):
    uses, res, final = {}, {}, None
    for t, raw in lines:
        try:
            o = json.loads(raw)
        except Exception:
            continue
        if o.get("type") == "assistant":
            for b in o.get("message", {}).get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    uses[b["id"]] = (b["name"], b.get("input"), t)
        elif o.get("type") == "user":
            c = o.get("message", {}).get("content")
            for b in c if isinstance(c, list) else []:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    cont = b.get("content")
                    txt = cont if isinstance(cont, str) else json.dumps(cont, ensure_ascii=False)[:200]
                    res[b["tool_use_id"]] = (b.get("is_error", "ABSENT"), t, txt)
        elif o.get("type") == "result":
            final = o
    return uses, res, final


async def make_tiles(d):
    n = 0
    async with Session() as s:
        for name, w, h, mob in VIEWPORTS:
            v = await s.open("file://" + LIVE, w, h, mob, settle=2.0)
            for i, (y, th) in enumerate(tile_ranges(v["sh"]), 1):
                open(os.path.join(d, f"{name}-{i:02d}.png"), "wb").write(await s.tile(w, y, th))
                n += 1
    return n


def main():
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    cname = f"t18-m1-canary-timing-{ts}"
    d = os.path.join(HARNESS, "runs", cname)
    os.makedirs(d)
    try:
        n = asyncio.run(make_tiles(d))
        files = sorted(os.listdir(d))
        print("tiles generated", n, "(desktop %d, mobile %d)" % (sum(f.startswith("desktop") for f in files), sum(f.startswith("mobile") for f in files)))
        prompt = ("감수 세션 시간 점검입니다. 아래 이미지 파일을 모두 Read 도구로 하나씩 열고, 파일마다 화면에 보이는 가장 큰 제목 한 줄을 적으세요. "
                  "열지 못한 파일은 열지 못했다고 적으세요.\n파일:\n" + "\n".join(f"- runs/{cname}/{f}" for f in files))
        lines, rc, to, el, errs = run_claude(prompt, 900, "timing")
        uses, res, final = pairs(lines)
        reads = [(u[1].get("file_path", "")[-14:], u[2], res[i][1], res[i][0]) for i, u in uses.items() if u[0] == "Read" and i in res]
        print("== TIMING (N10e/G5): rc", rc, "timed_out", to, "wall_s", el, "Read pairs", len(reads), "of", len(files))
        durs = [round(r[2] - r[1], 2) for r in reads]
        print("per-Read tool_use->tool_result s: min %.2f max %.2f mean %.2f" % (min(durs), max(durs), sum(durs) / len(durs)))
        print("first Read use t=%.2f, last Read result t=%.2f, span %.2f" % (min(r[1] for r in reads), max(r[2] for r in reads), max(r[2] for r in reads) - min(r[1] for r in reads)))
        print("is_error values:", sorted({str(r[3]) for r in reads}))
        print("result usage:", {k: (final or {}).get(k) for k in ("duration_ms", "num_turns", "total_cost_usd", "usage")} if final else None)
        print("stderr:", "".join(errs)[:300])
        print("final reply head:", ((final or {}).get("result") or "")[:300])
    finally:
        shutil.rmtree(d, ignore_errors=True)
        print("timing dir removed:", not os.path.exists(d))

    # (2) Write/Edit 허용 관측
    wname = f"t18-m1-canary-writeprobe-{ts}"
    wd = os.path.join(HARNESS, "runs", wname)
    os.makedirs(wd)
    try:
        prompt = (f"쓰기 권한 점검입니다. Write 도구로 runs/{wname}/probe.txt 를 내용 'hello'로 만들고, Edit 도구로 'hello'를 'world'로 바꾼 뒤, "
                  f"Read로 다시 읽어 내용을 답하세요. 실패하면 실패한 도구와 오류 문구를 그대로 적으세요.")
        lines, rc, to, el, errs = run_claude(prompt, 300, "writeprobe")
        uses, res, final = pairs(lines)
        print("== WRITE/EDIT PROBE: rc", rc, "wall_s", el)
        for i, u in uses.items():
            print("  tool", u[0], (u[1] or {}).get("file_path"), "->", res.get(i, (None, None, None))[0], str(res.get(i, (0, 0, ""))[2])[:160])
        print("  file exists after:", os.path.exists(os.path.join(wd, "probe.txt")), open(os.path.join(wd, "probe.txt")).read() if os.path.exists(os.path.join(wd, "probe.txt")) else None)
        print("  stderr:", "".join(errs)[:300])
        print("  reply:", ((final or {}).get("result") or "")[:300])
    finally:
        shutil.rmtree(wd, ignore_errors=True)
        print("write-probe dir removed:", not os.path.exists(wd))


main()
