"""Model service for live inference mode (GPU required)."""
import torch
import joblib
from pathlib import Path

from sqlrouter.common.prompt import extract_sql


class ModelService:
    """Wrapper for local model and probe for live inference."""
    
    def __init__(self, model_dir: str, probe_path: str):
        """Initialize model and probe.
        
        Args:
            model_dir: Path to merged model directory
            probe_path: Path to probe .joblib file
        """
        print(f"Loading model from {model_dir}...")
        
        # Lazy import to avoid loading torch in replay mode
        from transformers import AutoTokenizer, AutoModelForCausalLM
        
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_dir,
            torch_dtype=torch.float16,
            device_map="cuda",
        ).eval()
        
        print(f"Model loaded on {self.model.device}")
        
        # Load probe
        print(f"Loading probe from {probe_path}...")
        probe_bundle = joblib.load(probe_path)
        self.probe = probe_bundle["pipe"]
        self.layer = probe_bundle["layer"]
        
        print(f"Probe loaded (layer {self.layer})")
    
    @torch.no_grad()
    def score(self, prompt: str) -> float:
        """Compute uncertainty score for a prompt.
        
        Args:
            prompt: Formatted prompt string
            
        Returns:
            Uncertainty score (probability of failure)
        """
        # Encode (batch of 1, no padding needed)
        encoded = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        
        # Forward pass to get hidden states
        outputs = self.model(**encoded, output_hidden_states=True)
        
        # Extract last prompt token from specified layer
        hidden_state = outputs.hidden_states[self.layer][0, -1, :]
        
        # Run probe
        features = hidden_state.float().cpu().numpy()[None, :]
        prob = self.probe.predict_proba(features)[0, 1]
        
        return float(prob)
    
    @torch.no_grad()
    def generate(self, prompt: str, max_new_tokens: int = 256) -> str:
        """Generate SQL from a prompt.
        
        Args:
            prompt: Formatted prompt string
            max_new_tokens: Maximum tokens to generate
            
        Returns:
            Generated SQL (extracted from raw output)
        """
        encoded = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        
        outputs = self.model.generate(
            **encoded,
            max_new_tokens=max_new_tokens,
            do_sample=False,  # Greedy
            pad_token_id=self.tokenizer.pad_token_id,
        )
        
        # Decode only the generated part
        generated_ids = outputs[0, encoded.input_ids.shape[1]:]
        raw_text = self.tokenizer.decode(generated_ids, skip_special_tokens=True)
        
        # Extract SQL
        return extract_sql(raw_text)
