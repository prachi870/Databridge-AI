"""
Phase 2.2: QLoRA fine-tuning on the SFT split.

Trains the model with 4-bit quantization and LoRA adapters for parameter efficiency.
"""
import torch
from pathlib import Path
from datasets import Dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model
from trl import SFTTrainer, SFTConfig
import wandb

from sqlrouter.common.config import load_config
from sqlrouter.common.splits import load_split
from sqlrouter.common.prompt import schema_from_sqlite, build_messages


def prepare_dataset(split_rows, schemas, tokenizer):
    """Convert split rows to SFT format with prompt/completion structure."""
    data = []
    
    for row in split_rows:
        db_id = row["db_id"]
        schema = schemas[db_id]
        
        # Prompt: system + user messages
        prompt = build_messages(schema, row["question"])
        
        # Completion: assistant message with SQL
        completion = [{"role": "assistant", "content": row["gold"]}]
        
        data.append({
            "prompt": prompt,
            "completion": completion,
        })
    
    return Dataset.from_list(data)


def main():
    cfg = load_config("qlora")
    
    # Initialize W&B
    wandb.init(
        project="sql-router",
        name="qlora-training",
        config=cfg,
    )
    
    print("Loading model and tokenizer...")
    model_name = cfg["base_model"]
    
    # BitsAndBytes config for 4-bit quantization
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.float16,  # T4 doesn't support bf16
    )
    
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map="auto",
    )
    
    print(f"Model loaded with 4-bit quantization: {model_name}")
    
    # LoRA configuration
    lora_config = LoraConfig(
        r=cfg["lora"]["r"],
        lora_alpha=cfg["lora"]["alpha"],
        lora_dropout=cfg["lora"]["dropout"],
        target_modules="all-linear",
        use_dora=cfg["lora"]["dora"],
        task_type="CAUSAL_LM",
    )
    
    print(f"LoRA config: r={lora_config.r}, alpha={lora_config.lora_alpha}, "
          f"dropout={lora_config.lora_dropout}, DoRA={lora_config.use_dora}")
    
    # Load SFT split and prepare dataset
    print("\nPreparing training data...")
    sft_split = load_split("sft")
    print(f"Loaded {len(sft_split)} SFT questions")
    
    # Limit to configured number
    sft_split = sft_split[:cfg["data"]["sft_questions"]]
    print(f"Using {len(sft_split)} questions for training")
    
    # Cache schemas
    spider_db_path = Path("data/spider/database")
    schemas = {}
    for row in sft_split:
        db_id = row["db_id"]
        if db_id not in schemas:
            db_path = spider_db_path / db_id / f"{db_id}.sqlite"
            schemas[db_id] = schema_from_sqlite(str(db_path))
    
    print(f"Cached schemas for {len(schemas)} databases")
    
    # Prepare dataset
    train_dataset = prepare_dataset(sft_split, schemas, tokenizer)
    print(f"Dataset prepared: {len(train_dataset)} examples")
    
    # Training arguments
    output_dir = Path("artifacts/sft_out")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    training_args = SFTConfig(
        output_dir=str(output_dir),
        num_train_epochs=cfg["train"]["epochs"],
        per_device_train_batch_size=cfg["train"]["per_device_bs"],
        gradient_accumulation_steps=cfg["train"]["grad_accum"],
        learning_rate=cfg["train"]["lr"],
        lr_scheduler_type="cosine",
        warmup_ratio=cfg["train"]["warmup"],
        fp16=True,
        logging_steps=10,
        gradient_checkpointing=True,
        optim="paged_adamw_8bit",
        max_seq_length=cfg["train"]["max_len"],
        report_to="wandb",
        save_strategy="no",  # Don't save intermediate checkpoints
        dataset_text_field="text",  # TRL will format prompt+completion
    )
    
    print("\nTraining configuration:")
    print(f"  Epochs: {training_args.num_train_epochs}")
    print(f"  Batch size: {training_args.per_device_train_batch_size}")
    print(f"  Gradient accumulation: {training_args.gradient_accumulation_steps}")
    print(f"  Effective batch size: {training_args.per_device_train_batch_size * training_args.gradient_accumulation_steps}")
    print(f"  Learning rate: {training_args.learning_rate}")
    print(f"  Max sequence length: {training_args.max_seq_length}")
    
    # Create trainer
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        peft_config=lora_config,
        processing_class=tokenizer,
    )
    
    print("\n" + "="*50)
    print("Starting QLoRA training...")
    print("="*50 + "\n")
    
    # Train!
    trainer.train()
    
    # Save adapter
    adapter_dir = Path("artifacts/adapters/qlora_r16")
    adapter_dir.mkdir(parents=True, exist_ok=True)
    
    trainer.save_model(str(adapter_dir))
    tokenizer.save_pretrained(str(adapter_dir))
    
    print(f"\n✓ Training complete! Adapter saved to {adapter_dir}")
    
    # Log final stats
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())
    trainable_pct = 100 * trainable_params / total_params
    
    print(f"\nTrainable parameters: {trainable_params:,} ({trainable_pct:.2f}% of total)")
    
    wandb.log({
        "trainable_params": trainable_params,
        "total_params": total_params,
        "trainable_pct": trainable_pct,
    })
    
    print("\n✓ Phase 2.2 complete: QLoRA training done")
    
    wandb.finish()


if __name__ == "__main__":
    main()
