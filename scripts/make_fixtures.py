"""
Generate fixture data for frontend development.

Creates realistic synthetic JSON files matching the real data contract,
so the frontend can be built while the GPU pipeline runs.
"""
import json
from pathlib import Path
import numpy as np


def generate_pareto_curve(n_points=101, best_auroc=0.75):
    """Generate a realistic Pareto curve."""
    # Escalation fractions
    esc = np.linspace(0, 1, n_points)
    
    # Accuracy: starts at local-only, rises to API-only
    # Use a concave curve for realistic shape
    local_acc = 0.65
    api_acc = 0.92
    acc = local_acc + (api_acc - local_acc) * (1 - (1 - esc) ** 1.5)
    
    # Cost: linear interpolation between local and API
    local_cost = 0.05
    api_cost = 3.0
    cost = local_cost + (api_cost - local_cost) * esc
    
    return [
        {
            "esc": float(esc[i]),
            "acc": float(acc[i]),
            "cost_usd_per_1k": float(cost[i]),
        }
        for i in range(n_points)
    ]


def main():
    output_dir = Path("artifacts/results")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("Generating fixture data...")
    
    # router_config.json
    router_config = {
        "layer": 25,
        "threshold": 0.37,
        "alpha": 0.15,
        "delta": 0.1,
        "student": "Qwen2.5-Coder-3B",
        "teacher": "Claude 3.5 Sonnet",
        "costs": {
            "c_prefill": 0.0001,
            "c_decode": 0.00015,
            "c_api": 0.003,
            "gpu_usd_per_hour": 0.0,
            "api_in_per_tok": 3e-6,
            "api_out_per_tok": 15e-6,
        },
    }
    
    with open(output_dir / "router_config.json", "w") as f:
        json.dump(router_config, f, indent=2)
    
    print("  ✓ router_config.json")
    
    # pareto.json
    pareto = {
        "n": 700,
        "endpoints": {
            "all_local": {"acc": 0.65, "cost_usd_per_1k": 0.05},
            "all_api": {"acc": 0.92, "cost_usd_per_1k": 3.0},
        },
        "policies": [
            {
                "id": "sep",
                "label": "Entropy probe",
                "auroc": 0.75,
                "aurc": 0.12,
                "points": generate_pareto_curve(best_auroc=0.75),
            },
            {
                "id": "acc_probe",
                "label": "Accuracy probe",
                "auroc": 0.68,
                "aurc": 0.15,
                "points": generate_pareto_curve(best_auroc=0.68),
            },
            {
                "id": "token_entropy",
                "label": "Token entropy",
                "auroc": 0.62,
                "aurc": 0.18,
                "points": generate_pareto_curve(best_auroc=0.62),
            },
            {
                "id": "sampling_entropy",
                "label": "Sampling entropy",
                "auroc": 0.71,
                "aurc": 0.14,
                "points": generate_pareto_curve(best_auroc=0.71),
            },
            {
                "id": "random",
                "label": "Random",
                "auroc": 0.50,
                "aurc": 0.25,
                "points": generate_pareto_curve(best_auroc=0.50),
            },
            {
                "id": "oracle",
                "label": "Oracle (upper bound)",
                "auroc": 1.0,
                "aurc": 0.0,
                "points": generate_pareto_curve(best_auroc=1.0),
            },
        ],
    }
    
    with open(output_dir / "pareto.json", "w") as f:
        json.dump(pareto, f, indent=2)
    
    print("  ✓ pareto.json")
    
    # auroc.json
    auroc_data = [
        {"policy": "Entropy probe", "auroc": 0.75, "ci": [0.72, 0.78]},
        {"policy": "Accuracy probe", "auroc": 0.68, "ci": [0.65, 0.71]},
        {"policy": "Token entropy", "auroc": 0.62, "ci": [0.58, 0.66]},
        {"policy": "Sampling entropy", "auroc": 0.71, "ci": [0.68, 0.74]},
        {"policy": "Random", "auroc": 0.50, "ci": [0.46, 0.54]},
    ]
    
    with open(output_dir / "auroc.json", "w") as f:
        json.dump(auroc_data, f, indent=2)
    
    print("  ✓ auroc.json")
    
    # layers.json
    layers_data = []
    for layer in [9, 14, 19, 24, 29, 34]:
        frac = layer / 34
        # SEP improves with depth, peaks around 0.7
        sep_auroc = 0.55 + 0.25 * (1 - abs(frac - 0.7) * 2)
        acc_auroc = sep_auroc - 0.05
        
        layers_data.append({
            "layer": layer,
            "frac": round(frac, 2),
            "sep_auroc": round(sep_auroc, 3),
            "acc_auroc": round(acc_auroc, 3),
        })
    
    with open(output_dir / "layers.json", "w") as f:
        json.dump(layers_data, f, indent=2)
    
    print("  ✓ layers.json")
    
    # calibration.json
    calibration = {
        "ece": 0.043,
        "bins": [
            {"conf": 0.05, "freq": 0.02, "n": 42},
            {"conf": 0.15, "freq": 0.11, "n": 87},
            {"conf": 0.25, "freq": 0.21, "n": 95},
            {"conf": 0.35, "freq": 0.33, "n": 102},
            {"conf": 0.45, "freq": 0.48, "n": 89},
            {"conf": 0.55, "freq": 0.59, "n": 76},
            {"conf": 0.65, "freq": 0.68, "n": 64},
            {"conf": 0.75, "freq": 0.79, "n": 52},
            {"conf": 0.85, "freq": 0.88, "n": 48},
            {"conf": 0.95, "freq": 0.96, "n": 45},
        ],
    }
    
    with open(output_dir / "calibration.json", "w") as f:
        json.dump(calibration, f, indent=2)
    
    print("  ✓ calibration.json")
    
    # summary.json
    summary = {
        "n_test": 700,
        "greedy_acc_base": 0.58,
        "greedy_acc_ft": 0.65,
        "api_acc": 0.92,
        "router_acc": 0.88,
        "esc_rate": 0.22,
        "kept_local_error": 0.12,
        "cost_saving_pct": 68.5,
        "auroc_sep": 0.75,
        "auroc_token": 0.62,
    }
    
    with open(output_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    print("  ✓ summary.json")
    
    # ablation.json
    ablation = [
        {
            "variant": "Base (no tuning)",
            "trainable_params": 0,
            "greedy_acc": 0.58,
            "sep_auroc": 0.0,
            "acc_at_20pct_esc": 0.58,
        },
        {
            "variant": "QLoRA r=8",
            "trainable_params": 33554432,
            "greedy_acc": 0.63,
            "sep_auroc": 0.72,
            "acc_at_20pct_esc": 0.86,
        },
        {
            "variant": "QLoRA r=16",
            "trainable_params": 67108864,
            "greedy_acc": 0.65,
            "sep_auroc": 0.75,
            "acc_at_20pct_esc": 0.88,
        },
    ]
    
    with open(output_dir / "ablation.json", "w") as f:
        json.dump(ablation, f, indent=2)
    
    print("  ✓ ablation.json")
    
    # questions.json (sample)
    questions = [
        {
            "id": "test-0",
            "db_id": "concert_singer",
            "question": "How many singers do we have?",
            "gold": "SELECT count(*) FROM singer",
            "local_sql": "SELECT count(*) FROM singer",
            "local_ok": True,
            "api_sql": "SELECT count(*) FROM singer",
            "api_ok": True,
            "score_sep": 0.12,
            "score_token": 0.85,
            "entropy": 0.0,
        },
        {
            "id": "test-1",
            "db_id": "pets_1",
            "question": "Find the maximum age of the dog",
            "gold": "SELECT max(age) FROM Pets WHERE PetType = 'dog'",
            "local_sql": "SELECT max(age) FROM Pets WHERE pet_type = 'dog'",
            "local_ok": False,
            "api_sql": "SELECT max(age) FROM Pets WHERE PetType = 'dog'",
            "api_ok": True,
            "score_sep": 0.78,
            "score_token": 1.43,
            "entropy": 2.1,
        },
    ]
    
    with open(output_dir / "questions.json", "w") as f:
        json.dump(questions, f, indent=2)
    
    print("  ✓ questions.json")
    
    # demo_dbs index
    demo_dir = Path("artifacts/demo_dbs")
    demo_dir.mkdir(parents=True, exist_ok=True)
    
    demo_dbs = ["concert_singer", "pets_1", "car_1", "flight_2"]
    
    with open(demo_dir / "index.json", "w") as f:
        json.dump(demo_dbs, f)
    
    print("  ✓ demo_dbs/index.json")
    
    print("\n✅ Fixture data generated!")
    print("\nThese files allow frontend development before the ML pipeline completes.")
    print("Real pipeline results will overwrite them when ready.")


if __name__ == "__main__":
    main()
