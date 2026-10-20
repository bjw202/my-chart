"""AI 리포트 API 응답 스키마."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class HistoryItem(BaseModel):
    """리포트 히스토리 단일 항목.

    kind "markdown": 기존 Fast 리포트(`YYYY-MM-DD[_N].md`). kind "goose": SPEC-AI-REPORT-004 goose 실행
    (`goose/<run>/report.html`, design §5.3) — run·delivery_status·interrupted를 함께 싣는다.
    """

    filename: str
    date: str
    created_at: str
    kind: Literal["markdown", "goose"] = "markdown"
    run: str | None = None
    delivery_status: Literal["final", "draft"] | None = None
    interrupted: bool = False


class HistoryResponse(BaseModel):
    """리포트 히스토리 응답."""

    items: list[HistoryItem]


class ReportContentResponse(BaseModel):
    """저장된 리포트 내용 응답."""

    content: str
    filename: str
    date: str
