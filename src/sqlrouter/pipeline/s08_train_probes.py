"""
Phase 4.2: Train uncertainty probes on execution-based entropy labels.

Trains two types of probes per layer:
1. Entropy probe (SEP): predicts H > 0 (samples disagree)
2. Accuracy probe (baseline): predicts greedy answer is wrong

Both probes are evaluated on the same target: does the greedy answer fail?
"""
import json
from pathlib import Path
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegressionCV
from sklearn.metrics import roc_auc_score
from scipy import stats
import joblib

from sqlrouter.common.splits import load_split


def bootstrap_auroc(y_true, y_score, n_bootstrap=1000, confidence=0.95):
    """Compute AUROC with bootstrap confidence interval.
    
    Args:
        y_true: True labels
        y_score: Predicted scores
        n_bootstrap: Number of bootstrap samples
        confidence: Confidence level
        
    Returns:
        Tuple of (auroc, lower_bound, upper_bound)
    """
    n = len(y_true)
    aurocs = []
    
    rng = np.random.RandomState(42)
    
    for _ in range(n_bootstrap):
        # Resample with replacement
        indices = rng.choice(n, size=n, replace=True)
        y_true_sample = y_true[indices]
        y_score_sample = y_score[indices]
        
        # Skip if only one class in sample
        if len(np.unique(y_true_sample)) < 2:
            continue
        
        auroc = roc_auc_score(y_true_sample, y_score_sample)
        aurocs.append(auroc)
    
    aurocs = np.array(aurocs)
    alpha = (1 - confidence) / 2
    
    return (
        float(np.mean(aurocs)),
        float(np.percentile(aurocs, alpha * 100)),
        float(np.percentile(aurocs, (1 - alpha) * 100)),
    )


def train_probe(X, y, name: str):
    """Train a logistic regression probe with cross-validation.
    
    Args:
        X: Features [n_samples, hidden_dim]
        y: Binary labels [n_samples]
        name: Probe name for logging
        
    Returns:
        Trained pipeline (StandardScaler + LogisticRegression)
    """
    print(f"  Training {name}...")
    print(f"    Samples: {len(X)}, Positive: {y.sum()} ({y.mean():.1%})")
    
    pipeline = make_pipeline(
        StandardScaler(),
        LogisticRegressionCV(
            Cs=[0.001, 0.01, 0.1, 1.0, 10.0],
            cv=5,
            max_iter=3000,
            scoring="roc_auc",
            random_state=42,
        ),
    )
    
    pipeline.fit(X, y)
    
    # Report chosen C
    chosen_C = pipeline.named_steps["logisticregressioncv"].C_[0]
    print(f"    Best C: {chosen_C}")
    
    return pipeline


