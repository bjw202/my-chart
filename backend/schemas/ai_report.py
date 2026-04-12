"""AI 리포트 API 응답 스키마."""

from __future__ import annotations

from pydantic import BaseModel


class HistoryItem(BaseModel):
    """리포트 히스토리 단일 항목."""

    filename: str
    date: str
    created_at: str


class HistoryResponse(BaseModel):
    """리포트 히스토리 응답."""

    items: list[HistoryItem]


class ReportContentResponse(BaseModel):
    """저장된 리포트 내용 응답."""

    content: str
    filename: str
    date: str
