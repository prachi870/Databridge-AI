"""
Phase 3.2: Measure single-request latency for cost model.

Measures:
- Prefill time (probe path - forward pass only)
- Greedy generation time (total)
- 8-sample generation time (total)
"""
import json
import time
from pathlib import Path
import torch
import numpy as np
from transformers import AutoTokenizer, AutoModelForCausalLM

from sqlrouter.common.splits import load_split
from sqlrouter.common.prompt import schema_from_sqlite, render


def time_operation(func, inputs, n_reps: int = 64):
    """Time an operation over multiple repetitions.
    
    Args:
        func: Function to time
        inputs: List of inputs
        n_reps: Number of repetitions
        
    Returns:
        Mean time in seconds
    """
    times = []
    
    for inp in inputs[:n_reps]:
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        func(inp)
        torch.cuda.synchronize()
        times.append(time.perf_counter() - t0)
    
    return float(np.mean(times))


def main():
    model_path = Path("artifacts/merged/qlora_r16")
    
    if not model_path.exists():
        print(f"ERROR: Merged model not found at {model_path}")
        print("Please run s04_merge.py first")
        return
    
    print("Loading model...")
    tokenizer = AutoTokenizer.from_pretrained(str(model_path))
    model = AutoModelForCausalLM.from_pretrained(
        str(model_path),
        torch_dtype=torch.float16,
        device_map="cuda",
    ).eval()
    
    print(f"Model loaded on {torch.cuda.get_device_name(0)}")
    
    # Get sample prompts from test split
    print("\nPreparing test prompts...")
    test_split = load_split("test")
    spider_db_path = Path("data/spider/database")
    
    prompts = []
    for row in test_split[:64]:  # Use first 64 for timing
        db_id = row["db_id"]
        db_path = spider_db_path / db_id / f"{db_id}.sqlite"
        schema = schema_from_sqlite(str(db_path))
        prompt = render(tokenizer, schema, row["question"])
        prompts.append(prompt)
    
    print(f"Prepared {len(prompts)} prompts")
    
    # Prepare encoded inputs
    def encode(p):
        return tokenizer(p, return_tensors="pt").to("cuda")
    
    encoded = [encode(p) for p in prompts]
    
    # Time prefill (forward pass only, for probe)
    print("\nTiming prefill (probe path)...")
    def prefill(enc):
        with torch.no_grad():
            model(**enc, output_hidden_states=True)
    
    t_prefill = time_operation(prefill, encoded)
    print(f"  Mean prefill time: {t_prefill*1000:.1f} ms")
    
    # Time greedy generation
    print("\nTiming greedy generation...")
    def greedy(enc):
        with torch.no_grad():
            model.generate(
                **enc,
                max_new_tokens=256,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id,
            )
    
    t_greedy_total = time_operation(greedy, encoded)
    t_greedy_decode = t_greedy_total - t_prefill
    print(f"  Mean greedy total: {t_greedy_total*1000:.1f} ms")
    print(f"  Mean decode only: {t_greedy_decode*1000:.1f} ms")
    
    # Time 8-sample generation
    print("\nTiming 8-sample generation...")
    def sample8(enc):
        with torch.no_grad():
            model.generate(
                **enc,
                max_new_tokens=256,
                do_sample=True,
                temperature=0.8,
                top_p=0.95,
                num_return_sequences=8,
                pad_token_id=tokenizer.pad_token_id,
            )
    
    t_sample8_total = time_operation(sample8, encoded, n_reps=32)  # Slower, fewer reps
    print(f"  Mean 8-sample total: {t_sample8_total*1000:.1f} ms")
    
    # Save results
    output_path = Path("artifacts/results/timing.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    results = {
        "t_prefill": t_prefill,
        "t_greedy_total": t_greedy_total,
        "t_greedy_decode": t_greedy_decode,
        "t_sample8_total": t_sample8_total,
        "gpu": torch.cuda.get_device_name(0),
        "model": str(model_path),
    }
    
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to {output_path}")
    
    # Summary
    print("\n" + "="*50)
    print("TIMING SUMMARY")
    print("="*50)
    print(f"Prefill (probe):        {t_prefill*1000:6.1f} ms")
    print(f"Greedy decode:          {t_greedy_decode*1000:6.1f} ms")
    print(f"Greedy total:           {t_greedy_total*1000:6.1f} ms")
    print(f"8-sample total:         {t_sample8_total*1000:6.1f} ms")
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print("="*50)
    
    print("\n✓ Phase 3.2 complete: Timing measurements done")


if __name__ == "__main__":
    main()
