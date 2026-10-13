"""
Phase 5.1: Routing evaluation and cost model.

Compares routing policies:
- Random baseline
- Token entropy
- Sampling entropy (requires 8 samples per query)
- Accuracy probe
- Entropy probe (SEP) - our main contribution
- Oracle (upper bound)

Generates Pareto curves and computes AURC (area under risk-coverage curve).
"""
import json
import math
from pathlib import Path
import numpy as np
from sklearn.metrics import roc_auc_score
import joblib

from sqlrouter.common.config import load_costs


def compute_cost(n: int, k: int, policy: str, costs: dict) -> float:
    """Compute total cost for n queries with k escalations.
    
    Args:
        n: Total number of queries
        k: Number escalated to API
        policy: Policy name
        costs: Cost dict with keys c_prefill, c_decode, c_decode_8, c_api
        
    Returns:
        Total cost in USD
    """
    c_prefill = costs["c_prefill"]
    c_decode = costs["c_decode"]
    c_decode_8 = costs["c_decode_8"]
    c_api = costs["c_api"]
    
    if policy in ["sep", "acc_probe"]:
        # Probe policies: prefill for all, decode only for local answers
        return n * c_prefill + (n - k) * c_decode + k * c_api
    
    elif policy == "token_entropy":
        # Must generate before scoring
        return n * (c_prefill + c_decode) + k * c_api
    
    elif policy == "sampling_entropy":
        # Must generate 8 samples before scoring
        return n * (c_prefill + c_decode_8) + k * c_api
    
    elif policy in ["random", "oracle"]:
        # Baselines: same as token entropy
        return n * (c_prefill + c_decode) + k * c_api
    
    else:
        raise ValueError(f"Unknown policy: {policy}")


def sweep_policy(
    score: np.ndarray,
    local_ok: np.ndarray,
    api_ok: np.ndarray,
    policy: str,
    costs: dict,
    points: int = 101,
):
    """Sweep escalation threshold and compute accuracy and cost.
    
    Args:
        score: Uncertainty scores (higher = more likely to escalate)
        local_ok: Boolean array of local correctness
        api_ok: Boolean array of API correctness
        policy: Policy name
        costs: Cost dict
        points: Number of points on curve
        
    Returns:
        List of dicts with keys: esc, acc, cost_usd_per_1k
    """
    n = len(score)
    order = np.argsort(-score, kind="stable")  # Descending
    
    results = []
    
    for frac in np.linspace(0, 1, points):
        k = int(round(frac * n))
        
        # Escalate top-k by score
        escalated = np.zeros(n, dtype=bool)
        if k > 0:
            escalated[order[:k]] = True
        
        # Combined correctness
        correct = np.where(escalated, api_ok, local_ok)
        acc = float(correct.mean())
        
        # Cost
        total_cost = compute_cost(n, k, policy, costs)
        cost_per_1k = 1000 * total_cost / n
        
        results.append({
            "esc": float(frac),
            "acc": acc,
            "cost_usd_per_1k": cost_per_1k,
        })
    
    return results


def compute_aurc(score: np.ndarray, wrong: np.ndarray) -> float:
    """Compute Area Under Risk-Coverage curve.
    
    Lower is better. AURC measures the average error rate as we
    defer more queries.
    
    Args:
        score: Uncertainty scores
        wrong: Boolean array (True if answer is wrong)
        
    Returns:
        AURC value
    """
    n = len(score)
    order = np.argsort(-score)  # Descending
    
    # Cumulative risk at each coverage level
    aurc = 0.0
    cumulative_wrong = 0
    
    for i in range(n):
        idx = order[i]
        cumulative_wrong += int(wrong[idx])
        
        # Coverage: fraction of data seen so far
        coverage = (i + 1) / n
        
        # Risk: error rate on covered data
        risk = cumulative_wrong / (i + 1)
        
        # Add rectangle to AURC
        aurc += risk / n
    
    return aurc


