"""Teacher (frontier API) client for generating reference answers."""
import os
import time
from typing import Optional


class Teacher:
    """Client for calling frontier APIs (Anthropic, OpenAI, or Groq) for reference SQL."""
    
    def __init__(self):
        self.provider = os.environ.get("TEACHER_PROVIDER", "anthropic")
        self.model = os.environ["TEACHER_MODEL"]
        
        if self.provider == "anthropic":
            import anthropic
            self.client = anthropic.Anthropic()
        elif self.provider == "groq":
            from groq import Groq
            self.client = Groq()
        else:
            from openai import OpenAI
            self.client = OpenAI()
    
    def sql(
        self, messages: list[dict[str, str]], retries: int = 4
    ) -> tuple[str, int, int]:
        """Generate SQL from a frontier API with retry logic.
        
        Args:
            messages: List of message dicts (system, user)
            retries: Number of retry attempts on failure
            
        Returns:
            Tuple of (generated_text, input_tokens, output_tokens)
            
        Raises:
            RuntimeError: If all retries are exhausted
        """
        for i in range(retries):
            try:
                if self.provider == "anthropic":
                    response = self.client.messages.create(
                        model=self.model,
                        max_tokens=400,
                        system=messages[0]["content"],
                        messages=messages[1:],
                    )
                    return (
                        response.content[0].text,
                        response.usage.input_tokens,
                        response.usage.output_tokens,
                    )
                elif self.provider == "groq":
                    # Groq uses OpenAI-compatible API
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        max_tokens=400,
                    )
                    return (
                        response.choices[0].message.content,
                        response.usage.prompt_tokens,
                        response.usage.completion_tokens,
                    )
                else:
                    # OpenAI
                    response = self.client.chat.completions.create(
                        model=self.model, messages=messages
                    )
                    return (
                        response.choices[0].message.content,
                        response.usage.prompt_tokens,
                        response.usage.completion_tokens,
                    )
            except Exception as e:
                status_code = getattr(e, "status_code", None)
                if i == retries - 1 or (
                    status_code is not None
                    and 400 <= status_code < 500
                    and status_code != 429
                ):
                    raise
                # Exponential backoff
                time.sleep(2 ** i)
        
        raise RuntimeError("Teacher call failed after all retries")
