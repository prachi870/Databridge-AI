"""
Phase 5.2: Export results for the frontend app.

Creates the JSON contract files that the backend serves:
- router_config.json: threshold, costs, model names
- summary.json: headline numbers
- questions.json: per-question results for Browse page
- calibration.json: reliability diagram
- ablation.json: fine-tuning comparison (placeholder for now)

Also prepares demo databases.
"""
import json
import math
from pathlib import Path
import numpy as np
import joblib
import shutil

from sqlrouter.common.config import load_config, load_costs


def compute_ece(probs: np.ndarray, outcomes: np.ndarray, bins: int = 10):
    """Compute Expected Calibration Error and bin data.
    
    Args:
        probs: Predicted probabilities
        outcomes: Actual outcomes (0 or 1)
        bins: Number of bins
        
    Returns:
        Tuple of (ECE, bin_data)
    """
    edges = np.linspace(0, 1, bins + 1)
    ece = 0.0
    bin_data = []
    
    for i in range(bins):
        a, b = edges[i], edges[i + 1]
        
        # Last bin is inclusive on both ends
        if i == bins - 1:
            mask = (probs >= a) & (probs <= b)
        else:
            mask = (probs >= a) & (probs < b)
        
        if mask.sum() == 0:
            continue
        
        conf = float(probs[mask].mean())
        freq = float(outcomes[mask].mean())
        n = int(mask.sum())
        
        bin_data.append({"conf": conf, "freq": freq, "n": n})
        
        # Contribution to ECE
        weight = mask.sum() / len(probs)
        ece += weight * abs(conf - freq)
    
    return float(ece), bin_data


def pick_threshold_hoeffding(
    scores: np.ndarray, wrong: np.ndarray, alpha: float = 0.15, delta: float = 0.1
):
    """Pick threshold using Hoeffding bound for risk control.
    
    Finds largest set of lowest-scoring queries where the error upper bound
    stays below alpha.
    
    Args:
        scores: Uncertainty scores
        wrong: Boolean array (True if wrong)
        alpha: Maximum tolerable error rate
        delta: Confidence parameter
        
    Returns:
        Threshold value
    """
    n = len(scores)
    order = np.argsort(scores)  # Ascending (keep low-scoring)
    
    best_k = 0
    
    for k in range(1, n + 1):
        # Error rate on k lowest-scoring
        err = wrong[order[:k]].mean()
        
        # Hoeffding upper bound
        bound = err + math.sqrt(math.log(1 / delta) / (2 * k))
        
        if bound <= alpha:
            best_k = k
    
    if best_k == 0:
        return 0.0  # Too risky, escalate everything
    
    return float(scores[order[best_k - 1]])


