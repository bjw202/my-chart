#!/bin/bash
# 격리된 파이썬 실행: 임시 HOME + 임시 하네스 경로, -B 고정
W=/Users/byunjungwon/Dev/my-project-01/my_chart/.claude/worktrees/agent-aa2a25e79f99bda02
export HOME=$W/.moai/state/verify/t18-m4/home
export AI_REPORT_GOOSE_HARNESS_DIR=$HOME/.goose-harness
export PYTHONDONTWRITEBYTECODE=1
cd "$W" || exit 99
exec /Users/byunjungwon/Dev/my_chart/.venv/bin/python -B "$@"
