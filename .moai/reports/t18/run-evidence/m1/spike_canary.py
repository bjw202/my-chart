"""M1 GO/NO-GO 스파이크 (AC-AIR6-019 / REQ-AIR6-020). M1 전용 스크립트, 병합하지 않는다.

사용: spike_canary.py <attempt-no> [--model-timeout SEC]
- 캐너리 페이지를 서버가 만들어 두 뷰포트(각 타일 3개)로 찍는다(차단+스크립트 비활성+clip 타일).
- 타일을 ~/.goose-harness/runs/t18-m1-canary-<ts>/ 에 두고 claude -p(하네스 인자·설정)로 읽게 한다.
- 스트림을 기록해 (a) 토큰 인용 (b) Read 짝 (c) y>0 타일 해시·높이를 판정한다. 끝나면 캐너리 폴더를 지운다.
"""
import asyncio
import hashlib
import json
import os
import random
import shutil
import string
import subprocess
import sys
import threading
import time
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "..", "..")))  # 워크트리 루트(기존 goose_runner 재사용)
from cdp import Session, TILE_H, VIEWPORTS, png_wh, sha, tile_ranges  # noqa: E402
from backend.services.goose_runner import build_env, build_invocation  # noqa: E402

HARNESS = os.path.expanduser("~/.goose-harness")
ALPHABET = "ACDEFGHJKLMNPRTUVWXYZ2345679"  # 대소문자·0/O·1/I 혼동 글자 제외(기록: 가독성 임계값 아닌 글꼴 혼동 방지)
BODY_PX = 17  # probe_geometry.out: 라이브 초안 body 계산된 font-size 17px
SMALLER_PX = (12, 9)
PAGE_H = 4200  # 3타일(1568+1568+1064)


def token(rng):
    return "".join(rng.choice(ALPHABET) for _ in range(6))


def build_page(w, toks):
    """토큰 3개를 y>0 타일(타일 2: 1568~3136) 안에 둔다. y=0 타일에는 토큰이 없는 머리말만."""
    ff = '"Pretendard Variable", Pretendard, -apple-system, "system-ui", "Apple SD Gothic Neo", sans-serif'
    rows = [(2000, BODY_PX, toks["body"]), (2300, SMALLER_PX[0], toks["s1"]), (2600, SMALLER_PX[1], toks["s2"])]
    parts = [f"<html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
             f"<style>html,body{{margin:0;padding:0;background:#f4f3ee;color:#1a1a1a;font-family:{ff}}}"
             f"#p{{position:relative;height:{PAGE_H}px;width:100%}}.r{{position:absolute;left:24px;right:24px;white-space:nowrap}}"
             f"</style></head><body><div id=p>"
             f"<div class=r style='top:40px;font-size:24px'>캐너리 페이지 상단 타일</div>"
             f"<div class=r style='top:100px;font-size:{BODY_PX}px'>이 타일에는 확인 코드가 없습니다.</div>"]
    for top, px, tok in rows:
        parts.append(f"<div class=r style='top:{top}px;font-size:{px}px'>확인 코드 {tok}</div>")
    parts.append(f"<div class=r style='top:3500px;font-size:{BODY_PX}px'>하단 타일의 끝</div></div></body></html>")
    return "".join(parts)


async def capture(canary_dir, toks, evid):
    tiles = {}
    async with Session() as s:
        meta = {"block": s.block_result, "script_off": s.script_result, "browser_build": s.build}
        for name, w, h, mob in VIEWPORTS:
            html = os.path.join(evid, f"canary-{name}.html")
            open(html, "w").write(build_page(w, toks[name]))
            v = await s.open("file://" + html, w, h, mob, settle=1.0)
            meta[name] = v
            assert v["sh"] >= 2 * TILE_H, (name, v)
            rows = []
            for i, (y, th) in enumerate(tile_ranges(v["sh"]), 1):
                b = await s.tile(w, y, th)
                fn = f"{name}-{i:02d}.png"
                open(os.path.join(canary_dir, fn), "wb").write(b)
                pw, ph = png_wh(b)
                rows.append({"file": fn, "y": y, "req_h": th, "png_w": pw, "png_h": ph, "sha256": sha(b), "bytes": len(b)})
            tiles[name] = rows
    return tiles, meta


