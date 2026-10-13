"""Local account and bearer-session storage for the SQL Router web app."""
import hashlib
import hmac
import secrets
import sqlite3
import time
from contextlib import closing
from pathlib import Path


_ITERATIONS = 310_000
_SESSION_TTL_SECONDS = 7 * 24 * 60 * 60


def initialize_auth_store(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                expires_at INTEGER NOT NULL
            )
        """)
        connection.execute("CREATE INDEX IF NOT EXISTS sessions_expiry_idx ON sessions(expires_at)")


def _password_hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return f"{salt.hex()}:{derived.hex()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    salt_hex, expected_hex = stored_hash.split(":", 1)
    actual_hex = _password_hash(password, bytes.fromhex(salt_hex)).split(":", 1)[1]
    return hmac.compare_digest(actual_hex, expected_hex)


def _new_session(connection: sqlite3.Connection, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    connection.execute(
        "INSERT INTO sessions(token_hash, user_id, expires_at) VALUES (?, ?, ?)",
        (
            hashlib.sha256(token.encode("utf-8")).hexdigest(),
            user_id,
            int(time.time()) + _SESSION_TTL_SECONDS,
        ),
    )
    return token


def create_account(path: Path, email: str, password: str) -> tuple[str, dict]:
    normalized_email = email.strip().lower()
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            cursor = connection.execute(
                "INSERT INTO users(email, password_hash, created_at) VALUES (?, ?, ?)",
                (normalized_email, _password_hash(password), int(time.time())),
            )
        except sqlite3.IntegrityError as error:
            raise ValueError("An account with this email already exists.") from error
        user_id = cursor.lastrowid
        token = _new_session(connection, user_id)
    return token, {"id": user_id, "email": normalized_email}


def authenticate(path: Path, email: str, password: str) -> tuple[str, dict] | None:
    normalized_email = email.strip().lower()
    with closing(sqlite3.connect(path)) as connection, connection:
        row = connection.execute(
            "SELECT id, email, password_hash FROM users WHERE email = ?",
            (normalized_email,),
        ).fetchone()
        if row is None or not _verify_password(password, row[2]):
            return None
        token = _new_session(connection, row[0])
    return token, {"id": row[0], "email": row[1]}


def get_user(path: Path, token: str) -> dict | None:
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = int(time.time())
    with closing(sqlite3.connect(path)) as connection, connection:
        row = connection.execute(
            """SELECT users.id, users.email
               FROM sessions JOIN users ON users.id = sessions.user_id
               WHERE sessions.token_hash = ? AND sessions.expires_at > ?""",
            (token_hash, now),
        ).fetchone()
        connection.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))
    return {"id": row[0], "email": row[1]} if row else None


def revoke_session(path: Path, token: str) -> None:
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))
