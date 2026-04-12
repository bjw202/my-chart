"""AI 리포트 서비스: Perplexity API를 통한 종목 분석 리포트 생성/저장/조회."""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator

import httpx

from my_chart.registry import _name

logger = logging.getLogger(__name__)

# 현재 진행 중인 분석 요청을 추적하는 집합 (종목 코드)
# @MX:NOTE: [AUTO] 동일 종목 중복 요청 방지용 모듈 레벨 상태 (단일 프로세스 가정)
_active_analyses: set[str] = set()

# 리포트 저장 기본 경로
_REPORTS_BASE = Path(__file__).parent.parent / "reports"

# 파일명에 사용 불가한 문자 패턴
_UNSAFE_CHARS = re.compile(r'[/\\:*?"<>|]')

# @MX:NOTE: [AUTO] v1.1.0 - 한국 금융 애널리스트 시스템 프롬프트 (공간(Spaces) 품질 근접용)
# SPEC-AI-REPORT-001 NFR-006(서술 품질), NFR-008(소스 품질 관리) 강제
SYSTEM_PROMPT = """당신은 한국 주식시장 전문 스윙 트레이딩 애널리스트입니다.

작성 원칙:
1. 각 표 뒤에는 반드시 1-2문단의 서술형 인과 분석을 추가하세요.
   (예: "단기 테크니컬은 강하지만 공매도 수량 상위 기록과 급등 폭을 감안하면 변동성이 크다")
2. 모든 수치·주장에는 [1], [2] 형식의 출처 인용을 반드시 부여하세요.
3. 톱티어 2건 이상 교차 확인된 뉴스만 '확정'으로 분류하고, 단일 출처는 [루머]로 명시하세요.
4. 기대(내러티브) vs 팩트(실적/공시) 패턴을 명시적으로 구분하세요.
5. 출처 우선순위: DART/KRX 공시 > 주요 일간지(한경/매경/조선/뉴시스) > IR·분석 플랫폼.
6. 금지: 추상어("좋은/나쁜/강한" 단독 사용), 매매권유, 출처 없는 수치, 근거 없는 전망."""

# @MX:NOTE: [AUTO] v1.1.2 - 검색 도메인 필터 (최소 블랙리스트 전략)
# @MX:REASON: v1.1.1의 whitelist 전략은 실측 결과 품질 저하 원인이었음.
# 공간(Spaces) 출력 역분석 결과, blog.naver.com/tistory/youtube까지 적극 인용되어
# 공간 출처의 약 40%가 기존 whitelist/blacklist에 의해 차단되는 역효과 발생.
# → Perplexity 검색 풀을 최대한 개방하고, 명백한 저품질 SNS만 최소 블랙리스트로 제외.
# 시스템 프롬프트(SYSTEM_PROMPT 원칙 5)에서 "DART/KRX 우선" 인용을 강제하므로
# 도메인 필터 없이도 소스 품질은 유지됨.
# Perplexity API 제약: search_domain_filter 최대 20개.
SEARCH_DOMAIN_FILTER = [
    # SNS/광고성 플랫폼만 제외 (공간도 블로그/유튜브는 적극 활용)
    "-instagram.com",
    "-x.com",
    "-twitter.com",
    "-facebook.com",
    "-reddit.com",
]
assert len(SEARCH_DOMAIN_FILTER) <= 20, (
    f"search_domain_filter cannot exceed 20 entries (got {len(SEARCH_DOMAIN_FILTER)})"
)


def get_stock_name(code: str) -> str | None:
    """종목 코드로 종목명 조회.

    Args:
        code: 6자리 KRX 종목 코드.

    Returns:
        종목명 문자열, 존재하지 않으면 None.
    """
    name = _name(code)
    if name == "NonName":
        return None
    return name


def load_prompt(stock_name: str) -> str:
    """Perplexity 분석 프롬프트 로드 및 종목명 치환.

    Args:
        stock_name: 치환할 실제 종목명.

    Returns:
        종목명이 반영된 프롬프트 문자열.
    """
    prompt_path = Path(__file__).parent.parent.parent / "docs" / "perplexity-prompt.md"
    template = prompt_path.read_text(encoding="utf-8")
    # 〈종목명〉 플레이스홀더를 실제 종목명으로 치환 (한국어 겹낫표)
    return template.replace("〈종목명〉", stock_name)