def main():
    # Load test results
    results_dir = Path("artifacts/results")
    
    print("Loading test results...")
    test_samples_path = results_dir / "test_samples.jsonl"
    
    if not test_samples_path.exists():
        print(f"ERROR: {test_samples_path} not found")
        print("Please run s05_sample_entropy.py first")
        return
    
    # Load sampling results
    rows = []
    with open(test_samples_path, "r") as f:
        for line in f:
            rows.append(json.loads(line))
    
    n = len(rows)
    print(f"Loaded {n} test questions")
    
    # Extract arrays
    local_ok = np.array([r["greedy_ok"] for r in rows])
    token_nll = np.array([r["token_nll"] for r in rows])
    H = np.array([r["H"] for r in rows])
    wrong = ~local_ok
    
    print(f"  Local accuracy: {local_ok.mean():.1%}")
    print(f"  Fraction with H > 0: {(H > 0).mean():.1%}")
    
    # Load teacher results
    teacher_cache = Path("data/cache/teacher.jsonl")
    if not teacher_cache.exists():
        print(f"ERROR: {teacher_cache} not found")
        print("Please run s06_teacher_answers.py first")
        return
    
    teacher_data = {}
    with open(teacher_cache, "r") as f:
        for line in f:
            r = json.loads(line)
            teacher_data[r["id"]] = r
    
    # Match teacher results to test rows
    api_ok = np.array([teacher_data[r["id"]]["api_ok"] for r in rows])
    print(f"  API accuracy: {api_ok.mean():.1%}")
    
    # Load probe scores
    probes_dir = Path("artifacts/probes")
    
    sep = joblib.load(probes_dir / "sep.joblib")
    acc_probe = joblib.load(probes_dir / "acc.joblib")
    
    print(f"\nLoading features for layer {sep['layer']}...")
    features = np.load(Path("artifacts/features/test.npz"))
    X = features[f"L{sep['layer']}"].astype(np.float32)
    
    sep_scores = sep["pipe"].predict_proba(X)[:, 1]
    acc_scores = acc_probe["pipe"].predict_proba(X)[:, 1]
    
    # Compute costs
    print("\nComputing cost model...")
    cost_cfg = load_costs()
    timing_path = results_dir / "timing.json"
    
    if not timing_path.exists():
        print(f"WARNING: {timing_path} not found")
        print("Using placeholder costs. Run s05b_timing.py for real measurements.")
        costs = {
            "c_prefill": 0.0001,
            "c_decode": 0.0001,
            "c_decode_8": 0.0008,
            "c_api": 0.003,
        }
    else:
        timing = json.load(open(timing_path))
        gpu_usd_per_sec = cost_cfg["gpu_usd_per_hour"] / 3600
        
        costs = {
            "c_prefill": timing["t_prefill"] * gpu_usd_per_sec,
            "c_decode": timing["t_greedy_decode"] * gpu_usd_per_sec,
            "c_decode_8": (timing["t_sample8_total"] - timing["t_prefill"]) * gpu_usd_per_sec,
            "c_api": cost_cfg["api"]["input_usd_per_mtok"] * 1000 / 1e6,  # Rough avg
        }
    
    print(f"  Prefill: ${costs['c_prefill']:.6f}")
    print(f"  Decode (greedy): ${costs['c_decode']:.6f}")
    print(f"  Decode (8 samples): ${costs['c_decode_8']:.6f}")
    print(f"  API call (avg): ${costs['c_api']:.6f}")
    
    # Define policies
    policies = [
        {
            "id": "sep",
            "label": "Entropy probe",
            "score": sep_scores,
        },
        {
            "id": "acc_probe",
            "label": "Accuracy probe",
            "score": acc_scores,
        },
        {
            "id": "token_entropy",
            "label": "Token entropy",
            "score": token_nll,
        },
        {
            "id": "sampling_entropy",
            "label": "Sampling entropy",
            "score": H,
        },
        {
            "id": "random",
            "label": "Random",
            "score": np.random.RandomState(42).rand(n),
        },
        {
            "id": "oracle",
            "label": "Oracle (upper bound)",
            "score": wrong.astype(float),
        },
    ]
    
    # Sweep each policy
    print("\nSweeping policies...")
    pareto_data = []
    auroc_data = []
    
    for policy in policies:
        print(f"  {policy['label']}...")
        
        # Sweep
        points = sweep_policy(
            policy["score"],
            local_ok,
            api_ok,
            policy["id"],
            costs,
        )
        
        # AUROC (for uncertainty estimation quality)
        if policy["id"] != "oracle":
            auroc = roc_auc_score(wrong, policy["score"])
        else:
            auroc = 1.0
        
        # AURC (for routing quality)
        aurc = compute_aurc(policy["score"], wrong)
        
        pareto_data.append({
            "id": policy["id"],
            "label": policy["label"],
            "auroc": float(auroc),
            "aurc": float(aurc),
            "points": points,
        })
        
        auroc_data.append({
            "policy": policy["label"],
            "auroc": float(auroc),
        })
        
        print(f"    AUROC: {auroc:.3f}, AURC: {aurc:.3f}")
    
    # Endpoints (all-local and all-API)
    all_local_acc = float(local_ok.mean())
    all_local_cost = 1000 * compute_cost(n, 0, "sep", costs) / n
    
    all_api_acc = float(api_ok.mean())
    all_api_cost = 1000 * compute_cost(n, n, "sep", costs) / n
    
    # Save Pareto data
    pareto_output = {
        "n": n,
        "endpoints": {
            "all_local": {"acc": all_local_acc, "cost_usd_per_1k": all_local_cost},
            "all_api": {"acc": all_api_acc, "cost_usd_per_1k": all_api_cost},
        },
        "policies": pareto_data,
    }
    
    pareto_path = results_dir / "pareto.json"
    with open(pareto_path, "w") as f:
        json.dump(pareto_output, f, indent=2)
    
    print(f"\nSaved Pareto data to {pareto_path}")
    
    # Save AUROC data
    auroc_path = results_dir / "auroc.json"
    with open(auroc_path, "w") as f:
        json.dump(auroc_data, f, indent=2)
    
    print(f"Saved AUROC data to {auroc_path}")
    
    # Summary
    print("\n" + "="*50)
    print("ROUTING EVALUATION SUMMARY")
    print("="*50)
    print(f"Test set size: {n}")
    print(f"Local-only accuracy: {all_local_acc:.1%}")
    print(f"API-only accuracy: {all_api_acc:.1%}")
    print(f"\nBest probe (entropy): AUROC={pareto_data[0]['auroc']:.3f}")
    print("="*50)
    
    print("\n✓ Phase 5.1 complete: Routing evaluation done")
    print("\nNext: Run s10_export_results.py to prepare files for the app")


if __name__ == "__main__":
    main()
