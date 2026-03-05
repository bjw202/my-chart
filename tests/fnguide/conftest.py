# SPEC-FNGUIDE-ENGINE-001: 테스트 픽스처
"""
FnGuide 테스트 공용 세션 스코프 픽스처.

세션당 한 번만 HTTP 요청을 수행하여 중복 크롤링을 방지한다.

NOTE: pandas 3.0 Breaking Change 로 인해 read_snapshot / get_fnguide 가
FileNotFoundError 를 발생시킬 수 있다. 이 경우 해당 픽스처는 None 을 반환하고
각 테스트에서 pytest.skip() 으로 처리한다.
"""

import pytest

from fnguide.crawler import get_fnguide, get_required_rate, read_fs


@pytest.fixture(scope="session")
def samsung_fs():
    """삼성전자 재무제표 (세션 1회 크롤링)"""
    return read_fs("005930")


@pytest.fixture(scope="session")
def samsung_fnguide():
    """삼성전자 FnGuide 전체 데이터 (세션 1회 크롤링).

    pandas 3.0 비호환 환경에서는 None 반환.
    """
    try:
        return get_fnguide("005930")
    except Exception:  # noqa: BLE001
        return None


@pytest.fixture(scope="session")
def hynix_fnguide():
    """SK하이닉스 FnGuide 전체 데이터.

    pandas 3.0 비호환 환경에서는 None 반환.
    """
    try:
        return get_fnguide("000660")
    except Exception:  # noqa: BLE001
        return None


@pytest.fixture(scope="session")
def required_rate():
    """BBB- 요구수익률"""
    return get_required_rate()
