import re
import sys
from pathlib import Path

D = Path("/Users/byunjungwon/Dev/my-project-01/my_chart/.claude/worktrees/t18/.moai/specs/SPEC-AI-REPORT-006")
spec = (D / "spec.md").read_text(encoding="utf-8")
acc = (D / "acceptance.md").read_text(encoding="utf-8")
des = (D / "design.md").read_text(encoding="utf-8")
plan = (D / "plan.md").read_text(encoding="utf-8")
prog = (D / "progress.md").read_text(encoding="utf-8")

reqs = re.findall(r"\*\*REQ-AIR6-(\d{3})\*\*", spec)
print("REQ count", len(reqs), "sequential no gaps:", [int(x) for x in reqs] == list(range(1, len(reqs) + 1)))

heads = re.findall(r"^### AC-AIR6-(\d{3}) .*$", acc, flags=re.M)
print("AC count", len(heads), "sequential:", [int(x) for x in heads] == list(range(1, len(heads) + 1)))

cover = {r: [] for r in reqs}
bad = []
for m in re.finditer(r"^### AC-AIR6-(\d{3}) .*?\((.*?)\)\s*$", acc, flags=re.M):
    ac, paren = m.group(1), m.group(2)
    ids = []
    for part in re.findall(r"REQ-AIR6-(\d{3}(?:\s*[·,]\s*(?:REQ-AIR6-)?\d{3})*)", paren):
        ids += re.findall(r"\d{3}", part)
    if not ids:
        bad.append(ac)
    for i in ids:
        if i in cover:
            cover[i].append(ac)
        else:
            bad.append((ac, i))
print("uncovered REQ:", [r for r, a in cover.items() if not a])
print("AC with missing/invalid REQ:", bad)
for r in reqs:
    print("  REQ", r, "->", ",".join(cover[r]))

# condition lists
req16 = re.search(r"\*\*REQ-AIR6-016\*\*(.*?)\n\n## ", spec, flags=re.S)
r16 = req16.group(1) if req16 else ""
cond = re.findall(r"^(\d+)\. `([a-z_]+)`", r16, flags=re.M)
print("REQ-016 numbered conditions:", len(cond), [c[0] for c in cond][:1], "..", [c[0] for c in cond][-1:])
rows = re.findall(r"^\| (\d+) \| `([a-z_]+)` \|", des, flags=re.M)
print("design table rows:", len(rows), "first:", rows[0] if rows else None)
print("REQ order == design order (excluding #0):", [c[1] for c in cond] == [r[1] for r in rows if r[0] != "0"])

# every code appears in AC-016 block
m = re.search(r"### AC-AIR6-016.*?### AC-AIR6-017", acc, flags=re.S)
blk = m.group(0) if m else ""
codes = ["final_not_allowed"] + [c[1] for c in cond]
print("AC-016 codes missing:", [c for c in codes if c not in blk])

# every AC has catches / cannot-catch lines
miss = []
for m in re.finditer(r"^### AC-AIR6-(\d{3}) .*?(?=^### AC-AIR6-|^## )", acc, flags=re.S | re.M):
    body = m.group(0)
    if "잡는 구현" not in body or "잡지 못하는 것" not in body:
        miss.append(m.group(1))
print("AC missing catches/cannot-catch:", miss)

# version consistency
for name, txt in (("spec", spec), ("acceptance", acc), ("design", des), ("plan", plan)):
    print(name, "has 0.3.0:", "0.3.0" in txt, "| stale 0.2.0 header:", bool(re.search(r"버전 0\.2\.0|\"0\.2\.0\"", txt)))
print("progress has v0.3.0:", "v0.3.0" in prog)

# stale-claim checks
print("spec byte-for-byte present:", "byte-for-byte" in spec)
print("acceptance overclaim phrase present:", "조건 18개(`final_not_allowed` + 17개) 각각의 되돌림을 개별로 관측한다" in acc)
print("OutOfScope heading present:", "### Out of Scope" in spec)
print("NEEDS CLARIFICATION markers:", len(re.findall("NEEDS CLARIFICATION", plan)))
