import ast
import collections


def names(p):
    t = ast.parse(open(p, encoding="utf-8").read())
    out = []
    for n in t.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.append(n.name)
        elif isinstance(n, ast.Assign):
            for x in n.targets:
                if isinstance(x, ast.Name):
                    out.append(x.id)
    return out


b = ".moai/state/verify/t18-merge/stage/"
n1 = set(names(b + "t1.py"))
n2 = names(b + "t2.py")
n3 = names(b + "t3.py")
new3 = [x for x in n3 if x not in n1]
new2 = [x for x in n2 if x not in n1]
print("collide:", set(new3) & set(new2))
print("dups in t3:", [k for k, v in collections.Counter(n3).items() if v > 1])
print("dups in t2:", [k for k, v in collections.Counter(n2).items() if v > 1])
