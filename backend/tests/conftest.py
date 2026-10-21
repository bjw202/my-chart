"""SPEC-AI-REPORT-005 M3 — goose 테스트 공용 네트워크 가드 (REQ-AIR5-015, plan T12, AC-AIR5-014).

적용 범위: 테스트 파일 이름(`Path(request.node.fspath).name`)이 `test_goose_` 또는
`test_main_goose`로 시작하는 테스트. 모듈 이름은 `backend.tests.test_goose_*`라서 접두어 검사가
걸리지 않으므로 파일 이름으로 판정한다(plan-audit 3회차 R3-1).

동작: `socket.socket.connect`·`connect_ex`·`socket.create_connection`·`socket.getaddrinfo`를
원래 함수를 부르지 않는 대체 함수로 바꾼다. 대체 함수는 시도(대상 주소)를 기록한 뒤 예외를 던진다.
예외만 던지면 수집기의 fail-open 처리(REQ-AIR5-010)가 삼켜 테스트가 통과해 버리므로, 각 테스트
종료(teardown) 때 기록이 비어 있음을 따로 단언한다 — 코드가 무엇을 잡든 테스트가 실패한다.
"""

from __future__ import annotations

import socket
from pathlib import Path

import pytest

_GOOSE_PREFIXES = ("test_goose_", "test_main_goose")


class GooseNetworkBlocked(OSError):
    """goose 테스트에서 네트워크 연결·이름 조회를 시도했을 때 던지는 예외."""


def _is_goose_test(request: pytest.FixtureRequest) -> bool:
    return Path(str(request.node.fspath)).name.startswith(_GOOSE_PREFIXES)


# @MX:WARN: [AUTO] 소켓 전역 함수를 테스트 동안 바꿔치기한다(monkeypatch로 테스트마다 원복).
# @MX:REASON: 대체 함수가 원래 함수를 부르면 되돌림 관측(AC-AIR5-014 r1~r3) 중 실제 DNS·DART 연결이
#             일어난다. 기록을 남기지 않으면 fail-open이 예외를 삼켜 가드가 무력해진다(r3·r4).
@pytest.fixture
def goose_network_attempts(request, monkeypatch) -> list:
    """goose 테스트의 네트워크 시도 기록 목록. 가드 범위 밖 테스트에서는 빈 목록만 돌려준다."""
    attempts: list = []
    if not _is_goose_test(request):
        return attempts

    def _blocked(target):
        attempts.append(target)
        raise GooseNetworkBlocked(f"network blocked in goose test: {target!r}")

    def connect(self, address):  # noqa: ARG001
        _blocked(address)

    def connect_ex(self, address):  # noqa: ARG001
        _blocked(address)

    def create_connection(address, *args, **kwargs):  # noqa: ARG001
        _blocked(address)

    def getaddrinfo(host, port, *args, **kwargs):  # noqa: ARG001
        _blocked((host, port))

    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket.socket, "connect_ex", connect_ex)
    monkeypatch.setattr(socket, "create_connection", create_connection)
    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    return attempts


@pytest.fixture(autouse=True)
def _goose_network_guard(request):
    """goose 테스트마다 가드를 켜고, 종료 때 시도 기록 0건을 단언한다(teardown 실패 = ERROR at teardown)."""
    if not _is_goose_test(request):
        yield
        return
    attempts = request.getfixturevalue("goose_network_attempts")
    yield
    assert not attempts, f"network attempt in goose test: {attempts}"
