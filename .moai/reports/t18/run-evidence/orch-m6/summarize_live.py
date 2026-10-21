import json
from pathlib import Path

R = Path.home() / ".goose-harness/runs/0ffb8f9e490d40779b9b3d7c5224c1b3"


def load(rel):
    return json.loads((R / rel).read_text(encoding="utf-8"))


idx = load("screens/index.json")
print("index.outcome:", idx.get("outcome"))
for vp in idx.get("viewports", []):
    tiles = vp.get("tiles", [])
    print(" ", vp.get("name"), "ok=", vp.get("ok"), "outcome=", vp.get("outcome"), "tiles=", len(tiles))

rc = load("review/receipt.json")
print("receipt keys:", sorted(rc.keys()))
for k in ("outcome", "visual_admissible", "reasons"):
    print(" ", k, "=", rc.get(k))
sc = rc.get("screens", {})
print("  screens.tiles_expected/read:", len(sc.get("tiles_expected", [])), len(sc.get("tiles_read", [])),
      "| snapshot_start==end:", sc.get("snapshot_start") == sc.get("snapshot_end"))
pr = rc.get("process", {})
print("  process.exit_code/timed_out:", pr.get("exit_code"), pr.get("timed_out"))
print("  draft_unchanged:", rc.get("draft_unchanged"), "| judged_writes:", rc.get("judged_writes"))

ar = load("audit-review.json")
checks = ar.get("checks", {})
for name, c in checks.items():
    print("check", name, c.get("status"), "| evidence_len=", len(str(c.get("evidence", ""))))
print("visual evidence startswith marker:", str(checks.get("visual", {}).get("evidence", "")).startswith("[렌더 차이]"))

da = load("review/delivery-audit.json")
print("delivery-audit.decision:", da.get("decision"), "| keys:", sorted(da.keys())[:8])
print("final dir exists:", (R / "final").exists())
