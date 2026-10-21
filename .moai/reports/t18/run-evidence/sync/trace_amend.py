import re
from pathlib import Path

D = Path("/Users/byunjungwon/Dev/my-project-01/my_chart/.claude/worktrees/t18/.moai/specs/SPEC-AI-REPORT-006")
files = {n: (D / f"{n}.md").read_text(encoding="utf-8") for n in ("spec", "plan", "acceptance", "design", "research", "progress")}
spec, acc, des = files["spec"], files["acceptance"], files["design"]

reqs = re.findall(r"\*\*REQ-AIR6-(\d{3})\*\*", spec)
print("REQ count", len(reqs), "sequential:", [int(x) for x in reqs] == list(range(1, len(reqs) + 1)))
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

miss = []
for m in re.finditer(r"^### AC-AIR6-(\d{3}) .*?(?=^### AC-AIR6-|^## )", acc, flags=re.S | re.M):
    body = m.group(0)
    if "잡는 구현" not in body or "잡지 못하는 것" not in body:
        miss.append(m.group(1))
print("AC missing catches/cannot-catch:", miss)

print("version 0.3.4 present:", {n: ("0.3.4" in t) for n, t in files.items()})
print("stale 0.3.3 header strings:", {n: bool(re.search(r"버전 0\.3\.3|version: \"0\.3\.3\"|상태: draft · 버전 0\.3\.3", t)) for n, t in files.items()})
print("NEEDS CLARIFICATION markers:", {n: len(re.findall("NEEDS CLARIFICATION", t)) for n, t in files.items()})
print("OutOfScope H3 count in spec:", len(re.findall(r"^### Out of Scope", spec, flags=re.M)))
print("rule 10 sub-label mentions 10-11:", {n: t.count("10-11") for n, t in files.items()})
print("research Gaps:", sorted(set(re.findall(r"^\| (G\d+) \|", files["research"], flags=re.M)), key=lambda s: int(s[1:])))
print("research probes:", sorted(set(re.findall(r"^\| (P\d+) \|", files["research"], flags=re.M)), key=lambda s: int(s[1:])))