def parse_stream(lines):
    """assistant tool_use(Read) ↔ user tool_result 짝."""
    uses, results, final = {}, {}, None
    for t, raw in lines:
        try:
            o = json.loads(raw)
        except Exception:
            continue
        ty = o.get("type")
        if ty == "assistant":
            for b in (o.get("message", {}).get("content") or []):
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    uses[b["id"]] = {"name": b["name"], "input": b.get("input"), "t": t}
        elif ty == "user":
            c = o.get("message", {}).get("content")
            for b in (c if isinstance(c, list) else []):
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    cont = b.get("content")
                    kinds = [x.get("type") for x in cont] if isinstance(cont, list) else type(cont).__name__
                    results[b["tool_use_id"]] = {"is_error": b.get("is_error", "ABSENT"), "content_kinds": kinds, "t": t}
        elif ty == "result":
            final = o
    return uses, results, final


def run_claude(prompt, timeout, evid, tag):
    inv = build_invocation(prompt, claude_bin=os.path.expanduser("~/.local/bin/claude"))
    env = build_env(os.environ)
    open(os.path.join(evid, f"{tag}-argv.json"), "w").write(json.dumps(inv.argv, ensure_ascii=False, indent=1))
    t0 = time.monotonic()
    proc = subprocess.Popen(inv.argv, cwd=inv.cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            start_new_session=True, text=True, bufsize=1)
    lines, errs = [], []
    th = threading.Thread(target=lambda: errs.extend(proc.stderr.readlines()), daemon=True)
    th.start()

    def reader():
        for ln in proc.stdout:
            lines.append((round(time.monotonic() - t0, 2), ln.rstrip("\n")))

    rt = threading.Thread(target=reader, daemon=True)
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
    th.join(2)
    elapsed = round(time.monotonic() - t0, 2)
    with open(os.path.join(evid, f"{tag}-stream.jsonl"), "w") as f:
        f.write("\n".join(f"{t}\t{raw}" for t, raw in lines))
    open(os.path.join(evid, f"{tag}-stderr.txt"), "w").write("".join(errs))
    return lines, proc.returncode, timed_out, elapsed, errs, inv


