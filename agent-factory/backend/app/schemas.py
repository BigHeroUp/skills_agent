from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ClarificationAnswers(BaseModel):
    answers: dict[str, str] = Field(default_factory=dict)
    free_context: str = ""


class JobCreateResponse(BaseModel):
    job_id: str
    status: str
    clarification_questions: list[str] = Field(default_factory=list)


class DatabaseConnectionTestRequest(BaseModel):
    connection_string: str


class DatabaseConnectionTestResponse(BaseModel):
    connection_id: str
    status: str
    masked_connection_string: str
    db_schema: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class DatabaseQueryRequest(BaseModel):
    connection_id: str
    request: str


class DatabaseQueryResponse(BaseModel):
    mode: str
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class AgentEventModel(BaseModel):
    timestamp: datetime
    agent: str
    phase: str
    level: str
    message: str
    payload: dict[str, Any] = Field(default_factory=dict)


class JobSnapshot(BaseModel):
    job_id: str
    status: str
    created_at: datetime
    updated_at: datetime
    prompt: str
    business_requirements: str
    uploaded_files: list[str] = Field(default_factory=list)
    clarification_questions: list[str] = Field(default_factory=list)
    clarification_answers: dict[str, str] = Field(default_factory=dict)
    artifacts: dict[str, Any] = Field(default_factory=dict)
    events: list[AgentEventModel] = Field(default_factory=list)
