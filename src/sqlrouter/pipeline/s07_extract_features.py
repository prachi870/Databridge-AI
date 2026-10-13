"""
Phase 4.1: Extract hidden states from the model for probe training.

Extracts features from multiple layers at the last prompt token position
(the position that predicts the first SQL token). This allows ablation
over which layer provides the best signal.
"""
import json
from pathlib import Path
import torch
import numpy as np
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModelForCausalLM

from sqlrouter.common.config import load_config
from sqlrouter.common.splits import load_split
from sqlrouter.common.prompt import schema_from_sqlite, render


def extract_features_batch(
    model, tokenizer, prompts: list[str], layers: list[int], batch_size: int = 8
):
    """Extract hidden states from specified layers for a list of prompts.
    
    Args:
        model: The model to extract from
        tokenizer: Tokenizer (with left padding for batching)
        prompts: List of prompt strings
        layers: List of layer indices to extract from
        batch_size: Number of prompts to process at once
        
    Returns:
        Dict mapping layer index to numpy array of shape [n_prompts, hidden_dim]
    """
    # Sort prompts by length for efficient batching
    n = len(prompts)
    lengths = [len(p) for p in prompts]
    order = np.argsort(lengths)
    
    # Initialize output arrays
    hidden_size = model.config.hidden_size
    features = {layer: np.zeros((n, hidden_size), dtype=np.float16) for layer in layers}
    
    # Process in batches
    for i in range(0, n, batch_size):
        batch_indices = order[i:i + batch_size]
        batch_prompts = [prompts[j] for j in batch_indices]
        
        # Encode with padding
        encoded = tokenizer(
            batch_prompts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=2048,
        ).to(model.device)
        
        # Compute position IDs for left padding (critical for parity with serving)
        # This ensures padded positions are ignored correctly
        position_ids = (encoded.attention_mask.cumsum(-1) - 1).clamp(min=0)
        
        # Forward pass
        with torch.no_grad():
            outputs = model(
                **encoded,
                position_ids=position_ids,
                output_hidden_states=True,
            )
        
        # Extract last prompt token for each sequence
        # Last token position before generation starts
        last_positions = encoded.attention_mask.sum(dim=1) - 1
        
        for layer in layers:
            hidden_states = outputs.hidden_states[layer]  # [batch, seq, hidden]
            
            # Extract [batch, hidden] at last_positions
            batch_features = torch.stack([
                hidden_states[b, last_positions[b], :]
                for b in range(len(batch_prompts))
            ])
            
            # Convert to fp16 numpy and store
            batch_features_np = batch_features.float().cpu().numpy().astype(np.float16)
            
            for k, idx in enumerate(batch_indices):
                features[layer][idx] = batch_features_np[k]
    
    return features


def main():
    cfg = load_config("qlora")
    model_path = Path("artifacts/merged/qlora_r16")
    
    if not model_path.exists():
        print(f"ERROR: Merged model not found at {model_path}")
        print("Please run s04_merge.py first")
        return
    
    print("Loading model...")
    tokenizer = AutoTokenizer.from_pretrained(str(model_path))
    tokenizer.padding_side = "left"  # Important for batching
    
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    model = AutoModelForCausalLM.from_pretrained(
        str(model_path),
        torch_dtype=torch.float16,
        device_map="cuda",
    ).eval()
    
    print(f"Model loaded: {model.config.num_hidden_layers} layers")
    
    # Select layers to extract (distributed across depth)
    num_layers = model.config.num_hidden_layers
    layer_fractions = [0.25, 0.4, 0.55, 0.7, 0.85, 1.0]
    layers = sorted(set(int(num_layers * f) for f in layer_fractions))
    
    print(f"Extracting from layers: {layers}")
    print(f"  (fractions: {[round(l/num_layers, 2) for l in layers]})")
    
    # Process each split
    splits_to_process = ["probe", "cal", "test"]
    spider_db_path = Path("data/spider/database")
    
    # Cache schemas
    print("\nCaching schemas...")
    all_db_ids = set()
    for split_name in splits_to_process:
        split = load_split(split_name)
        all_db_ids.update(row["db_id"] for row in split)
    
    schemas = {}
    for db_id in all_db_ids:
        db_path = spider_db_path / db_id / f"{db_id}.sqlite"
        schemas[db_id] = schema_from_sqlite(str(db_path))
    
    print(f"Cached {len(schemas)} schemas")
    
    # Extract features for each split
    output_dir = Path("artifacts/features")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for split_name in splits_to_process:
        print(f"\nProcessing {split_name} split...")
        split = load_split(split_name)
        
        # Build prompts
        prompts = []
        for row in split:
            schema = schemas[row["db_id"]]
            prompt = render(tokenizer, schema, row["question"])
            prompts.append(prompt)
        
        print(f"  Extracting features from {len(prompts)} prompts...")
        
        # Extract with progress bar
        features = extract_features_batch(model, tokenizer, prompts, layers)
        
        # Save as compressed npz
        output_path = output_dir / f"{split_name}.npz"
        
        # Prepare data dict with layer keys like "L25"
        save_dict = {f"L{layer}": features[layer] for layer in layers}
        
        np.savez_compressed(output_path, **save_dict)
        
        print(f"  Saved to {output_path}")
        
        # Report sizes
        for layer in layers:
            print(f"    L{layer}: {features[layer].shape}")
    
    print("\n" + "="*50)
    print("Feature extraction complete!")
    print("="*50)
    print(f"Layers extracted: {layers}")
    print(f"Splits processed: {splits_to_process}")
    print(f"Output directory: {output_dir}")
    
    print("\n✓ Phase 4.1 complete: Feature extraction done")
    print("\nNext: Run s08_train_probes.py to train uncertainty probes")


if __name__ == "__main__":
    main()
