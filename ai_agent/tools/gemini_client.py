"""Client interface for interacting with Google Gemini models or Groq models."""

import os
import json
import time
import urllib.request
from typing import Dict, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from config import settings


class GeminiClient:
    """Wrapper class around Google Gemini or Groq LLM API client.

    Provides interface for standard text generation and structured outputs.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        api_key: Optional[str] = None,
    ):
        """Initializes the Client wrapper.

        Args:
            model_name: Overrides default model name from settings.
            temperature: Overrides default temperature from settings.
            api_key: Optional specific API key.
        """
        self.model_name = model_name or "gemini-2.5-flash"
        self.temperature = (
            temperature
            if temperature is not None
            else settings.DEFAULT_TEMPERATURE
        )
        self.api_key = (
            api_key
            or os.getenv("GROQ_API_KEY")
            or settings.GEMINI_API_KEY
            or os.getenv("GOOGLE_API_KEY")
            or "DUMMY_KEY"
        )

        # Detect if we should use Groq instead of Gemini
        self.use_groq = self.api_key.startswith("gsk_")
        if not self.use_groq and not self.model_name.startswith("gemini"):
            self.model_name = "gemini-2.5-flash"

        if self.use_groq:
            # Normalize model name for Groq API format
            self.groq_model = self.model_name
            if "qwen" in self.groq_model.lower():
                self.groq_model = self.groq_model.lower().replace(" ", "-")
            print(f"[GeminiClient] Groq integration active. Target model: '{self.groq_model}'")
            self.llm = None
        else:
            self.llm = ChatGoogleGenerativeAI(
                model=self.model_name,
                temperature=self.temperature,
                google_api_key=self.api_key,
                max_retries=0,
            )

    def _query_groq_api(self, messages: list, response_format: Optional[dict] = None) -> str:
        """Sends a request directly to the Groq chat completions API."""
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        }

        # Try to resolve user requested model first, fallback to standard Qwen models if rejected
        models_to_try = [self.groq_model, "qwen/qwen3.6-27b", "qwen/qwen3-32b"]
        last_error = None

        for model in models_to_try:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": self.temperature
            }
            if response_format:
                payload["response_format"] = response_format

            try:
                print(f"[GeminiClient] Attempting Groq request with model: '{model}'")
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers=headers,
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=60) as response:
                    res_data = json.loads(response.read().decode("utf-8"))
                    print(f"[GeminiClient] Groq request succeeded with model: '{model}'")
                    return res_data["choices"][0]["message"]["content"]
            except urllib.error.HTTPError as e:
                err_text = e.read().decode("utf-8")
                print(f"[GeminiClient] Groq model '{model}' HTTP Error {e.code}: {err_text}")
                
                # Check for Rate Limit Exceeded (429)
                if e.code == 429:
                    print("[GeminiClient] Rate limit hit. Entering backoff retry loop...")
                    for attempt in range(1, 4):
                        sleep_time = 12 * attempt
                        print(f"[GeminiClient] Rate limit 429 - Attempt {attempt}/3: Sleeping {sleep_time}s...")
                        time.sleep(sleep_time)
                        try:
                            req_retry = urllib.request.Request(
                                url,
                                data=json.dumps(payload).encode("utf-8"),
                                headers=headers,
                                method="POST"
                            )
                            with urllib.request.urlopen(req_retry, timeout=60) as response:
                                res_data = json.loads(response.read().decode("utf-8"))
                                print(f"[GeminiClient] Groq request succeeded on retry attempt {attempt} for model '{model}'")
                                return res_data["choices"][0]["message"]["content"]
                        except urllib.error.HTTPError as retry_e:
                            retry_err_text = retry_e.read().decode("utf-8")
                            print(f"[GeminiClient] Retry attempt {attempt} HTTP Error {retry_e.code}: {retry_err_text}")
                            if retry_e.code != 429:
                                last_error = retry_err_text
                                break
                            last_error = retry_err_text
                        except Exception as retry_sys_e:
                            print(f"[GeminiClient] Retry attempt {attempt} system error: {str(retry_sys_e)}")
                            last_error = str(retry_sys_e)
                            break
                else:
                    last_error = err_text
            except Exception as e:
                print(f"[GeminiClient] Groq model '{model}' system error: {str(e)}")
                last_error = str(e)

        raise Exception(f"Failed to query Groq API after trying models {models_to_try}. Last error: {last_error}")

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generates text response from Gemini or Groq model.

        Args:
            prompt: User message prompt.
            system_instruction: Optional system instruction prompt.
            config: Optional LLM call configuration parameters.

        Returns:
            The generated response string.
        """
        if self.use_groq:
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({"role": "user", "content": prompt})
            return self._query_groq_api(messages)
        else:
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
        """Generates structured data mapped to a Pydantic schema using Gemini or Groq.

        Args:
            prompt: User message prompt.
            response_schema: Pydantic model class to validate output against.
            system_instruction: Optional system instruction prompt.

        Returns:
            An instance of the response_schema class.
        """
        if self.use_groq:
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})

            # Fetch the schema structure
            schema_json = json.dumps(response_schema.model_json_schema() if hasattr(response_schema, "model_json_schema") else response_schema.schema())
            struct_prompt = (
                f"{prompt}\n\n"
                f"You MUST return a JSON object that matches the following schema:\n"
                f"{schema_json}\n\n"
                f"Do not include any Markdown styling, wrap in triple backticks, or extra explanation text."
            )
            messages.append({"role": "user", "content": struct_prompt})

            raw_response = self._query_groq_api(messages, response_format={"type": "json_object"})
            
            try:
                # Remove markdown wraps if any
                cleaned = raw_response.strip()
                if cleaned.startswith("```"):
                    lines = cleaned.splitlines()
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines[-1].startswith("```"):
                        lines = lines[:-1]
                    cleaned = "\n".join(lines).strip()
                
                return response_schema.parse_raw(cleaned)
            except Exception as parse_err:
                print(f"[GeminiClient] Failed to parse structured JSON: {raw_response}. Error: {parse_err}")
                raise parse_err
        else:
            messages = []
            if system_instruction:
                messages.append(("system", system_instruction))
            messages.append(("user", prompt))

            # Use LangChain's native with_structured_output method
            structured_llm = self.llm.with_structured_output(response_schema)
            response = structured_llm.invoke(messages)
            return response
