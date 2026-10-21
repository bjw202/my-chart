"""되돌림 RED 관측 하네스: 보호 동작을 하나씩 임시로 되돌리고 시험을 돌린 뒤 반드시 복원한다.

사용: python3 mutate.py <worktree 절대경로>
출력: 변이마다 `ID | AC | 실패한 시험 수 | 실패 시험 이름들`, 마지막에 복원 해시 일치 여부.
"""
import hashlib
import subprocess
import sys
from pathlib import Path

WT = Path(sys.argv[1])
SRC = WT / "backend/services/goose_screenshot.py"
PY = str(WT / "../../../.venv/bin/python")
TEST = "backend/tests/test_goose_screenshot.py"

M = []  # (id, ac, 설명, [(old, new), ...])


def add(i, ac, desc, *pairs):
    M.append((i, ac, desc, list(pairs)))


add("006a", "006", "타일 없이 한 장 전체 저장",
    ("count = -(-total // TILE_HEIGHT)", "count = 1"),
    ("tile_h = min(TILE_HEIGHT, total - y)", "tile_h = total - y"))
add("006b", "006", "두 뷰포트가 같은 폭", ('("mobile", 390, 844, True)', '("mobile", 1280, 844, True)'))
add("006c", "006", "모바일 에뮬레이션 누락", ('("mobile", 390, 844, True)', '("mobile", 390, 844, False)'))
add("006d", "006", "스크립트 비활성이 navigate 뒤",
    ("            await driver.disable_scripts()\n        except Exception as exc:", "        except Exception as exc:"),
    ("        raw = await driver.open(url, width, height, mobile)\n",
     "        raw = await driver.open(url, width, height, mobile)\n        await driver.disable_scripts()\n"))
add("006e", "006", "보고서 내용으로 파일 이름 생성",
    ('file = f"{name}-{index + 1:02d}.png"',
     'file = f"{name}-{(screens.parent / \'draft\' / \'report.html\').read_text()[19:27]}-{index + 1:02d}.png"'))
add("006f", "006", "심볼릭 링크를 따라감(검사 전부 제거)",
    ('    if draft.is_symlink() or not draft.is_file():\n        return "draft_not_regular_file"\n    if not draft.resolve().is_relative_to(job_dir.resolve()):\n        return "draft_outside_job_dir"\n    return None',
     "    return None"))
add("006g", "006", "폴더 심볼릭 링크(해석 경로 검사) 제거",
    ('    if not draft.resolve().is_relative_to(job_dir.resolve()):\n        return "draft_outside_job_dir"\n', ""))
add("007a", "007", "색인 키 이름 변경",
    ('"preview_sha256": None,', '"preview_hash": None,'),
    ('index["preview_sha256"] =', 'index["preview_hash"] ='))
add("007b", "007", "시간대 없는 시각", ("datetime.now(_KST).isoformat", "datetime.now().isoformat"))
add("007c", "007", "입력 JSON 해시를 preview_sha256에 기록",
    ('index["preview_sha256"] = _sha256(draft.read_bytes())',
     'index["preview_sha256"] = _sha256((draft.parent / "report-input.json").read_bytes())'))
add("007d", "007", "타일 해시를 메모리 사본에서 계산",
    ('"bytes": len(written), "sha256": _sha256(written)', '"bytes": len(png), "sha256": _sha256(png)'))
add("007e", "007", ">= 로 넘침 판정", ('raw["scroll_width"] > raw["client_width"]', 'raw["scroll_width"] >= raw["client_width"]'))
add("008a", "008", "타일 상한 없음", ("if count > TILE_CAP:", "if False:"))
add("008a2", "008", "상한 경계 오류(>=)", ("if count > TILE_CAP:", "if count >= TILE_CAP:"))
add("008b", "008", "상한 초과 때 앞 TILE_CAP개만 저장",
    ('            vp["status"] = "too_tall"\n            return', "            count = TILE_CAP"))
