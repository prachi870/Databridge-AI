"""
Phase 3.1: Generate samples and compute execution-based semantic entropy.

For each question:
- Generate 1 greedy answer (what user gets)
- Generate N=8 sampled answers
- Execute all, cluster by result set
- Compute entropy H of cluster distribution
- Compute token-level entropy baseline
"""
import json
import math
import collections
from pathlib import Path
from tqdm import tqdm
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

from sqlrouter.common.config import load_config
from sqlrouter.common.splits import load_split
from sqlrouter.common.prompt import schema_from_sqlite, render, extract_sql
from sqlrouter.common.sqlexec import run_sql, result_key, is_correct


def entropy(keys: list) -> tuple[float, int]:
    """Compute entropy of a distribution and number of unique clusters.
    
    Args:
        keys: List of result keys (from result_key function)
        
    Returns:
        Tuple of (entropy, num_clusters)
    """
    if not keys:
        return 0.0, 0
    
    n = len(keys)
    counts = collections.Counter(keys)
    
    # Shannon entropy: -sum(p * log(p))
    H = -sum(count / n * math.log(count / n) for count in counts.values())
    
    return H, len(counts)


def sample_with_fallback(model, tokenizer, prompt: str, n_samples: int = 8):
    """Generate samples, trying vLLM first, falling back to HuggingFace.
    
    Returns: (greedy_output, greedy_logprobs, samples)
    """
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    
    # Try to use vLLM if available (faster for batched sampling)
    try:
        from vllm import LLM, SamplingParams
        
        # Load vLLM model (cache this in production)
        llm = LLM(
            "artifacts/merged/qlora_r16",
            dtype="float16",
            max_model_len=2048,
            gpu_memory_utilization=0.85,
        )
        
        # Greedy
        greedy_params = SamplingParams(
            temperature=0.0,
            max_tokens=256,
            logprobs=0,  # Get token logprobs
        )
        greedy_out = llm.generate([prompt], greedy_params)[0]
        greedy_text = greedy_out.outputs[0].text
        greedy_logprobs = [
            logprob_dict[token_id].logprob
            for logprob_dict, token_id in zip(
                greedy_out.outputs[0].logprobs,
                greedy_out.outputs[0].token_ids
            )
        ]
        
        # Sampling
        sample_params = SamplingParams(
            n=n_samples,
            temperature=0.8,
            top_p=0.95,
            max_tokens=256,
        )
        sample_out = llm.generate([prompt], sample_params)[0]
        samples = [out.text for out in sample_out.outputs]
        
        return greedy_text, greedy_logprobs, samples
        
    except ImportError:
        print("vLLM not available, using HuggingFace (slower)")
        
        # Greedy with logprobs
        with torch.no_grad():
            greedy_out = model.generate(
                **inputs,
                max_new_tokens=256,
                do_sample=False,
                return_dict_in_generate=True,
                output_scores=True,
                pad_token_id=tokenizer.pad_token_id,
            )
        
        greedy_tokens = greedy_out.sequences[0, inputs.input_ids.shape[1]:]
        greedy_text = tokenizer.decode(greedy_tokens, skip_special_tokens=True)
        
        # Compute logprobs from scores
        greedy_logprobs = []
        for i, token_id in enumerate(greedy_tokens):
            logits = greedy_out.scores[i][0]  # [vocab_size]
            log_probs = torch.nn.functional.log_softmax(logits, dim=0)
            greedy_logprobs.append(log_probs[token_id].item())
        
        # Sampling
        with torch.no_grad():
            sample_out = model.generate(
                **inputs,
                max_new_tokens=256,
                do_sample=True,
                temperature=0.8,
                top_p=0.95,
                num_return_sequences=n_samples,
                pad_token_id=tokenizer.pad_token_id,
            )
        
        samples = [
            tokenizer.decode(
                sample_out[i, inputs.input_ids.shape[1]:],
                skip_special_tokens=True
            )
            for i in range(n_samples)
        ]
        
        return greedy_text, greedy_logprobs, samples


def process_split(split_name: str, model, tokenizer, schemas, spider_db_path):
    """Process one split and save results."""
    split = load_split(split_name)
    print(f"\nProcessing {split_name} split ({len(split)} questions)...")
    
    output_path = Path(f"artifacts/results/{split_name}_samples.jsonl")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w") as f:
        for row in tqdm(split, desc=f"Sampling {split_name}"):
            db_id = row["db_id"]
            schema = schemas[db_id]
            db_path = spider_db_path / db_id / f"{db_id}.sqlite"
            
            # Generate
            prompt = render(tokenizer, schema, row["question"])
            greedy_text, greedy_logprobs, samples = sample_with_fallback(
                model, tokenizer, prompt, n_samples=8
            )
            
            # Extract SQL
            greedy_sql = extract_sql(greedy_text)
            sample_sqls = [extract_sql(s) for s in samples]
            
            # Execute all and get result keys
            result_keys = []
            for sql in sample_sqls:
                status, result = run_sql(str(db_path), sql)
                key = result_key(status, result)
                result_keys.append(key)
            
            # Compute entropy
            H, n_clusters = entropy(result_keys)
            
            # Token entropy (mean negative log probability)
            token_nll = (
                -sum(greedy_logprobs) / max(len(greedy_logprobs), 1)
                if greedy_logprobs else 0.0
            )
            
            # Check greedy correctness
            greedy_ok = is_correct(str(db_path), greedy_sql, row["gold"])
            
            # Save
            f.write(json.dumps({
                "id": row["id"],
                "db_id": db_id,
                "question": row["question"],
                "gold": row["gold"],
                "greedy_sql": greedy_sql,
                "greedy_ok": greedy_ok,
                "token_nll": token_nll,
                "H": H,
                "n_clusters": n_clusters,
            }) + "\n")
    
    print(f"Saved to {output_path}")


def main():
    cfg = load_config("qlora")
    
    model_path = Path("artifacts/merged/qlora_r16")
    if not model_path.exists():
        print(f"ERROR: Merged model not found at {model_path}")
        print("Please run s04_merge.py first")
        return
    
    print("Loading merged model...")
    tokenizer = AutoTokenizer.from_pretrained(str(model_path))
    model = AutoModelForCausalLM.from_pretrained(
        str(model_path),
        torch_dtype=torch.float16,
        device_map="auto",
    ).eval()
    
    print("Model loaded")
    
    # Cache schemas for all splits
    print("\nCaching schemas...")
    spider_db_path = Path("data/spider/database")
    splits_to_process = ["probe", "cal", "test"]
    
    all_db_ids = set()
    for split_name in splits_to_process:
        split = load_split(split_name)
        all_db_ids.update(row["db_id"] for row in split)
    
    schemas = {}
    for db_id in all_db_ids:
        db_path = spider_db_path / db_id / f"{db_id}.sqlite"
        schemas[db_id] = schema_from_sqlite(str(db_path))
    
    print(f"Cached {len(schemas)} schemas")
    
    # Process each split
    for split_name in splits_to_process:
        process_split(split_name, model, tokenizer, schemas, spider_db_path)
    
    print("\n✓ Phase 3.1 complete: Sampling and entropy computation done")
    print("\nNext steps:")
    print("  - Run s05b_timing.py for latency measurements")
    print("  - Run s06_teacher_answers.py for API reference answers")


if __name__ == "__main__":
    main()
