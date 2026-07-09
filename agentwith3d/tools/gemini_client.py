"""Client interface for interacting with Google Gemini models."""

import os
from typing import Dict, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from config import settings


class GeminiClient:
    """Wrapper class around Google Gemini LLM API client.

    Provides interface for standard text generation and structured outputs.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
    ):
        """Initializes the Gemini Client wrapper.

        Args:
            model_name: Overrides default model name from settings.
            temperature: Overrides default temperature from settings.
        """
        self.model_name = model_name or settings.DEFAULT_MODEL_NAME
        self.temperature = (
            temperature
            if temperature is not None
            else settings.DEFAULT_TEMPERATURE
        )
        # Use GEMINI_API_KEY or GOOGLE_API_KEY or fall back to "DUMMY_KEY" to pass init validation
        self.api_key = (
            settings.GEMINI_API_KEY
            or os.getenv("GOOGLE_API_KEY")
            or "DUMMY_KEY"
        )

        # Initialize the ChatGoogleGenerativeAI client
        self.llm = ChatGoogleGenerativeAI(
            model=self.model_name,
            temperature=self.temperature,
            google_api_key=self.api_key,
        )

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generates text response from Gemini model.

        Args:
            prompt: User message prompt.
            system_instruction: Optional system instruction prompt.
            config: Optional LLM call configuration parameters.

        Returns:
            The generated response string.
        """
        messages = []
        if system_instruction:
            messages.append(("system", system_instruction))
        messages.append(("user", prompt))

        response = self.llm.invoke(messages, config=config or {})
        return str(response.content)

    def generate_structured(
        self,
        prompt: str,
        response_schema: Any,
        system_instruction: Optional[str] = None,
    ) -> Any:
        """Generates structured data mapped to a Pydantic schema using Gemini.

        Args:
            prompt: User message prompt.
            response_schema: Pydantic model class to validate output against.
            system_instruction: Optional system instruction prompt.

        Returns:
            An instance of the response_schema class.
        """
        messages = []
        if system_instruction:
            messages.append(("system", system_instruction))
        messages.append(("user", prompt))

        # Use LangChain's native with_structured_output method
        structured_llm = self.llm.with_structured_output(response_schema)
        response = structured_llm.invoke(messages)
        return response
