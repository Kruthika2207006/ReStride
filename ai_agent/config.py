"""Configuration module for the AI Agent system.

This module loads environment variables and defines settings for the LLM
and external services.
"""

import os
from dotenv import load_dotenv

# Load environment variables from a .env file if present
load_dotenv()


class Settings:
    """System-wide configuration settings.

    TODO: Implement additional custom configurations as needed, such as
    database settings, logger configurations, or connection timeouts.
    """

    # Gemini API Key
    GEMINI_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")

    # OpenRouter API Key
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")

    # Hugging Face API Key
    HUGGINGFACE_API_KEY: str = os.getenv("HUGGINGFACE_API_KEY", "")

    # Alternate Gemini Keys
    GOOGLE_API_KEY2: str = os.getenv("GOOGLE_API_KEY2", "")
    GOOGLE_API_KEY3: str = os.getenv("GOOGLE_API_KEY3", "")

    # LLM Settings
    DEFAULT_MODEL_NAME: str = os.getenv("DEFAULT_MODEL_NAME", "gemini-2.5-flash")
    DEFAULT_TEMPERATURE: float = float(os.getenv("DEFAULT_TEMPERATURE", "0.2"))

    # Orchestrator Settings
    MAX_ROUTING_LOOPS: int = int(os.getenv("MAX_ROUTING_LOOPS", "5"))


# Instantiate a global settings object
settings = Settings()
