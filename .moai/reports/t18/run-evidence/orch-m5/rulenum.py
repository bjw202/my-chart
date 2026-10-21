import re, sys
cur = None; tops = []; errs = []
for n, line in enumerate(open(sys.argv[1], encoding="utf-8"), 1):
    m = re.match(r"^(\d+)\. ", line)
    if m:
        cur = int(m.group(1)); tops.append(cur); body = line[m.end():]
    else:
        s = re.match(r"^\s+- (\d+)-\d+[a-z]?\. ", line)
        if s and int(s.group(1)) != cur:
            errs.append("line %d: sub-item %s-* under rule %s" % (n, s.group(1), cur))
        body = line[s.end():] if s else line
    # 본문 안 `N-M` 참조는 자기 규칙 번호만 가리켜야 한다(다시 매긴 뒤 남은 옛 참조를 잡는다)
    for r in re.finditer(r"(?<![\d.\-])(\d{1,2})-\d{1,2}[a-z]?(?![\d\-])", body):
        if cur is not None and int(r.group(1)) != cur:
            errs.append("line %d: in-text reference %s inside rule %s" % (n, r.group(0), cur))
if tops != list(range(1, len(tops) + 1)):
    errs.append("top-level numbers not 1..K unique: %s" % tops)
print("rules", tops)
print("rule numbering ok" if not errs else "\n".join(errs))
