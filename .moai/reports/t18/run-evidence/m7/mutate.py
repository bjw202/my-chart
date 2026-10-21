"""M7 reversal-variant runner (evidence only, not shipped).

Applies one temporary mutation at a time to the shipped sources, runs the relevant pytest selection,
records which tests went RED, and restores the file byte-for-byte. Run from the worktree root:
    python3 -B .moai/state/verify/t18-m7/mutate.py [id-prefix ...]
"""

import os
import re
import subprocess
import sys
from pathlib import Path

RUN = ".moai/state/verify/t18-m7/run.sh"
SHOT = "backend/services/goose_screenshot.py"
REV = "backend/services/goose_review.py"
INSTR = "backend/goose_harness_src/harness-instructions.md"
SHOT_TESTS = ["backend/tests/test_goose_screenshot.py"]
REV_TESTS = ["backend/tests/test_goose_review.py", "backend/tests/test_goose_job_service.py", "-k", "air6_014"]
HARNESS_TESTS = ["backend/tests/test_goose_harness.py"]

M = []  # (id, file, old, new, tests)


def mut(mid, path, old, new, tests):
    M.append((mid, path, old, new, tests))


# --- AC-AIR6-009 (f)-(q) -------------------------------------------------------------------------------------
mut("009-f1 drop --proxy-server", SHOT, '    "--proxy-server=127.0.0.1:1",\n', "", SHOT_TESTS)
mut("009-f2 drop --proxy-bypass-list", SHOT, '    "--proxy-bypass-list=<-loopback>",\n', "", SHOT_TESTS)
mut("009-f3 drop --host-resolver-rules", SHOT, '    "--host-resolver-rules=MAP * ~NOTFOUND",\n', "", SHOT_TESTS)
mut("009-g Popen without env", SHOT, "        env=build_env(environ),\n", "", SHOT_TESTS)
mut("009-h Fetch.enable only on page session", SHOT,
    '        await self._call("Fetch.enable", _FETCH_ALL, session)\n', "", SHOT_TESTS)
mut("009-i runIfWaitingForDebugger before Fetch.enable", SHOT,
    '        await self._call("Fetch.enable", _FETCH_ALL, session)\n'
    '        await self._call("Target.setAutoAttach", _AUTO_ATTACH, session)\n'
    '        await self._call("Runtime.runIfWaitingForDebugger", None, session)\n',
    '        await self._call("Runtime.runIfWaitingForDebugger", None, session)\n'
    '        await self._call("Fetch.enable", _FETCH_ALL, session)\n'
    '        await self._call("Target.setAutoAttach", _AUTO_ATTACH, session)\n', SHOT_TESTS)
mut("009-j continueRequest for everything", SHOT,
    '        return "continue" if url.startswith("data:") else "fail"', '        return "continue"', SHOT_TESTS)
mut("009-k only http(s) failed, file:// passes", SHOT,
    '        return "continue" if url.startswith("data:") else "fail"',
    '        return "fail" if url.startswith(("http:", "https:")) else "continue"', SHOT_TESTS)
mut("009-l1 draft compare by prefix", SHOT, "if url == self._draft_url:", "if url.startswith(self._draft_url):", SHOT_TESTS)
mut("009-l2 draft compare case-insensitive", SHOT, "if url == self._draft_url:",
    "if url.lower() == self._draft_url.lower():", SHOT_TESTS)
mut("009-l3 draft compare by substring", SHOT, "if url == self._draft_url:", "if self._draft_url in url:", SHOT_TESTS)
mut("009-m1 no CSP header", SHOT,
    '            {"name": "Content-Security-Policy", "value": DOCUMENT_CSP},\n', "", SHOT_TESTS)
mut("009-m2 CSP without frame-src", SHOT, "\"frame-src 'none'; object-src 'none'; form-action 'none'; base-uri 'none'\"",
    "\"object-src 'none'; form-action 'none'; base-uri 'none'\"", SHOT_TESTS)
mut("009-m3 CSP without object-src", SHOT, "\"frame-src 'none'; object-src 'none'; form-action 'none'; base-uri 'none'\"",
    "\"frame-src 'none'; form-action 'none'; base-uri 'none'\"", SHOT_TESTS)
mut("009-n served body differs from disk bytes", SHOT, "base64.b64encode(self._draft_body)",
    "base64.b64encode(self._draft_body + b' ')", SHOT_TESTS)
