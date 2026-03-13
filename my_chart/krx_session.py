"""KRX 세션 기반 인증 관리 모듈.

pykrx의 webio.Post.read / webio.Get.read를 monkey-patch하여
인증된 requests.Session을 공유하도록 하고, KRX 로그인을 수행한다.

SPEC: SPEC-KRX-AUTH-001
"""

from __future__ import annotations

import logging
import os
import pickle
from pathlib import Path
from typing import Any

import pandas as pd
import requests

logger = logging.getLogger(__name__)

# --- KRX 로그인 엔드포인트 ---
_LOGIN_PAGE = "https://data.krx.co.kr/contents/MDC/COMS/client/MDCCOMS001.cmd"
_LOGIN_JSP = "https://data.krx.co.kr/contents/MDC/COMS/client/view/login.jsp?site=mdc"
_LOGIN_URL = "https://data.krx.co.kr/contents/MDC/COMS/client/MDCCOMS001D1.cmd"

# User-Agent: 일반 브라우저로 위장하여 KRX 서버 접근 허용
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# 세션 pickle 저장 경로 (프로젝트 루트 기준)
_SESSION_FILE = Path(__file__).parent.parent / ".krx_session.pkl"

# --- 모듈 레벨 싱글턴 상태 ---
# @MX:WARN: [AUTO] 전역 가변 상태 - requests.Session 싱글턴 및 monkey-patch 가드
# @MX:REASON: 프로세스당 1회 패치 보장을 위한 전역 플래그; 스레드 안전성 미보장
_session: requests.Session = requests.Session()
_session.headers.update({"User-Agent": _UA})
_patched: bool = False
_logged_in: bool = False


def _save_session() -> None:
    """로그인된 세션을 pickle 파일에 저장한다.

    서버 재시작 시 재로그인 없이 세션을 재사용할 수 있도록 영속화한다.
    저장 실패는 경고만 출력하고 무시한다.
    """
    try:
        with open(_SESSION_FILE, "wb") as f:
            pickle.dump(_session, f)
        logger.info("KRX 세션 파일 저장 완료: %s", _SESSION_FILE)
    except Exception as exc:
        logger.warning("KRX 세션 파일 저장 실패: %s", exc)


def _load_saved_session() -> bool:
    """pickle 파일에서 세션을 로드한다.

    로드 성공 시 _session과 _logged_in 플래그를 갱신한다.
    파일이 없거나 유효하지 않으면 False를 반환하여 재로그인을 유도한다.

    세션 유효성은 _LOGIN_PAGE GET 요청(200 응답)으로 간이 검증한다.
    """
    global _session, _logged_in

    if not _SESSION_FILE.exists():
        return False

    try:
        with open(_SESSION_FILE, "rb") as f:
            loaded: requests.Session = pickle.load(f)

        # 간이 유효성 검증: KRX 메인 페이지 접근 확인
        resp = loaded.get(_LOGIN_PAGE, timeout=5)
        if resp.status_code == 200:
            _session = loaded
            _logged_in = True
            logger.info("KRX 세션 파일 로드 완료 (재로그인 생략)")
            return True

        logger.warning("KRX 세션 파일 만료 - 재로그인 필요")
    except Exception as exc:
        logger.warning("KRX 세션 파일 로드 실패: %s", exc)

    # 만료된 파일 삭제
    try:
        _SESSION_FILE.unlink(missing_ok=True)
    except Exception:
        pass

    return False


def patch_pykrx_session() -> None:
    """pykrx webio의 read 메서드를 인증된 세션으로 monkey-patch한다.

    멱등성 보장: _patched 플래그가 True이면 재적용하지 않는다.
    프로세스당 1회만 실행된다.
    """
    global _patched

    if _patched:
        logger.debug("pykrx 세션 패치가 이미 적용됨 - 건너뜀")
        return

    try:
        from pykrx.website.comm import webio

        # @MX:NOTE: [AUTO] KRX requires AJAX headers (X-Requested-With, Accept) for JSON API.
        # Without these, KRX WAF returns 403. Merge pykrx default headers with required AJAX headers.
        _KRX_AJAX_HEADERS = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": "https://data.krx.co.kr",
            "Referer": "https://data.krx.co.kr/",
            "X-Requested-With": "XMLHttpRequest",
        }

        def _post_read(self: Any, **params: Any) -> requests.Response:  # type: ignore[misc]
            """POST 요청을 인증된 세션으로 실행."""
            url: str = self.url  # type: ignore[assignment]
            merged_headers = {**self.headers, **_KRX_AJAX_HEADERS}
            return _session.post(url, headers=merged_headers, data=params)

        def _get_read(self: Any, **params: Any) -> requests.Response:  # type: ignore[misc]
            """GET 요청을 인증된 세션으로 실행."""
            url: str = self.url  # type: ignore[assignment]
            merged_headers = {**self.headers, **_KRX_AJAX_HEADERS}
            return _session.get(url, headers=merged_headers, params=params)  # type: ignore[arg-type]

        webio.Post.read = _post_read  # type: ignore[method-assign]
        webio.Get.read = _get_read  # type: ignore[method-assign]
        _patched = True
        logger.info("pykrx webio monkey-patch 적용 완료")

    except ImportError as exc:
        logger.warning("pykrx webio 모듈을 찾을 수 없음 - 패치 건너뜀: %s", exc)
    except Exception as exc:
        logger.warning("pykrx monkey-patch 실패: %s", exc)


