"""Client interface for interacting with OpenRouter API using Qwen models."""

import os
import json
from typing import Dict, Any, Optional
from openai import OpenAI
from config import settings


class OpenRouterClient:
    """Wrapper class around OpenRouter API client.

    Provides interface for standard text generation and structured outputs using Qwen models.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
    ):
        """Initializes the OpenRouter Client wrapper.

        Args:
            model_name: Overrides default model name from settings.
            temperature: Overrides default temperature from settings.
        """
        # Resolve target model (default to qwen-2.5-vl-72b-instruct)
        self.model_name = model_name or settings.DEFAULT_MODEL_NAME
        if not self.model_name or "gemini" in self.model_name or "qwen3" in self.model_name:
            self.model_name = "qwen/qwen-2.5-vl-72b-instruct"

        self.temperature = (
            temperature
            if temperature is not None
            else settings.DEFAULT_TEMPERATURE
        )
        self.api_key = settings.OPENROUTER_API_KEY or os.getenv("OPENROUTER_API_KEY") or ""

        # Initialize the OpenAI client pointing to OpenRouter
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key,
            default_headers={
                "HTTP-Referer": "https://restride-clinical-assistant.com",
                "X-Title": "ReStride Clinical Assistant",
            }
        )
        print(f"[OpenRouterClient] Initialized with model: '{self.model_name}' and temperature: {self.temperature}")

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generates text response from OpenRouter model.

        Args:
            prompt: User message prompt.
            system_instruction: Optional system instruction prompt.
            config: Optional LLM call configuration parameters.

        Returns:
            The generated response string.
        """
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        print(f"[OpenRouterClient] Sending text completion query to model '{self.model_name}'")
        
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=self.temperature,
            max_tokens=2048,
        )
        return response.choices[0].message.content

    def generate_structured(
        self,
        prompt: str,
        response_schema: Any,
        system_instruction: Optional[str] = None,
    ) -> Any:
        """Generates structured data mapped to a Pydantic schema using OpenRouter.

        Args:
            prompt: User message prompt.
            response_schema: Pydantic model class to validate output against.
            system_instruction: Optional system instruction prompt.

        Returns:
            An instance of the response_schema class.
        """
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})

        # Inject JSON schema instructions
        schema_json = json.dumps(
            response_schema.model_json_schema()
            if hasattr(response_schema, "model_json_schema")
            else response_schema.schema()
        )
        struct_prompt = (
            f"{prompt}\n\n"
            f"You MUST return a JSON object that matches the following schema:\n"
            f"{schema_json}\n\n"
            f"Do not include any Markdown styling, wrap in triple backticks, or extra explanation text."
        )
        messages.append({"role": "user", "content": struct_prompt})

        print(f"[OpenRouterClient] Sending structured completion query to model '{self.model_name}'")

        # OpenRouter supports JSON Mode
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=self.temperature,
            max_tokens=2048,
            response_format={"type": "json_object"}
        )
        raw_response = response.choices[0].message.content

        try:
            # Clean markdown formatting if any was returned despite JSON Mode
            cleaned = raw_response.strip()
            if cleaned.startswith("```"):
                lines = cleaned.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                cleaned = "\n".join(lines).strip()

            if hasattr(response_schema, "model_validate_json"):
                return response_schema.model_validate_json(cleaned)
            else:
                return response_schema.parse_raw(cleaned)
        except Exception as parse_err:
            print(f"[OpenRouterClient] Failed to parse structured JSON: {raw_response}. Error: {parse_err}")
            raise parse_err
