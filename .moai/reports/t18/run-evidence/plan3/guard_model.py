"""v0.3.1 read-guard model: a literal reading of spec.md REQ-AIR6-016 guard text.

Not the implementation. It only shows what the guard text yields for the AC cases.
"""
CODES = {1: "no_receipt", 2: "receipt_invalid", 3: "review_not_completed", 4: "judged_input_write_attempt",
         5: "screens_not_complete", 6: "screens_changed", 7: "tile_missing", 8: "tile_hash_mismatch",
         9: "draft_changed", 10: "preview_hash_mismatch", 11: "tile_not_read", 12: "mobile_overflow",
         13: "no_audit_review", 14: "mode_not_separate_review_pass", 15: "visual_not_pass",
         16: "reviewed_before_capture", 17: "font_note_missing"}

# skip lists exactly as written in the patched spec.md
RECEIPT_DEP = {3, 4, 6, 9, 11}
INDEX_DEP = {7, 8, 11, 12, 16}          # + index side of 10 (handled below)
REVIEW_DEP = {14, 15, 16, 17}           # + review-record side of 10
ALL_INDEX_DEP = {7, 8, 11, 12, 16}      # every condition that reads the parsed index (v0.3.1 list)


def evaluate(raw_unmet, receipt="ok", index="ok", review="ok", index_dep=INDEX_DEP):
    """raw_unmet: set of conditions whose own check fails when its inputs ARE readable."""
    out = []
    for n in range(1, 18):
        if n == 1:
            unmet = receipt == "absent"
        elif n == 2:
            unmet = receipt == "invalid"  # evaluated only when 1 holds
            if receipt == "absent":
                continue
        else:
            if receipt in ("absent", "invalid") and n in RECEIPT_DEP:
                continue
            if index != "ok" and n in index_dep:
                continue
            if review != "ok" and n in REVIEW_DEP:
                continue
            if n == 5:
                unmet = index != "ok" or 5 in raw_unmet
            elif n == 13:
                unmet = review != "ok" or 13 in raw_unmet
            elif n == 10:
                # index side skipped when index unreadable, review side skipped when review unreadable
                unmet = 10 in raw_unmet and index == "ok" and review == "ok"
            else:
                unmet = n in raw_unmet
                # an unreadable input counts as unmet if the condition is evaluated at all
                if n in ALL_INDEX_DEP and index != "ok":
                    unmet = True
                if n in REVIEW_DEP and review != "ok":
                    unmet = True
        if unmet:
            out.append(CODES[n])
    return out


def show(label, got, want):
    print(f"{label}: {got}  expected {want}  {'OK' if got == want else 'MISMATCH'}")


# AC-016 read-failure cases
show("b3  receipt broken", evaluate(set(), receipt="invalid"), ["receipt_invalid"])
show("d2  index broken (16 in skip list)", evaluate(set(), index="unreadable"), ["screens_not_complete"])
show("d2  index broken (v0.3.0 list, 16 NOT skipped)",
     evaluate(set(), index="unreadable", index_dep={7, 8, 11, 12}), ["screens_not_complete"])
show("o2  review broken", evaluate(set(), review="unreadable"), ["no_audit_review"])
show("b   receipt absent", evaluate(set(), receipt="absent"), ["no_receipt"])
# AC-014 planted-file cases (N13): writer reasons for conditions 1-17
show("(11) outcome=review_failed, record absent, tiles read", evaluate({3, 13}, review="unreadable"),
     ["review_not_completed", "no_audit_review"])
show("(12) honest record, tiles read, final removed (cond 1-17 only)", evaluate(set()), [])
show("(13) review not launched, planted record readable, no tiles read", evaluate({3, 11}),
     ["review_not_completed", "tile_not_read"])
