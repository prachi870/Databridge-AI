"""Utilities for loading and working with data splits."""
import json
from pathlib import Path
from typing import Optional


def load_splits(splits_path: Optional[str] = None) -> dict[str, list[dict]]:
    """Load the splits.json file.
    
    Args:
        splits_path: Optional custom path to splits.json
        
    Returns:
        Dictionary with keys: sft, probe, cal, test
        Each value is a list of dicts with keys: id, db_id, question, gold
    """
    if splits_path is None:
        splits_path = Path(__file__).parent.parent.parent.parent / "data" / "splits" / "splits.json"
    else:
        splits_path = Path(splits_path)
    
    with open(splits_path, "r") as f:
        return json.load(f)


def load_split(split_name: str, splits_path: Optional[str] = None) -> list[dict]:
    """Load a specific split.
    
    Args:
        split_name: One of 'sft', 'probe', 'cal', 'test'
        splits_path: Optional custom path to splits.json
        
    Returns:
        List of question dicts
    """
    splits = load_splits(splits_path)
    return splits[split_name]


def check_leakage(splits: dict[str, list[dict]]) -> tuple[bool, str]:
    """Check that no database ID appears in multiple splits.
    
    Args:
        splits: Dictionary of splits
        
    Returns:
        Tuple of (is_valid, message)
    """
    db_ids = {}
    
    for split_name, rows in splits.items():
        for row in rows:
            db_id = row["db_id"]
            if db_id in db_ids:
                return False, f"Database {db_id} appears in both {db_ids[db_id]} and {split_name}"
            db_ids[db_id] = split_name
    
    return True, "No database leakage detected"
