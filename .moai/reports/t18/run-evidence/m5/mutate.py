"""AC-AIR6-013/021 되돌림 변형을 실제 harness-instructions.md에 적용하고 pytest를 돌린 뒤 원상 복구한다."""
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[4]
TARGET = ROOT / "backend/goose_harness_src/harness-instructions.md"
PY = ROOT.parent.parent.parent / ".venv/bin/python"
ENV = dict(os.environ, AI_REPORT_GOOSE_HARNESS_DIR=str(ROOT / ".moai/state/verify/t18-m5/home/.goose-harness"))
ORIG = TARGET.read_text(encoding="utf-8")

MARKER = "리터럴 표지 `[렌더 차이]`로 시작하고, 이어서 외부 네트워크와 웹 글꼴을 막고 그렸으므로 실제 화면과 조금 다르다는 사실을 적는다. 이 사실의 문장은 `context.json`의 `screens.render_note`에 있다. 표지가 없으면 최종본이 되지 않는다."
MUTATIONS = {
    "a_remove_marker_sentence": lambda t: t.replace(MARKER, "visual 증거를 적는다."),
    "b_drop_never_write_review_record": lambda t: t.replace("`audit-review.json`을 쓰지 않고 ", ""),
    "c_number_collision": lambda t: t.replace("\n10. ", "\n9. ", 1),
    "d_stale_nine_label": lambda t: t.replace("- 10-2.", "- 9-2.", 1),
    "e_stale_in_text_reference": lambda t: t.replace("10-3의", "9-3의"),
    "f_drop_all_tiles_read_condition": lambda t: t.replace("모든 타일 파일을 Read 도구로 하나씩 연", "타일 파일을 본"),
    "g_final_unconditional": lambda t: t.replace("감사 결정이 `pass`일 때만 최종본을 만든다", "최종본을 만든다"),
}

try:
    for name, fn in MUTATIONS.items():
        mutated = fn(ORIG)
        assert mutated != ORIG, f"mutation {name} did not change the file"
        TARGET.write_text(mutated, encoding="utf-8")
        proc = subprocess.run(
            [str(PY), "-B", "-m", "pytest", "-p", "no:cacheprovider", "backend/tests/test_goose_harness.py",
             "-k", "air6_013 or air6_021", "-q", "--no-header"],
            cwd=ROOT, env=ENV, capture_output=True, text=True,
        )
        lines = [ln for ln in proc.stdout.splitlines() if ln.startswith("FAILED") or " passed" in ln or " failed" in ln]
        print(f"=== {name} (pytest exit {proc.returncode})")
        print("\n".join(lines))
finally:
    TARGET.write_text(ORIG, encoding="utf-8")
sys.exit(0)
