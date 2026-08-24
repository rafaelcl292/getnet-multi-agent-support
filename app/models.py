from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    user_id: str = Field(min_length=1, max_length=100)


class Citation(BaseModel):
    title: str
    url: str
    excerpt: str = ""


class TraceStep(BaseModel):
    agent: str
    action: str
    status: Literal["success", "warning", "error"] = "success"
    duration_ms: int = 0
    details: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    answer: str
    route: str
    confidence: float = Field(ge=0, le=1)
    trace_id: str
    citations: list[Citation] = Field(default_factory=list)
    trace: list[TraceStep] = Field(default_factory=list)
    handoff: bool = False


class EvalCase(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    expected_answer: str = Field(min_length=1, max_length=8000)
    actual_answer: str | None = Field(default=None, max_length=8000)
    user_id: str = "cliente1988"


class EvaluationResult(BaseModel):
    passed: bool
    score: float = Field(ge=0, le=1)
    reason: str
    criteria: dict[str, float]
    actual_answer: str
    trace_id: str | None = None