async def stream_perplexity(stock_name: str) -> AsyncGenerator[str, None]:
    """Perplexity API를 통해 종목 분석 리포트를 스트리밍 생성.

    Args:
        stock_name: 분석할 종목명.

    Yields:
        각 스트리밍 청크의 텍스트 델타.

    Note:
        전체 응답은 완료 후 자동 저장됨. 이 제너레이터는 내용만 yield함.
    """
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        raise EnvironmentError("PERPLEXITY_API_KEY 환경변수가 설정되지 않았습니다.")

    prompt = load_prompt(stock_name)

    # @MX:NOTE: [AUTO] v1.1.3 - sonar-reasoning-pro로 전환 (Chain-of-Thought 추론)
    # 실측: sonar-pro 대비 분량 +14%, 표에 "확인도" 컬럼 추가, 인과 분석 풍부화 (65%→80% 품질)
    # 비용: 응답 시간 +15% (42초 vs 36초), reasoning 블록 생성 비용 추가
    payload = {
        "model": "sonar-reasoning-pro",
        "stream": True,
        "temperature": 0.2,  # 재현성 있는 결과
        "max_tokens": 12000,  # reasoning 블록 + 리포트 본문 동시 생성 고려
        "web_search_options": {
            "search_context_size": "high",  # 공간 수준 검색 컨텍스트 (품질 1차 레버)
        },
        "search_recency_filter": "month",  # 최근 30일 소스 우선 (NFR-007)
        "search_domain_filter": SEARCH_DOMAIN_FILTER,  # 공시+일간지+금융포털 (NFR-008)
        "return_related_questions": True,  # 다중 패스 리서치 활성화
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,  # v1.1.0 한국 애널리스트 프롬프트 (NFR-006)
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }

    accumulated = []

    # 타임아웃 180초: search_context_size: high는 응답 시간이 길어질 수 있음
    async with httpx.AsyncClient(timeout=180.0) as client:
        async with client.stream(
            "POST",
            "https://api.perplexity.ai/chat/completions",
            headers=headers,
            json=payload,
        ) as response:
            # @MX:NOTE: [AUTO] HTTP 에러 시 본문을 읽어 구체 메시지 전달 (search_domain_filter 제한 등)
            if response.status_code >= 400:
                error_body = await response.aread()
                error_text = error_body.decode(errors="replace")
                logger.error("Perplexity API %d: %s", response.status_code, error_text[:500])
                raise RuntimeError(
                    f"Perplexity API 오류 (HTTP {response.status_code}): {error_text[:300]}"
                )

            # @MX:NOTE: [AUTO] v1.1.3 - <think> 블록 스트리밍 필터링 상태
            # sonar-reasoning-pro는 응답 시작에 <think>...</think> CoT 블록을 포함.
            # 이를 사용자에게 노출하지 않고 최종 리포트만 yield.
            in_think_block = False
            buffer = ""

            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue

                raw = line[6:].strip()
                if raw == "[DONE]":
                    break

                try:
                    chunk = json.loads(raw)
                except json.JSONDecodeError:
                    logger.warning("JSON 파싱 실패: %s", raw)
                    continue

                choices = chunk.get("choices", [])
                if not choices:
                    continue

                delta = choices[0].get("delta", {})
                content = delta.get("content", "")
                if not content:
                    continue

                # <think> 블록 필터링: 스트리밍 중 태그 경계가 청크에 걸칠 수 있으므로 버퍼 사용
                buffer += content
                output = ""
                while buffer:
                    if in_think_block:
                        # </think> 종료 태그 탐색
                        end = buffer.find("</think>")
                        if end == -1:
                            # 종료 태그 미발견 → 현재 버퍼 전체를 think로 간주하고 소비
                            # 단 마지막 7글자는 다음 청크에서 종료 태그가 완성될 수 있으므로 보존
                            if len(buffer) > 7:
                                buffer = buffer[-7:]
                            break
                        # 종료 태그 발견 → 태그 이후부터 다음 루프에서 처리
                        buffer = buffer[end + len("</think>"):]
                        in_think_block = False
                    else:
                        # <think> 시작 태그 탐색
                        start = buffer.find("<think>")
                        if start == -1:
                            # 시작 태그 미발견 → 전체 출력. 단 마지막 6글자는 보존 (태그 경계 가능성)
                            if len(buffer) > 6:
                                output += buffer[:-6]
                                buffer = buffer[-6:]
                            break
                        # 시작 태그 발견 → 태그 이전까지 출력, 태그 이후부터 다음 루프에서 think 모드
                        output += buffer[:start]
                        buffer = buffer[start + len("<think>"):]
                        in_think_block = True

                if output:
                    accumulated.append(output)
                    yield output

            # 스트림 종료 후 버퍼에 남은 내용 처리 (think 블록 밖에 있던 잔여분)
            if buffer and not in_think_block:
                accumulated.append(buffer)
                yield buffer

    # 전체 응답 저장 (<think> 블록이 제거된 최종 리포트만)
    full_content = "".join(accumulated)
    if full_content:
        filename = save_report(stock_name, full_content)
        logger.info("리포트 저장 완료: %s / %s", stock_name, filename)


