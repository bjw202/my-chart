# Codex CLI 호출 레퍼런스

`backend/services/codex_cli_runner.py` 구현자를 위한 실행 스펙 + 프롬프트 템플릿. 이 문서만 보면 어댑터를 바로 작성할 수 있도록 정리.

## 설치·인증 현황 (조사 시점)

```
$ which codex
/Users/byunjungwon/.nvm/versions/node/v24.12.0/bin/codex

$ codex --version
codex-cli 0.121.0

$ codex login status
# 기대: "Logged in using ChatGPT"
```

환경변수 `OPENAI_API_KEY` **불필요**. 구독 계정 기반.

## 최종 argv

```
codex exec
  --skip-git-repo-check
  --sandbox read-only
  -C <staging_sources_dir>
  --output-last-message <staging_sources_dir>/codex_research.md
  --color never
  --json
  "<prompt_text>"
```

### 플래그 설명

| 플래그 | 용도 |
|---|---|
| `--skip-git-repo-check` | `/tmp/analysis_*` 는 git repo 아님 — 이 검사를 건너뛰어야 실행 가능 |
| `--sandbox read-only` | Codex 가 로컬 파일을 쓰지 않도록 차단. `--output-last-message` 경로만 쓰기 허용됨 |
| `-C <dir>` | Codex cwd 고정. 스테이징 디렉터리로 지정해 안전성 확보 |
| `-o, --output-last-message <FILE>` | Codex 의 마지막 assistant 메시지를 이 파일에 저장. stdout JSONL 파싱 불필요 |
| `--color never` | ANSI 이스케이프 제거 (stderr 드레인 시 깔끔) |
| `--json` | 진단용 JSONL 이벤트를 stdout 에 기록 (web_search 도구 호출 이벤트 로깅 가능) |

### argv 빌더 (파이썬 예시)

```python
def build_codex_argv(staging_sources_dir: Path, prompt_text: str) -> list[str]:
    output_md = staging_sources_dir / "codex_research.md"
    return [
        "codex", "exec",
        "--skip-git-repo-check",
        "--sandbox", "read-only",
        "-C", str(staging_sources_dir),
        "--output-last-message", str(output_md),
        "--color", "never",
        "--json",
        prompt_text,
    ]
```

## 프롬프트 템플릿

Codex 는 system prompt 분리 인자가 없다 (`codex exec` 는 단일 prompt). 역할/제약을 prompt 본문 앞단에 포함.

```python
CODEX_RESEARCH_PROMPT = """\
너는 한국 주식 스윙 트레이딩 분석가다. 다음 종목에 대해 웹을 검색해
최근 3~6개월 범위의 기술적/수급/뉴스 정보를 수집하고 한국어 Markdown
보고서를 작성하라.

종목: {stock_name}({code}) — 한국 KOSPI/KOSDAQ {code}

출력 섹션:
## 요약  (3~5 문장)
## 가격·거래량 동향  (최근 가격대, 거래량 스파이크, 추세)
## 기술적 지표  (이동평균, RSI, MACD 등 — 구체 수치)
## 뉴스·이벤트  (최근 공시/실적/업계 이슈, 출처 URL 필수)
## 리스크  (3~5 항목)
## 스윙 진입/청산 관점  (지지·저항·손절 시나리오)

제약:
- 반드시 웹 검색 결과를 근거로 하며, 주장 옆에 [n] 형식 각주 + 맨 끝
  참고문헌 섹션에 URL 나열.
- 학습 데이터만으로 추정한 가격/뉴스는 금지.
- 응답은 보고서 본문만. 메타 설명/사과/도구 사용 설명 금지.
"""
```

format 주입: `CODEX_RESEARCH_PROMPT.format(stock_name=stock_name, code=code)`.

## 어댑터 시그니처 (제안)

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class CodexResult:
    success: bool
    markdown_path: Path | None
    char_count: int  # 0 if failed
    error_type: str | None  # "timeout" | "exit_error" | "binary_missing" | "empty_output" | "auth"
    error_message: str | None
    duration_ms: int


async def run_codex_research(
    *,
    code: str,
    stock_name: str,
    staging_sources_dir: Path,
    timeout: float = 180.0,
    _cmd_override: list[str] | None = None,   # 테스트 전용 fake 바이너리 주입
) -> CodexResult:
    """Codex CLI 를 subprocess 로 실행해 codex_research.md 를 작성한다.

    Args:
        code: 종목 코드 (6자리).
        stock_name: 종목명.
        staging_sources_dir: 스테이징 디렉터리 내부 sources/ 경로.
        timeout: 단일 호출 타임아웃 (초).
        _cmd_override: 테스트에서 fake bash wrapper 경로 주입.

    Returns:
        CodexResult — success=True 이면 markdown_path 와 char_count 유효.
    """
