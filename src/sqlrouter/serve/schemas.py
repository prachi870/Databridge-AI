"""Pydantic models for API request/response validation."""
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class ConversationTurn(BaseModel):
    """A prior question and its reviewed SQL, used to interpret follow-ups."""
    question: str = Field(min_length=3, max_length=500)
    sql: str = Field(min_length=1, max_length=5000)


class RouteRequest(BaseModel):
    """Request to route a question."""
    db_id: str = Field(
        pattern=r"^[A-Za-z0-9_\-]+$",
        max_length=64,
        description="Database ID (alphanumeric, underscore, dash only)"
    )
    question: str = Field(
        min_length=3,
        max_length=500,
        description="Natural language question"
    )
    mode: Literal["auto", "local", "api"] = Field(
        default="auto",
        description="Routing mode: auto (use probe), local (force local), api (force API)"
    )
    threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Custom threshold (overrides default if provided)"
    )
    preview_only: bool = Field(
        default=False,
        description="Generate SQL for review without executing it"
    )
    context: list[ConversationTurn] = Field(
        default_factory=list,
        max_length=4,
        description="Up to four earlier questions and SQL statements for follow-up interpretation",
    )


class AuthCredentials(BaseModel):
    """Email and password credentials."""
    email: str = Field(
        min_length=5,
        max_length=254,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    )
    password: str = Field(min_length=1, max_length=128)


class Timing(BaseModel):
    """Timing breakdown for a request."""
    probe_ms: Optional[float] = Field(None, description="Probe forward pass time")
    generate_ms: Optional[float] = Field(None, description="Local generation time")
    api_ms: Optional[float] = Field(None, description="API call time")
    execute_ms: float = Field(description="SQL execution time")
    total_ms: float = Field(description="Total request time")


class RouteResponse(BaseModel):
    """Response from routing a question."""
    # Routing decision
    mode: Literal["live", "replay"] = Field(description="Backend mode used")
    route: Literal["local", "api"] = Field(description="Which tier answered")
    reason: str = Field(description="Human-readable routing explanation")
    score: float = Field(description="Uncertainty score from probe")
    threshold: float = Field(description="Threshold used for routing")
    
    # SQL and execution
    sql: str = Field(description="Generated or retrieved SQL query")
    status: Literal["ok", "err"] = Field(description="SQL execution status")
    error: Optional[str] = Field(None, description="Error message if status=err")
    columns: list[str] = Field(description="Column names")
    rows: list[list[Any]] = Field(description="Result rows")
    truncated: bool = Field(description="Whether results were truncated")
    
    # Performance and cost
    timing: Timing
    cost_usd: float = Field(description="Estimated cost for this query")
    always_api_cost_usd: float = Field(description="Cost if sent to API")
    requires_confirmation: bool = Field(default=False, description="Whether SQL is awaiting user confirmation")
    safety_warnings: list[str] = Field(default_factory=list, description="Read-only execution safety notes")
    query_id: Optional[str] = Field(default=None, description="Query identifier for history and feedback")


class ExecutePreviewRequest(BaseModel):
    """A reviewed SQL statement submitted for safe execution."""
    query_id: str = Field(min_length=1, max_length=64)
    db_id: str = Field(pattern=r"^[A-Za-z0-9_\-]+$", max_length=64)
    question: str = Field(min_length=3, max_length=1000)
    sql: str = Field(min_length=1, max_length=20000)
    route: Literal["local", "api"]


class QueryFeedbackRequest(BaseModel):
    """User evaluation of an executed query."""
    query_id: str = Field(min_length=1, max_length=64)
    correct: bool
    expected_answer: Optional[str] = Field(default=None, max_length=2000)


class HealthResponse(BaseModel):
    """Health check response."""
    status: Literal["ok", "degraded"]
    mode: Literal["live", "replay"]
    device: Optional[str] = None
    teacher_configured: bool


class ConfigResponse(BaseModel):
    """Router configuration."""
    layer: int
    threshold: float
    alpha: float
    delta: float
    student: str
    teacher: str
    mode: Literal["live", "replay"]
    costs: dict[str, float]


class DatabaseInfo(BaseModel):
    """Database metadata."""
    db_id: str
    schema: str


class QuestionItem(BaseModel):
    """Question from benchmark."""
    id: str
    db_id: str
    question: str
    gold: str
    local_sql: str
    local_ok: bool
    api_sql: str
    api_ok: bool
    score_sep: float
    score_token: float
    entropy: float


class BenchmarkResponse(BaseModel):
    """Paginated benchmark questions."""
    total: int
    items: list[QuestionItem]


class QueryHistoryItem(BaseModel):
    """Query history item."""
    id: str
    timestamp: str
    db_id: str
    question: str
    route: str
    status: str
    sql: str
    execution_time_ms: float


class QueryHistoryResponse(BaseModel):
    """Query history response."""
    total: int
    items: list[QueryHistoryItem]


class PerformanceStats(BaseModel):
    """Performance statistics."""
    total_queries: int
    avg_execution_time_ms: float
    local_route_count: int
    api_route_count: int
    success_count: int
    error_count: int
    fastest_query_ms: float
    slowest_query_ms: float
    queries_by_database: dict[str, int]