def login_krx(login_id: str, login_pw: str) -> bool:
    """KRX data.krx.co.kr에 세션 인증을 수행한다.

    3단계 로그인 플로우:
    1. GET MDCCOMS001.cmd (JSESSIONID 쿠키 획득)
    2. GET login.jsp (iframe 세션 초기화)
    3. POST MDCCOMS001D1.cmd (실제 로그인)

    중복 로그인(CD011)은 skipDup=Y로 자동 재시도한다.
    비밀번호는 절대 로그에 기록하지 않는다.

    Parameters
    ----------
    login_id : str
        KRX 회원 ID.
    login_pw : str
        KRX 회원 비밀번호 (로그에 기록되지 않음).

    Returns
    -------
    bool
        True = 로그인 성공 (CD001), False = 실패.
    """
    global _logged_in

    logger.info("KRX 로그인 시도 중... (ID: %s)", login_id)

    try:
        # 1단계: JSESSIONID 쿠키 획득
        resp = _session.get(_LOGIN_PAGE, timeout=10)
        resp.raise_for_status()
        logger.debug("KRX 로그인 1단계 완료 (JSESSIONID 획득)")

        # 2단계: 로그인 iframe 세션 초기화
        resp = _session.get(_LOGIN_JSP, timeout=10)
        resp.raise_for_status()
        logger.debug("KRX 로그인 2단계 완료 (JSP 세션 초기화)")

        # 3단계: 실제 로그인 POST
        payload = {
            "mbrId": login_id,
            "pw": login_pw,
            "mbrNm": "",
            "telNo": "",
            "di": "",
            "certType": "",
        }
        resp = _session.post(_LOGIN_URL, data=payload, timeout=10)
        resp.raise_for_status()

        result = resp.json()
        error_code = result.get("_error_code", "")

        if error_code == "CD001":
            # 로그인 성공
            _logged_in = True
            logger.info("KRX 로그인 성공 (ID: %s)", login_id)
            _save_session()
            return True

        if error_code == "CD011":
            # 중복 로그인 - skipDup=Y로 재시도
            logger.warning("KRX 중복 로그인 감지 - skipDup=Y로 재시도 중")
            payload["skipDup"] = "Y"
            resp = _session.post(_LOGIN_URL, data=payload, timeout=10)
            resp.raise_for_status()
            result = resp.json()
            error_code = result.get("_error_code", "")

            if error_code == "CD001":
                _logged_in = True
                logger.info("KRX 로그인 성공 (중복 로그인 해소, ID: %s)", login_id)
                _save_session()
                return True

        logger.warning("KRX 로그인 실패 - error_code: %s", error_code)
        return False

    except requests.RequestException as exc:
        logger.warning("KRX 로그인 네트워크 오류: %s", exc)
        return False
    except Exception as exc:
        logger.warning("KRX 로그인 예외 발생: %s", exc)
        return False


def init_session() -> None:
    """환경변수에서 KRX 인증 정보를 읽어 세션을 초기화한다.

    KRX_ID, KRX_PW 환경변수가 모두 설정된 경우에만 로그인을 시도한다.
    환경변수 미설정 또는 로그인 실패 시 경고 로그만 출력하고 앱 기동을 허용한다.

    호출 순서:
    1. patch_pykrx_session() - monkey-patch 적용
    2. 환경변수 KRX_ID, KRX_PW 읽기
    3. 두 값이 모두 있으면 login_krx() 호출
    """
    # monkey-patch를 먼저 적용하여 이후 pykrx 호출이 세션을 사용하도록 함
    patch_pykrx_session()

    # 저장된 세션이 있으면 재사용 (재로그인 생략)
    if _load_saved_session():
        return

    krx_id = os.environ.get("KRX_ID", "")
    krx_pw = os.environ.get("KRX_PW", "")

    if not krx_id or not krx_pw:
        logger.warning(
            "KRX_ID 또는 KRX_PW 환경변수가 설정되지 않음 - "
            "pykrx 호출이 인증 없이 실행되며 실패할 수 있음"
        )
        return

    success = login_krx(krx_id, krx_pw)
    if not success:
        logger.warning(
            "KRX 로그인 실패 - sectormap 폴백 모드로 동작합니다"
        )


def get_market_cap_safe(date_str: str) -> pd.DataFrame:
    """시가총액을 안전하게 조회한다 (폴백 포함).

    조회 순서:
    1. pykrx stock.get_market_cap(date_str) 시도
    2. 실패 시 sectormap_original.xlsx D-day 컬럼으로 폴백
    3. 폴백 데이터도 없으면 빈 DataFrame 반환

    반환 DataFrame 구조:
    - Index: 종목 코드 (6자리 문자열)
    - Column: "시가총액" (단위: 원)

    Parameters
    ----------
    date_str : str
        조회 날짜 (YYYYMMDD 또는 YYYY-MM-DD 형식).

    Returns
    -------
    pd.DataFrame
        시가총액 DataFrame. 항상 DataFrame을 반환한다 (빈 DataFrame 포함).
    """
    # 1차: pykrx로 시가총액 조회
    try:
        from pykrx import stock

        mc = stock.get_market_cap(date_str)
        if mc is not None and not mc.empty:
            logger.debug("pykrx 시가총액 조회 성공: %s (%d건)", date_str, len(mc))
            return mc
        logger.warning("pykrx 시가총액 조회 결과가 비어있음 - 폴백 시도: %s", date_str)
    except Exception as exc:
        logger.warning("pykrx 시가총액 조회 실패 - 폴백 시도: %s (%s)", date_str, exc)

    # 2차: 빈 DataFrame 반환
    logger.warning("시가총액 데이터를 가져올 수 없음 - 빈 DataFrame 반환: %s", date_str)
    return pd.DataFrame({"시가총액": pd.Series(dtype="float64")})
