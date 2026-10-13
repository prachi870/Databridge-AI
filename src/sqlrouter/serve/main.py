"""FastAPI main application."""
import time
import threading
import collections
import sqlite3
import shutil
import csv
import io
import json
import math
import uuid
import logging
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from contextlib import asynccontextmanager, closing
from typing import Optional

logger = logging.getLogger(__name__)

from fastapi import Depends, FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from sqlrouter.common.prompt import build_messages, render
from sqlrouter.common.sqlexec import _jsonable, preview_sql
from sqlrouter.common.teacher import Teacher

from .settings import settings
from . import auth
from .schemas import (
    AuthCredentials,
    RouteRequest,
    RouteResponse,
    ExecutePreviewRequest,
    Timing,
    HealthResponse,
    ConfigResponse,
    DatabaseInfo,
    BenchmarkResponse,
    QueryHistoryItem,
    QueryHistoryResponse,
    PerformanceStats,
    QueryFeedbackRequest,
)
from .store import Store
from .router_logic import decide_route, estimate_cost, estimate_always_api_cost


# Global state
state: dict = {}
gpu_lock = threading.Lock()  # For thread-safe GPU access

# Rate limiting state
_request_history: dict[str, list[float]] = collections.defaultdict(list)
_api_calls = {"date": time.strftime("%Y-%m-%d"), "count": 0}

