# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-03-04

### Added

- **KRX 세션 기반 인증** (SPEC-KRX-AUTH-001)
  - `my_chart/krx_session.py`: KRX 세션 관리 모듈
    - `patch_pykrx_session()`: pykrx webio를 인증된 세션으로 monkey-patch
    - `login_krx(id, pw)`: 3단계 KRX 인증 (JSESSIONID 획득 → JSP 세션 초기화 → 실제 로그인)
    - `init_session()`: KRX_ID/KRX_PW 환경변수에서 자동 초기화
    - `get_market_cap_safe(date)`: 3단계 폴백 (pykrx → sectormap Excel → 빈 DataFrame)
  - `.env.example`: 인증 정보 템플릿
  - `python-dotenv` 의존성 추가

- **설정 개선**
  - `my_chart/config.py`: dotenv 로드 및 자동 세션 초기화
  - 7개 파일에서 `stock.get_market_cap()` → `get_market_cap_safe()` 교체

### Changed

- Type hints 및 Pyright 호환성 개선
  - `my_chart/krx_session.py`: 타입 안전성 강화 (monkey-patch 함수의 Any 타입 적절한 처리)

### Fixed

- Pyright 타입 오류 수정
  - `my_chart/krx_session.py`: pandas 타입 힌트 개선, type: ignore 주석 추가
