import ast

b = ".moai/state/verify/t18-merge/stage/"
t2 = open(b + "t2.py", encoding="utf-8").read()
add3 = open(b + "add3.py", encoding="utf-8").read()
out = t2.rstrip("\n") + "\n\n\n" + add3.rstrip("\n") + "\n"
ast.parse(out)
open("backend/tests/test_goose_job_service.py", "w", encoding="utf-8").write(out)
print(len(out.splitlines()))
