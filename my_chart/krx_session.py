"""KRX 세션 기반 인증 관리 모듈.

pykrx의 webio.Post.read / webio.Get.read를 monkey-patch하여
인증된 requests.Session을 공유하도록 하고, KRX 로그인을 수행한다.

SPEC: SPEC-KRX-AUTH-001
"""

from __future__ import annotations

import logging
import os
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

# --- 모듈 레벨 싱글턴 상태 ---
# @MX:WARN: [AUTO] 전역 가변 상태 - requests.Session 싱글턴 및 monkey-patch 가드
# @MX:REASON: 프로세스당 1회 패치 보장을 위한 전역 플래그; 스레드 안전성 미보장
_session: requests.Session = requests.Session()
_session.headers.update({"User-Agent": _UA})
_patched: bool = False
_logged_in: bool = False


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

        def _post_read(self: Any, **params: Any) -> requests.Response:  # type: ignore[misc]
            """POST 요청을 인증된 세션으로 실행."""
            url: str = self.url  # type: ignore[assignment]
            return _session.post(url, headers=self.headers, data=params)

        def _get_read(self: Any, **params: Any) -> requests.Response:  # type: ignore[misc]
            """GET 요청을 인증된 세션으로 실행."""
            url: str = self.url  # type: ignore[assignment]
            return _session.get(url, headers=self.headers, params=params)  # type: ignore[arg-type]

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

    # 2차: sectormap_original.xlsx D-day 컬럼 폴백
    try:
        from my_chart.config import SECTORMAP_PATH

        df_sector = pd.read_excel(str(SECTORMAP_PATH), skiprows=8)
        df_sector["종목\n코드"] = df_sector["종목\n코드"].astype(str).str.zfill(6)

        # D-day 컬럼 탐색 (억원 단위 → 원 단위 변환)
        dday_col = None
        for col in df_sector.columns:
            if str(col).strip().lower() in ("d-day", "d day", "dday"):
                dday_col = col
                break

        if dday_col is None:
            # 컬럼명 패턴 기반 탐색 (대소문자 무관)
            for col in df_sector.columns:
                if "d" in str(col).lower() and "day" in str(col).lower():
                    dday_col = col
                    break

        if dday_col is not None:
            col_name = str(dday_col)
            df_fallback = df_sector[["종목\n코드", col_name]].copy()
            df_fallback = df_fallback.dropna(subset=[col_name])  # type: ignore[call-overload]
            df_fallback.set_index("종목\n코드", inplace=True)
            # 억원 → 원 변환 (1억 = 100,000,000)
            numeric_vals: pd.Series = pd.to_numeric(  # type: ignore[assignment]
                df_fallback[col_name], errors="coerce"
            )
            df_fallback["시가총액"] = numeric_vals * 100_000_000  # type: ignore[operator]
            result: pd.DataFrame = df_fallback[["시가총액"]].dropna()  # type: ignore[assignment]

            if not result.empty:
                logger.info(
                    "sectormap D-day 폴백 사용: %d건 (날짜: %s)", len(result), date_str
                )
                return result

        logger.warning("sectormap에서 D-day 컬럼을 찾을 수 없음")

    except Exception as exc:
        logger.warning("sectormap 폴백 실패: %s", exc)

    # 3차: 빈 DataFrame 반환
    logger.warning("시가총액 데이터를 가져올 수 없음 - 빈 DataFrame 반환: %s", date_str)
    return pd.DataFrame({"시가총액": pd.Series(dtype="float64")})
