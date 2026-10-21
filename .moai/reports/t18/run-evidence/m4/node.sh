#!/bin/bash
# 격리된 프런트 도구 실행: 임시 HOME + 임시 하네스 경로. 첫 인자는 frontend/node_modules/.bin 아래 도구 이름
W=/Users/byunjungwon/Dev/my-project-01/my_chart/.claude/worktrees/agent-aa2a25e79f99bda02
export HOME=$W/.moai/state/verify/t18-m4/home
export AI_REPORT_GOOSE_HARNESS_DIR=$HOME/.goose-harness
cd "$W/frontend" || exit 99
tool=$1
shift
exec "$W/frontend/node_modules/.bin/$tool" "$@"
