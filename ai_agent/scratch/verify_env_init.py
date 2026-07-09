"""Verification script to test environment variable loading and client init."""

import os
import sys

# Add workspace directory to python path for correct imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.gemini_client import GeminiClient
from config import settings


def test_init():
    """Validates that GeminiClient initializes with the key from the root .env."""
    print("=== Environment Loading Verification ===")

    # Ensure python-dotenv has loaded it into os.environ
    env_key = os.getenv("GOOGLE_API_KEY")
    print(f"os.getenv('GOOGLE_API_KEY'): {env_key[:10] if env_key else 'None'}...")
    print(
        f"settings.GEMINI_API_KEY:     {settings.GEMINI_API_KEY[:10] if settings.GEMINI_API_KEY else 'None'}..."
    )

    # Instantiate the client
    client = GeminiClient()
    print("GeminiClient instantiated successfully!")
    print(f"Client API key:              {client.api_key[:10]}...")

    # Assertions
    assert client.api_key != "DUMMY_KEY", "Client fell back to DUMMY_KEY!"
    assert client.api_key.startswith(
        "AQ."
    ), "Loaded API key is invalid or incorrect!"
    print("\n[+] Verification PASSED!")


if __name__ == "__main__":
    test_init()
