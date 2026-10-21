import sys
from pathlib import Path

PRIMARY = "/Users/byunjungwon/Dev/my-project-01/my_chart"
sys.path.insert(0, PRIMARY)
from backend.services import goose_harness as g  # noqa: E402

src = Path(PRIMARY) / "backend" / "goose_harness_src"
m = g.load_manifest(src)
print("entries", len(m), "| verify_installed vs primary manifest:", g.verify_installed(Path.home() / ".goose-harness", m))
