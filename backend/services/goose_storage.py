"""SPEC-AI-REPORT-004 M5 — goose 리포트 보관·기록·서빙 경로.

설계: design.md §5.1(보관 위치), §5.2(final 판정과 복사, 중단 규칙 T10), §5.3(기록), §5.4(경로 검증).

경계:
- 리포트 선택은 goose_runner.select_report(§5.2 단일 규칙)를 그대로 쓴다. 모델이 출력한 경로는 보지 않는다.
- 종목 폴더(`backend/reports/<sanitize(종목명)>`)는 ai_report_service가 정한다. 이 모듈은 그 경로를
  인자로 받는다(테스트에서 tmp 경로 주입). 기본 해석만 ai_report_service를 늦게 불러온다.
- 이 모듈은 goose_runner 밖의 backend.services 모듈을 맨 위에서 불러오지 않는다(테스트 격리 로드).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from backend.services import goose_runner

logger = logging.getLogger(__name__)

# 선택된 원본 폴더(final/ 또는 draft/)에서 복사하는 파일 — 이 밖의 이름은 복사하지 않는다(design §5.2)
ALLOWED_FILES = (
    "report.html",
    "report-input.json",
    "source-ledger.json",
    "render-validation.json",
    "delivery-audit.json",
)
ASSUMPTIONS_FILE = "assumptions.md"  # 작업 디렉터리 최상위(REQ-005), 없어도 오류 아님
JOB_META_FILE = "job.json"
REPORT_FILE = "report.html"
DELIVERY_STATUSES = ("final", "draft")
RUN_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}(_\d+)?$")

_KST = timezone(timedelta(hours=9))


@dataclass(frozen=True)
class Archived:
    run: str
    delivery_status: str
    interrupted: bool
    path: Path


def report_url(code: str, run: str) -> str:
    return f"/api/ai-report/{code}/goose/{run}/report.html"


# ─────────────────────────────────────────────────────────────────────────────
# 보관 (design §5.2)
# ─────────────────────────────────────────────────────────────────────────────


def _regular_file(path: Path) -> bool:
    return path.is_file() and not path.is_symlink()


def _new_run_dir(goose_dir: Path, now: datetime) -> Path:
    """`YYYY-MM-DD`, 이미 있으면 `_2`, `_3`… mkdir 성공으로 자리를 잡는다(같은 이름 경쟁 방지)."""
    goose_dir.mkdir(parents=True, exist_ok=True)
    date = now.astimezone(_KST).strftime("%Y-%m-%d")
    seq = 1
    while True:
        name = date if seq == 1 else f"{date}_{seq}"
        try:
            (goose_dir / name).mkdir()
            return goose_dir / name
        except FileExistsError:
            seq += 1


def _write_json(path: Path, data: dict[str, Any]) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".job-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def archive_job(
    *, job_dir: Path, stock_dir: Path, meta: dict[str, Any], interrupted: bool, now: datetime
) -> Archived | None:
    """선택되는 리포트가 있으면 `stock_dir/goose/<run>/`에 허용 파일만 복사하고 job.json을 쓴다.

    선택되는 리포트가 없으면 보관 폴더를 만들지 않고 None(design §5.2 마지막 줄).
    """
    selected = goose_runner.select_report(job_dir)
    if selected is None:
        return None
    delivery_status, source = selected
    run_dir = _new_run_dir(stock_dir / "goose", now)
    for name in ALLOWED_FILES:
        # 심볼릭 링크·폴더는 복사하지 않는다. 링크 확인 후 copyfile이 링크를 따라가지 않도록 정규 파일만.
        if _regular_file(source / name):
            shutil.copyfile(source / name, run_dir / name, follow_symlinks=False)
    if _regular_file(job_dir / ASSUMPTIONS_FILE):
        shutil.copyfile(job_dir / ASSUMPTIONS_FILE, run_dir / ASSUMPTIONS_FILE, follow_symlinks=False)
    _write_json(
        run_dir / JOB_META_FILE,
        {**meta, "run": run_dir.name, "delivery_status": delivery_status, "interrupted": interrupted},
    )
    logger.info("goose 리포트 보관: %s (%s, interrupted=%s)", run_dir, delivery_status, interrupted)
    return Archived(run_dir.name, delivery_status, interrupted, run_dir)


def default_stock_dir(stock_name: str) -> Path:
    from backend.services.ai_report_service import report_dir  # 늦은 import: my_chart 의존 회피

    return report_dir(stock_name)


def make_finish_hook(
    *,
    runs_root: Callable[[], Path],
    stock_dir: Callable[[str], Path] = default_stock_dir,
    clock: Callable[[], datetime] | None = None,
) -> Callable[[Any, Any], Any]:
    """GooseJobService ``on_finish`` 훅. 작업 서비스가 ``job.ending``(상태, 오류 종류)을 정한 뒤 부른다.

    `done`이 아닌 종료(시간 초과·비정상 종료·취소·서버 종료)에서도 선택되는 리포트가 있으면
    같은 방식으로 보관하고 ``interrupted: true``를 기록한다(결정 T10). 전달 상태는 선택 결과 그대로.
    돌려준 dict는 종료 이벤트 데이터에 합쳐진다(design §4.4).
    """
    now_fn = clock or (lambda: datetime.now(_KST))

    async def hook(job: Any, result: Any) -> dict[str, Any]:
        status, error_kind = job.ending
        now = now_fn()
        meta = {
            "job_id": job.job_id,
            "code": job.code,
            "stock_name": job.stock_name,
            "started_at": job.created_at.isoformat(timespec="seconds"),
            "finished_at": now.isoformat(timespec="seconds"),
            "status": status,
            "error_kind": error_kind,
        }
        if job.cancel_reason:
            meta["cancel_reason"] = job.cancel_reason
        archived = await asyncio.to_thread(
            archive_job,
            job_dir=runs_root() / job.job_id,
            stock_dir=stock_dir(job.stock_name),
            meta=meta,
            interrupted=status != "done",
            now=now,
        )
        if archived is None:
            return {}
        data: dict[str, Any] = {
            "run": archived.run,
            "delivery_status": archived.delivery_status,
            "report_url": report_url(job.code, archived.run),
        }
        if archived.interrupted:
            data["interrupted"] = True
        return data

    return hook


# ─────────────────────────────────────────────────────────────────────────────
# 기록 (design §5.3)
# ─────────────────────────────────────────────────────────────────────────────


def _seq(run: str) -> int:
    return int(run.split("_", 1)[1]) if "_" in run else 1


def list_goose_runs(stock_dir: Path) -> list[dict[str, Any]]:
    """`goose/*/job.json`을 읽어 기록 항목을 만든다. 형식이 맞지 않는 실행은 건너뛴다. 최신이 먼저."""
    goose_dir = stock_dir / "goose"
    if not goose_dir.is_dir():
        return []
    items: list[dict[str, Any]] = []
    for run_dir in goose_dir.iterdir():
        run = run_dir.name
        meta_path = run_dir / JOB_META_FILE
        if not RUN_PATTERN.fullmatch(run) or run_dir.is_symlink() or not _regular_file(meta_path):
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            logger.warning("goose 기록 job.json 읽기 실패: %s", meta_path)
            continue
        if not isinstance(meta, dict) or meta.get("delivery_status") not in DELIVERY_STATUSES:
            continue
        created = datetime.fromtimestamp(meta_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        items.append({
            "filename": REPORT_FILE,
            "date": run[:10],
            "created_at": created,
            "kind": "goose",
            "run": run,
            "delivery_status": meta["delivery_status"],
            "interrupted": meta.get("interrupted") is True,
        })
    items.sort(key=lambda item: (item["date"], _seq(item["run"])), reverse=True)
    return items


# ─────────────────────────────────────────────────────────────────────────────
# HTML 경로 검증 (design §5.4, REQ-016)
# ─────────────────────────────────────────────────────────────────────────────


# @MX:WARN: [AUTO] 외부 입력(run)으로 파일 경로를 만드는 보안 게이트(REQ-AIR4-016, AC-016).
# @MX:REASON: 정규식 → 고정 파일명 → resolve() 후 루트·종목 goose 폴더 하위 확인의 3중 방어.
#             하나라도 빼면 `..`·인코딩·심볼릭 링크로 리포트 루트 밖 파일을 읽힐 수 있다.
def resolve_report_html(reports_root: Path, stock_dir: Path, run: str) -> Path | None:
    """보관된 `report.html`의 실제 경로 또는 None. None이면 라우터는 404를 돌려준다."""
    if not isinstance(run, str) or not RUN_PATTERN.fullmatch(run):
        return None
    try:
        root = reports_root.resolve()
        goose_root = (stock_dir / "goose").resolve()
        target = (stock_dir / "goose" / run / REPORT_FILE).resolve()
        goose_root.relative_to(root)
        target.relative_to(goose_root)
    except (OSError, ValueError, RuntimeError):
        return None
    if not target.is_file():
        return None
    return target