add("008c", "008", "예산 미적용", ("timeout=CAPTURE_BUDGET_SEC", "timeout=None"))
add("008d", "008", "타일 크기 상한 없음", ("if len(png) > MAX_TILE_BYTES:", "if False:"))
add("008d2", "008", "크기 경계 오류(>=)", ("if len(png) > MAX_TILE_BYTES:", "if len(png) >= MAX_TILE_BYTES:"))
add("008e", "008", "임시 프로필을 성공 경로에서만 삭제",
    ("        shutil.rmtree(profile, ignore_errors=True)\n\n\ndef _finish", "        pass\n\n\ndef _finish"),
    ("            current[:] = []\n    finally:", "            current[:] = []\n        shutil.rmtree(profile, ignore_errors=True)\n    finally:"))
add("008f", "008", "실패 뷰포트의 부분 타일 미정리",
    ("        for stale in screens.glob(f\"{vp['name']}-*.png\"):\n            stale.unlink(missing_ok=True)\n", ""))
add("002b", "002", "브라우저 프로세스 하나만 종료(그룹 아님)", ("os.killpg(proc.pid, signal.SIGKILL)", "os.kill(proc.pid, signal.SIGKILL)"))
add("002c", "002", "취소 때 브라우저를 정리하지 않음",
    ("        if proc is not None:\n            _kill_group(proc)\n", ""))
add("009a", "009", "브라우저 인자에 비허용 문자열 추가", ('        "about:blank",\n    ]', '        "about:blank",\n        "--evil-flag",\n    ]'))
add("009b", "009", "스크립트 비활성 호출 누락",
    ("            await driver.disable_scripts()\n        except Exception as exc:", "        except Exception as exc:"))
add("009c", "009", "네트워크 차단 누락", ("            await driver.block_network(list(BLOCK_ALL_PATTERNS))\n", ""))
add("009d", "009", "디버깅 주소 0.0.0.0", ('        "about:blank",\n    ]', '        "--remote-debugging-address=0.0.0.0",\n        "about:blank",\n    ]'))
add("009e", "009", "글꼴 호스트 예외 허용",
    ('BLOCK_ALL_PATTERNS = ("*",)', 'BLOCK_ALL_PATTERNS = ("*", "-cdn.jsdelivr.net", "-fonts.googleapis.com")'))
add("010a", "010", "환경 변수 무시", ("configured = environ.get(ENV_BROWSER)", "configured = None"))
add("010b", "010", "잘못된 변수일 때 캐시로 폴백",
    ('        return None, "none", "browser_env_not_executable"\n', "        pass\n"))
add("010c", "010", "후보 없음일 때 예외", ('    return None, "none", "browser_not_found"', '    raise FileNotFoundError("none")'))
add("010d", "010", "빌드 번호를 문자열로 비교", ("int(match.group(1))", "match.group(1)"))
add("010d2", "010", "첫 후보를 선택(최고 빌드 아님)", ("(best is None or int(match.group(1)) > best[0])", "best is None"))
add("010e", "010", "PATH 탐색",
    ('    return None, "none", "browser_not_found"',
     '    found = shutil.which("chromium", path=environ.get("PATH"))\n    if found:\n        return Path(found), "playwright_cache", None\n    return None, "none", "browser_not_found"'))

original = SRC.read_text(encoding="utf-8")
digest = hashlib.sha256(original.encode()).hexdigest()
only = sys.argv[2:]
try:
    for i, ac, desc, pairs in M:
        if only and i not in only:
            continue
        text = original
        for old, new in pairs:
            if text.count(old) < 1:
                print(f"{i} | {ac} | 변이 적용 실패(old 없음): {old[:50]!r}")
                break
            text = text.replace(old, new)
        else:
            SRC.write_text(text, encoding="utf-8")
            r = subprocess.run([PY, "-m", "pytest", TEST, "-q", "--no-header", "-p", "no:cacheprovider",
                                "--maxfail=50"], cwd=WT, capture_output=True, text=True, timeout=600)
            failed = [ln.split("::")[1].split(" ")[0] for ln in r.stdout.splitlines() if ln.startswith("FAILED")]
            print(f"{i} | AC-{ac} | {desc} | RED={'YES' if failed else 'NO(미관측)'} failed={len(failed)} | {', '.join(failed)[:200]}", flush=True)
        SRC.write_text(original, encoding="utf-8")
finally:
    SRC.write_text(original, encoding="utf-8")
    print("restored-sha-match:", hashlib.sha256(SRC.read_bytes()).hexdigest() == digest)
