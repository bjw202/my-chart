#!/bin/sh
# usage: run.sh <pytest args...>
AI_REPORT_GOOSE_HARNESS_DIR=.moai/state/verify/t18-m7/home/.goose-harness ../../../.venv/bin/python -B -m pytest -p no:cacheprovider "$@"
