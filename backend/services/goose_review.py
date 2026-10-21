"""SPEC-AI-REPORT-006 M3 — 감수 보조: 컨텍스트·세션 전후 스냅샷·영수증·최종본 인정 판정.

설계: design.md §2(후처리 순서), §4.2·4.3(스키마), §5(판정 함수), §6(열람 기록 수집).
규칙 7 불변식: 화면 확인 "통과"는 서버가 직접 확인한 사실(영수증의 서버 기록 + 디스크 현재 상태)로만
인정한다. 감수 세션은 `Write(./runs/**)` 권한이 있어 판단 대상을 고칠 수 있으므로, 이 모듈이
세션 전 측정·종료 후 측정·쓰기 시도 기록으로 변조를 탐지하고 영수증을 서버가 직접 쓴다.

경계: 프로세스 실행은 goose_runner(`run_review`)의 일이다. 이 모듈은 goose_runner를 import하지
않는다 — M4에서 `select_report`가 이 모듈의 판정 래퍼를 부르므로 순환 import를 피한다.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1
REVIEW_DIR = "review"
CONTEXT_NAME = "context.json"
RECEIPT_NAME = "receipt.json"
AUDIT_REVIEW_NAME = "audit-review.json"
AUDIT_OUTPUT_NAME = "delivery-audit.json"
REVIEW_MODE = "separate_review_pass"
# 감수 증거에 반드시 들어가야 하는 표지(조건 17)
FONT_MARK = "[렌더 차이]"
RENDER_NOTE = (
    "외부 네트워크와 웹 글꼴을 막고 그렸으므로 렌더링이 실제 화면과 조금 다르다."
)
OUTCOMES = ("reviewed", "review_failed", "timeout", "cancelled", "integrity_failed", "disabled")
# 영수증의 고정 키 집합(조건 2가 검사). acceptance.md §B와 같다
RECEIPT_KEYS = frozenset({
    "schema_version", "outcome", "started_at", "finished_at", "process", "hashes", "draft_unchanged",
    "screens", "judged_writes", "audit_review", "visual_admissible", "reasons",
})

_KST = timezone(timedelta(hours=9))
_INVALID = object()  # 영수증 파일이 있으나 JSON 객체로 읽히지 않음


def _now() -> str:
    return datetime.now(_KST).isoformat(timespec="seconds")


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str | None:
    """정규 파일의 SHA-256. 없거나 읽을 수 없으면 None."""
    try:
        return _sha_bytes(path.read_bytes()) if path.is_file() else None
    except OSError:
        return None


def _load_json_object(path: Path) -> dict | None:
    """JSON 객체로 읽히면 dict, 아니면 None."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _dig(data: object, *keys: str) -> object:
    """중첩 dict에서 값을 꺼낸다. 중간이 dict가 아니면 None."""
    for key in keys:
        if not isinstance(data, dict):
            return None
        data = data.get(key)
    return data


# ─────────────────────────────────────────────────────────────────────────────
# 측정
# ─────────────────────────────────────────────────────────────────────────────


def measure_screens(job_dir: Path) -> dict:
    """`screens/` 스냅샷: 색인 해시 + 하위 폴더까지 재귀로 훑은 {상대 경로: SHA-256}(조건 6)."""
    screens = job_dir / "screens"
    files: dict[str, str | None] = {}
    for root, _dirs, names in os.walk(screens):
        for name in names:
            path = Path(root) / name
            files[path.relative_to(screens).as_posix()] = sha256_file(path)
    return {"index_sha256": sha256_file(screens / "index.json"), "files": files}


def _measure_draft(job_dir: Path) -> dict:
    return {
        "input": sha256_file(job_dir / "draft" / "report-input.json"),
        "preview": sha256_file(job_dir / "draft" / "report.html"),
    }


def _index_tiles(index: dict | None) -> list[str]:
    """색인에 적힌 타일 파일 이름(뷰포트 순서). 읽을 수 없으면 빈 목록."""
    tiles: list[str] = []
    for vp in _dig(index, "viewports") or []:
        for tile in _dig(vp, "tiles") or []:
            name = _dig(tile, "file")
            if isinstance(name, str):
                tiles.append(name)
    return tiles