mut("009-o data: also failed", SHOT, '        return "continue" if url.startswith("data:") else "fail"', '        return "fail"', SHOT_TESTS)
mut("009-p handler error swallowed", SHOT, "            self._broken = True\n            raise\n", "            pass\n", SHOT_TESTS)
mut("009-q1 Fetch.enable error ignored (page session)", SHOT,
    '        await self._call("Fetch.enable", _FETCH_ALL)\n',
    '        try:\n            await self._call("Fetch.enable", _FETCH_ALL)\n        except CaptureError:\n            pass\n', SHOT_TESTS)
mut("009-q2 Fetch.enable error ignored (attached target)", SHOT,
    '        await self._call("Fetch.enable", _FETCH_ALL, session)\n',
    '        try:\n            await self._call("Fetch.enable", _FETCH_ALL, session)\n        except CaptureError:\n            pass\n',
    SHOT_TESTS)
mut("009-r isolate() not called", SHOT, "            await driver.isolate(url, draft_bytes)", "            pass  # await driver.isolate(url, draft_bytes)",
    SHOT_TESTS)

# --- AC-AIR6-014 (n)-(q) -------------------------------------------------------------------------------------
mut("014-n review/ not emptied", REV, "        if not _empty_review(job_dir):\n            return False\n", "", REV_TESTS)
mut("014-o symlinks followed", REV, "    if path.is_symlink() or not path.is_dir():\n        path.unlink()\n",
    "    if path.is_symlink():\n        target = path.resolve()\n"
    "        shutil.rmtree(target) if target.is_dir() else target.unlink()\n        path.unlink()\n"
    "    elif not path.is_dir():\n        path.unlink()\n", REV_TESTS)
mut("014-p review delete failure ignored", REV, "        if not _empty_review(job_dir):\n            return False\n",
    "        try:\n            _empty_review(job_dir)\n        except OSError:\n            pass\n", REV_TESTS)
mut("014-q context.json not written", REV,
    "    (review / CONTEXT_NAME).write_text(json.dumps(context, ensure_ascii=False, indent=2), encoding=\"utf-8\")\n",
    "", REV_TESTS)
mut("014-x review/ itself a symlink is followed", REV, "    if review.is_symlink() or review.is_file():\n        review.unlink()\n",
    "    if review.is_file():\n        review.unlink()\n", REV_TESTS)

# --- AC-AIR6-013 (e) + (b) -----------------------------------------------------------------------------------
INSTR_TEXT = Path(INSTR).read_text(encoding="utf-8")
LINE_1011 = next(line for line in INSTR_TEXT.splitlines(keepends=True) if line.startswith("   - 10-11."))
mut("013-e delete rule 10-11", INSTR, LINE_1011.rstrip("\n"), "", HARNESS_TESTS)
mut("013-b instruction edited without regenerating the manifest", INSTR, "(감수에 필요하지 않다)", "(감수에 필요하지 않다 .)", HARNESS_TESTS)


def run(tests):
    proc = subprocess.run([RUN, *tests, "-q", "-x" if False else "-q"], capture_output=True, text=True)
    out = proc.stdout + proc.stderr
    failed = re.findall(r"^FAILED (\S+)", out, re.M)
    tail = [ln for ln in out.splitlines() if re.match(r"^\d+ (passed|failed).* in [\d.]+s", ln)][-1:]
    return failed, tail[0] if tail else out[-200:]


def main() -> None:
    want = sys.argv[1:]
    for mid, path, old, new, tests in M:
        if want and not any(mid.startswith(w) for w in want):
            continue
        original = Path(path).read_bytes()
        text = original.decode("utf-8")
        if text.count(old) != 1:
            print(f"## {mid}\n   !! old string matched {text.count(old)} times; skipped")
            continue
        try:
            Path(path).write_text(text.replace(old, new), encoding="utf-8")
            failed, tail = run(["backend/tests/test_goose_screenshot_live.py"] if os.environ.get("M7_LIVE") else tests)
        finally:
            Path(path).write_bytes(original)
        assert Path(path).read_bytes() == original
        print(f"## {mid}\n   {tail}  ->  RED: {len(failed)}")
        for name in failed:
            print(f"   - {name.split('::', 1)[1]}")
        sys.stdout.flush()


main()
