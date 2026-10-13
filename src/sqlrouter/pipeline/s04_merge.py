"""
Phase 2.3: Merge LoRA adapter into fp16 base model.

This creates a standalone model for sampling and serving without needing
to load the adapter separately. Merging into fp16 ensures consistency
between training and inference.
"""
import torch
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

from sqlrouter.common.config import load_config


def main():
    cfg = load_config("qlora")
    model_name = cfg["base_model"]
    
    adapter_path = Path("artifacts/adapters/qlora_r16")
    output_path = Path("artifacts/merged/qlora_r16")
    
    if not adapter_path.exists():
        print(f"ERROR: Adapter not found at {adapter_path}")
        print("Please run s03_train_qlora.py first")
        return
    
    print("Loading base model in fp16...")
    base_model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float16,
        device_map="auto",
    )
    
    print(f"Loading adapter from {adapter_path}...")
    model = PeftModel.from_pretrained(base_model, str(adapter_path))
    
    print("Merging adapter into base model...")
    merged_model = model.merge_and_unload()
    
    print(f"Saving merged model to {output_path}...")
    output_path.mkdir(parents=True, exist_ok=True)
    merged_model.save_pretrained(str(output_path))
    
    # Save tokenizer as well
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    tokenizer.save_pretrained(str(output_path))
    
    print(f"\n✓ Merged model saved to {output_path}")
    print("This model can now be used for:")
    print("  - Sampling (Phase 3)")
    print("  - Feature extraction (Phase 4)")
    print("  - Serving (Phase 6)")
    
    print("\n✓ Phase 2.3 complete: Model merging done")


if __name__ == "__main__":
    main()