def main():
    features_dir = Path("artifacts/features")
    
    # Check that features exist
    required_files = ["probe.npz", "cal.npz", "test.npz"]
    for fname in required_files:
        if not (features_dir / fname).exists():
            print(f"ERROR: {features_dir / fname} not found")
            print("Please run s07_extract_features.py first")
            return
    
    # Load sampling results
    results_dir = Path("artifacts/results")
    
    def load_results(split_name):
        """Load sampling results and extract labels."""
        path = results_dir / f"{split_name}_samples.jsonl"
        if not path.exists():
            print(f"ERROR: {path} not found")
            print("Please run s05_sample_entropy.py first")
            return None
        
        rows = []
        with open(path, "r") as f:
            for line in f:
                rows.append(json.loads(line))
        
        # Extract labels
        H = np.array([r["H"] for r in rows])
        wrong = np.array([not r["greedy_ok"] for r in rows])
        
        return H, wrong, rows
    
    print("Loading sampling results...")
    H_probe, wrong_probe, _ = load_results("probe")
    H_cal, wrong_cal, _ = load_results("cal")
    H_test, wrong_test, _ = load_results("test")
    
    # Load features
    print("\nLoading features...")
    feat_probe = np.load(features_dir / "probe.npz")
    feat_cal = np.load(features_dir / "cal.npz")
    feat_test = np.load(features_dir / "test.npz")
    
    layers = sorted([int(k[1:]) for k in feat_probe.keys()])
    print(f"Layers available: {layers}")
    
    # Train probes for each layer
    print("\nTraining probes...")
    results = []
    
    for layer in layers:
        key = f"L{layer}"
        print(f"\n--- Layer {layer} ---")
        
        # Get features (convert to float32 for sklearn)
        Xp = feat_probe[key].astype(np.float32)
        Xc = feat_cal[key].astype(np.float32)
        Xt = feat_test[key].astype(np.float32)
        
        # Train entropy probe (H > 0)
        sep = train_probe(Xp, (H_probe > 0).astype(int), "Entropy probe (SEP)")
        
        # Train accuracy probe (greedy wrong)
        acc_probe = train_probe(Xp, wrong_probe.astype(int), "Accuracy probe")
        
        # Evaluate both on cal and test
        # Both predict: will greedy answer be wrong?
        sep_scores_cal = sep.predict_proba(Xc)[:, 1]
        sep_scores_test = sep.predict_proba(Xt)[:, 1]
        
        acc_scores_cal = acc_probe.predict_proba(Xc)[:, 1]
        acc_scores_test = acc_probe.predict_proba(Xt)[:, 1]
        
        # Compute AUROCs
        sep_auroc_cal = roc_auc_score(wrong_cal, sep_scores_cal)
        sep_auroc_test = roc_auc_score(wrong_test, sep_scores_test)
        
        acc_auroc_cal = roc_auc_score(wrong_cal, acc_scores_cal)
        acc_auroc_test = roc_auc_score(wrong_test, acc_scores_test)
        
        print(f"  Entropy probe AUROC: cal={sep_auroc_cal:.3f}, test={sep_auroc_test:.3f}")
        print(f"  Accuracy probe AUROC: cal={acc_auroc_cal:.3f}, test={acc_auroc_test:.3f}")
        
        results.append({
            "layer": layer,
            "frac": layer / max(layers),
            "sep_cal": sep_auroc_cal,
            "sep_test": sep_auroc_test,
            "acc_cal": acc_auroc_cal,
            "acc_test": acc_auroc_test,
            "sep": sep,
            "acc": acc_probe,
        })
    
    # Select best layer based on calibration set SEP AUROC
    best_idx = max(range(len(results)), key=lambda i: results[i]["sep_cal"])
    best = results[best_idx]
    
    print("\n" + "="*50)
    print("LAYER SELECTION")
    print("="*50)
    print(f"Best layer: {best['layer']} (fraction {best['frac']:.2f})")
    print(f"  Entropy probe AUROC on cal: {best['sep_cal']:.3f}")
    print(f"  Entropy probe AUROC on test: {best['sep_test']:.3f}")
    print("="*50)
    
    # Compute bootstrap CI for test AUROC
    print("\nComputing confidence intervals for test set...")
    Xt_best = feat_test[f"L{best['layer']}"].astype(np.float32)
    sep_scores_test = best["sep"].predict_proba(Xt_best)[:, 1]
    
    auroc, lower, upper = bootstrap_auroc(wrong_test, sep_scores_test)
    print(f"Entropy probe AUROC: {auroc:.3f} (95% CI: [{lower:.3f}, {upper:.3f}])")
    
    # Save best probes
    probes_dir = Path("artifacts/probes")
    probes_dir.mkdir(parents=True, exist_ok=True)
    
    sep_path = probes_dir / "sep.joblib"
    acc_path = probes_dir / "acc.joblib"
    
    joblib.dump({"pipe": best["sep"], "layer": best["layer"]}, sep_path)
    joblib.dump({"pipe": best["acc"], "layer": best["layer"]}, acc_path)
    
    print(f"\nSaved probes:")
    print(f"  Entropy probe: {sep_path}")
    print(f"  Accuracy probe: {acc_path}")
    
    # Save layer ablation results
    layers_path = results_dir / "layers.json"
    layers_data = [
        {
            "layer": r["layer"],
            "frac": r["frac"],
            "sep_auroc": r["sep_test"],
            "acc_auroc": r["acc_test"],
        }
        for r in results
    ]
    
    with open(layers_path, "w") as f:
        json.dump(layers_data, f, indent=2)
    
    print(f"  Layer ablation: {layers_path}")
    
    print("\n✓ Phase 4.2 complete: Probe training done")
    print("\nNext: Run s09_route_eval.py for routing evaluation")


if __name__ == "__main__":
    main()
