import re, sys
p = "backend/services/goose_job_service.py"
s = open(p, encoding="utf-8").read()
pat = re.compile(r"<<<<<<< HEAD\n(.*?)=======\n(.*?)>>>>>>> main\n", re.S)
n = [0]
def rep(m):
    n[0] += 1
    a, b = m.group(1), m.group(2)
    if n[0] == 2:  # imports
        return ("from backend.services import (\n    goose_dart_prefetch,\n    goose_harness,\n    goose_naver_prefetch,\n"
                "    goose_review,\n    goose_runner,\n    goose_screenshot,\n    goose_storage,\n)\n")
    if n[0] == 7:  # methods: need blank line between
        return a.rstrip("\n") + "\n\n" + b
    return a + b
s2 = pat.sub(rep, s)
open(p, "w", encoding="utf-8").write(s2)
print(n[0])