def _sanitize_name(stock_name: str) -> str:
    """파일시스템 안전 문자열로 변환.

    Args:
        stock_name: 원본 종목명.

    Returns:
        파일명에 사용 가능한 문자열.
    """
    return _UNSAFE_CHARS.sub("", stock_name)


def save_report(stock_name: str, content: str) -> str:
    """분석 리포트를 파일로 저장.

    Args:
        stock_name: 종목명 (디렉토리명으로 사용).
        content: 저장할 마크다운 내용.

    Returns:
        저장된 파일명 (예: "2026-04-12.md" 또는 "2026-04-12_2.md").
    """
    safe_name = _sanitize_name(stock_name)
    report_dir = _REPORTS_BASE / safe_name
    os.makedirs(report_dir, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    base_filename = f"{today}.md"
    target = report_dir / base_filename

    # 같은 날짜 파일이 이미 존재하면 시퀀스 번호 부여
    if target.exists():
        seq = 2
        while True:
            candidate = report_dir / f"{today}_{seq}.md"
            if not candidate.exists():
                target = candidate
                break
            seq += 1

    target.write_text(content, encoding="utf-8")
    logger.info("리포트 저장: %s", target)
    return target.name


def get_history(stock_name: str) -> list[dict[str, str]]:
    """저장된 리포트 히스토리 조회.

    Args:
        stock_name: 종목명.

    Returns:
        날짜 내림차순 정렬된 리포트 목록.
        각 항목: {"filename": str, "date": str, "created_at": str}
    """
    safe_name = _sanitize_name(stock_name)
    report_dir = _REPORTS_BASE / safe_name

    if not report_dir.exists():
        return []

    items = []
    for path in report_dir.glob("*.md"):
        # 파일명에서 날짜 추출 (예: "2026-04-12.md" → "2026-04-12")
        stem = path.stem
        # 시퀀스 번호가 있으면 제거 (예: "2026-04-12_2" → "2026-04-12")
        date_part = stem.split("_")[0] if "_" in stem else stem

        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        items.append(
            {
                "filename": path.name,
                "date": date_part,
                "created_at": mtime.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

    # 날짜 내림차순 정렬 (파일명 기준)
    items.sort(key=lambda x: x["filename"], reverse=True)
    return items


def get_report_content(stock_name: str, filename: str) -> str | None:
    """저장된 리포트 내용 조회.

    Args:
        stock_name: 종목명.
        filename: 조회할 파일명 (예: "2026-04-12.md").

    Returns:
        리포트 마크다운 내용, 파일이 없으면 None.
    """
    safe_name = _sanitize_name(stock_name)
    target = _REPORTS_BASE / safe_name / filename

    if not target.exists():
        return None

    return target.read_text(encoding="utf-8")
