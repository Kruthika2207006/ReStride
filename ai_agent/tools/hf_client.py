import os
import json
import base64
import urllib.request
import urllib.error
from typing import Dict, Any, Optional


class HFClient:
    """Sends multimodal requests to Hugging Face's Inference API."""

    def __init__(self, model_name: Optional[str] = None):
        """Initializes HFClient with a vision-language model."""
        self.model_name = model_name or "Qwen/Qwen2.5-VL-72B-Instruct"
        self.api_key = os.getenv("HUGGINGFACE_API_KEY") or ""
        print(f"[HFClient] Initialized with model: '{self.model_name}'")

    def generate(
        self,
        prompt: str,
        image_path: Optional[str] = None,
        system_instruction: Optional[str] = None,
    ) -> str:
        """Generates text or multimodal completion via Hugging Face Inference API.

        Args:
            prompt: User message prompt.
            image_path: Optional path to image.
            system_instruction: Optional system instruction prompt.

        Returns:
            The generated response string.
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # Build messages content list if image is present
        user_content = []
        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as f:
                img_base64 = base64.b64encode(f.read()).decode("utf-8")
            # Determine mime type (default to png)
            ext = os.path.splitext(image_path)[1].lower()
            mime_type = "image/png"
            if ext in [".jpg", ".jpeg"]:
                mime_type = "image/jpeg"
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime_type};base64,{img_base64}"}
            })
            user_content.append({"type": "text", "text": prompt})
        else:
            user_content = prompt

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": user_content})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.2
        }

        # Try user's specified endpoint first, fall back to router endpoint if DNS fails
        primary_url = f"https://api-inference.huggingface.co/models/{self.model_name}"
        fallback_url = "https://router.huggingface.co/v1/chat/completions"

        last_error = None
        for url in [primary_url, fallback_url]:
            print(f"[HFClient] Sending POST request to: {url}")
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            try:
                with urllib.request.urlopen(req, timeout=90) as response:
                    if response.status != 200:
                        raise Exception(f"HTTP status {response.status}")
                    res_data = json.loads(response.read().decode("utf-8"))
                    
                    if "choices" in res_data:
                        return res_data["choices"][0]["message"]["content"]
                    elif isinstance(res_data, list) and len(res_data) > 0 and "generated_text" in res_data[0]:
                        return res_data[0]["generated_text"]
                    else:
                        return str(res_data)
            except Exception as e:
                err_content = ""
                if hasattr(e, "read"):
                    try:
                        err_content = e.read().decode("utf-8")
                    except:
                        pass
                last_error = f"{str(e)}: {err_content}"
                print(f"[HFClient] Request failed for {url}. Error: {last_error}")

        raise Exception(f"HFClient failed to generate response. Last error: {last_error}")

    def generate_structured(
        self,
        prompt: str,
        response_schema: Any,
        system_instruction: Optional[str] = None,
        image_path: Optional[str] = None,
    ) -> Any:
        """Generates structured output validating against Pydantic schema.

        Args:
            prompt: User message prompt.
            response_schema: Pydantic model class to validate output against.
            system_instruction: Optional system instruction prompt.
            image_path: Optional path to image.

        Returns:
            An instance of the response_schema class.
        """
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

        raw_response = self.generate(
            prompt=struct_prompt,
            image_path=image_path,
            system_instruction=system_instruction
        )

        try:
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
            print(f"[HFClient] Failed to parse structured JSON: {raw_response}. Error: {parse_err}")
            raise parse_err
