"""
Phase 1: Generate database-disjoint splits from Spider dataset.

This script ensures no database ID appears in multiple splits,
which is critical for testing on truly unseen schemas.
"""
import json
import random
from pathlib import Path
from sqlrouter.common.splits import check_leakage


def main():
    # Set random seed for reproducibility
    R = random.Random(7)
    
    # Paths
    spider_dir = Path("data/spider")
    train_path = spider_dir / "train_spider.json"
    dev_path = spider_dir / "dev.json"
    output_dir = Path("data/splits")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Check that Spider data exists
    if not train_path.exists():
        print(f"ERROR: {train_path} not found!")
        print("\nPlease download Spider dataset from:")
        print("https://yale-lily.github.io/spider")
        print("\nExtract to data/spider/ directory")
        return
    
    print("Loading Spider data...")
    train = json.load(open(train_path))
    dev = json.load(open(dev_path))
    
    print(f"Loaded {len(train)} training examples, {len(dev)} dev examples")
    
    # Group by database ID
    def by_db(rows):
        d = {}
        for r in rows:
            d.setdefault(r["db_id"], []).append(r)
        return d
    
    train_by_db = by_db(train)
    dev_by_db = by_db(dev)
    
    # Split training databases: 75% for SFT, 25% for probe training
    train_dbs = sorted(train_by_db.keys())
    R.shuffle(train_dbs)
    cut = int(len(train_dbs) * 0.75)
    sft_dbs = train_dbs[:cut]
    probe_dbs = train_dbs[cut:]
    
    print(f"\nTraining databases: {len(train_dbs)}")
    print(f"  SFT databases: {len(sft_dbs)}")
    print(f"  Probe databases: {len(probe_dbs)}")
    
    # Split dev databases: first 6 for calibration, rest for test
    dev_dbs = sorted(dev_by_db.keys())
    R.shuffle(dev_dbs)
    cal_dbs = dev_dbs[:6]
    test_dbs = dev_dbs[6:]
    
    print(f"\nDev databases: {len(dev_dbs)}")
    print(f"  Calibration databases: {len(cal_dbs)}")
    print(f"  Test databases: {len(test_dbs)}")
    
    # Pick questions from selected databases
    def pick(rows, dbs, n):
        db_set = set(dbs)
        out = [r for r in rows if r["db_id"] in db_set]
        R.shuffle(out)
        return out[:n]
    
    splits = {
        "sft": pick(train, sft_dbs, 4000),
        "probe": pick(train, probe_dbs, 1500),
        "cal": pick(dev, cal_dbs, 10_000),  # Will get all available
        "test": pick(dev, test_dbs, 10_000),  # Will get all available
    }
    
    # Add stable IDs and keep only needed fields
    output = {}
    for k, v in splits.items():
        output[k] = [
            {
                "id": f"{k}-{i}",
                "db_id": r["db_id"],
                "question": r["question"],
                "gold": r["query"],
            }
            for i, r in enumerate(v)
        ]
    
    # Report sizes
    print("\nSplit sizes:")
    for k, v in output.items():
        print(f"  {k}: {len(v)} questions")
    
    # CRITICAL: Check for database leakage
    print("\nLeakage check:")
    is_valid, message = check_leakage(output)
    print(f"  {message}")
    
    if not is_valid:
        print("\nERROR: Database leakage detected! Not saving splits.")
        return
    
    # Save splits
    output_path = output_dir / "splits.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\nSaved splits to {output_path}")
    print("\n✓ Phase 1 complete: Database-disjoint splits created")


if __name__ == "__main__":
    main()