```

## 에러 케이스 분류

| 감지 | error_type | 발생 조건 |
|---|---|---|
| `FileNotFoundError` on `create_subprocess_exec` | `binary_missing` | codex 가 PATH 에 없음 |
| `asyncio.TimeoutError` | `timeout` | timeout 초과 — terminate → kill 2단계 정리 |
| `returncode != 0` | `exit_error` | Codex 비정상 종료 — stderr 마지막 500자를 `error_message` 에 포함 |
| 출력 파일 미존재 or 크기 0 | `empty_output` | Codex 가 메시지를 쓰지 않음 |
| stderr 에 `not logged in` 문구 | `auth` | ChatGPT 세션 만료 |
| `asyncio.CancelledError` | (re-raise) | 부모 태스크 취소 시 terminate → kill 후 전파 |

## subprocess 실행 패턴 (참고: `claude_cli_streamer.py:110-202`)

```python
import asyncio
import time
from pathlib import Path

async def _terminate_proc(proc: asyncio.subprocess.Process, *, grace: float = 2.0) -> None:
    """terminate → kill 2단계. claude_cli_streamer.py:110-131 패턴 복제."""
    if proc.returncode is not None:
        return
    try:
        proc.terminate()
        await asyncio.wait_for(proc.wait(), timeout=grace)
    except (asyncio.TimeoutError, ProcessLookupError):
        try:
            proc.kill()
            await proc.wait()
        except ProcessLookupError:
            pass


async def _drain_stderr(stderr: asyncio.StreamReader | None, *, max_lines: int = 50) -> list[str]:
    """stderr 마지막 N 라인만 보관. claude_cli_streamer.py:194-202 패턴."""
    if stderr is None:
        return []
    buf: list[str] = []
    try:
        async for raw in stderr:
            line = raw.decode("utf-8", errors="replace").rstrip()
            buf.append(line)
            if len(buf) > max_lines:
                buf.pop(0)
    except Exception:
        pass
    return buf
```

## 테스트 전용 fake codex 스크립트

`backend/tests/test_codex_cli_runner.py` 에서 `_cmd_override` 로 주입할 bash wrapper. `tmp_path` 안에 생성하고 `chmod +x`.

### 성공 케이스 wrapper

```bash
#!/bin/bash
# fake_codex_success.sh — $1..$N 중 --output-last-message 다음 인자에 md 쓰기
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-last-message)
      echo "# 테스트 보고서" > "$2"
      shift 2
      ;;
    *) shift ;;
  esac
done
exit 0
```

### 타임아웃 wrapper

```bash
#!/bin/bash
sleep 300
```

### empty_output wrapper

```bash
#!/bin/bash
exit 0  # 아무 파일도 쓰지 않음
```

### exit_error wrapper

```bash
#!/bin/bash
echo "codex: simulated failure" >&2
exit 7
```

## 스모크 커맨드 (실 Codex, Step 7.1)

```bash
# 웹 검색 기본 활성 여부 판정
codex exec --json --skip-git-repo-check \
  "오늘 2026-04-23 삼성전자(005930) 종가를 웹에서 검색해 URL과 함께 한국어로 알려줘" \
  2>/dev/null \
  | jq 'select(.type | contains("tool_call") or contains("web_search"))'

# 기대:
# {"type": "tool_call", "name": "web_search", ...}
# 또는 유사한 이벤트. 아무 이벤트도 안 나오면 웹 검색 기본 비활성 — Risks #1 진입.
```

### 2차 계획 (웹 검색 기본 비활성일 때)

`~/.codex/config.toml` 에 MCP 서버 등록:

```toml
[[mcp_servers]]
name = "brave-search"
command = "npx"
args = ["-y", "@modelcontextprotocol/server-brave-search"]
env = { BRAVE_API_KEY = "${BRAVE_API_KEY}" }
```

그리고 Codex 프롬프트에 "brave-search 도구를 사용해 웹 검색을 수행하라" 명시.

이 경우 `BRAVE_API_KEY` 는 이미 `.env` 에 있다 (my_chart 기존 5개 소스 중 하나가 Brave). 하지만 Codex 는 `~/.codex/config.toml` 의 `env` 를 shell env 에서 읽으므로 서비스 기동 전 export 필요.

## 참고: Codex 플래그 전체

```
$ codex exec --help
Usage: codex exec [OPTIONS] [PROMPT]
       codex exec [OPTIONS] <COMMAND> [ARGS]

Commands:
  resume  Resume a previous session by id
  review  Run a code review against the current repository
  help    Print this message

Options:
  -c, --config <key=value>         Override config value
      --enable <FEATURE>           Enable a feature
      --disable <FEATURE>          Disable a feature
  -i, --image <FILE>...            Attach images
  -m, --model <MODEL>              Model override
      --oss                        Use open-source provider
  -p, --profile <CONFIG_PROFILE>   Named profile from config.toml
  -s, --sandbox <SANDBOX_MODE>     read-only | workspace-write | danger-full-access
      --dangerously-bypass-approvals-and-sandbox
      --skip-git-repo-check
      --json                       Emit JSONL events to stdout
      --color <WHEN>               always | auto | never
  -o, --output-last-message <FILE>
  -C, --cd <DIR>                   cwd override
      --add-dir <DIR>              Additional writable dir
      --include-plan-tool
      --output-schema <FILE>       JSON schema for structured output
  -h, --help                       Print help
```

`--include-plan-tool` 은 Codex 의 plan 도구 활성화. 심층 리서치에는 무관 (우리 태스크는 단일 보고서 작성).
`--output-schema` 는 JSON 구조화 응답 강제. `codex_research.md` 는 자연어 이므로 미사용.
