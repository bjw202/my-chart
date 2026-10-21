"""D7 probe: with the naver channel satisfied, does the real render_report.py --final produce final/ with
delivery_allowed true? Scratch dirs under this evidence folder only."""
import json, subprocess, shutil, hashlib
from datetime import datetime, timezone
from pathlib import Path

H = Path("/Users/byunjungwon/.goose-harness/.claude/skills/goose/workflows")
RUN = Path("/Users/byunjungwon/.goose-harness/runs/a5becbb9b1a14483a1055c118d1b0be8")
W = Path("/Users/byunjungwon/Dev/my-project-01/my_chart/.claude/worktrees/t18/.moai/state/verify/t18-plan2/final_path")
shutil.rmtree(W, ignore_errors=True)
(W / "in").mkdir(parents=True)
data = json.loads((RUN / "draft" / "report-input.json").read_bytes())
w = data["research_window"]
w["searches"] = [s for s in w["searches"] if s.get("result") != "blocked"]
w["searches"].append({"channel": "naver", "searched_at": w["cutoff"], "query": "synthetic probe query",
                      "note": "synthetic probe note", "result": "no_results"})
(W / "in" / "input.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
raw = (W / "in" / "input.json").read_bytes()
r = subprocess.run(["/usr/bin/python3", "-I", str(H / "stock-report/scripts/render_report.py"), "--input", str(W / "in/input.json"), "--output-dir", str(W / "draft")], capture_output=True, text=True)
print("draft rc", r.returncode, r.stderr[:200])
preview = (W / "draft" / "report.html").read_bytes()
rev = {"input_sha256": hashlib.sha256(raw).hexdigest(), "preview_sha256": hashlib.sha256(preview).hexdigest(),
       "reviewed_at": datetime.now(timezone.utc).isoformat(), "mode": "separate_review_pass",
       "checks": {n: {"status": "pass", "evidence": "synthetic probe"} for n in ("source_accuracy", "calculations", "coverage", "opinion", "visual")},
       "issues": []}
(W / "in" / "audit-review.json").write_text(json.dumps(rev), encoding="utf-8")
r = subprocess.run(["/usr/bin/python3", "-I", str(H / "stock-report/scripts/render_report.py"), "--final", "--input", str(W / "in/input.json"), "--preview", str(W / "draft/report.html"), "--audit-review", str(W / "in/audit-review.json"), "--output-dir", str(W / "final")], capture_output=True, text=True)
print("final rc", r.returncode, r.stderr[:300])
v = json.loads((W / "final" / "render-validation.json").read_text())
print("delivery_allowed", v["delivery_allowed"], v["delivery_status"])
