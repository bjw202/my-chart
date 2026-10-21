"""plan-phase v0.2.0 probe (D7): can a synthetic input satisfy the audit's search-channel rule so that a
fully passing review record yields decision pass? In-memory copy only; nothing is delivered."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

RUN = Path("/Users/byunjungwon/.goose-harness/runs/a5becbb9b1a14483a1055c118d1b0be8")
AUDIT = Path("/Users/byunjungwon/.goose-harness/.claude/skills/goose/workflows/fact-check/scripts/audit_report.py")

spec = importlib.util.spec_from_file_location("audit_report", AUDIT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

raw = (RUN / "draft" / "report-input.json").read_bytes()
preview = (RUN / "draft" / "report.html").read_bytes()
data = json.loads(raw)
window = data["research_window"]
print("cutoff", window.get("cutoff"), "mode", window.get("mode"))
for s in window.get("searches", []):
    print("search", s.get("channel"), s.get("result"), s.get("searched_at"))


def review(visual="pass"):
    base = {
        "input_sha256": mod.digest(raw),
        "preview_sha256": mod.digest(preview),
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "mode": "separate_review_pass",
        "checks": {n: {"status": "pass", "evidence": "synthetic probe"} for n in
                   ("source_accuracy", "calculations", "coverage", "opinion")},
        "issues": [],
    }
    base["checks"]["visual"] = {"status": visual, "evidence": "synthetic probe"}
    return base


def run(label, d):
    result = mod.audit(d, raw, review(), preview)
    print(label, result["decision"], sorted(f["code"] for f in result["findings"]))


run("live-as-is   ", data)

patched = json.loads(raw)
w = patched["research_window"]
w["searches"] = [s for s in w.get("searches", []) if s.get("result") != "blocked"]
have = {s.get("channel") for s in w.get("searches", [])}
cutoff = mod.stamp(w["cutoff"])
for ch in ("original_news", "company_ir", "naver", "industry", "dart"):
    if ch not in have:
        w.setdefault("searches", []).append({
            "channel": ch,
            "searched_at": (cutoff.replace(microsecond=0)).isoformat(),
            "query": "synthetic probe query",
            "note": "synthetic probe note",
            "result": "no_results",
        })
run("patched-naver", patched)
