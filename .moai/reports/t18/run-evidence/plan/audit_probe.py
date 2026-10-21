"""plan-phase 프로브(SPEC-AI-REPORT-006 research P-audit): audit_report.py가 감수 기록 필드로 어떤 결함 코드를
내고 거두는지 관측한다. 합성 감수 기록은 이 증거 폴더 안에서만 쓰며 어떤 보고서에도 전달되지 않는다(규칙 7 대상 아님 —
감사기 로직 관측용 입력이다)."""
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


def codes(review):
    result = mod.audit(data, raw, review, preview)
    return sorted(f["code"] for f in result["findings"])


def review(visual="pass", **over):
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
    base.update(over)
    return base


print("A none      ", codes(None))
print("B full pass ", codes(review("pass")))
print("C visual rev", codes(review("revise")))
print("D bad input ", codes(review(input_sha256="0" * 64)))
print("E bad prev  ", codes(review(preview_sha256="0" * 64)))
print("F bad mode  ", codes(review(mode="self")))
print("G open issue", codes(review(issues=[{"owner": "goose", "description": "x", "status": "open"}])))
