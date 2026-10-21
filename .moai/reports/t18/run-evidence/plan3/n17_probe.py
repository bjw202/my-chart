"""N17 probe: literal read-guard model for AC-014 (13), with and without start values measured on deletion failure.

Case (13): both planted files remain, reviewer never launched, outcome review_failed, capture complete,
planted audit-review.json well-formed (hashes copied, mode ok, visual pass, marker present, future reviewed_at),
no tiles read.
"""
import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("guard_model_probe", os.path.join(HERE, "guard_model.py"))
gm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gm)

# fix applied: start == end == now  -> 6 and 9 met
with_fix = gm.evaluate({3, 11})
# before the fix: start values empty -> 6 and 9 unmet
without_fix = gm.evaluate({3, 6, 9, 11})
want = ["review_not_completed", "tile_not_read"]
print("(13) with start values measured :", with_fix, "OK" if with_fix == want else "MISMATCH")
print("(13) start values left empty    :", without_fix, "(reversal variant m: differs from AC list)")
