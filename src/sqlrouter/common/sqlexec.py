"""Safe, read-only SQL execution with timeouts and authorization."""
import sqlite3
import time
from typing import Literal, Any


# Only allow these SQLite operations (read-only)
_ALLOWED = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION}


def _authorizer(action: int, *_) -> int:
    """SQLite authorizer callback that blocks all non-read operations."""
    return sqlite3.SQLITE_OK if action in _ALLOWED else sqlite3.SQLITE_DENY


def run_sql(
    db_path: str, sql: str, timeout: float = 5.0, max_rows: int = 5000
) -> tuple[Literal["ok", "err"], list[tuple] | str]:
    """Execute SQL query in read-only mode with timeout and row limit.
    
    Args:
        db_path: Path to SQLite database file
        sql: SQL query to execute
        timeout: Maximum execution time in seconds
        max_rows: Maximum number of rows to fetch
        
    Returns:
        Tuple of (status, result) where:
        - status is "ok" or "err"
        - result is list of row tuples on success, error message on failure
    """
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    con.set_authorizer(_authorizer)
    
    # Set up timeout via progress handler
    t0 = time.time()
    con.set_progress_handler(
        lambda: 1 if time.time() - t0 > timeout else 0, 10000
    )
    
    try:
        cur = con.execute(sql)
        rows = cur.fetchmany(max_rows)
        return "ok", rows
    except Exception as e:
        return "err", str(e)
    finally:
        con.close()


def result_key(status: str, rows: list[tuple] | str) -> tuple:
    """Create a hashable fingerprint of a result set (order-insensitive).
    
    All errors share one key. Used for clustering results by semantic equivalence.
    
    Args:
        status: "ok" or "err"
        rows: Result rows or error message
        
    Returns:
        Hashable tuple representing the result
    """
    if status != "ok":
        return ("err",)
    
    # Sort row representations for order-insensitive comparison
    return ("ok", tuple(sorted(repr(r) for r in rows)))


def is_correct(db_path: str, pred_sql: str, gold_sql: str) -> bool:
    """Check if predicted SQL produces the same result as gold SQL.
    
    Args:
        db_path: Path to SQLite database
        pred_sql: Predicted SQL query
        gold_sql: Gold standard SQL query
        
    Returns:
        True if both queries succeed and produce identical results
    """
    ps, pr = run_sql(db_path, pred_sql)
    gs, gr = run_sql(db_path, gold_sql)
    
    return ps == "ok" and gs == "ok" and result_key(ps, pr) == result_key(gs, gr)


def _jsonable(v: Any) -> Any:
    """Convert a value to JSON-safe format."""
    if isinstance(v, (bytes, bytearray)):
        return f"<{len(v)} bytes>"
    return v


def preview_sql(
    db_path: str, sql: str, timeout: float = 5.0, limit: int = 50
) -> dict[str, Any]:
    """Execute SQL and return results in JSON-safe format for the API.
    
    Args:
        db_path: Path to SQLite database
        sql: SQL query to execute
        timeout: Maximum execution time in seconds
        limit: Maximum number of rows to return
        
    Returns:
        Dictionary with keys: status, error, columns, rows, truncated
    """
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    con.set_authorizer(_authorizer)
    
    t0 = time.time()
    con.set_progress_handler(
        lambda: 1 if time.time() - t0 > timeout else 0, 10000
    )
    
    try:
        cur = con.execute(sql)
        cols = [d[0] for d in (cur.description or [])]
        rows = cur.fetchmany(limit + 1)
        
        return {
            "status": "ok",
            "error": None,
            "columns": cols,
            "truncated": len(rows) > limit,
            "rows": [[_jsonable(v) for v in r] for r in rows[:limit]],
        }
    except Exception as e:
        return {
            "status": "err",
            "error": str(e),
            "columns": [],
            "rows": [],
            "truncated": False,
        }
    finally:
        con.close()
