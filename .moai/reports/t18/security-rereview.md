# Independent security re-review: SPEC-AI-REPORT-006 screenshot pipeline hardening (HEAD bc56cc7)

Scope: diff f0926e2..bc56cc7 (goose_screenshot.py, goose_review.py, harness-instructions.md, job service MX tags), plus full read of goose_screenshot.py and the admissibility path.
Method: new PoCs under `.moai/state/verify/t18-resec/` (lib.py, v1-v5.py, outputs `*.out`, tiles under `jobs/*/screens/`). A loopback listener recorded any request leaving the browser. Every vector ran twice: with the real document CSP (layer B) and with the CSP relaxed to `default-src *` (to test layers A1/A2 alone). Tiles were viewed for rendered local-file text. No tracked file was modified; HARNESS_DIR was always under t18-resec/.

## Verdict: PASS

No verified bypass of S1 (file:// content) or S2 (any outbound request) through the browser. No unresolved HIGH/CRITICAL. Both previous HIGH findings (file:// iframe rendering; loopback/network requests from the draft) are closed: layer A1 (Fetch interception of every target, only the exact draft URL and `data:` allowed) holds on its own even with the CSP removed, and layer B (CSP) is redundant on top of it.

## Findings

### F1 - MEDIUM - HYPOTHESIS (code-read + config-read, not run against a live `claude`)
Review-session rule 10-11 is wording only; the permissions still allow the dangerous tools.
- `backend/goose_harness_src/claude-settings.json` allows `WebSearch`, `WebFetch`, `Agent`, `Skill`, `Read(./**)`, `Write(./runs/**)`. `backend/services/goose_runner.py:642` (`run_review`) reuses `build_invocation`, i.e. the same settings, for the review session. Rule 10-11 (harness-instructions.md) merely tells the model not to call them.
- A prompt-injected reviewer (injection via report text or text inside a tile, S3) can still call WebFetch/WebSearch with data read from any `runs/**` file (other jobs' ledgers, dart/, naver/) in the URL, or write to `runs/<other job>/...` (the server only tracks Write/Edit on this job's draft/ and screens/, `judged_writes`).
- Fix: give the review invocation a stricter settings file or `--disallowedTools WebSearch WebFetch Agent Skill`, and narrow Write to `runs/<job_id>/audit-review.json`, `runs/<job_id>/review/**`, `runs/<job_id>/final/**`. Treat the prompt rule as a second line only.

### F2 - LOW - VERIFIED
Draft hardlink to an outside file passes `_check_draft` and is rendered as HTML (S1 via hardlink).
- `goose_screenshot.py:378-384`: checks only `is_symlink()`, `is_file()` and `resolve()` inside job dir; a hardlink has none of those properties.
- Repro: `os.link(secret.txt, jobs/hardlink_secret/draft/report.html)`, then capture. Result `complete`, desktop-01.png shows `TOP-SECRET-LOCAL-FILE-CONTENT-12345` (same with `/etc/hosts` as `hardlink_etc_hosts`). Also hashed as the preview.
- Exploitability today is low: the goose session's Bash is limited to two Python scripts (claude-settings.json), so it cannot run `ln`; a draft session that can already `Read(./**)` can copy text into the HTML anyway. Hardlink matters only if some other process or a script bug can create links under runs/.
- Fix: open with `os.open(..., O_NOFOLLOW)` and `fstat`, reject `st_nlink != 1` (and non-regular), then read from the fd (also removes the TOCTOU below).

### F3 - LOW - HYPOTHESIS (not reproduced)
TOCTOU between `_check_draft` and `draft.read_bytes()` (goose_screenshot.py:428-432). If anything can swap `draft/report.html` for a symlink after the check, the target is read, hashed and served as the document. Since the first session has exited before capture and cannot create symlinks, practical risk is low. Same fix as F2 (single fd).

### F4 - LOW - VERIFIED (S6)
DevTools port is unauthenticated for any local process/user. `lsof` shows `127.0.0.1:<port> (LISTEN)` only (not exposed off-host); `curl /json/version` works and `PUT /json/new?file:///etc/hosts` creates a target (output in v4.out). On a single-user dev box this is accepted; on a shared host another local user can drive the browser as the server user for up to the 60 s budget (read any file via a new target + screenshot). The draft itself cannot reach it (loopback blocked by proxy flags + Fetch; listener got 0 hits).
- Fix: use `--remote-debugging-pipe` (fd transport) instead of a TCP port, or at minimum document the shared-host limitation.

### F5 - LOW - VERIFIED (availability, fail-closed)
- A planted `runs/<job>/screens` regular file makes `capture()` raise `FileExistsError` (`rmtree(ignore_errors=True)` silently fails, `mkdir` raises; v5.out). The job service swallows it (goose_job_service.py:387-389) and prepare_review then sees no index, so the final is not admitted (fail closed). A planted `screens/` directory with forged index/tiles is removed by capture (verified: only server files remain).
- Meta-refresh to a blocked URL (http/file) hangs until the 60 s budget and ends `budget_exceeded`; a draft of 40 MB / 200k nested divs ends in `TimeoutError`/`budget_exceeded` (41-60 s). The budget is enforced and the process group and temp profile were cleaned every time (0 leftover chrome processes after each run). So a hostile draft can only deny itself a final, at the cost of up to 60 s of server time.
- Fix (optional): `if screens.is_symlink() or screens.is_file(): screens.unlink()` before rmtree; cap draft size (for example 5 MB) before serving.

### F6 - INFO
- S5 verified: with `SECRET_TEST_TOKEN` and `ANTHROPIC_API_KEY` set in the parent, the browser child env (via `ps -E`) contained only HOME, LANG, PATH, SHELL, TMPDIR, USER.
- Content placed off-screen (`left:-99999px`) or hidden is not in tiles (reviewer coverage gap, not a leak).
- Meta refresh to `data:` did not replace the document (tile shows original). `data:` frames render only when CSP is relaxed; with the real CSP they are blocked.
- S9: `_empty_review` removes files, directories and symlinks in `review/` without following links; reviewed by code only (no live planted-file run, see below).

## Vectors tested with zero listener hits and no local-file text in tiles (strict and CSP-relaxed)
iframe/object/embed/frame/frameset to file:// and http; meta refresh (http, file, data); link preconnect/prefetch/preload/prerender/modulepreload/stylesheet/icon/manifest/next/alternate; CSS `@import`, `@font-face`, `url()`, `image-set`, `mask`, `border-image`, `cursor`, `content`, `list-style`; img/srcset/picture/video poster/audio/track/input image/table background; SVG use/image/foreignObject iframe; SVG-as-data-image with external hrefs; forms, formaction, `a ping`, `target=_blank`; srcdoc with nested file:// frame; about:blank, javascript:, blob:, filesystem:, view-source:, chrome:, data: frames; `data:` iframe/object containing file:// and http children; `data:` CSS importing file://; base tag; protocol-relative, `[::1]` and `localhost` URLs; script fetch/XHR/WebSocket/EventSource/sendBeacon/window.open/Worker/serviceWorker/location; event handlers; speculationrules; `javascript:` URLs; self-referencing frame/stylesheet. In the relaxed-CSP runs the page scripts did not execute (tile shows `NOSCRIPT`, not `SCRIPT-RAN`), so `Emulation.setScriptExecutionDisabled` also holds. Existing poc1.py and poc2.py: poc2 `HITS: []`, poc1 tile shows no secret text.

## NOT tested
- Real `claude -p` review session behaviour (prompt injection through tiles, F1 exploitation, WebFetch exfiltration); tools restrictions were read from config only.
- `_empty_review`/`_delete_planted` against live planted files (symlinked review/, nested dirs, permission-locked entries) and the full `evaluate_core` conditions; only read.
- Race/TOCTOU swap between check and read (F3), free-port race on the DevTools port, multi-user host scenario.
- Other Chrome builds (only chromium_headless_shell-1243 / HeadlessChrome 153 on macOS arm64), Linux behaviour, `--proxy-server`/host-resolver flags in isolation (A1 alone was sufficient in all tests).
- Real internet (not needed), user-gesture-driven navigations (no input is ever dispatched), GPU/renderer-exploit class bugs.
- Job service end-to-end (integrity recheck, receipt, final selection) with a hostile draft.
