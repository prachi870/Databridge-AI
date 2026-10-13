"""Data store for artifacts and benchmark results."""
import json
import re
import threading
from pathlib import Path
from typing import Optional

from sqlrouter.common.prompt import schema_from_sqlite


# Pattern for safe database IDs (prevent path traversal)
_SAFE_ID = re.compile(r"^[A-Za-z0-9_\-]+$")

# Available metric files
METRICS = {"pareto", "auroc", "layers", "ablation", "calibration", "summary"}
_INDEX_LOCK = threading.Lock()


def _normalize_question(q: str) -> str:
    """Normalize question for matching (lowercase, collapse whitespace)."""
    return " ".join(q.lower().split())


class Store:
    """Storage for artifacts, config, and benchmark data."""
    
    def __init__(self, artifacts_path: Path):
        """Initialize store from artifacts directory.
        
        Args:
            artifacts_path: Path to artifacts/ directory
        """
        self.artifacts = artifacts_path
        self.results_dir = artifacts_path / "results"
        self.demo_dbs_dir = artifacts_path / "demo_dbs"
        
        # Load router config
        config_path = self.results_dir / "router_config.json"
        if not config_path.exists():
            raise FileNotFoundError(
                f"Router config not found at {config_path}. "
                "Run the export script or generate fixtures."
            )
        
        self.config = json.loads(config_path.read_text())
        
        # Load questions for replay mode
        questions_path = self.results_dir / "questions.json"
        if questions_path.exists():
            self.questions = json.loads(questions_path.read_text())
            
            # Build lookup index: (db_id, normalized_question) -> question dict
            self._question_index = {
                (q["db_id"], _normalize_question(q["question"])): q
                for q in self.questions
            }
        else:
            self.questions = []
            self._question_index = {}
        
        # Load available database IDs
        db_index_path = self.demo_dbs_dir / "index.json"
        if db_index_path.exists():
            self.db_ids = json.loads(db_index_path.read_text())
        else:
            self.db_ids = []
        
        # Cache for schemas
        self._schema_cache: dict[str, str] = {}
    
    def get_config(self) -> dict:
        """Get router configuration."""
        return self.config
    
    def get_db_path(self, db_id: str) -> Path:
        """Get path to a database file.
        
        Args:
            db_id: Database ID
            
        Returns:
            Path to SQLite file
            
        Raises:
            ValueError: If db_id is invalid or not found
        """
        if not _SAFE_ID.match(db_id):
            raise ValueError(f"Invalid database ID: {db_id}")
        
        if db_id not in self.db_ids:
            raise ValueError(f"Database not found: {db_id}")
        
        path = self.demo_dbs_dir / db_id / f"{db_id}.sqlite"
        
        if not path.exists():
            raise FileNotFoundError(f"Database file missing: {path}")
        
        return path

    def register_database(self, db_id: str) -> None:
        """Persist a newly uploaded database in the available database index."""
        if not _SAFE_ID.fullmatch(db_id):
            raise ValueError(f"Invalid database ID: {db_id}")

        db_path = self.demo_dbs_dir / db_id / f"{db_id}.sqlite"
        if not db_path.is_file():
            raise FileNotFoundError(f"Database file missing: {db_path}")

        with _INDEX_LOCK:
            index_path = self.demo_dbs_dir / "index.json"
            index_path.parent.mkdir(parents=True, exist_ok=True)
            db_ids = json.loads(index_path.read_text()) if index_path.exists() else []
            if db_id not in db_ids:
                db_ids.append(db_id)
                temporary_path = index_path.with_suffix(".json.tmp")
                temporary_path.write_text(json.dumps(db_ids, indent=2) + "\n")
                temporary_path.replace(index_path)

        self.db_ids = db_ids
        self._schema_cache.pop(db_id, None)

    def unregister_database(self, db_id: str) -> None:
        """Remove a database ID from the persisted index."""
        with _INDEX_LOCK:
            index_path = self.demo_dbs_dir / "index.json"
            if not index_path.exists():
                self.db_ids = []
                return

            db_ids = json.loads(index_path.read_text())
            if db_id in db_ids:
                db_ids.remove(db_id)
                temporary_path = index_path.with_suffix(".json.tmp")
                temporary_path.write_text(json.dumps(db_ids, indent=2) + "\n")
                temporary_path.replace(index_path)

        self.db_ids = db_ids
        self._schema_cache.pop(db_id, None)
    
    def get_schema(self, db_id: str) -> str:
        """Get schema for a database (cached).
        
        Args:
            db_id: Database ID
            
        Returns:
            Schema text (CREATE TABLE statements)
        """
        if db_id not in self._schema_cache:
            db_path = self.get_db_path(db_id)
            self._schema_cache[db_id] = schema_from_sqlite(str(db_path))
        
        return self._schema_cache[db_id]
    
    def find_question(self, db_id: str, question: str) -> Optional[dict]:
        """Find a question in the benchmark for replay mode.
        
        Args:
            db_id: Database ID
            question: Question text
            
        Returns:
            Question dict if found, None otherwise
        """
        key = (db_id, _normalize_question(question))
        return self._question_index.get(key)
    
    def get_questions(
        self,
        db_id: Optional[str] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[dict], int]:
        """Get paginated benchmark questions.
        
        Args:
            db_id: Optional filter by database ID
            offset: Skip this many questions
            limit: Maximum number to return
            
        Returns:
            Tuple of (questions, total_count)
        """
        # Filter by database if specified
        if db_id:
            filtered = [q for q in self.questions if q["db_id"] == db_id]
        else:
            filtered = self.questions
        
        total = len(filtered)
        
        # Apply pagination
        start = max(0, offset)
        end = min(start + limit, total)
        
        return filtered[start:end], total
    
    def get_metric(self, name: str) -> dict:
        """Get a metric file.
        
        Args:
            name: Metric name (pareto, auroc, etc.)
            
        Returns:
            Metric data as dict
            
        Raises:
            ValueError: If metric name is invalid
            FileNotFoundError: If metric file doesn't exist
        """
        if name not in METRICS:
            raise ValueError(f"Unknown metric: {name}. Available: {METRICS}")
        
        path = self.results_dir / f"{name}.json"
        
        if not path.exists():
            raise FileNotFoundError(f"Metric file not found: {path}")
        
        return json.loads(path.read_text())
    
    def get_databases(self) -> list[dict]:
        """Get list of available databases with schemas.
        
        Returns:
            List of dicts with db_id and schema
        """
        return [
            {"db_id": db_id, "schema": self.get_schema(db_id)}
            for db_id in self.db_ids
        ]