def main():
    attempt = sys.argv[1]
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    cname = f"t18-m1-canary-{ts}"
    cdir = os.path.join(HARNESS, "runs", cname)
    evid = os.path.join(HERE, f"attempt{attempt}")
    os.makedirs(evid, exist_ok=True)
    os.makedirs(cdir)
    rng = random.SystemRandom()
    toks = {n: {"body": token(rng), "s1": token(rng), "s2": token(rng)} for n, *_ in VIEWPORTS}
    json.dump({"canary_dir": cname, "tokens": toks, "alphabet": ALPHABET, "sizes_px": {"body": BODY_PX, "s1": SMALLER_PX[0], "s2": SMALLER_PX[1]}},
              open(os.path.join(evid, "tokens.json"), "w"), indent=1)
    try:
        tiles, meta = asyncio.run(capture(cdir, toks, evid))
        files = [r["file"] for n, *_ in VIEWPORTS for r in tiles[n]]
        prompt = ("감수 세션 점검입니다. 아래 이미지 파일 각각을 Read 도구로 열고, 그림 안에 적힌 영숫자 6자 토큰을 보이는 그대로 옮겨 적으세요. "
                  "한 파일에 토큰이 여러 개이면 위에서 아래 순서로 적고, 없으면 빈 목록으로 적으세요. 읽을 수 없으면 추측하지 말고 읽을 수 없다고 적으세요.\n"
                  "파일:\n" + "\n".join(f"- runs/{cname}/{f}" for f in files) + "\n"
                  "마지막에 JSON 객체 하나만 출력하세요: {\"<파일 이름>\": [\"<토큰>\", ...], ...}")
        for n in toks:
            for k, tk in toks[n].items():
                assert tk not in prompt, "토큰이 프롬프트에 노출됨"
        open(os.path.join(evid, "prompt.txt"), "w").write(prompt)
        lines, rc, timed_out, elapsed, errs, inv = run_claude(prompt, 900, evid, f"attempt{attempt}")
        uses, results, final = parse_stream(lines)
        reply = (final or {}).get("result", "") if final else ""
        # 입력 로그(argv·프롬프트)에 토큰이 없음
        argv_blob = json.dumps(inv.argv, ensure_ascii=False)
        exposed = [tk for n in toks for tk in toks[n].values() if tk in argv_blob]
        # (a) 토큰 인용
        ans = None
        try:
            s, e = reply.index("{"), reply.rindex("}") + 1
            ans = json.loads(reply[s:e])
        except Exception:
            pass
        quoted = {}
        for n in toks:
            for k, tk in toks[n].items():
                quoted[f"{n}.{k}"] = {"token": tk, "px": {"body": BODY_PX, "s1": SMALLER_PX[0], "s2": SMALLER_PX[1]}[k],
                                      "in_reply_exact": tk in reply,
                                      "expected_tile": f"{n}-02.png"}
        # (b) Read 짝
        pairs = []
        for f in files:
            m = [(i, u) for i, u in uses.items() if u["name"] == "Read" and str((u["input"] or {}).get("file_path", "")).endswith(f)]
            pr = [{"id": i, "file_path": u["input"].get("file_path"), "t_use": u["t"], "result": results.get(i)} for i, u in m]
            ok = any(p["result"] is not None and p["result"]["is_error"] in (False, "ABSENT") for p in pr)
            pairs.append({"tile": f, "pairs": pr, "ok": ok})
        # (c) clip 해시·높이
        c_ok = True
        c_rows = []
        for n, w, *_ in VIEWPORTS:
            rows = tiles[n]
            y0 = rows[0]
            for r in rows[1:]:
                good = r["sha256"] != y0["sha256"] and r["png_h"] == r["req_h"] and r["png_w"] == w
                c_ok &= good
                c_rows.append((n, r["file"], r["y"], r["req_h"], r["png_h"], r["sha256"][:12], "!= y0:" + y0["sha256"][:12], good))
        a_ok = all(quoted[f"{n}.body"]["in_reply_exact"] for n in toks)
        b_ok = all(p["ok"] for p in pairs)
        thr = sorted((q["px"] for q in quoted.values() if q["in_reply_exact"]))
        rec = {"attempt": attempt, "canary_dir": cname, "rc": rc, "timed_out": timed_out, "elapsed_s": elapsed,
               "tokens_exposed_in_input": exposed, "a_body_tokens_quoted": a_ok, "b_all_tiles_read_pair": b_ok, "c_clip_ok": c_ok,
               "verdict": "GO" if (a_ok and b_ok and c_ok and not exposed) else "NO-GO",
               "quoted": quoted, "reply": reply, "answer_json": ans, "read_pairs": pairs, "clip_rows": c_rows,
               "min_px_quoted_correctly": thr[0] if thr else None, "capture_meta": meta, "tiles": tiles,
               "tool_use_names": sorted({u["name"] for u in uses.values()}), "stderr_tail": [l.rstrip() for l in errs[-10:]]}
        json.dump(rec, open(os.path.join(evid, "record.json"), "w"), ensure_ascii=False, indent=1, default=str)
        for n, *_ in VIEWPORTS:
            for r in tiles[n]:
                shutil.copy(os.path.join(cdir, r["file"]), os.path.join(evid, r["file"]))
        print("VERDICT", rec["verdict"], "rc", rc, "timed_out", timed_out, "elapsed", elapsed)
        print("(a) body tokens exact:", {n: (toks[n]["body"], quoted[f"{n}.body"]["in_reply_exact"]) for n in toks})
        print("small tokens:", {k: (q["token"], q["px"], q["in_reply_exact"]) for k, q in quoted.items() if not k.endswith("body")})
        print("(b) Read pairs:")
        for p in pairs:
            print("   ", p["tile"], p["ok"], [(x["file_path"], x["result"]["is_error"] if x["result"] else None, x["result"]["content_kinds"] if x["result"] else None, x["t_use"], x["result"]["t"] if x["result"] else None) for x in p["pairs"]])
        print("(c) clip rows:")
        for r in c_rows:
            print("   ", r)
        print("input log exposure of tokens:", exposed)
        print("reply:", reply[:800])
        print("min px quoted correctly:", rec["min_px_quoted_correctly"])
    finally:
        shutil.rmtree(cdir, ignore_errors=True)
        print("canary dir removed:", not os.path.exists(cdir))


main()
