# 단일 명령으로 다중 프로세스 제어하기

> 주제: FastAPI + React 두 서버를 하나의 명령/클릭으로 실행/종료하기

---

## 목차

1. [선결 개념: 왜 단순 순차 실행이 안 되는가?](#1-선결-개념)
2. [핵심 원리: 프로세스 그룹과 신호](#2-핵심-원리)
3. [방법 1: Makefile](#3-방법-1-makefile)
4. [방법 2: Shell 스크립트 (dev.sh)](#4-방법-2-shell-스크립트)
5. [방법 3: macOS 아이콘 더블클릭 (.command)](#5-방법-3-macos-command-파일)
6. [비교 및 선택 기준](#6-비교-및-선택-기준)
7. [함정과 주의사항](#7-함정과-주의사항)
8. [심화 학습 과제](#8-심화-학습-과제)
9. [핵심 요약 체크리스트](#9-핵심-요약-체크리스트)

---

## 1. 선결 개념

### 단순 순차 실행의 문제점

```bash
# 이렇게 하면 안 된다
uvicorn backend.main:app --reload --port 8000 &   # 백그라운드
cd frontend && pnpm dev                            # 포그라운드
```

여기서 `Ctrl+C`를 누르면:
- `pnpm dev`는 종료된다 (포그라운드 프로세스라 SIGINT를 받음)
- `uvicorn`은 **살아있는 좀비**가 된다 (백그라운드에서 신호를 못 받음)

```bash
# 확인 방법
lsof -i :8000   # 포트 8000을 점유한 프로세스 확인
# PID를 확인 후 수동으로 kill PID 해야 함
```

---

## 2. 핵심 원리

### 2.1 프로세스 그룹 (Process Group)

```
터미널 (TTY)
  └── Shell (bash/zsh)  ← PGID 리더
        ├── uvicorn     ← 같은 PGID 공유
        └── pnpm dev    ← 같은 PGID 공유
```

`Ctrl+C`는 `SIGINT`를 **포그라운드 프로세스 그룹 전체**에 보낸다.
`&`로 백그라운드에 보낸 프로세스는 이 그룹에서 분리된다.

### 2.2 Unix 신호 (Signal)

| 신호      | 숫자 | 의미                         | 발생 방법               |
|-----------|------|------------------------------|------------------------|
| `SIGINT`  | 2    | 인터럽트 (사용자 요청 종료)  | Ctrl+C                 |
| `SIGTERM` | 15   | 정상 종료 요청               | `kill <PID>`           |
| `SIGKILL` | 9    | 강제 종료 (무시 불가)        | `kill -9 <PID>`        |
| `SIGHUP`  | 1    | 터미널 연결 끊김             | 터미널 창 닫기         |
| `EXIT`    | -    | 스크립트 종료 시 (bash 확장) | 스크립트 자연 종료 포함|

### 2.3 `trap` 명령어

```bash
trap '실행할_명령' 신호_목록
```

`trap`은 신호를 **가로채서** 원하는 함수나 명령을 실행하게 해준다.

```bash
# 예시: SIGINT 발생 시 "종료합니다" 출력
trap 'echo "종료합니다"' SIGINT
```

### 2.4 `$!` (최근 백그라운드 PID)

```bash
uvicorn backend.main:app --reload &
BACKEND_PID=$!   # 방금 실행한 백그라운드 프로세스의 PID
echo $BACKEND_PID  # 예: 12345
```

### 2.5 `wait` 명령어

```bash
wait            # 모든 백그라운드 자식 프로세스가 끝날 때까지 대기
wait $PID       # 특정 PID 프로세스가 끝날 때까지 대기
```

`wait`가 없으면 스크립트가 즉시 종료되어 백그라운드 프로세스들도 죽는다.

---

## 3. 방법 1: Makefile

### 사용법

```bash
make dev   # 두 서버 동시 시작
# Ctrl+C   # 두 서버 동시 종료
```

### 구현 (프로젝트 루트에 `Makefile` 생성)

```makefile
.PHONY: dev

dev:
	@echo "두 서버 시작..."
	@trap 'kill %1 %2' INT; \
	 (source venv/bin/activate && uvicorn backend.main:app --reload --port 8000) & \
	 (cd frontend && pnpm dev) & \
	 wait
```

### 원리 설명

- `trap 'kill %1 %2' INT` → SIGINT(Ctrl+C) 발생 시 작업 1번(%1), 2번(%2) kill
- `%1`, `%2` → bash의 **작업 번호(job number)**, `$!`와 다름
- `&` 사이에 `wait`를 두어 두 프로세스가 모두 끝날 때까지 대기

### 장점

- 단순하고 표준적
- Make가 설치된 모든 Unix 환경에서 동작
- 팀 프로젝트에서 관례적으로 사용

---

## 4. 방법 2: Shell 스크립트

### 사용법

```bash
chmod +x dev.sh   # 최초 1회
./dev.sh          # 실행
# Ctrl+C          # 종료
```

### 구현 (`dev.sh`)

```bash
#!/bin/bash
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
    echo ""
    echo "종료 중..."
    [ -n "$BACKEND_PID" ]  && kill "$BACKEND_PID"  2>/dev/null
    [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null
    wait
    echo "두 서버 모두 종료됨"
    exit 0
}

trap cleanup SIGINT SIGTERM

# 스크립트 위치 기준으로 디렉토리 이동 (중요!)
cd "$(dirname "$0")"

echo "[백엔드] uvicorn 시작 (포트 8000)..."
source venv/bin/activate
uvicorn backend.main:app --reload --port 8000 &
BACKEND_PID=$!

echo "[프론트엔드] Vite 개발 서버 시작..."
cd frontend && pnpm dev &
FRONTEND_PID=$!

echo ""
echo "두 서버가 실행 중입니다. Ctrl+C로 종료하세요."
echo "  백엔드 PID : $BACKEND_PID"
echo "  프론트 PID : $FRONTEND_PID"

wait
```

### 원리 설명

- `[ -n "$VAR" ]` → 변수가 비어있지 않은지 확인 (PID가 없으면 kill 시도 안 함)
- `2>/dev/null` → kill 오류 메시지 숨김 (이미 죽은 프로세스 오류 무시)
- `cd "$(dirname "$0")"` → **매우 중요**: 어디서 실행하든 스크립트 위치를 기준으로 경로를 잡음

---

## 5. 방법 3: macOS .command 파일

### 핵심 특징

macOS는 `.command` 확장자 파일을 **Finder에서 더블클릭 가능한 터미널 스크립트**로 인식한다.
터미널 명령 없이 Finder에서 직접 실행 가능.

### 사용법

```bash
chmod +x dev.command   # 최초 1회
# Finder에서 dev.command 더블클릭 → Terminal.app이 열리며 실행
# 터미널 창 닫기 → 두 서버 모두 종료
```

### 구현 (`dev.command`)

```bash
#!/bin/bash
# macOS Finder 더블클릭 실행용

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
    echo "서버를 종료합니다..."
    [ -n "$BACKEND_PID" ]  && kill "$BACKEND_PID"  2>/dev/null
    [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null
    wait
    echo "종료 완료. 이 창을 닫아도 됩니다."
}

# EXIT: 터미널 창 닫기 포함 모든 종료 상황을 포착
trap cleanup EXIT

# 스크립트 위치로 이동 (더블클릭 시 홈 디렉토리에서 시작하므로 필수!)
cd "$(dirname "$0")"

echo "============================="
echo "  KR Stock Screener 시작"
echo "============================="

source venv/bin/activate

echo "[백엔드] http://localhost:8000"
uvicorn backend.main:app --reload --port 8000 &
BACKEND_PID=$!

echo "[프론트엔드] http://localhost:5173"
cd frontend && pnpm dev &
FRONTEND_PID=$!

echo ""
echo "서버가 실행 중입니다."
echo "이 창을 닫으면 모든 서버가 종료됩니다."

wait
```

### .command vs .sh 차이점

| 항목 | `.sh` | `.command` |
|------|-------|-----------|
| 실행 방법 | 터미널에서 `./dev.sh` | Finder 더블클릭 |
| 시작 디렉토리 | 현재 작업 디렉토리 | 홈 디렉토리 (`~/`) |
| `cd "$(dirname "$0")"` | 선택사항 | **필수** |
| trap 신호 | `SIGINT`, `SIGTERM` | `EXIT` 권장 (창 닫기 포함) |

---

## 6. 비교 및 선택 기준

| 기준 | Makefile | dev.sh | dev.command |
|------|----------|--------|-------------|
| 터미널 사용 여부 | 필요 | 필요 | 불필요 |
| 설치 필요 | make | 없음 | 없음 |
| 아이콘 더블클릭 | 불가 | 불가 | 가능 |
| 팀 협업 친화도 | 높음 | 보통 | macOS 전용 |
| 가독성/표준성 | 높음 | 보통 | 낮음 |
| 확장성 | 높음 | 보통 | 낮음 |

**추천 조합:**
- CLI 개발자: Makefile
- 터미널 없이 쓰고 싶을 때: dev.command
- 두 가지 모두: Makefile + dev.command 동시 운영 가능

---

## 7. 함정과 주의사항

### 함정 1: 포트 충돌

서버가 비정상 종료되면 포트가 해제되지 않을 수 있다.

```bash
# 포트 8000 점유 프로세스 확인 및 강제 종료
lsof -ti :8000 | xargs kill -9
lsof -ti :5173 | xargs kill -9
```

### 함정 2: venv 활성화 문제

```bash
# 틀린 방식 (서브셸에서 활성화는 부모 셸에 영향 없음)
source venv/bin/activate && uvicorn ...

# 올바른 방식 (직접 venv의 python/uvicorn 바이너리 사용)
./venv/bin/uvicorn backend.main:app --reload --port 8000 &
```

### 함정 3: cd 명령의 서브셸 격리

```bash
# 이렇게 하면 스크립트 전체가 frontend 디렉토리로 이동
cd frontend
pnpm dev &
# 이후 코드들이 frontend/ 에서 실행됨 (버그!)

# 올바른 방식: 서브셸에서 실행
(cd frontend && pnpm dev) &
# 또는
cd frontend && pnpm dev & cd ..
```

### 함정 4: kill 타이밍

```bash
# uvicorn은 SIGINT를 받으면 graceful shutdown을 시작
# 그러나 --reload 모드에서는 부모/자식 프로세스가 있어
# kill $PID로는 자식 프로세스가 남을 수 있음

# 더 확실한 종료: 프로세스 그룹 전체 kill
kill -- -$BACKEND_PID   # 음수 PID = 프로세스 그룹 전체
```

---

## 8. 심화 학습 과제

### 과제 1 (기초): 신호 동작 분석

다음 스크립트를 실행하고 Ctrl+C를 눌러보자. 무슨 일이 일어나는가?

```bash
#!/bin/bash
sleep 100 &
PID=$!
echo "PID: $PID"
wait $PID
echo "여기까지 도달했나?"
```

**분석 포인트**: `wait`는 신호를 받으면 어떻게 동작하는가?

### 과제 2 (중급): 재시작 기능 추가

SIGUSR1 신호를 받으면 두 서버를 재시작하는 기능을 `dev.sh`에 추가하라.

```bash
kill -USR1 $(cat .dev.pid)   # 재시작 명령
```

### 과제 3 (고급): 헬스체크 루프

두 서버가 실행 중인지 주기적으로 확인하고, 죽어있으면 자동 재시작하는 로직을 추가하라.

```bash
# 힌트: curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health
```

---

## 9. 핵심 요약 체크리스트

- [ ] `&`로 백그라운드 실행하면 Ctrl+C 신호를 받지 못한다는 것을 이해했다
- [ ] `$!`로 백그라운드 프로세스의 PID를 캡처하는 방법을 안다
- [ ] `trap`으로 신호를 가로채 cleanup 함수를 실행하는 패턴을 이해했다
- [ ] `wait`가 없으면 스크립트가 즉시 종료되는 이유를 안다
- [ ] `cd "$(dirname "$0")"` 가 왜 필요한지 안다
- [ ] `.command` 파일이 macOS에서 더블클릭 가능한 이유를 안다
- [ ] SIGINT vs SIGTERM vs EXIT의 차이를 설명할 수 있다
- [ ] 포트 충돌 상황을 해결하는 방법을 안다

---

## 관련 학습 자료

- `man trap` - bash trap 명령어 매뉴얼
- `man signal` - Unix 신호 목록
- GNU Make Manual: https://www.gnu.org/software/make/manual/
- Advanced Bash-Scripting Guide: https://tldp.org/LDP/abs/html/

---

*생성일: 2026-02-28*
*프로젝트: my_chart (FastAPI + React Vite)*
*파일 위치: `.moai/learning/single-command-multi-process.md`*