# Query history storage (in-memory for now, could be persisted to SQLite)
_query_history: list[dict] = []
_pending_previews: dict[str, dict] = {}
_feedback_lock = threading.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup/shutdown."""
    print(f"\n{'='*50}")
    print(f"Starting SQL Router backend")
    print(f"Mode: {settings.mode}")
    print(f"{'='*50}\n")
    
    # Validate settings
    try:
        settings.validate()
    except Exception as e:
        print(f"ERROR: Configuration validation failed: {e}")
        raise
    
    # Load store (works in both modes)
    auth.initialize_auth_store(settings.artifacts / "auth.sqlite")
    print("Loading artifact store...")
    state["store"] = Store(settings.artifacts)
    print(f"  ✓ Loaded {len(state['store'].db_ids)} databases")
    
    # Initialize model service in live mode
    if settings.mode == "live":
        print("\nInitializing live mode components...")
        
        try:
            from .model_service import ModelService
            
            probe_path = settings.artifacts / "probes" / "sep.joblib"
            
            state["model"] = ModelService(settings.model_dir, str(probe_path))
            print("  ✓ Model service ready")
            
            state["teacher"] = Teacher()
            print(f"  ✓ Teacher API ready ({state['teacher'].provider})")
            
        except Exception as e:
            print(f"  ✗ Failed to initialize live mode: {e}")
            raise
    else:
        print("\nReplay mode: using cached benchmark results")
        # Initialize teacher for custom questions fallback
        try:
            state["teacher"] = Teacher()
            print(f"  ✓ Teacher API ready for custom questions ({state['teacher'].provider})")
        except Exception as e:
            print(f"  ⚠ Teacher API not configured - custom questions will not work")
            print(f"    Configure GROQ_API_KEY, ANTHROPIC_API_KEY or OPENAI_API_KEY in .env file")
            state["teacher"] = None
    
    print(f"\n{'='*50}")
    print(f"Backend ready at http://{settings.host}:{settings.port}")
    print(f"API docs: http://{settings.host}:{settings.port}/docs")
    print(f"{'='*50}\n")
    
    yield
    
    print("\nShutting down...")


# Create FastAPI app
app = FastAPI(
    title="SQL Router API",
    description="Route text-to-SQL queries between local model and frontier API",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def require_authentication(request: Request, call_next):
    path = request.url.path
    is_public = path == "/api/health" or path in {"/api/auth/register", "/api/auth/login"}
    if request.method != "OPTIONS" and path.startswith("/api/") and not is_public:
        scheme, _, token = request.headers.get("Authorization", "").partition(" ")
        user = auth.get_user(settings.artifacts / "auth.sqlite", token) if scheme.lower() == "bearer" and token else None
        if user is None:
            return JSONResponse(
                status_code=401,
                content={"detail": "Sign in to access this project."},
            )
    return await call_next(request)


def rate_limit(request: Request):
    """Check rate limit for an IP address."""
    ip = request.client.host
    now = time.time()
    
    # Clean old requests (outside 1-minute window)
    _request_history[ip] = [
        t for t in _request_history[ip] if now - t < 60
    ]
    
    # Check limit
    if len(_request_history[ip]) >= settings.rate_per_min:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Maximum {settings.rate_per_min} requests per minute.",
        )
    
    # Record this request
    _request_history[ip].append(now)


def check_api_budget():
    """Check and update daily API call budget."""
    today = time.strftime("%Y-%m-%d")
    
    # Reset counter if new day
    if _api_calls["date"] != today:
        _api_calls["date"] = today
        _api_calls["count"] = 0
    
    # Check limit
    if _api_calls["count"] >= settings.daily_api_cap:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Daily API call limit ({settings.daily_api_cap}) reached. "
                "Use local model or try again tomorrow."
            ),
        )
    
    # Increment counter
    _api_calls["count"] += 1


def require_user(request: Request) -> dict:
    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    user = auth.get_user(settings.artifacts / "auth.sqlite", token) if scheme.lower() == "bearer" and token else None
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to access this project.")
    return user


@app.post("/api/auth/register", status_code=201)
async def register_account(credentials: AuthCredentials, request: Request):
    rate_limit(request)
    if len(credentials.password) < 12:
        raise HTTPException(status_code=422, detail="Password must be at least 12 characters.")
    try:
        token, user = auth.create_account(
            settings.artifacts / "auth.sqlite",
            credentials.email,
            credentials.password,
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return {"access_token": token, "token_type": "bearer", "user": user}


@app.post("/api/auth/login")
async def login_account(credentials: AuthCredentials, request: Request):
    rate_limit(request)
    session = auth.authenticate(
        settings.artifacts / "auth.sqlite",
        credentials.email,
        credentials.password,
    )
    if session is None:
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    token, user = session
    return {"access_token": token, "token_type": "bearer", "user": user}


@app.get("/api/auth/me")
async def get_current_user(user: dict = Depends(require_user)):
    return user


@app.post("/api/auth/logout", dependencies=[Depends(require_user)])
async def logout_account(request: Request):
    _, _, token = request.headers.get("Authorization", "").partition(" ")
    auth.revoke_session(settings.artifacts / "auth.sqlite", token)
    return {"success": True}


@app.get("/api/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    device = None
    
    if settings.mode == "live" and "model" in state:
        import torch
        device = str(state["model"].model.device)
    
    return HealthResponse(
        status="ok",
        mode=settings.mode,
        device=device,
        teacher_configured=state.get("teacher") is not None,
    )


@app.get("/api/config", response_model=ConfigResponse)
async def get_config():
    """Get router configuration."""
    config = state["store"].get_config()
    
    return ConfigResponse(
        layer=config["layer"],
        threshold=config["threshold"],
        alpha=config["alpha"],
        delta=config["delta"],
        student=config["student"],
        teacher=config["teacher"],
        mode=settings.mode,
        costs=config["costs"],
    )


@app.get("/api/databases", response_model=list[DatabaseInfo])
async def get_databases():
    """Get list of available databases with schemas."""
    return state["store"].get_databases()


@app.get("/api/database/{db_id}/profile")
async def get_database_profile(db_id: str):
    """Summarize table sizes, column types, nulls, ranges, and example rows."""
    try:
        db_path = state["store"].get_db_path(db_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    tables = []
    with closing(sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        table_names = [
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        for table_name in table_names:
            quoted_table = '"' + table_name.replace('"', '""') + '"'
            column_info = connection.execute(f"PRAGMA table_info({quoted_table})").fetchall()
            columns = []
            for column in column_info:
                column_name = column["name"]
                quoted_column = '"' + column_name.replace('"', '""') + '"'
                column_type = (column["type"] or "").upper()
                stats = connection.execute(
                    f"SELECT COUNT(*) - COUNT({quoted_column}) AS null_count, "
                    f"MIN({quoted_column}) AS min_value, MAX({quoted_column}) AS max_value "
                    f"FROM {quoted_table}"
                ).fetchone()
                columns.append({
                    "name": column_name,
                    "type": column_type or "UNKNOWN",
                    "null_count": stats["null_count"],
                    "min": stats["min_value"] if any(
                        token in column_type for token in ("INT", "REAL", "NUM", "DEC", "FLOAT", "DOUBLE")
                    ) else None,
                    "max": stats["max_value"] if any(
                        token in column_type for token in ("INT", "REAL", "NUM", "DEC", "FLOAT", "DOUBLE")
                    ) else None,
                })
            sample_rows = connection.execute(f"SELECT * FROM {quoted_table} LIMIT 3").fetchall()
            row_count = connection.execute(f"SELECT COUNT(*) FROM {quoted_table}").fetchone()[0]
            tables.append({
                "name": table_name,
                "row_count": row_count,
                "columns": columns,
                "examples": [
                    {key: _jsonable(value) for key, value in dict(row).items()}
                    for row in sample_rows
                ],
            })
    return {"db_id": db_id, "tables": tables}


@app.get("/api/benchmark/questions", response_model=BenchmarkResponse)
async def get_benchmark_questions(
    db_id: Optional[str] = None,
    offset: int = 0,
    limit: int = 50,
):
    """Get paginated benchmark questions."""
    # Validate limit
    limit = min(limit, 200)
    
    questions, total = state["store"].get_questions(db_id, offset, limit)
    
    return BenchmarkResponse(total=total, items=questions)


@app.get("/api/metrics/{name}")
async def get_metric(name: str):
    """Get a metric file (pareto, auroc, layers, ablation, calibration, summary)."""
    try:
        return state["store"].get_metric(name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Metric '{name}' not found. Run the export script first.",
        )


@app.post("/api/route", response_model=RouteResponse)
async def route_question(req: RouteRequest, request: Request):
    """Route a question to local model or API."""
    # Rate limiting
    rate_limit(request)
    
    # Get store and config
    store = state["store"]
    config = store.get_config()
    
    # Validate database
    try:
        db_path = store.get_db_path(req.db_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    # Use custom threshold or default
    threshold = req.threshold if req.threshold is not None else config["threshold"]
    
    # Start timing
    t_start = time.perf_counter()
    probe_ms = None
    generate_ms = None
    api_ms = None
    input_tokens = 0
    output_tokens = 0
    
    # REPLAY MODE: Use cached results or fallback to API for custom questions
    if settings.mode == "replay":
        # Look up cached result
        cached = store.find_question(req.db_id, req.question) if not req.context else None
        
        if cached is None:
            # Fallback: Use API for custom questions in replay mode
            logger.info(f"Custom question not in benchmark, using API fallback")
            
            # Check if teacher API is configured
            teacher = state.get("teacher")
            if teacher is None:
                raise HTTPException(
                    status_code=503,
                    detail=(
                        "Custom questions require API access. "
                        "Please configure GROQ_API_KEY, ANTHROPIC_API_KEY or OPENAI_API_KEY in your .env file."
                    ),
                )
            
            # Use API to generate SQL
            check_api_budget()
            schema = store.get_schema(req.db_id)
            context = [turn.model_dump() for turn in req.context]
            messages = build_messages(schema, req.question, context)
            
            logger.info(f"Calling teacher API for custom question...")
            try:
                t0 = time.perf_counter()
                raw_sql, input_tokens, output_tokens = teacher.sql(messages)
                api_ms = (time.perf_counter() - t0) * 1000
                logger.info(f"Teacher API responded in {api_ms:.0f}ms")
            except Exception as e:
                logger.error(f"Teacher API call failed: {e}")
                if getattr(e, "status_code", None) == 404 or "model_not_found" in str(e):
                    detail = (
                        f"The configured {teacher.provider} model '{teacher.model}' is unavailable. "
                        "Set TEACHER_MODEL in .env to an active model and restart the backend."
                    )
                else:
                    detail = f"Failed to generate SQL using API: {str(e)}"
                raise HTTPException(
                    status_code=503,
                    detail=detail,
                ) from e
            
            from sqlrouter.common.prompt import extract_sql
            sql = extract_sql(raw_sql)
            
            # Set route as API since we used the API
            route = "api"
            reason = "Custom question (not in benchmark dataset), routed to API"
            score = 0.0  # No probe score for custom questions in replay mode
        else:
            # Use cached score and SQL
            score = cached["score_sep"]
            route, reason = decide_route(score, threshold, req.mode)
            
            sql = cached["local_sql"] if route == "local" else cached["api_sql"]
    
    # LIVE MODE: Real inference
    else:
        model = state["model"]
        teacher = state["teacher"]
        schema = store.get_schema(req.db_id)
        
        # Build prompt
        context = [turn.model_dump() for turn in req.context]
        prompt = render(model.tokenizer, schema, req.question, context)
        
        # GPU operations must be thread-safe
        with gpu_lock:
            # Probe forward pass
            t0 = time.perf_counter()
            score = model.score(prompt)
            probe_ms = (time.perf_counter() - t0) * 1000
            
            # Routing decision
            route, reason = decide_route(score, threshold, req.mode)
            
            # Generate if local
            if route == "local":
                t0 = time.perf_counter()
                sql = model.generate(prompt)
                generate_ms = (time.perf_counter() - t0) * 1000
        
        # API call if escalated
        if route == "api":
            check_api_budget()
            
            messages = build_messages(schema, req.question, context)
            
            t0 = time.perf_counter()
            raw_sql, input_tokens, output_tokens = teacher.sql(messages)
            api_ms = (time.perf_counter() - t0) * 1000
            
            from sqlrouter.common.prompt import extract_sql
            sql = extract_sql(raw_sql)
    
    query_id = str(uuid.uuid4())
    if req.preview_only:
        generation_ms = (time.perf_counter() - t_start) * 1000
        _pending_previews[query_id] = {
            "db_id": req.db_id,
            "question": req.question,
            "sql": sql,
            "route": route,
            "generation_ms": generation_ms,
        }
        if len(_pending_previews) > 100:
            _pending_previews.pop(next(iter(_pending_previews)))
        return RouteResponse(
            mode=settings.mode,
            route=route,
            reason=reason,
            score=score,
            threshold=threshold,
            sql=sql,
            status="ok",
            error=None,
            columns=[],
            rows=[],
            truncated=False,
            timing=Timing(
                probe_ms=probe_ms,
                generate_ms=generate_ms,
                api_ms=api_ms,
                execute_ms=0.0,
                total_ms=generation_ms,
            ),
            cost_usd=estimate_cost(config["costs"], route, input_tokens, output_tokens),
            always_api_cost_usd=estimate_always_api_cost(config["costs"]),
            requires_confirmation=True,
            safety_warnings=[
                "SQL has not been executed yet. Review it before continuing.",
                "Execution is read-only; database writes and schema changes are blocked.",
            ],
            query_id=query_id,
        )

    # Execute SQL using a read-only connection and SQLite authorizer.
    t0 = time.perf_counter()
    result = preview_sql(str(db_path), sql)
    execute_ms = (time.perf_counter() - t0) * 1000
    
    total_ms = (time.perf_counter() - t_start) * 1000
    
    # Estimate costs
    costs = config["costs"]
    cost_usd = estimate_cost(costs, route, input_tokens, output_tokens)
    always_api_cost = estimate_always_api_cost(costs)
    
    # Save to query history
    _query_history.append({
        "id": query_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "db_id": req.db_id,
        "question": req.question,
        "route": route,
        "status": result["status"],
        "sql": sql,
        "execution_time_ms": total_ms,
        "cost_usd": cost_usd,
    })
    
    # Keep only last 100 queries
    if len(_query_history) > 100:
        _query_history.pop(0)
    
    return RouteResponse(
        mode=settings.mode,
        route=route,
        reason=reason,
        score=score,
        threshold=threshold,
        sql=sql,
        status=result["status"],
        error=result["error"],
        columns=result["columns"],
        rows=result["rows"],
        truncated=result["truncated"],
        timing=Timing(
            probe_ms=probe_ms,
            generate_ms=generate_ms,
            api_ms=api_ms,
            execute_ms=execute_ms,
            total_ms=total_ms,
        ),
        cost_usd=cost_usd,
        always_api_cost_usd=always_api_cost,
        query_id=query_id,
    )


@app.post("/api/execute-preview")
async def execute_reviewed_sql(req: ExecutePreviewRequest, request: Request):
    """Execute reviewed SQL through the same read-only SQL authorizer."""
    rate_limit(request)
    preview = _pending_previews.get(req.query_id)
    if preview is None:
        raise HTTPException(status_code=404, detail="SQL preview not found or already executed")
    if any(preview[field] != getattr(req, field) for field in ("db_id", "question", "sql", "route")):
        raise HTTPException(status_code=409, detail="Dataset, question, route, or SQL changed after review; generate a new preview")
    _pending_previews.pop(req.query_id)

    try:
        db_path = state["store"].get_db_path(req.db_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    started = time.perf_counter()
    result = preview_sql(str(db_path), req.sql)
    execution_ms = (time.perf_counter() - started) * 1000
    _query_history.append({
        "id": req.query_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "db_id": req.db_id,
        "question": req.question,
        "route": req.route,
        "status": result["status"],
        "sql": req.sql,
        "execution_time_ms": preview["generation_ms"] + execution_ms,
        "cost_usd": 0.0,
    })
    if len(_query_history) > 100:
        _query_history.pop(0)

    return {
        **result,
        "execution_ms": execution_ms,
    }


@app.post("/api/feedback")
async def submit_query_feedback(feedback: QueryFeedbackRequest):
    """Save correctness feedback beside project artifacts for future evaluation."""
    query = next((item for item in _query_history if item["id"] == feedback.query_id), None)
    if query is None:
        raise HTTPException(status_code=404, detail="Executed query not found in recent history")

    feedback_path = settings.artifacts / "results" / "user_feedback.json"
    with _feedback_lock:
        records = json.loads(feedback_path.read_text()) if feedback_path.exists() else []
        record = {
            "query_id": feedback.query_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "db_id": query["db_id"],
            "question": query["question"],
            "sql": query["sql"],
            "route": query["route"],
            "correct": feedback.correct,
            "expected_answer": feedback.expected_answer,
        }
        records = [item for item in records if item["query_id"] != feedback.query_id]
        records.append(record)
        feedback_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = feedback_path.with_suffix(".json.tmp")
        temporary_path.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n")
        temporary_path.replace(feedback_path)

    return {"success": True, "message": "Feedback saved for future evaluation"}


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "sqlrouter.serve.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


def _clean_identifier(value: str) -> str:
    identifier = "".join(c if c.isalnum() or c in "_-" else "_" for c in value.strip())
    identifier = identifier.strip("_-")
    if not identifier:
        raise ValueError("Names must contain at least one letter or number")
    if not (identifier[0].isalpha() or identifier[0] == "_"):
        identifier = f"data_{identifier}"
    return identifier[:64]


def _unique_identifiers(values: list[str]) -> list[str]:
    unique = []
    used: set[str] = set()
    for value in values:
        base = _clean_identifier(value)
        candidate = base
        suffix = 2
        while candidate.casefold() in used:
            ending = f"_{suffix}"
            candidate = f"{base[:64 - len(ending)]}{ending}"
            suffix += 1
        used.add(candidate.casefold())
        unique.append(candidate)
    return unique


def _parse_csv(content: bytes, filename: str) -> tuple[str, list[str], list[list[Optional[str]]]]:
    try:
        reader = csv.reader(
            io.StringIO(content.decode("utf-8-sig"), newline=""),
            strict=True,
        )
        headers = next(reader, [])
    except UnicodeDecodeError as error:
        raise ValueError(f"{filename}: CSV must be UTF-8 encoded") from error
    except csv.Error as error:
        raise ValueError(f"{filename}: invalid CSV format: {error}") from error

    if not headers or not any(header.strip() for header in headers):
        raise ValueError(f"{filename}: CSV is empty or has no column headers")
    headers = _unique_identifiers([
        header.strip() or f"column_{index}"
        for index, header in enumerate(headers)
    ])
    rows: list[list[Optional[str]]] = []
    try:
        for row_number, row in enumerate(reader, start=2):
            if not row or not any(value.strip() for value in row):
                continue
            if len(row) != len(headers):
                raise ValueError(
                    f"{filename}: row {row_number} has {len(row)} values; "
                    f"expected {len(headers)}"
                )
            rows.append([value if value != "" else None for value in row])
    except csv.Error as error:
        raise ValueError(f"{filename}: invalid CSV format: {error}") from error

    if not rows:
        raise ValueError(f"{filename}: CSV has no data rows")
    table_name = _clean_identifier(Path(filename.replace("\\", "/").rsplit("/", 1)[-1]).stem)
    return table_name, headers, rows


def _infer_sqlite_type(values: list[Optional[str]]) -> str:
    populated = [value.strip() for value in values if value and value.strip()]
    if not populated:
        return "TEXT"
    try:
        for value in populated:
            int(value)
        return "INTEGER"
    except ValueError:
        pass
    try:
        for value in populated:
            if not math.isfinite(float(value)):
                return "TEXT"
        return "REAL"
    except ValueError:
        return "TEXT"


async def _upload_database(
    file: Optional[UploadFile],
    files: Optional[list[UploadFile]],
    requested_db_id: Optional[str],
):
    uploads = ([file] if file is not None else []) + (files or [])
    if not uploads:
        raise HTTPException(status_code=400, detail="Choose at least one file to upload")

    names = [(upload.filename or "").replace("\\", "/").rsplit("/", 1)[-1] for upload in uploads]
    extensions = [Path(name).suffix.lower() for name in names]
    csv_upload = all(extension == ".csv" for extension in extensions)
    sqlite_extensions = {".sqlite", ".db", ".sqlite3"}
    if len(uploads) > 1 and not csv_upload:
        raise HTTPException(status_code=400, detail="Multiple-file uploads must contain CSV files only")
    if len(uploads) == 1 and extensions[0] not in sqlite_extensions | {".csv", ".zip"}:
        raise HTTPException(
            status_code=400,
            detail="Allowed formats: .sqlite, .db, .sqlite3, .csv, or .zip",
        )

    contents = []
    for upload, name in zip(uploads, names):
        content = await upload.read(100 * 1024 * 1024 + 1)
        if len(content) > 100 * 1024 * 1024:
            raise HTTPException(status_code=413, detail=f"{name} exceeds the 100MB file limit")
        contents.append(content)
    if sum(map(len, contents)) > 100 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Combined upload exceeds the 100MB limit")

    source = "csv" if csv_upload or extensions[0] == ".zip" else "sqlite"
    csv_sources: list[tuple[str, bytes]] = []
    sqlite_content: Optional[bytes] = None
    if csv_upload:
        csv_sources = list(zip(names, contents))
    elif extensions[0] == ".zip":
        try:
            with zipfile.ZipFile(io.BytesIO(contents[0])) as archive:
                members = [item for item in archive.infolist() if not item.is_dir()]
                if any(Path(item.filename).suffix.lower() != ".csv" for item in members):
                    raise HTTPException(status_code=400, detail="ZIP archives may contain CSV files only")
                if not members:
                    raise HTTPException(status_code=400, detail="ZIP archive contains no CSV files")
                if len(members) > 100:
                    raise HTTPException(status_code=400, detail="ZIP archives may contain at most 100 CSV files")
                if sum(item.file_size for item in members) > 500 * 1024 * 1024:
                    raise HTTPException(status_code=413, detail="Expanded ZIP exceeds the 500MB limit")
                csv_sources = [
                    (item.filename.replace("\\", "/").rsplit("/", 1)[-1], archive.read(item))
                    for item in members
                ]
        except zipfile.BadZipFile as error:
            raise HTTPException(status_code=400, detail="Uploaded ZIP archive is invalid") from error
    else:
        sqlite_content = contents[0]

    try:
        if source == "csv":
            if len(csv_sources) > 100:
                raise HTTPException(status_code=400, detail="Upload may contain at most 100 CSV files")
            parsed = [_parse_csv(content, name) for name, content in csv_sources]
            table_names = _unique_identifiers([table[0] for table in parsed])
            parsed = [
                (table_names[index], headers, rows)
                for index, (_, headers, rows) in enumerate(parsed)
            ]
            default_db_id = Path(names[0]).stem
        else:
            parsed = []
            default_db_id = Path(names[0]).stem
        database_id = _clean_identifier(requested_db_id or default_db_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    store = state["store"]
    db_dir = settings.artifacts / "demo_dbs" / database_id
    if db_dir.exists() or database_id in store.db_ids:
        raise HTTPException(
            status_code=409,
            detail=f"Database '{database_id}' already exists. Choose another name or delete it first.",
        )

    registered = False
    try:
        db_dir.mkdir(parents=True, exist_ok=False)
        db_path = db_dir / f"{database_id}.sqlite"
        if source == "csv":
            with closing(sqlite3.connect(db_path)) as connection, connection:
                for table_name, headers, rows in parsed:
                    column_types = [
                        _infer_sqlite_type([row[index] for row in rows])
                        for index in range(len(headers))
                    ]
                    columns = ",\n".join(
                        f'    "{header}" {column_types[index]}'
                        for index, header in enumerate(headers)
                    )
                    connection.execute(f'CREATE TABLE "{table_name}" (\n{columns}\n)')
                    placeholders = ", ".join("?" for _ in headers)
                    connection.executemany(
                        f'INSERT INTO "{table_name}" VALUES ({placeholders})',
                        rows,
                    )
            table_names = [table_name for table_name, _, _ in parsed]
        else:
            db_path.write_bytes(sqlite_content or b"")
            with closing(sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)) as connection:
                table_names = [
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND sql IS NOT NULL"
                    )
                ]
                if not table_names:
                    raise HTTPException(status_code=400, detail="Invalid database: No tables found")

        store.register_database(database_id)
        registered = True
        state["store"] = Store(settings.artifacts)
    except HTTPException:
        if registered:
            store.unregister_database(database_id)
        if db_dir.exists():
            try:
                shutil.rmtree(db_dir)
            except OSError:
                logger.exception("Failed to clean up incomplete upload at %s", db_dir)
        raise
    except FileExistsError as error:
        raise HTTPException(
            status_code=409,
            detail=f"Database '{database_id}' already exists.",
        ) from error
    except sqlite3.Error as error:
        if registered:
            store.unregister_database(database_id)
        if db_dir.exists():
            try:
                shutil.rmtree(db_dir)
            except OSError:
                logger.exception("Failed to clean up incomplete upload at %s", db_dir)
        raise HTTPException(status_code=400, detail=f"Could not import database: {error}") from error
    except (OSError, ValueError) as error:
        if registered:
            store.unregister_database(database_id)
        if db_dir.exists():
            try:
                shutil.rmtree(db_dir)
            except OSError:
                logger.exception("Failed to clean up incomplete upload at %s", db_dir)
        logger.exception("Database upload failed for %s", database_id)
        raise HTTPException(status_code=500, detail=f"Failed to process upload: {error}") from error

    row_counts = {
        table_name: len(rows)
        for table_name, _, rows in parsed
    } if source == "csv" else {}
    if source == "csv":
        details = "; ".join(
            f"{table_name} ({len(rows)} rows; "
            f"{', '.join(f'{headers[index]} { _infer_sqlite_type([row[index] for row in rows])}' for index in range(len(headers)))})"
            for table_name, headers, rows in parsed
        )
        question = f"📤 Uploaded CSV dataset: {database_id}"
        summary = f"-- CSV import\n-- {details}"
    else:
        question = f"📤 Uploaded SQLite database: {names[0]}"
        summary = f"-- SQLite database upload\n-- Tables: {', '.join(table_names)}"
    _query_history.append({
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "db_id": database_id,
        "question": question,
        "route": "upload",
        "status": "ok",
        "sql": summary,
        "execution_time_ms": 0.0,
        "cost_usd": 0.0,
    })
    if len(_query_history) > 100:
        _query_history.pop(0)

    return {
        "success": True,
        "db_id": database_id,
        "message": f"Database '{database_id}' uploaded successfully",
        "source": source,
        "tables": len(table_names),
        "table_names": table_names,
        "rows": sum(row_counts.values()) if source == "csv" else None,
        "row_counts": row_counts,
    }


@app.post("/api/upload-database")
async def upload_database(
    file: Optional[UploadFile] = File(None),
    files: Optional[list[UploadFile]] = File(None),
    db_id: Optional[str] = Form(None),
):
    return await _upload_database(file, files, db_id)


@app.delete("/api/database/{db_id}")
async def delete_database(db_id: str):
    """
    Delete a custom uploaded database.
    
    Args:
        db_id: Database identifier to delete
        
    Returns:
        Success message
    """
    store = state["store"]
    if db_id not in store.db_ids:
        raise HTTPException(
            status_code=404,
            detail=f"Database '{db_id}' not found"
        )

    try:
        db_path = store.get_db_path(db_id)
    except (ValueError, FileNotFoundError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    db_dir = db_path.parent
    try:
        shutil.rmtree(db_dir)
        store.unregister_database(db_id)
        state["store"] = Store(settings.artifacts)

        query_id = str(uuid.uuid4())
        _query_history.append({
            "id": query_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "db_id": db_id,
            "question": f"🗑️ Deleted database: {db_id}",
            "route": "delete",
            "status": "ok",
            "sql": f"-- Database Deletion\n-- Removed: {db_id}",
            "execution_time_ms": 0.0,
            "cost_usd": 0.0,
        })
        
        if len(_query_history) > 100:
            _query_history.pop(0)

        return {
            "success": True,
            "message": f"Database '{db_id}' deleted successfully"
        }
    except OSError as e:
        logger.exception("Failed to delete database %s", db_id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete database: {str(e)}"
        ) from e


@app.get("/api/history", response_model=QueryHistoryResponse)
async def get_query_history(
    offset: int = 0,
    limit: int = 50,
):
    """
    Get query history.
    
    Args:
        offset: Pagination offset
        limit: Maximum number of items to return
        
    Returns:
        Query history with pagination
    """
    # Validate limit
    limit = min(limit, 200)
    
    # Get total count
    total = len(_query_history)
    
    # Get slice (reverse order - newest first)
    history_slice = list(reversed(_query_history))[offset:offset + limit]
    
    items = [
        QueryHistoryItem(
            id=item["id"],
            timestamp=item["timestamp"],
            db_id=item["db_id"],
            question=item["question"],
            route=item["route"],
            status=item["status"],
            sql=item["sql"],
            execution_time_ms=item["execution_time_ms"],
        )
        for item in history_slice
    ]
    
    return QueryHistoryResponse(total=total, items=items)


@app.delete("/api/history/{query_id}")
async def delete_query_history(query_id: str):
    """
    Delete a query from history.
    
    Args:
        query_id: Query identifier to delete
        
    Returns:
        Success message
    """
    global _query_history
    
    # Find and remove the query
    original_length = len(_query_history)
    _query_history = [q for q in _query_history if q["id"] != query_id]
    
    if len(_query_history) == original_length:
        raise HTTPException(
            status_code=404,
            detail=f"Query '{query_id}' not found in history"
        )
    
    return {
        "success": True,
        "message": f"Query '{query_id}' deleted from history"
    }


@app.delete("/api/history")
async def clear_query_history():
    """
    Clear all query history.
    
    Returns:
        Success message
    """
    global _query_history
    count = len(_query_history)
    _query_history = []
    
    return {
        "success": True,
        "message": f"Cleared {count} queries from history"
    }


@app.get("/api/performance", response_model=PerformanceStats)
async def get_performance_stats():
    """
    Get performance statistics from query history.
    
    Returns:
        Performance statistics
    """
    if not _query_history:
        return PerformanceStats(
            total_queries=0,
            avg_execution_time_ms=0.0,
            local_route_count=0,
            api_route_count=0,
            success_count=0,
            error_count=0,
            fastest_query_ms=0.0,
            slowest_query_ms=0.0,
            queries_by_database={},
        )
    
    # Calculate statistics
    execution_times = [q["execution_time_ms"] for q in _query_history]
    local_count = sum(1 for q in _query_history if q["route"] == "local")
    api_count = sum(1 for q in _query_history if q["route"] == "api")
    success_count = sum(1 for q in _query_history if q["status"] == "ok")
    error_count = sum(1 for q in _query_history if q["status"] == "err")
    
    # Queries by database
    db_counts: dict[str, int] = {}
    for q in _query_history:
        db_id = q["db_id"]
        db_counts[db_id] = db_counts.get(db_id, 0) + 1
    
    return PerformanceStats(
        total_queries=len(_query_history),
        avg_execution_time_ms=sum(execution_times) / len(execution_times),
        local_route_count=local_count,
        api_route_count=api_count,
        success_count=success_count,
        error_count=error_count,
        fastest_query_ms=min(execution_times),
        slowest_query_ms=max(execution_times),
        queries_by_database=db_counts,
    )


@app.get("/api/evaluation")
async def get_evaluation_summary():
    """Compare saved benchmark outcomes for each model and the configured router."""
    store = state["store"]
    questions = store.questions
    feedback_path = settings.artifacts / "results" / "user_feedback.json"
    feedback = json.loads(feedback_path.read_text()) if feedback_path.exists() else []
    reviewed_count = len(feedback)
    feedback_accuracy = (
        sum(bool(item["correct"]) for item in feedback) / reviewed_count * 100
        if reviewed_count
        else 0.0
    )
    total = len(questions)
    if total == 0:
        return {
            "sample_count": 0,
            "local_accuracy": 0.0,
            "api_accuracy": 0.0,
            "routed_accuracy": 0.0,
            "api_route_percent": 0.0,
            "estimated_cost_savings_percent": 0.0,
            "user_feedback_count": reviewed_count,
            "user_feedback_accuracy": feedback_accuracy,
        }

    threshold = store.get_config()["threshold"]
    routed_correct = 0
    api_routes = 0
    costs = store.get_config().get("costs", {})
    estimated_router_cost = 0.0
    always_api_cost = costs.get("c_api", 0.0)

    for question in questions:
        route, _ = decide_route(question["score_sep"], threshold, "auto")
        if route == "api":
            api_routes += 1
            routed_correct += bool(question["api_ok"])
            estimated_router_cost += costs.get("c_prefill", 0.0) + always_api_cost
        else:
            routed_correct += bool(question["local_ok"])
            estimated_router_cost += costs.get("c_prefill", 0.0) + costs.get("c_decode", 0.0)

    local_accuracy = sum(bool(question["local_ok"]) for question in questions) / total
    api_accuracy = sum(bool(question["api_ok"]) for question in questions) / total
    baseline_cost = always_api_cost * total
    savings = (
        max(0.0, (baseline_cost - estimated_router_cost) / baseline_cost * 100)
        if baseline_cost > 0
        else 0.0
    )

    return {
        "sample_count": total,
        "local_accuracy": local_accuracy * 100,
        "api_accuracy": api_accuracy * 100,
        "routed_accuracy": routed_correct / total * 100,
        "api_route_percent": api_routes / total * 100,
        "estimated_cost_savings_percent": savings,
        "user_feedback_count": reviewed_count,
        "user_feedback_accuracy": feedback_accuracy,
    }