# ─────────────────────────────────────────────────────────────────────────────
# 세션 전: 정리·스냅샷·컨텍스트
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class ReviewStart:
    """세션 시작 전에 서버가 측정한 값. ``launch``가 False면 세션을 시작하지 않는다."""

    job_id: str
    started_at: str
    launch: bool
    hashes: dict
    snapshot: dict
    tiles_expected: list[str] = field(default_factory=list)


def _delete_planted(job_dir: Path) -> bool:
    """1차 세션이 심었을 수 있는 `audit-review.json`과 `final/`을 지운다. 둘 다 사라졌을 때만 True."""
    try:
        (job_dir / AUDIT_REVIEW_NAME).unlink(missing_ok=True)
        final = job_dir / "final"
        if final.is_symlink() or final.is_file():
            final.unlink()
        elif final.exists():
            shutil.rmtree(final)
    except OSError:
        logger.warning("goose review: 사전 심기 파일 삭제 실패 (%s)", job_dir.name)
        return False
    return not ((job_dir / AUDIT_REVIEW_NAME).exists() or (job_dir / "final").exists())


def prepare_review(job_dir: Path, *, code: str, now: str | None = None) -> ReviewStart:
    """세션 전 정리 → 스냅샷 → `review/context.json` 쓰기(design §2). 캡처 성패와 무관하게 쓴다.

    삭제가 실패하면 시작 값만 측정해 돌려주고(``launch=False``) 컨텍스트는 쓰지 않는다. 호출자는
    세션을 시작하지 않고 ``finish_review``로 영수증을 쓴다(시작·종료 값이 같아 변경으로 읽히지 않는다).
    """
    job_id = job_dir.name
    stamp = now or _now()
    cleaned = _delete_planted(job_dir)
    hashes = _measure_draft(job_dir)
    snapshot = measure_screens(job_dir)
    index = _load_json_object(job_dir / "screens" / "index.json")
    tiles = _index_tiles(index)
    start = ReviewStart(job_id, stamp, cleaned, hashes, snapshot, tiles)
    if not cleaned:
        return start
    rel = f"runs/{job_id}"
    context = {
        "schema_version": SCHEMA_VERSION,
        "job_id": job_id,
        "code": code,
        "now": stamp,
        "input": {"path": f"{rel}/draft/report-input.json", "sha256": hashes["input"]},
        "preview": {"path": f"{rel}/draft/report.html", "sha256": hashes["preview"]},
        "screens": {
            "index_path": f"{rel}/screens/index.json",
            "outcome": _dig(index, "outcome") or "failed",
            "tiles": [f"{rel}/screens/{name}" for name in tiles],
            "render_note": RENDER_NOTE,
        },
        "audit_review_path": f"{rel}/{AUDIT_REVIEW_NAME}",
        "audit_output_path": f"{rel}/{REVIEW_DIR}/{AUDIT_OUTPUT_NAME}",
        "final_dir": f"{rel}/final",
        "copy_into_review_record": {
            "input_sha256": hashes["input"],
            "preview_sha256": hashes["preview"],
            "reviewed_at": stamp,
            "mode": REVIEW_MODE,
        },
    }
    review = job_dir / REVIEW_DIR
    review.mkdir(parents=True, exist_ok=True)
    (review / CONTEXT_NAME).write_text(json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8")
    return start


# ─────────────────────────────────────────────────────────────────────────────
# 열람·쓰기 시도 집계 (design §6)
# ─────────────────────────────────────────────────────────────────────────────


def _normalize(raw: str, harness_dir: Path) -> str | None:
    """절대 경로면 하네스 아래여야 하고, 상대 경로면 하네스 기준으로 풀어 normpath한다. 밖이면 None."""
    if not isinstance(raw, str) or not raw:
        return None
    base = os.path.normpath(harness_dir)
    path = os.path.normpath(raw if os.path.isabs(raw) else os.path.join(base, raw))
    if path.startswith(base + os.sep):
        return path
    # 별칭 경로(예: /private/var ↔ /var)면 실제 경로 기준으로 한 번 더 본다
    real_base = os.path.realpath(base)
    real = os.path.realpath(path)
    if real.startswith(real_base + os.sep):
        return os.path.join(base, os.path.relpath(real, real_base))
    return None


def tiles_read(read_paths: Iterable[str], harness_dir: Path, job_id: str, expected: list[str]) -> list[str]:
    """성공한 `Read` 경로 중 이 작업 `screens/`의 기대 타일과 정확히 일치하는 것(기대 순서).

    기본 이름·부분 문자열 비교는 하지 않는다. 대소문자도 정확히 같아야 읽음으로 센다(안전 방향).
    """
    base = os.path.join(os.path.normpath(harness_dir), "runs", job_id, "screens")
    seen = {_normalize(p, harness_dir) for p in read_paths}
    return [name for name in expected if os.path.join(base, name) in seen]


def judged_writes(write_paths: Iterable[str], harness_dir: Path, job_id: str) -> list[str]:
    """이 작업 `draft/`·`screens/` 아래로 풀리는 `Write`/`Edit` 시도(결과와 무관, 대소문자 무시).

    값은 하네스 기준 상대 경로. macOS 파일시스템은 대소문자를 구분하지 않아(research P32)
    대소문자만 바꾼 경로가 같은 폴더를 가리킬 수 있다.
    """
    base = os.path.normpath(harness_dir)
    found: list[str] = []
    for raw in write_paths:
        path = _normalize(raw, harness_dir)
        if path is None:
            continue
        rel = os.path.relpath(path, base)
        folded = rel.casefold().split(os.sep)
        if len(folded) >= 3 and folded[0] == "runs" and folded[1] == job_id.casefold() and folded[2] in (
            "draft", "screens"
        ):
            found.append(Path(rel).as_posix())
    return found


# ─────────────────────────────────────────────────────────────────────────────
# 최종본 인정 판정 (design §5, REQ-AIR6-016)
# ─────────────────────────────────────────────────────────────────────────────


def _parse_time(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else None  # 시간대 없는 값은 비교하지 않는다(미충족)


# @MX:ANCHOR: [AUTO] evaluate_core — 최종본 인정의 단일 조건 코어(조건 1~17, REQ-AIR6-016).
# @MX:REASON: 영수증 작성기(finish_review), 디스크 래퍼 evaluate_admissibility, M4 select_report·재평가가
#             같은 조건을 실행한다(fan_in 3). 조건 목록·순서·사유 코드를 바꾸면 AC-AIR6-014/015/016/021이
#             모두 깨진다. 저장된 visual_admissible 값은 절대 입력으로 쓰지 않는다.
def evaluate_core(job_dir: Path, receipt: object) -> list[str]:
    """영수증 사실(인자)과 디스크 현재 상태로 조건 1~17을 평가해 미충족 사유를 순서대로 돌려준다.

    ``receipt``는 파싱된 dict, 없으면 None, 읽을 수 없으면 ``_INVALID``. 예외를 던지지 않는다.
    읽기 보호: 1·2 미충족이면 영수증 의존 조건(3·4·6·9·11), 색인을 읽지 못하면 7·8·11·12·16과
    10의 색인 쪽, 조건 13 미충족이면 14~17과 10의 감수 기록 쪽은 평가·보고하지 않는다.
    """
    reasons: list[str] = []
    screens = job_dir / "screens"
    receipt_ok = False
    if receipt is None:
        reasons.append("no_receipt")
    elif not isinstance(receipt, dict) or receipt.get("schema_version") != SCHEMA_VERSION or not (
        RECEIPT_KEYS <= receipt.keys()
    ):
        reasons.append("receipt_invalid")
    else:
        receipt_ok = True
    facts = receipt if receipt_ok else {}
    if receipt_ok and facts["outcome"] != "reviewed":
        reasons.append("review_not_completed")
    if receipt_ok and facts["judged_writes"] != []:
        reasons.append("judged_input_write_attempt")

    index = _load_json_object(screens / "index.json")
    index_ok = index is not None and index.get("outcome") == "complete"
    if not index_ok:
        reasons.append("screens_not_complete")

    if receipt_ok:
        now_snapshot = measure_screens(job_dir)
        if not (now_snapshot == _dig(facts, "screens", "snapshot_start") == _dig(facts, "screens", "snapshot_end")):
            reasons.append("screens_changed")

    tiles = _index_tiles(index) if index is not None else []
    if index is not None:
        paths = {name: screens / name for name in tiles}
        # 파일 이름이 경로 구분자를 담으면 없는 것으로 본다
        missing = [n for n, p in paths.items() if Path(n).name != n or not p.is_file() or p.is_symlink()]
        if missing:
            reasons.append("tile_missing")
        index_tiles = _dig(index, "viewports") or []
        wrong = False
        for vp in index_tiles:
            for tile in _dig(vp, "tiles") or []:
                name = _dig(tile, "file")
                if name in paths and name not in missing and sha256_file(paths[name]) != _dig(tile, "sha256"):
                    wrong = True
        if wrong:
            reasons.append("tile_hash_mismatch")

    draft = _measure_draft(job_dir)
    if receipt_ok:
        hashes = facts["hashes"] if isinstance(facts["hashes"], dict) else {}
        if not (
            draft["input"] is not None
            and draft["input"] == hashes.get("input_start") == hashes.get("input_end")
            and draft["preview"] is not None
            and draft["preview"] == hashes.get("preview_start") == hashes.get("preview_end")
        ):
            reasons.append("draft_changed")

    audit = _load_json_object(job_dir / AUDIT_REVIEW_NAME)
    sides = []
    if index is not None:
        sides.append(_dig(index, "preview_sha256"))
    if audit is not None:
        sides.append(_dig(audit, "preview_sha256"))
    if sides and not all(side is not None and side == draft["preview"] for side in sides):
        reasons.append("preview_hash_mismatch")

    if receipt_ok and index is not None:
        expected = _dig(facts, "screens", "tiles_expected")
        read = _dig(facts, "screens", "tiles_read")
        if not (
            isinstance(expected, list)
            and isinstance(read, list)
            and sorted(map(str, expected)) == sorted(tiles)
            and set(tiles) <= set(read)
        ):
            reasons.append("tile_not_read")

    if index is not None:
        mobile = [vp for vp in _dig(index, "viewports") or [] if _dig(vp, "name") == "mobile"]
        if not (mobile and _dig(mobile[0], "metrics", "horizontal_overflow") is False):
            reasons.append("mobile_overflow")

    if audit is None:
        reasons.append("no_audit_review")
    else:
        if audit.get("mode") != REVIEW_MODE:
            reasons.append("mode_not_separate_review_pass")
        if _dig(audit, "checks", "visual", "status") != "pass":
            reasons.append("visual_not_pass")
        if index is not None:
            reviewed_at = _parse_time(audit.get("reviewed_at"))
            finished_at = _parse_time(_dig(index, "finished_at"))
            if reviewed_at is None or finished_at is None or reviewed_at < finished_at:
                reasons.append("reviewed_before_capture")
        evidence = _dig(audit, "checks", "visual", "evidence")
        if not (isinstance(evidence, str) and FONT_MARK in evidence):
            reasons.append("font_note_missing")
    return reasons


def evaluate_admissibility(job_dir: Path) -> tuple[bool, list[str]]:
    """디스크 래퍼: `review/receipt.json`을 읽어 조건 코어를 부른다. 예외를 던지지 않는다."""
    try:
        path = job_dir / REVIEW_DIR / RECEIPT_NAME
        receipt: object = None
        if path.exists():
            receipt = _load_json_object(path)
            if receipt is None:
                receipt = _INVALID
        reasons = evaluate_core(job_dir, receipt)
    except Exception:  # noqa: BLE001 - 판정은 실패해도 미인정(fail-closed)으로만 끝난다
        logger.exception("goose review: 판정 중 예기치 않은 오류 — 미인정 처리")
        return False, ["receipt_invalid"]
    if reasons:
        logger.info("goose review: 최종본 미인정 %s (첫 사유 %s)", job_dir.name, reasons[0])
    return not reasons, reasons


# ─────────────────────────────────────────────────────────────────────────────
# 세션 후: 영수증
# ─────────────────────────────────────────────────────────────────────────────


def _remove(path: Path) -> None:
    path.unlink(missing_ok=True)


def _replace(src: Path, dst: Path) -> None:
    os.replace(src, dst)


@dataclass
class ReceiptResult:
    receipt: dict
    written: bool
    file_remains: bool  # 쓰기가 실패했는데 같은 이름 파일이 남아 있음(완료 이벤트는 draft로 확정, REQ-AIR6-019)


def _write_receipt_file(path: Path, receipt: dict) -> ReceiptResult:
    """세션이 쓴 같은 이름 파일을 먼저 지우고 임시 파일 + 원자적 교체로 한 번만 쓴다(REQ-AIR6-015)."""
    tmp = path.with_name(f".{path.name}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        _remove(path)
        tmp.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
        _replace(tmp, path)
    except OSError:
        logger.error("receipt_write_failed: %s", path)
        try:
            _remove(path)  # 제거 재시도 — 세션이 쓴 영수증을 남기지 않는다
        except OSError:
            pass
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        return ReceiptResult(receipt, False, path.exists())
    return ReceiptResult(receipt, True, False)


def _audit_summary(job_dir: Path) -> dict:
    path = job_dir / AUDIT_REVIEW_NAME
    record = _load_json_object(path)
    return {
        "present": path.is_file(),
        "sha256": sha256_file(path),
        "mode": _dig(record, "mode"),
        "visual_status": _dig(record, "checks", "visual", "status"),
        "input_sha256": _dig(record, "input_sha256"),
        "preview_sha256": _dig(record, "preview_sha256"),
        "reviewed_at": _dig(record, "reviewed_at"),
    }


def _outcome(start: ReviewStart, exit_code: int | None, timed_out: bool, has_record: bool) -> str:
    if not start.launch:
        return "review_failed"
    if timed_out:
        return "timeout"
    if exit_code != 0 or not has_record:
        return "review_failed"
    return "reviewed"


def finish_review(
    job_dir: Path,
    start: ReviewStart,
    *,
    harness_dir: Path,
    exit_code: int | None = None,
    timed_out: bool = False,
    read_paths: Iterable[str] = (),
    write_paths: Iterable[str] = (),
    outcome: str | None = None,
) -> ReceiptResult:
    """세션 종료 후 종료 측정 → 판정 코어 호출 → 영수증을 한 번만 원자적으로 쓴다.

    영수증은 아직 디스크에 없으므로 방금 측정한 사실을 인자로 코어를 부른다(디스크 래퍼 사용 불가).
    ``outcome``은 취소처럼 호출자가 아는 결과를 강제할 때만 쓴다.
    """
    snapshot_end = measure_screens(job_dir)
    draft_end = _measure_draft(job_dir)
    summary = _audit_summary(job_dir)
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "outcome": outcome or _outcome(start, exit_code, timed_out, summary["present"]),
        "started_at": start.started_at,
        "finished_at": _now(),
        "process": {"exit_code": exit_code, "timed_out": timed_out},
        "hashes": {
            "input_start": start.hashes["input"],
            "input_end": draft_end["input"],
            "preview_start": start.hashes["preview"],
            "preview_end": draft_end["preview"],
        },
        "draft_unchanged": start.hashes == draft_end,
        "screens": {
            "outcome": _dig(_load_json_object(job_dir / "screens" / "index.json"), "outcome"),
            "index_sha256": snapshot_end["index_sha256"],
            "tiles_expected": list(start.tiles_expected),
            "tiles_read": tiles_read(read_paths, harness_dir, start.job_id, start.tiles_expected),
            "snapshot_start": start.snapshot,
            "snapshot_end": snapshot_end,
        },
        "judged_writes": judged_writes(write_paths, harness_dir, start.job_id),
        "audit_review": summary,
        "visual_admissible": False,  # 자리표시 — 아래 코어 결과로 채운다(입력이 아니다)
        "reasons": [],
    }
    reasons = evaluate_core(job_dir, receipt)
    receipt["visual_admissible"] = not reasons
    receipt["reasons"] = reasons
    return _write_receipt_file(job_dir / REVIEW_DIR / RECEIPT_NAME, receipt)


def write_outcome_receipt(job_dir: Path, outcome: str, *, harness_dir: Path) -> ReceiptResult:
    """세션 없이 끝난 경우(`integrity_failed`·`disabled`·`cancelled`)의 영수증을 서버가 쓴다.

    감수 세션을 시작하지 않았으므로 열람·쓰기 기록은 비어 있고 시작·종료 측정값은 같다.
    어떤 outcome이든 `reviewed`가 아니므로 최종본은 인정되지 않는다(조건 3).
    """
    if outcome not in OUTCOMES or outcome == "reviewed":
        raise ValueError(f"세션 없는 영수증 outcome이 아님: {outcome!r}")
    index = _load_json_object(job_dir / "screens" / "index.json")
    start = ReviewStart(
        job_dir.name, _now(), False, _measure_draft(job_dir), measure_screens(job_dir), _index_tiles(index)
    )
    return finish_review(job_dir, start, harness_dir=harness_dir, outcome=outcome)
