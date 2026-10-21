"""SPEC-AI-REPORT-004 (REQ-AIR4-001, 결정 T11) — goose 하네스 원본 대조·설치·무결성 검사.

리포에는 `.claude`·`CLAUDE.md` 이름이 없는 추적 원본(`backend/goose_harness_src/`)과
설치본 경로 기준 sha256 매니페스트(`goose-manifest.json`)만 둔다. `claude`는 리포 밖
설치본(`AI_REPORT_GOOSE_HARNESS_DIR`, 기본 `~/.goose-harness`)에서만 실행한다.

M4 작업 서비스가 쓰는 API:
- ``install_at_startup()`` — 서버 시작(lifespan)에서 1회 호출. 예외를 던지지 않는다.
  원본이 매니페스트와 맞을 때만 설치하고, 실패하면 "시작 시 무결성 실패"를 프로세스가
  끝날 때까지 기록한다(닫힌 실패, plan-audit R5-1).
- ``check_job_integrity()`` — goose 작업 시작 직전(REQ-008 무결성 단계) 호출.
  ``ok``가 거짓이면 작업을 ``error``/``integrity``로 끝내고 claude를 띄우지 않는다.
  시작 시 실패 기록이 있거나, 시작 설치가 이 프로세스에서 실행되지 않았거나,
  설치본이 매니페스트와 다르면(목록 밖 `.claude/` 파일 포함, `.DS_Store` 제외) 실패.
- ``resolve_harness_dir()`` — 하네스 경로 해석(M3 실행기의 cwd와 같은 값).
- ``build_manifest()`` — 원본 갱신(goose 재벤더링) 시 매니페스트 재생성용.
  ``python -m backend.services.goose_harness`` 가 JSON을 표준 출력으로 낸다.

이 모듈은 backend.services 의 다른 모듈을 import하지 않는다(테스트 격리 로드 가능).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

ENV_HARNESS_DIR = "AI_REPORT_GOOSE_HARNESS_DIR"
DEFAULT_HARNESS_DIR = "~/.goose-harness"
MANIFEST_NAME = "goose-manifest.json"
DS_STORE = ".DS_Store"
ERROR_KIND_INTEGRITY = "integrity"

SOURCE_DIR = Path(__file__).resolve().parent.parent / "goose_harness_src"
REPO_ROOT = Path(__file__).resolve().parents[2]

# 원본 상대 경로 → 설치본 상대 경로. 파일 두 개는 정확히 일치, skills/ 아래는 접두어 대응.
_FILE_MAP = {
    "harness-instructions.md": "CLAUDE.md",
    "claude-settings.json": ".claude/settings.json",
}
_SKILLS_PREFIX = ("skills/", ".claude/skills/")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class HarnessStatus:
    """서버 시작 설치 결과. ``ok``가 거짓이면 ``reason``이 실패 사유다."""

    ok: bool
    reason: str
    harness_dir: Path | None


@dataclass(frozen=True)
class IntegrityResult:
    """작업 시작 직전 무결성 검사 결과."""

    ok: bool
    reason: str

    @property
    def error_kind(self) -> str | None:
        return None if self.ok else ERROR_KIND_INTEGRITY


# @MX:WARN: [AUTO] 프로세스 전역 상태 — 시작 설치 결과와 기준 매니페스트를 서버 수명 동안 보관한다.
# @MX:REASON: 닫힌 실패(R5-1)는 "이 프로세스에서 시작 대조가 실패했다"는 사실을 작업 시작 시점까지
#   유지해야 한다. 단일 uvicorn 워커 전제(spec §5). 테스트는 reset_state()로 재시작을 흉내 낸다.
_startup_status: HarnessStatus | None = None
_baseline_manifest: dict[str, str] | None = None


def reset_state() -> None:
    """프로세스 상태 초기화(테스트용 — 서버 재시작과 같은 효과)."""
    global _startup_status, _baseline_manifest
    _startup_status = None
    _baseline_manifest = None


def resolve_harness_dir(environ: Mapping[str, str] | None = None) -> Path:
    """`AI_REPORT_GOOSE_HARNESS_DIR`(없으면 `~/.goose-harness`)를 펼친 경로를 돌려준다.

    `~`는 ``environ``의 ``HOME``으로 펼친다(주입 가능, 기본 os.environ).
    """
    env = os.environ if environ is None else environ
    raw = env.get(ENV_HARNESS_DIR) or DEFAULT_HARNESS_DIR
    if raw == "~" or raw.startswith("~/"):
        home = env.get("HOME") or str(Path.home())
        raw = home + raw[1:]
    return Path(raw)


def source_to_installed(rel_source: str) -> str | None:
    """원본 상대 경로를 설치본 상대 경로로 바꾼다. 알려진 배치 밖이면 None."""
    if rel_source in _FILE_MAP:
        return _FILE_MAP[rel_source]
    src_prefix, inst_prefix = _SKILLS_PREFIX
    if rel_source.startswith(src_prefix) and len(rel_source) > len(src_prefix):
        return inst_prefix + rel_source[len(src_prefix):]
    return None


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _iter_tree(root: Path) -> list[tuple[str, Path]]:
    """``root`` 아래 모든 항목(디렉터리 제외)의 (상대 경로, 경로). 심볼릭 링크는 따라가지 않는다."""
    out: list[tuple[str, Path]] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        base = Path(dirpath)
        # 디렉터리 심볼릭 링크는 walk가 내려가지 않으므로 항목으로 보고한다.
        names = filenames + [d for d in dirnames if (base / d).is_symlink()]
        for name in names:
            p = base / name
            out.append((p.relative_to(root).as_posix(), p))
    return sorted(out)


def load_manifest(source_dir: Path) -> dict[str, str]:
    """리포 매니페스트를 읽어 ``{설치본 상대 경로: sha256}``를 돌려준다. 형식 오류는 ValueError."""
    data = json.loads((source_dir / MANIFEST_NAME).read_text(encoding="utf-8"))
    files = data.get("files") if isinstance(data, dict) else None
    if not isinstance(files, dict) or not files:
        raise ValueError("manifest has no 'files' mapping")
    for rel, digest in files.items():
        if not isinstance(rel, str) or not isinstance(digest, str) or not _SHA256_RE.match(digest):
            raise ValueError(f"manifest entry invalid: {rel!r}")
        if rel.startswith("/") or ".." in rel.split("/"):
            raise ValueError(f"manifest path not relative: {rel!r}")
    return dict(files)


def verify_source(source_dir: Path, manifest: Mapping[str, str]) -> list[str]:
    """원본을 설치 경로로 바꿔 매니페스트와 대조한다. 문제 목록(빈 목록 = 일치)을 돌려준다.

    제외: 원본 최상위 `goose-manifest.json`, 모든 `.DS_Store`.
    """
    problems: list[str] = []
    seen: set[str] = set()
    for rel, path in _iter_tree(source_dir):
        if rel == MANIFEST_NAME or path.name == DS_STORE:
            continue
        if path.is_symlink() or not path.is_file():
            problems.append(f"source not a regular file: {rel}")
            continue
        installed = source_to_installed(rel)
        if installed is None or installed not in manifest:
            problems.append(f"unlisted source file: {rel}")
            continue
        seen.add(installed)
        if _sha256_file(path) != manifest[installed]:
            problems.append(f"source sha256 mismatch: {rel}")
    for missing in sorted(set(manifest) - seen):
        problems.append(f"listed file missing from source: {missing}")
    return problems


def verify_installed(harness_dir: Path, manifest: Mapping[str, str]) -> list[str]:
    """설치본을 매니페스트와 대조한다(목록 밖 `.claude/` 파일 포함, `.DS_Store` 제외 — N1)."""
    problems: list[str] = []
    for rel, digest in sorted(manifest.items()):
        path = harness_dir / rel
        if path.is_symlink() or not path.is_file():
            problems.append(f"installed file missing: {rel}")
        elif _sha256_file(path) != digest:
            problems.append(f"installed sha256 mismatch: {rel}")
    claude_dir = harness_dir / ".claude"
    if claude_dir.is_symlink():
        problems.append("installed .claude is a symlink")
    elif claude_dir.is_dir():
        for rel, path in _iter_tree(claude_dir):
            full_rel = f".claude/{rel}"
            if path.name == DS_STORE:
                continue
            if path.is_symlink():
                problems.append(f"symlink under installed .claude: {full_rel}")
            elif full_rel not in manifest:
                problems.append(f"unlisted installed file: {full_rel}")
    return problems


def _overlaps_repo(harness_dir: Path, repo_root: Path) -> bool:
    """하네스 경로가 리포 안이거나 리포를 포함하는 상위 경로면 참(N3)."""
    h = harness_dir.resolve()
    r = repo_root.resolve()
    return h == r or r in h.parents or h in r.parents


def _install(source_dir: Path, harness_dir: Path) -> None:
    """임시 디렉터리에 설치본을 만든 뒤 `CLAUDE.md`·`.claude`를 이름 바꾸기로 교체한다.

    `runs/`를 포함해 `<H>`의 다른 항목은 건드리지 않는다. 교체 중 실패하면 이전 항목을 되돌린다.
    """
    harness_dir.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".goose-install-", dir=harness_dir))
    backup = Path(tempfile.mkdtemp(prefix=".goose-old-", dir=harness_dir))
    try:
        for rel, path in _iter_tree(source_dir):
            if rel == MANIFEST_NAME or path.name == DS_STORE:
                continue
            installed = source_to_installed(rel)
            if installed is None:  # verify_source가 먼저 걸러낸다
                raise ValueError(f"unmapped source file: {rel}")
            dest = staging / installed
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, dest)
        names = ("CLAUDE.md", ".claude")
        moved: list[str] = []
        placed: list[str] = []
        try:
            for name in names:
                if os.path.lexists(harness_dir / name):
                    os.replace(harness_dir / name, backup / name)
                    moved.append(name)
            for name in names:
                os.replace(staging / name, harness_dir / name)
                placed.append(name)
        except OSError:
            for name in placed:
                _remove(harness_dir / name)
            for name in moved:
                os.replace(backup / name, harness_dir / name)
            raise
    finally:
        _remove(staging)
        _remove(backup)


def _remove(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.is_dir():
        shutil.rmtree(path, ignore_errors=True)


def _record(status: HarnessStatus, manifest: dict[str, str] | None) -> HarnessStatus:
    global _startup_status, _baseline_manifest
    _startup_status = status
    _baseline_manifest = manifest if status.ok else None
    if status.ok:
        logger.info("goose 하네스 설치 완료: %s", status.harness_dir)
    else:
        logger.error("goose 하네스 시작 시 무결성 실패 — 이 서버 실행 동안 goose 작업 불가: %s", status.reason)
    return status


# @MX:ANCHOR: [AUTO] 서버 시작 시 하네스 원본 대조·설치 진입점 (REQ-AIR4-001, AC-AIR4-001)
# @MX:REASON: main.py lifespan과 M4 작업 서비스의 무결성 판정이 이 결과(프로세스 상태)에 의존한다.
def install_at_startup(
    *,
    source_dir: Path = SOURCE_DIR,
    harness_dir: Path | None = None,
    repo_root: Path = REPO_ROOT,
) -> HarnessStatus:
    """원본을 매니페스트로 대조해 맞으면 설치하고 설치본을 다시 검사한다. 예외를 던지지 않는다."""
    target = harness_dir if harness_dir is not None else resolve_harness_dir()
    try:
        target = target.expanduser()
        if not target.is_absolute():
            target = Path.cwd() / target
        if _overlaps_repo(target, repo_root):
            return _record(
                HarnessStatus(False, f"harness dir overlaps repository: {target}", target), None
            )
        target = target.resolve()
        manifest = load_manifest(source_dir)
        problems = verify_source(source_dir, manifest)
        if problems:
            return _record(HarnessStatus(False, "; ".join(problems), target), None)
        _install(source_dir, target)
        problems = verify_installed(target, manifest)
        if problems:
            return _record(HarnessStatus(False, "post-install: " + "; ".join(problems), target), None)
        return _record(HarnessStatus(True, "installed", target), manifest)
    except (OSError, ValueError) as exc:
        return _record(HarnessStatus(False, f"{type(exc).__name__}: {exc}", target), None)


# @MX:ANCHOR: [AUTO] 작업 시작 직전 무결성 판정 (REQ-AIR4-001·008 무결성 단계, AC-AIR4-001 (2b)(3)(4))
# @MX:REASON: M4 goose_job_service.start()가 잠금 안에서 호출한다. 실패 시 claude 미실행·active 미등록.
def check_job_integrity() -> IntegrityResult:
    """시작 시 실패 기록과 설치본-매니페스트 대조를 모두 통과해야 ``ok``다."""
    status = _startup_status
    if status is None:
        return IntegrityResult(False, "harness startup install has not run in this process")
    if not status.ok or _baseline_manifest is None or status.harness_dir is None:
        return IntegrityResult(False, f"startup integrity failure: {status.reason}")
    problems = verify_installed(status.harness_dir, _baseline_manifest)
    if problems:
        logger.error("goose 하네스 설치본 무결성 실패: %s", "; ".join(problems))
        return IntegrityResult(False, "; ".join(problems))
    return IntegrityResult(True, "ok")


def build_manifest(source_dir: Path = SOURCE_DIR) -> dict[str, dict[str, str]]:
    """원본에서 매니페스트를 만든다(원본 갱신 시 유지보수용). 매핑 밖 원본 파일은 ValueError."""
    files: dict[str, str] = {}
    for rel, path in _iter_tree(source_dir):
        if rel == MANIFEST_NAME or path.name == DS_STORE:
            continue
        installed = source_to_installed(rel)
        if installed is None or path.is_symlink():
            raise ValueError(f"source file outside harness layout: {rel}")
        files[installed] = _sha256_file(path)
    return {"files": dict(sorted(files.items()))}


if __name__ == "__main__":  # pragma: no cover - 유지보수 CLI
    print(json.dumps(build_manifest(), indent=2, ensure_ascii=False))
