"""Backend configuration from environment variables."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application settings loaded from environment."""
    
    # Operating mode: "replay" (CPU, cached results) or "live" (GPU, real inference)
    mode: str = os.getenv("MODE", "replay")
    
    # Paths
    artifacts: Path = Path(os.getenv("ARTIFACTS", "artifacts"))
    model_dir: str = os.getenv("MODEL_DIR", "artifacts/merged/qlora_r16")
    
    # CORS origins (comma-separated)
    cors_origins: list[str] = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    
    # Rate limiting
    daily_api_cap: int = int(os.getenv("DAILY_API_CAP", "200"))
    rate_per_min: int = int(os.getenv("RATE_PER_MIN", "20"))
    
    # Server
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    
    @classmethod
    def validate(cls):
        """Validate settings on startup."""
        if cls.mode not in ["replay", "live"]:
            raise ValueError(f"MODE must be 'replay' or 'live', got: {cls.mode}")
        
        if cls.mode == "replay" and not (cls.artifacts / "results" / "router_config.json").exists():
            raise FileNotFoundError(
                f"Replay mode requires {cls.artifacts}/results/router_config.json. "
                "Run python scripts/make_fixtures.py to generate fixture data."
            )
        
        if cls.mode == "live":
            model_path = Path(cls.model_dir)
            if not model_path.exists():
                raise FileNotFoundError(
                    f"Live mode requires model at {model_path}. "
                    "Run the ML pipeline (s01-s10) to generate it."
                )


# Create singleton instance
settings = Settings()
