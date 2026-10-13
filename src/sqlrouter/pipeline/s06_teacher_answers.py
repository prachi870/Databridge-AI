"""
Phase 3.3: Generate teacher (frontier API) answers for cal and test splits.

Caches results so re-runs don't cost additional API calls.
"""
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from sqlrouter.common.teacher import Teacher
from sqlrouter.common.splits import load_split
from sqlrouter.common.prompt import schema_from_sqlite, build_messages, extract_sql
from sqlrouter.common.sqlexec import is_correct


def process_question(teacher, row, schema, db_path, existing_ids):
    """Process one question, skipping if already cached."""
    if row["id"] in existing_ids:
        return None  # Skip
    
    try:
        # Call teacher API
        messages = build_messages(schema, row["question"])
        text, tin, tout = teacher.sql(messages)
        
        # Extract and check SQL
        api_sql = extract_sql(text)
        api_ok = is_correct(str(db_path), api_sql, row["gold"])
        
        return {
            "id": row["id"],
            "api_sql": api_sql,
            "api_ok": api_ok,
            "tin": tin,
            "tout": tout,
        }
    except Exception as e:
        print(f"\nError on {row['id']}: {e}")
        return None


def main():
    # Initialize teacher
    print("Initializing teacher API client...")
    try:
        teacher = Teacher()
        print(f"Using {teacher.provider} / {teacher.model}")
    except KeyError as e:
        print(f"\nERROR: Missing environment variable: {e}")
        print("Please set TEACHER_PROVIDER, TEACHER_MODEL, and API key in .env")
        return
    
    # Setup cache
    cache_dir = Path("data/cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / "teacher.jsonl"
    
    # Load existing cache
    existing_ids = set()
    if cache_path.exists():
        with open(cache_path, "r") as f:
            for line in f:
                row = json.loads(line)
                existing_ids.add(row["id"])
        print(f"Found {len(existing_ids)} cached answers")
    
    # Prepare questions from cal and test splits
    spider_db_path = Path("data/spider/database")
    
    all_questions = []
    for split_name in ["cal", "test"]:
        split = load_split(split_name)
        
        for row in split:
            if row["id"] not in existing_ids:
                db_id = row["db_id"]
                db_path = spider_db_path / db_id / f"{db_id}.sqlite"
                schema = schema_from_sqlite(str(db_path))
                
                all_questions.append({
                    "row": row,
                    "schema": schema,
                    "db_path": db_path,
                })
    
    if not all_questions:
        print("\nAll questions already cached!")
        print("✓ Phase 3.3 complete: Teacher answers ready")
        return
    
    print(f"\nNeed to process {len(all_questions)} new questions")
    print(f"Estimated cost: ~${len(all_questions) * 0.003:.2f} (rough estimate)")
    
    response = input("\nProceed with API calls? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled")
        return
    
    # Process in parallel (8 threads for API calls)
    results = []
    
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(
                process_question,
                teacher,
                q["row"],
                q["schema"],
                q["db_path"],
                existing_ids
            ): q["row"]["id"]
            for q in all_questions
        }
        
        # Progress bar
        with tqdm(total=len(futures), desc="Calling teacher API") as pbar:
            for future in as_completed(futures):
                result = future.result()
                if result:
                    results.append(result)
                pbar.update(1)
    
    # Append to cache
    print(f"\nSaving {len(results)} new answers to cache...")
    with open(cache_path, "a") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")
    
    # Calculate stats
    total_cached = len(existing_ids) + len(results)
    total_tin = sum(r["tin"] for r in results)
    total_tout = sum(r["tout"] for r in results)
    
    print(f"\n✓ Cache now contains {total_cached} answers")
    print(f"  New input tokens: {total_tin:,}")
    print(f"  New output tokens: {total_tout:,}")
    
    print("\n✓ Phase 3.3 complete: Teacher answers generated")


if __name__ == "__main__":
    main()
