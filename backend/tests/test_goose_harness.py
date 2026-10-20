"""SPEC-AI-REPORT-004 M2 — goose 하네스 원본 대조·설치·작업 시작 무결성 검사 단위 테스트.

테스트 대상: backend/services/goose_harness.py
- install_at_startup(): 서버 시작 시 원본 대조 → 설치(원자적 교체, runs/ 보존) → 설치본 재검사
- check_job_integrity(): 작업 시작 직전 무결성 검사(시작 시 실패 기록 + 설치본 대조)

커버리지: AC-AIR4-001 (1)(2)(2b)(2c)(3)(4)(5)의 하네스 쪽 판정, N1(설치본 .DS_Store 무시),
N3(리포 아래·리포 상위 경로 설치 거부). 라우터 응답(202·active·쿼터)은 M4 범위다.

격리 방식:
- 모듈을 파일 경로로 직접 로드해 backend/services/__init__.py 연쇄 import를 피한다.
- 모든 경로는 tmp_path로 주입한다. 실제 ~/.goose-harness와 실제 홈은 건드리지 않는다.
- 기대 sha256은 hashlib로 테스트가 직접 계산한다(구현의 해시·매핑 헬퍼를 기대값 계산에 쓰지 않음).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_MODULE_PATH = Path(__file__).parent.parent / "services" / "goose_harness.py"
_REAL_SOURCE = Path(__file__).parent.parent / "goose_harness_src"


@pytest.fixture()
def gh():
    """goose_harness 모듈을 테스트마다 새로 로드한다(프로세스 상태 = 새 서버 프로세스)."""
    spec = importlib.util.spec_from_file_location("_test_goose_harness", _MODULE_PATH)
    assert spec and spec.loader, f"모듈 스펙 로드 실패: {_MODULE_PATH}"
    module = importlib.util.module_from_spec(spec)
    sys.modules["_test_goose_harness"] = module  # dataclass 처리에 필요
    spec.loader.exec_module(module)
    yield module
    sys.modules.pop("_test_goose_harness", None)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# 원본 상대 경로 → 설치본 상대 경로 (테스트가 리터럴로 고정한 기대 대응)
_SOURCE_FILES = {
    "harness-instructions.md": ("CLAUDE.md", b"# rules\n"),
    "claude-settings.json": (".claude/settings.json", b'{"permissions": {}}\n'),
    "skills/goose/SKILL.md": (".claude/skills/goose/SKILL.md", b"---\nname: goose\n---\n"),
    "skills/goose/workflows/stock-report/GUIDE.md": (
        ".claude/skills/goose/workflows/stock-report/GUIDE.md",
        b"guide body\n",
    ),
    "skills/goose/assets/goose.png": (".claude/skills/goose/assets/goose.png", b"\x89PNG\x00\x01"),
}


@pytest.fixture()
def env(tmp_path: Path):
    """임시 리포 루트·원본·매니페스트·설치 대상 <H>(runs/keep.txt 미리 존재)."""
    repo = tmp_path / "repo"
    source = repo / "backend" / "goose_harness_src"
    for rel, (_installed, data) in _SOURCE_FILES.items():
        p = source / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    # 매니페스트에 없는 .DS_Store (대조·설치 모두 제외 대상)
    (source / "skills" / "goose" / ".DS_Store").write_bytes(b"finder junk")
    (source / ".DS_Store").write_bytes(b"finder junk top")
    manifest = {"files": {inst: _sha(data) for inst, data in _SOURCE_FILES.values()}}
    (source / "goose-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    harness = tmp_path / "home" / ".goose-harness"
    (harness / "runs").mkdir(parents=True)
    (harness / "runs" / "keep.txt").write_bytes(b"keep me")
    return {"repo": repo, "source": source, "harness": harness, "manifest": manifest}


def _start(gh, env, **overrides):
    kwargs = {
        "source_dir": env["source"],
        "harness_dir": env["harness"],
        "repo_root": env["repo"],
    }
    kwargs.update(overrides)
    return gh.install_at_startup(**kwargs)


def _installed_hashes(harness: Path) -> dict[str, str]:
    out = {}
    for p in sorted(harness.rglob("*")):
        if p.is_file() and "runs" not in p.relative_to(harness).parts:
            out[p.relative_to(harness).as_posix()] = _sha(p.read_bytes())
    return out


# ─────────────────────────────────────────────────────────────────────────────
# AC-001 (1) — 일치하는 원본 설치
# ─────────────────────────────────────────────────────────────────────────────


def test_matching_source_installs_listed_files_and_preserves_runs(gh, env):
    status = _start(gh, env)

    assert status.ok is True, status.reason
    harness = env["harness"]
    for installed, data in _SOURCE_FILES.values():
        p = harness / installed
        assert p.is_file(), installed
        assert _sha(p.read_bytes()) == env["manifest"]["files"][installed] == _sha(data)
    assert (harness / "runs" / "keep.txt").read_bytes() == b"keep me"
    names = {p.name for p in harness.rglob("*")}
    assert "goose-manifest.json" not in names
    assert ".DS_Store" not in names
    # 설치 임시 디렉터리가 남지 않음
    assert sorted(p.name for p in harness.iterdir()) == [".claude", "CLAUDE.md", "runs"]


def test_job_integrity_passes_after_clean_install(gh, env):
    _start(gh, env)

    result = gh.check_job_integrity()

    assert result.ok is True, result.reason
    assert result.error_kind is None


# ─────────────────────────────────────────────────────────────────────────────
# AC-001 (2)(2c) — 원본 대조 실패 시 설치하지 않음
# ─────────────────────────────────────────────────────────────────────────────


def test_one_byte_change_in_source_blocks_install(gh, env):
    guide = env["source"] / "skills/goose/workflows/stock-report/GUIDE.md"
    guide.write_bytes(b"guide bodY\n")

    status = _start(gh, env)

    assert status.ok is False
    assert not (env["harness"] / ".claude").exists()
    assert not (env["harness"] / "CLAUDE.md").exists()
    assert (env["harness"] / "runs" / "keep.txt").read_bytes() == b"keep me"
    result = gh.check_job_integrity()
    assert result.ok is False
    assert result.error_kind == "integrity"


def test_unlisted_source_file_blocks_install(gh, env):
    (env["source"] / "skills" / "goose" / "extra.md").write_bytes(b"not in manifest\n")

    status = _start(gh, env)

    assert status.ok is False
    assert "extra.md" in status.reason
    assert not (env["harness"] / ".claude").exists()


def test_source_file_outside_known_layout_blocks_install(gh, env):
    """원본 최상위의 매핑 밖 파일(예: notes.md)도 목록 밖 원본 파일이다."""
    (env["source"] / "notes.md").write_bytes(b"x")

    status = _start(gh, env)

    assert status.ok is False
    assert not (env["harness"] / ".claude").exists()


def test_nested_manifest_named_file_is_not_excluded(gh, env):
    """제외 대상은 원본 최상위의 매니페스트 파일 하나뿐이다."""
    (env["source"] / "skills" / "goose" / "goose-manifest.json").write_bytes(b"{}")

    status = _start(gh, env)

    assert status.ok is False


def test_listed_file_missing_from_source_blocks_install(gh, env):
    (env["source"] / "skills/goose/assets/goose.png").unlink()

    status = _start(gh, env)

    assert status.ok is False
    assert not (env["harness"] / ".claude").exists()


def test_missing_manifest_blocks_install(gh, env):
    (env["source"] / "goose-manifest.json").unlink()

    status = _start(gh, env)

    assert status.ok is False
    assert not (env["harness"] / ".claude").exists()
    assert gh.check_job_integrity().ok is False


def test_malformed_manifest_blocks_install(gh, env):
    (env["source"] / "goose-manifest.json").write_text('{"files": {"CLAUDE.md": "nothex"}}')

    status = _start(gh, env)

    assert status.ok is False
    assert not (env["harness"] / ".claude").exists()


# ─────────────────────────────────────────────────────────────────────────────
# AC-001 (2b) — 닫힌 실패: 원본 대조 실패 기록 후에는 맞는 옛 설치본으로도 실행하지 않음
# ─────────────────────────────────────────────────────────────────────────────


def test_startup_source_failure_keeps_old_install_but_fails_every_job(gh, env):
    assert _start(gh, env).ok is True
    before = _installed_hashes(env["harness"])
    gh.reset_state()  # 서버 재시작
    (env["source"] / "skills/goose/SKILL.md").write_bytes(b"---\nname: goosE\n---\n")

    status = _start(gh, env)

    assert status.ok is False
    assert _installed_hashes(env["harness"]) == before  # 교체 안 됨
    assert gh.verify_installed(env["harness"], env["manifest"]["files"]) == []  # 옛 설치본은 맞음
    result = gh.check_job_integrity()
    assert result.ok is False
    assert result.error_kind == "integrity"
    assert gh.check_job_integrity().ok is False  # 프로세스 동안 유지


# ─────────────────────────────────────────────────────────────────────────────
# AC-001 (3)(4)(5) — 작업 시작 시 설치본 검사
# ─────────────────────────────────────────────────────────────────────────────


def test_modified_installed_file_fails_job_integrity(gh, env):
    _start(gh, env)
    target = env["harness"] / ".claude/skills/goose/workflows/stock-report/GUIDE.md"
    target.write_bytes(b"guide bodY\n")

    result = gh.check_job_integrity()

    assert result.ok is False
    assert result.error_kind == "integrity"


def test_modified_installed_claude_md_fails_job_integrity(gh, env):
    _start(gh, env)
    (env["harness"] / "CLAUDE.md").write_bytes(b"# ruleS\n")

    assert gh.check_job_integrity().ok is False


def test_unlisted_file_under_installed_claude_dir_fails_job_integrity(gh, env):
    _start(gh, env)
    (env["harness"] / ".claude" / "settings.local.json").write_text("{}")

    result = gh.check_job_integrity()

    assert result.ok is False
    assert "settings.local.json" in result.reason


def test_missing_installed_file_fails_job_integrity(gh, env):
    _start(gh, env)
    (env["harness"] / ".claude/skills/goose/assets/goose.png").unlink()

    assert gh.check_job_integrity().ok is False


def test_symlink_under_installed_claude_dir_fails_job_integrity(gh, env, tmp_path):
    _start(gh, env)
    outside = tmp_path / "outside.txt"
    outside.write_text("x")
    (env["harness"] / ".claude" / "skills" / "link.md").symlink_to(outside)

    assert gh.check_job_integrity().ok is False


def test_restart_restores_tampered_install(gh, env):
    _start(gh, env)
    (env["harness"] / ".claude/skills/goose/SKILL.md").write_bytes(b"tampered")
    (env["harness"] / ".claude" / "settings.local.json").write_text("{}")
    assert gh.check_job_integrity().ok is False
    gh.reset_state()  # 서버 재시작

    status = _start(gh, env)

    assert status.ok is True, status.reason
    assert gh.check_job_integrity().ok is True
    assert not (env["harness"] / ".claude" / "settings.local.json").exists()
    assert (env["harness"] / "runs" / "keep.txt").read_bytes() == b"keep me"


def test_job_integrity_fails_closed_when_startup_never_ran(gh):
    result = gh.check_job_integrity()

    assert result.ok is False
    assert result.error_kind == "integrity"


# ─────────────────────────────────────────────────────────────────────────────
# N1 — 설치본 검사도 .DS_Store는 무시
# ─────────────────────────────────────────────────────────────────────────────


def test_ds_store_under_installed_claude_dir_is_ignored(gh, env):
    _start(gh, env)
    (env["harness"] / ".claude" / ".DS_Store").write_bytes(b"finder")
    (env["harness"] / ".claude" / "skills" / "goose" / ".DS_Store").write_bytes(b"finder")

    result = gh.check_job_integrity()

    assert result.ok is True, result.reason


# ─────────────────────────────────────────────────────────────────────────────
# N3 — 리포 안(또는 리포를 포함하는 상위) 하네스 경로는 설치 거부 + 닫힌 실패
# ─────────────────────────────────────────────────────────────────────────────


def test_harness_dir_inside_repo_is_refused(gh, env):
    inside = env["repo"] / "backend" / "goose_harness"

    status = _start(gh, env, harness_dir=inside)

    assert status.ok is False
    assert not inside.exists()
    result = gh.check_job_integrity()
    assert result.ok is False
    assert result.error_kind == "integrity"


def test_harness_dir_that_contains_repo_is_refused(gh, env):
    ancestor = env["repo"].parent

    status = _start(gh, env, harness_dir=ancestor)

    assert status.ok is False
    assert not (ancestor / "CLAUDE.md").exists()
    assert not (ancestor / ".claude").exists()
    assert gh.check_job_integrity().ok is False


def test_harness_dir_symlinked_into_repo_is_refused(gh, env, tmp_path):
    real_inside = env["repo"] / "hidden"
    real_inside.mkdir()
    link = tmp_path / "looks-outside"
    link.symlink_to(real_inside)

    status = _start(gh, env, harness_dir=link)

    assert status.ok is False
    assert not (real_inside / ".claude").exists()


# ─────────────────────────────────────────────────────────────────────────────
# 기존 설치본 교체
# ─────────────────────────────────────────────────────────────────────────────


def test_install_replaces_stale_install_contents(gh, env):
    old = env["harness"] / ".claude" / "skills" / "old-skill"
    old.mkdir(parents=True)
    (old / "SKILL.md").write_text("stale")
    (env["harness"] / "CLAUDE.md").write_text("stale rules")

    status = _start(gh, env)

    assert status.ok is True, status.reason
    assert not old.exists()
    assert (env["harness"] / "CLAUDE.md").read_bytes() == b"# rules\n"


# ─────────────────────────────────────────────────────────────────────────────
# 하네스 경로 해석
# ─────────────────────────────────────────────────────────────────────────────


def test_resolve_harness_dir_defaults_to_home_dot_goose_harness(gh, tmp_path):
    home = tmp_path / "T"
    resolved = gh.resolve_harness_dir({"HOME": str(home)})

    assert resolved == home / ".goose-harness"


def test_resolve_harness_dir_uses_env_override(gh, tmp_path):
    resolved = gh.resolve_harness_dir(
        {"HOME": str(tmp_path), "AI_REPORT_GOOSE_HARNESS_DIR": "/tmp/h2"}
    )

    assert resolved == Path("/tmp/h2")


def test_resolve_harness_dir_expands_tilde_in_override(gh, tmp_path):
    resolved = gh.resolve_harness_dir(
        {"HOME": str(tmp_path), "AI_REPORT_GOOSE_HARNESS_DIR": "~/custom-h"}
    )

    assert resolved == tmp_path / "custom-h"


def test_install_at_startup_reads_env_when_harness_dir_omitted(gh, env, monkeypatch):
    monkeypatch.setenv("AI_REPORT_GOOSE_HARNESS_DIR", str(env["harness"]))

    status = gh.install_at_startup(source_dir=env["source"], repo_root=env["repo"])

    assert status.ok is True, status.reason
    assert status.harness_dir == env["harness"].resolve()
    assert (env["harness"] / "CLAUDE.md").is_file()


# ─────────────────────────────────────────────────────────────────────────────
# 커밋된 원본·매니페스트 자체 점검 (리포 실물)
# ─────────────────────────────────────────────────────────────────────────────


def test_committed_source_matches_committed_manifest(gh):
    manifest = json.loads((_REAL_SOURCE / "goose-manifest.json").read_text(encoding="utf-8"))

    problems = gh.verify_source(_REAL_SOURCE, manifest["files"])

    assert problems == []


def test_committed_manifest_covers_instructions_settings_and_whole_skill(gh):
    files = json.loads((_REAL_SOURCE / "goose-manifest.json").read_text(encoding="utf-8"))["files"]
    skill_files = sorted(
        p.relative_to(_REAL_SOURCE / "skills").as_posix()
        for p in (_REAL_SOURCE / "skills").rglob("*")
        if p.is_file() and p.name != ".DS_Store"
    )

    assert files["CLAUDE.md"] == _sha((_REAL_SOURCE / "harness-instructions.md").read_bytes())
    assert files[".claude/settings.json"] == _sha((_REAL_SOURCE / "claude-settings.json").read_bytes())
    assert len(skill_files) >= 30
    for rel in skill_files:
        assert files[f".claude/skills/{rel}"] == _sha((_REAL_SOURCE / "skills" / rel).read_bytes())
    assert len(files) == 2 + len(skill_files)


def test_committed_source_uses_no_claude_names():
    """REQ-022/T11: 리포 원본에 `.claude` 디렉터리나 `CLAUDE.md` 파일 이름이 없어야 한다."""
    names = {p.name for p in _REAL_SOURCE.rglob("*")}

    assert ".claude" not in names
    assert "CLAUDE.md" not in names


def test_committed_settings_deny_reads_outside_harness():
    """REQ-003 둘째 절(AC-003 6a~6f)을 막는 거부 규칙과 M1 측정 설정 키가 있어야 한다."""
    settings = json.loads((_REAL_SOURCE / "claude-settings.json").read_text(encoding="utf-8"))
    deny = settings["permissions"]["deny"]

    assert settings["disableAllHooks"] is True
    assert settings["autoMemoryEnabled"] is False
    assert "/usr/bin" in settings["env"]["PATH"].split(":")
    assert "/bin" in settings["env"]["PATH"].split(":")
    for rule in ("Bash(*..*)", "Read(../**)", "Edit(./.claude/**)", "Write(./.claude/**)"):
        assert rule in deny
    assert "bypassPermissions" not in json.dumps(settings)
