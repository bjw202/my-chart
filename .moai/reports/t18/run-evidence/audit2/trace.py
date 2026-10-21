import re, sys
d = sys.argv[1]
spec = open(d + 'spec.md').read()
ac = open(d + 'acceptance.md').read()
reqs = sorted(set(re.findall(r'^\*\*(REQ-AIR6-\d{3})\*\*', spec, re.M)))
print('REQ count', len(reqs), 'sequential no gaps:', reqs == ['REQ-AIR6-%03d' % i for i in range(1, 21)])
hdr = {}
for m in re.finditer(r'^### (AC-AIR6-\d{3})([^\n]*)', ac, re.M):
    s = set(re.findall(r'REQ-AIR6-\d{3}', m[2]))
    for x in re.findall(r'REQ-AIR6-(\d{3})·(\d{3})', m[2]):
        s |= {'REQ-AIR6-' + x[0], 'REQ-AIR6-' + x[1]}
    hdr[m[1]] = s
print('AC count', len(hdr), 'sequential:', sorted(hdr) == ['AC-AIR6-%03d' % i for i in range(1, 23)])
cov = {r: [a for a, s in hdr.items() if r in s] for r in reqs}
for r, a in cov.items():
    print(r, '<-', a)
print('uncovered REQ:', [r for r, a in cov.items() if not a])
print('AC with missing/invalid REQ:', [a for a, s in hdr.items() if not s or not s <= set(reqs)])
parts = re.split(r'(?m)^### (AC-AIR6-\d{3})', ac)
for i in range(1, len(parts), 2):
    b = parts[i + 1].split('\n## ')[0]
    print(parts[i], 'catches-line', '잡는 구현' in b, 'cannot-catch-line', '잡지 못하는 것' in b)
req16 = spec.split('**REQ-AIR6-016**')[1].split('**REQ-AIR6-017**')[0]
print('REQ-016 numbered conditions:', len(re.findall(r'(?m)^\d+\. `', req16)))
design = open(d + 'design.md').read()
print('design table rows 0..17:', len(re.findall(r'(?m)^\| \d+ \| `', design)))
rc = [re.search(r'`(\w+)`', l)[1] for l in req16.splitlines() if re.match(r'\d+\. `', l)]
dc = [re.search(r'\| `(\w+)` \|', l)[1] for l in design.splitlines() if re.match(r'\| \d+ \| `', l)]
print('REQ order == design order (excluding #0):', rc == dc[1:], 'design#0 =', dc[0])
print('occurrences of each reason code in acceptance.md:')
for c in dc:
    print(' ', c, ac.count(c))
