"""
Phase 2.1: Evaluate the untuned base model on test set.

This establishes the baseline accuracy before fine-tuning.
"""
import json
import torch
from pathlib import Path
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModelForCausalLM
import wandb

from sqlrouter.common.config import load_config
from sqlrouter.common.splits import load_split
from sqlrouter.common.prompt import schema_from_sqlite, render, extract_sql
from sqlrouter.common.sqlexec import is_correct


def main():
    cfg = load_config("qlora")
    
    # Initialize W&B
    wandb.init(project="sql-router", name="baseline-eval", config=cfg)
    
    print("Loading base model...")
    model_name = cfg["base_model"]
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float16,
        device_map="auto",
    ).eval()
    
    print(f"Model loaded: {model_name}")
    
    # Load test split
    test_split = load_split("test")
    print(f"Evaluating on {len(test_split)} test questions")
    
    # Cache schemas
    spider_db_path = Path("data/spider/database")
    schemas = {}
    
    results = []
    correct_count = 0
    
    with torch.no_grad():
        for row in tqdm(test_split, desc="Evaluating baseline"):
            db_id = row["db_id"]
            
            # Load schema if not cached
            if db_id not in schemas:
                db_path = spider_db_path / db_id / f"{db_id}.sqlite"
                schemas[db_id] = schema_from_sqlite(str(db_path))
            
            # Generate SQL
            prompt = render(tokenizer, schemas[db_id], row["question"])
            inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
            
            outputs = model.generate(
                **inputs,
                max_new_tokens=256,
                do_sample=False,  # Greedy decoding
                pad_token_id=tokenizer.pad_token_id,
            )
            
            # Extract generated SQL
            generated = tokenizer.decode(
                outputs[0, inputs.input_ids.shape[1]:],
                skip_special_tokens=True
            )
            pred_sql = extract_sql(generated)
            
            # Check correctness
            db_path = spider_db_path / db_id / f"{db_id}.sqlite"
            ok = is_correct(str(db_path), pred_sql, row["gold"])
            
            if ok:
                correct_count += 1
            
            results.append({
                "id": row["id"],
                "pred_sql": pred_sql,
                "ok": ok,
            })
    
    # Calculate accuracy
    accuracy = correct_count / len(test_split)
    print(f"\nBaseline accuracy: {accuracy:.1%} ({correct_count}/{len(test_split)})")
    
    # Log to W&B
    wandb.log({
        "baseline_accuracy": accuracy,
        "baseline_correct": correct_count,
        "baseline_total": len(test_split),
    })
    
    # Save results
    output_dir = Path("artifacts/results")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / "base_greedy.jsonl"
    with open(output_path, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")
    
    print(f"Results saved to {output_path}")
    print("\n✓ Phase 2.1 complete: Baseline evaluation done")
    
    wandb.finish()


if __name__ == "__main__":
    main()