def main():
    cfg = load_config("qlora")
    costs_cfg = load_costs()
    
    results_dir = Path("artifacts/results")
    
    # Check required files
    required = [
        "test_samples.jsonl",
        "pareto.json",
        "auroc.json",
        "layers.json",
    ]
    
    for fname in required:
        path = results_dir / fname
        if not path.exists():
            print(f"ERROR: {path} not found")
            print("Please run previous pipeline steps first")
            return
    
    print("Loading results...")
    
    # Load test samples
    test_rows = []
    with open(results_dir / "test_samples.jsonl", "r") as f:
        for line in f:
            test_rows.append(json.loads(line))
    
    # Load teacher data
    teacher_data = {}
    teacher_path = Path("data/cache/teacher.jsonl")
    with open(teacher_path, "r") as f:
        for line in f:
            r = json.loads(line)
            teacher_data[r["id"]] = r
    
    # Load calibration samples for threshold selection
    cal_rows = []
    with open(results_dir / "cal_samples.jsonl", "r") as f:
        for line in f:
            cal_rows.append(json.loads(line))
    
    print(f"  Test: {len(test_rows)} questions")
    print(f"  Calibration: {len(cal_rows)} questions")
    
    # Load probe
    probe = joblib.load(Path("artifacts/probes/sep.joblib"))
    layer = probe["layer"]
    
    # Load features and compute scores
    print(f"\nComputing probe scores (layer {layer})...")
    
    cal_features = np.load(Path("artifacts/features/cal.npz"))
    test_features = np.load(Path("artifacts/features/test.npz"))
    
    X_cal = cal_features[f"L{layer}"].astype(np.float32)
    X_test = test_features[f"L{layer}"].astype(np.float32)
    
    cal_scores = probe["pipe"].predict_proba(X_cal)[:, 1]
    test_scores = probe["pipe"].predict_proba(X_test)[:, 1]
    
    # Select threshold on calibration set
    print("\nSelecting threshold...")
    cal_wrong = np.array([not r["greedy_ok"] for r in cal_rows])
    
    alpha, delta = 0.15, 0.1
    threshold = pick_threshold_hoeffding(cal_scores, cal_wrong, alpha, delta)
    
    print(f"  Threshold: {threshold:.3f} (alpha={alpha}, delta={delta})")
    
    # Apply to test set
    test_wrong = np.array([not r["greedy_ok"] for r in test_rows])
    escalated = test_scores > threshold
    esc_rate = float(escalated.mean())
    
    kept_local = ~escalated
    if kept_local.sum() > 0:
        kept_local_error = float(test_wrong[kept_local].mean())
    else:
        kept_local_error = 0.0
    
    print(f"  Escalation rate: {esc_rate:.1%}")
    print(f"  Kept-local error: {kept_local_error:.1%}")
    
    # Router accuracy (combining local and API)
    test_api_ok = np.array([teacher_data[r["id"]]["api_ok"] for r in test_rows])
    test_local_ok = np.array([r["greedy_ok"] for r in test_rows])
    
    router_correct = np.where(escalated, test_api_ok, test_local_ok)
    router_acc = float(router_correct.mean())
    
    print(f"  Router accuracy: {router_acc:.1%}")
    
    # Load costs
    timing_path = results_dir / "timing.json"
    if timing_path.exists():
        timing = json.load(open(timing_path))
        gpu_usd_per_sec = costs_cfg["gpu_usd_per_hour"] / 3600
        
        c_prefill = timing["t_prefill"] * gpu_usd_per_sec
        c_decode = timing["t_greedy_decode"] * gpu_usd_per_sec
        c_api_avg = costs_cfg["api"]["input_usd_per_mtok"] * 1000 / 1e6
    else:
        print("  WARNING: Using placeholder costs")
        c_prefill = 0.0001
        c_decode = 0.0001
        c_api_avg = 0.003
    
    # Cost per query
    n = len(test_rows)
    k = escalated.sum()
    
    router_cost = (n * c_prefill + (n - k) * c_decode + k * c_api_avg) / n
    all_api_cost = c_api_avg
    
    cost_saving_pct = 100 * (1 - router_cost / all_api_cost)
    
    print(f"  Cost saving: {cost_saving_pct:.1f}%")
    
    # Calibration
    print("\nComputing calibration...")
    ece, cal_bins = compute_ece(test_scores, test_wrong.astype(float))
    print(f"  ECE: {ece:.3f}")
    
    # Load baseline accuracy
    base_greedy_path = results_dir / "base_greedy.jsonl"
    if base_greedy_path.exists():
        base_correct = 0
        base_total = 0
        with open(base_greedy_path, "r") as f:
            for line in f:
                r = json.loads(line)
                if r["ok"]:
                    base_correct += 1
                base_total += 1
        greedy_acc_base = base_correct / base_total if base_total > 0 else 0.0
    else:
        greedy_acc_base = 0.0
    
    # Export router_config.json
    print("\nExporting router_config.json...")
    router_config = {
        "layer": layer,
        "threshold": threshold,
        "alpha": alpha,
        "delta": delta,
        "student": cfg["base_model"].split("/")[-1],
        "teacher": "claude-3-5-sonnet" if "anthropic" in str(costs_cfg) else "gpt-4",
        "costs": {
            "c_prefill": c_prefill,
            "c_decode": c_decode,
            "c_api": c_api_avg,
            "gpu_usd_per_hour": costs_cfg["gpu_usd_per_hour"],
            "api_in_per_tok": costs_cfg["api"]["input_usd_per_mtok"] / 1e6,
            "api_out_per_tok": costs_cfg["api"]["output_usd_per_mtok"] / 1e6,
        },
    }
    
    with open(results_dir / "router_config.json", "w") as f:
        json.dump(router_config, f, indent=2)
    
    # Export summary.json
    print("Exporting summary.json...")
    
    pareto = json.load(open(results_dir / "pareto.json"))
    auroc_data = json.load(open(results_dir / "auroc.json"))
    
    sep_auroc = next(d["auroc"] for d in auroc_data if "Entropy probe" in d["policy"])
    token_auroc = next(d["auroc"] for d in auroc_data if "Token entropy" in d["policy"])
    
    summary = {
        "n_test": len(test_rows),
        "greedy_acc_base": greedy_acc_base,
        "greedy_acc_ft": float(test_local_ok.mean()),
        "api_acc": float(test_api_ok.mean()),
        "router_acc": router_acc,
        "esc_rate": esc_rate,
        "kept_local_error": kept_local_error,
        "cost_saving_pct": cost_saving_pct,
        "auroc_sep": sep_auroc,
        "auroc_token": token_auroc,
    }
    
    with open(results_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    # Export calibration.json
    print("Exporting calibration.json...")
    calibration = {
        "ece": ece,
        "bins": cal_bins,
    }
    
    with open(results_dir / "calibration.json", "w") as f:
        json.dump(calibration, f, indent=2)
    
    # Export questions.json (for Browse page)
    print("Exporting questions.json...")
    questions = []
    
    for i, row in enumerate(test_rows):
        teacher = teacher_data[row["id"]]
        
        questions.append({
            "id": row["id"],
            "db_id": row["db_id"],
            "question": row["question"],
            "gold": row["gold"],
            "local_sql": row["greedy_sql"],
            "local_ok": row["greedy_ok"],
            "api_sql": teacher["api_sql"],
            "api_ok": teacher["api_ok"],
            "score_sep": float(test_scores[i]),
            "score_token": float(row["token_nll"]),
            "entropy": float(row["H"]),
        })
    
    with open(results_dir / "questions.json", "w") as f:
        json.dump(questions, f, indent=2)
    
    # Export ablation.json (placeholder - would need additional training runs)
    print("Exporting ablation.json (placeholder)...")
    ablation = [
        {
            "variant": "Base (no tuning)",
            "trainable_params": 0,
            "greedy_acc": greedy_acc_base,
            "sep_auroc": 0.0,
            "acc_at_20pct_esc": 0.0,
        },
        {
            "variant": "QLoRA r=16",
            "trainable_params": 0,  # Fill in from training log
            "greedy_acc": summary["greedy_acc_ft"],
            "sep_auroc": sep_auroc,
            "acc_at_20pct_esc": 0.0,  # Compute from Pareto
        },
    ]
    
    with open(results_dir / "ablation.json", "w") as f:
        json.dump(ablation, f, indent=2)
    
    # Copy demo databases
    print("\nPreparing demo databases...")
    demo_dbs_dir = Path("artifacts/demo_dbs")
    demo_dbs_dir.mkdir(parents=True, exist_ok=True)
    
    # Select a few interesting databases
    db_ids = list(set(r["db_id"] for r in test_rows[:10]))  # First 10 unique
    
    spider_db_path = Path("data/spider/database")
    
    for db_id in db_ids:
        src = spider_db_path / db_id / f"{db_id}.sqlite"
        dst_dir = demo_dbs_dir / db_id
        dst_dir.mkdir(exist_ok=True)
        dst = dst_dir / f"{db_id}.sqlite"
        
        if src.exists():
            shutil.copy(src, dst)
    
    # Save index
    with open(demo_dbs_dir / "index.json", "w") as f:
        json.dump(db_ids, f)
    
    print(f"  Copied {len(db_ids)} demo databases")
    
    # Summary
    print("\n" + "="*50)
    print("EXPORT COMPLETE")
    print("="*50)
    print("Files created in artifacts/results/:")
    print("  - router_config.json")
    print("  - summary.json")
    print("  - questions.json")
    print("  - calibration.json")
    print("  - ablation.json")
    print("  - pareto.json (already existed)")
    print("  - auroc.json (already existed)")
    print("  - layers.json (already existed)")
    print("\nDemo databases:")
    print(f"  - {len(db_ids)} databases in artifacts/demo_dbs/")
    print("="*50)
    
    # Headline result
    print("\n🎉 HEADLINE RESULT:")
    print(f"At {esc_rate:.0%} escalation, the entropy probe keeps")
    print(f"{router_acc:.0%} of API accuracy at {100-cost_saving_pct:.0%} of API cost.")
    
    print("\n✓ Phase 5.2 complete: Export done")
    print("\n✅ ML PIPELINE COMPLETE!")
    print("\nNext steps:")
    print("  1. Review artifacts/results/ files")
    print("  2. Build the backend (Phase 6)")
    print("  3. Build the frontend (Phase 7)")


if __name__ == "__main__":
    main()
