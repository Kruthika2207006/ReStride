import os
import time
import logging
from typing import Dict, Any, Optional

from tools.openrouter_client import OpenRouterClient
from tools.hf_client import HFClient
from tools.gemini_client import GeminiClient

logger = logging.getLogger("FallbackClient")


class FallbackClient:
    """A client wrapper that routes calls through multiple providers sequentially if one fails."""

    def __init__(self):
        """Initializes the fallback providers."""
        self.openrouter = OpenRouterClient()
        self.hf = HFClient()
        self.gemini2 = GeminiClient(api_key=os.getenv("GOOGLE_API_KEY2"))
        self.gemini3 = GeminiClient(api_key=os.getenv("GOOGLE_API_KEY3"))

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        image_path: Optional[str] = None,
    ) -> str:
        """Attempts to generate text response using the fallback sequence.

        Args:
            prompt: User message prompt.
            system_instruction: Optional system instruction prompt.
            image_path: Optional path to image.

        Returns:
            The generated response string.
        """
        last_error = None

        # 1. OpenRouter
        try:
            print("[FallbackClient] Attempting OpenRouter for generate...")
            try:
                return self.openrouter.generate(prompt=prompt, system_instruction=system_instruction)
            except Exception as e:
                # If error is likely 429, retry once
                if "429" in str(e):
                    print("[FallbackClient] OpenRouter hit 429. Retrying in 3 seconds...")
                    time.sleep(3)
                    return self.openrouter.generate(prompt=prompt, system_instruction=system_instruction)
                raise e
        except Exception as e:
            last_error = str(e)
            print(f"[FallbackClient] OpenRouter failed: {last_error}. Falling back to HF...")

        # 2. Hugging Face
        try:
            print("[FallbackClient] Attempting Hugging Face for generate...")
            return self.hf.generate(prompt=prompt, image_path=image_path, system_instruction=system_instruction)
        except Exception as e:
            last_error = str(e)
            print(f"[FallbackClient] HF failed: {last_error}. Falling back to Gemini 2...")

        # 3. Gemini 2
        try:
            print("[FallbackClient] Attempting Gemini 2 for generate...")
            return self.gemini2.generate(prompt=prompt, system_instruction=system_instruction)
        except Exception as e:
            last_error = str(e)
            print(f"[FallbackClient] Gemini 2 failed: {last_error}. Falling back to Gemini 3...")

        # 4. Gemini 3
        try:
            print("[FallbackClient] Attempting Gemini 3 for generate...")
            return self.gemini3.generate(prompt=prompt, system_instruction=system_instruction)
        except Exception as e:
            last_error = str(e)
            print(f"[FallbackClient] Gemini 3 failed: {last_error}.")

        raise Exception(f"FallbackClient failed all providers. Last error: {last_error}")

    def generate_structured(
        self,
        prompt: str,
        response_schema: Any,
        system_instruction: Optional[str] = None,
        image_path: Optional[str] = None,
    ) -> Any:
        """Attempts to generate structured response matching schema using fallback sequence.

        Args:
            prompt: User message prompt.
            response_schema: Pydantic model class to validate output against.
            system_instruction: Optional system instruction prompt.
            image_path: Optional path to image.

        Returns:
            An instance of the response_schema class.
        """
        last_error = None

        # 1. OpenRouter
        try:
            print("[FallbackClient] Attempting OpenRouter for generate_structured...")
            try:
                return self.openrouter.generate_structured(
                    prompt=prompt,
                    response_schema=response_schema,
                    system_instruction=system_instruction
                )
            except Exception as e:
                if "429" in str(e):
                    print("[FallbackClient] OpenRouter hit 429 in structured. Retrying in 3 seconds...")
                    time.sleep(3)
                    return self.openrouter.generate_structured(
                        prompt=prompt,
                        response_schema=response_schema,
                        system_instruction=system_instruction
                    )
                raise e
        except Exception as e:
            last_error = str(e)
            print(f"[FallbackClient] OpenRouter structured failed: {last_error}. Falling back to HF...")

        # 2. Hugging Face
        try:
            print("[FallbackClient] Attempting Hugging Face for generate_structured...")
            return self.hf.generate_structured(
                prompt=prompt,
                response_schema=response_schema,
                system_instruction=system_instruction,
                image_path=image_path
            )
        except Exception as e:
            last_error = str(e)
            print(f"[FallbackClient] HF structured failed: {last_error}. Falling back to Gemini 2...")

        # 3. Gemini 2
        try:
            print("[FallbackClient] Attempting Gemini 2 for generate_structured...")
            return self.gemini2.generate_structured(
                prompt=prompt,
                response_schema=response_schema,
                system_instruction=system_instruction
            )
        except Exception as e:
            last_error = str(e)
            print(f"[FallbackClient] Gemini 2 structured failed: {last_error}. Falling back to Gemini 3...")

        # 4. Gemini 3
        try:
            print("[FallbackClient] Attempting Gemini 3 for generate_structured...")
            return self.gemini3.generate_structured(
                prompt=prompt,
                response_schema=response_schema,
                system_instruction=system_instruction
            )
        except Exception as e:
            last_error = str(e)
            print(f"[FallbackClient] Gemini 3 structured failed: {last_error}.")

        raise Exception(f"FallbackClient structured failed all providers. Last error: {last_error}")
