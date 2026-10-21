"""M3 Step 0: 운영 argv(build_invocation/build_env)와 같은 인자로 쓰기 허용·거부 관측.

claude -p 세션에 도구 호출 5건을 시도시키고 tool_use 입력, tool_result(is_error+텍스트), stderr를 원문 그대로 저장한다.
인자: 시도 번호(1 또는 2). 프로브 파일은 관측 뒤 별도 명령으로 지운다.
"""
import json
import os
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "..", "..")))
from backend.services.goose_runner import build_env, build_invocation  # noqa: E402

CLAUDE = os.path.expanduser("~/.local/bin/claude")
attempt = sys.argv[1]

PROMPT = (
    "쓰기 권한 점검입니다. 아래 도구 호출을 순서대로 정확히 한 번씩 시도하고, 각 호출의 결과(성공 또는 오류 문구 전문)를 "
    "번호와 함께 그대로 보고하세요. 거부되면 다른 방법으로 우회하지 말고 거부됐다고만 보고하세요.\n"
    "(1) Write 도구로 ./runs/t18-m3-probe/ok.txt 를 내용 'hello'로 만든다.\n"
    "(2) Edit 도구로 ./runs/t18-m3-probe/ok.txt 의 'hello'를 'world'로 바꾼다.\n"
    "(3) Write 도구로 ./t18-m3-outside.txt 를 내용 'x'로 만든다.\n"
    "(4) Write 도구로 ./.claude/t18-m3-deny.txt 를 내용 'x'로 만든다.\n"
    "(5) Edit 도구로 존재하지 않는 ./.claude/t18-m3-nonexistent.txt 의 'a'를 'b'로 바꾸려 시도한다."
)

inv = build_invocation(PROMPT, claude_bin=CLAUDE)
with open(os.path.join(HERE, f"step0-attempt{attempt}-argv.json"), "w") as f:
    json.dump({"argv": inv.argv[:2] + ["<PROMPT>"] + inv.argv[3:], "cwd": str(inv.cwd)}, f, ensure_ascii=False, indent=1)
t0 = time.monotonic()
proc = subprocess.Popen(inv.argv, cwd=inv.cwd, env=build_env(os.environ), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        stdin=subprocess.DEVNULL, start_new_session=True, text=True, bufsize=1)
lines, errs = [], []
threading.Thread(target=lambda: errs.extend(proc.stderr.readlines()), daemon=True).start()
rt = threading.Thread(target=lambda: [lines.append(l.rstrip("\n")) for l in proc.stdout], daemon=True)
rt.start()
try:
    proc.wait(timeout=300)
except subprocess.TimeoutExpired:
    os.killpg(proc.pid, 15)
    proc.wait(15)
rt.join(5)
open(os.path.join(HERE, f"step0-attempt{attempt}-stream.jsonl"), "w").write("\n".join(lines))
open(os.path.join(HERE, f"step0-attempt{attempt}-stderr.txt"), "w").write("".join(errs))

uses, res, final, order = {}, {}, None, []
for raw in lines:
    try:
        o = json.loads(raw)
    except ValueError:
        continue
    if o.get("type") == "assistant":
        for b in o.get("message", {}).get("content") or []:
            if isinstance(b, dict) and b.get("type") == "tool_use":
                uses[b["id"]] = (b["name"], b.get("input"))
                order.append(b["id"])
    elif o.get("type") == "user":
        c = o.get("message", {}).get("content")
        for b in c if isinstance(c, list) else []:
            if isinstance(b, dict) and b.get("type") == "tool_result":
                res[b["tool_use_id"]] = (b.get("is_error", "ABSENT"), b.get("content"))
    elif o.get("type") == "system" and o.get("subtype") == "permission_denied":
        print("SYSTEM permission_denied:", json.dumps(o, ensure_ascii=False))
    elif o.get("type") == "result":
        final = o
print("rc", proc.returncode, "wall_s", round(time.monotonic() - t0, 1), "tool_uses", len(order))
for i in order:
    n, inp = uses[i]
    ie, content = res.get(i, ("NO_RESULT", None))
    print("TOOL", n, json.dumps(inp, ensure_ascii=False), "| is_error:", ie, "| result:", json.dumps(content, ensure_ascii=False))
print("STDERR:", "".join(errs))
print("REPLY:", ((final or {}).get("result") or ""))
