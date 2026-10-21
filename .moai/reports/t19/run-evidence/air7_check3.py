# AC-AIR7-012 검사 3 — naver 기록과 서버 색인 대조
# 3F(지어냄 검사)는 모든 회차, 3S(성공 검사)는 색인 outcome이 complete·partial인 회차에만 적용한다
import json, os, sys
MARK = "서버 사전 수집본으로 열람"
SUMMARY = "API 요약본(약 150자), 원문 미확인"  # 3S에서만 요구(spec D3)
idx = json.load(open(sys.argv[1], encoding="utf-8")) if os.path.exists(sys.argv[1]) else {"outcome": "missing", "articles": []}
d = json.load(open(sys.argv[2], encoding="utf-8"))
outcome = str(idx.get("outcome"))
arts = [a for a in (idx.get("articles") or []) if isinstance(a, dict)]
ok = {a.get("article_url"): a for a in arts if a.get("status") == "ok"}
indexed = {a.get("article_url") for a in arts}
src = {str(s.get("id")): s for s in d.get("sources", []) if isinstance(s, dict)}
nav = [s for s in d.get("research_window", {}).get("searches", []) if isinstance(s, dict) and s.get("channel") == "naver"]
reads = [s for s in nav if s.get("result") == "read"]
success = outcome in ("complete", "partial")
v = []

def source_findings(sid, strict):
    x = src.get(str(sid))
    if x is None:
        return [str(sid) + ": source id not in sources"] if strict else []
    a = ok.get(x.get("url"))
    if a is None:
        return [str(sid) + ": url is not an ok index article_url"] if strict or x.get("url") in indexed else []
    if str(a.get("text_file") or "\0") not in str(x.get("read_scope", "")) or MARK not in str(x.get("limitations", "")):
        return [str(sid) + ": read_scope/limitations mismatch"]
    if strict and SUMMARY not in str(x.get("limitations", "")):
        return [str(sid) + ": limitations lacks summary phrase"]
    return []

for s in nav:  # 3F-F1
    if s.get("result") == "no_results" and outcome != "no_results":
        v.append("naver no_results while index outcome=" + outcome)
if success:  # 3S-S1, S4
    if not reads:
        v.append("no naver read entry")
    if len(nav) > 1:
        v.append("naver entries=%d (the read entry must be the only naver entry)" % len(nav))
for s in reads:  # 3F-F2 (모든 회차) / 3S-S2, S3 (성공 회차)
    ids = s.get("source_ids")
    if not isinstance(ids, list) or not ids:
        if success:
            v.append("naver read entry has no source_ids")
        continue
    for i in ids:
        v += source_findings(i, success)
print("violations", len(v))
print("mode", "3F+3S" if success else "3F only (outcome=" + outcome + ")")
for line in v:
    print(" ", line)
