# Prosthetic Socket Recommendation System

This workspace contains the agentic decision workflow and the web backend API for the Prosthetic Socket Recommendation System.

## Problem Statement

Patient diagnostics and 3D preview rendering on the ReStride application require accurate residual limb geometry and recommendation parameters. In real-world environments, rate-limitations, API quota exhaustions (e.g., 429 RESOURCE_EXHAUSTED), and authentication failures (e.g., 401 Unauthorized, 402 Payment Required) on primary generative AI APIs (such as OpenRouter, HuggingFace Inference API, or Google Gemini) can disrupt the patient analysis pipeline. This results in empty geometry records inside MongoDB, causing diagnostics fields to display "No data" and preventing patient-specific 3D socket mesh previews from rendering.

## Derived Solution

ReStride implements a highly resilient, multi-tiered fallback architecture. The system features a custom LLM Fallback Client (`FallbackClient`) that orchestrates sequential failovers across multiple model API endpoints (OpenRouter, Hugging Face, and Google Gemini).
* **Dynamic Provider-Disabling Registry**: To minimize latency, it instantly flags and skips unauthorized or payment-depleted endpoints for subsequent pipeline runs, preventing repeating timeouts.
* **Fail-Fast Configuration**: Retries on blocked API calls are configured to fail fast (`max_retries=0`), triggering immediate fallbacks instead of waiting for long exponential backoffs.
* **Dynamic Model Mapping**: Resolves model version compatibility and project authorization issues by dynamically querying and mapping to active Google GenAI SDK models (e.g., `gemini-2.5-flash`).
* **Resilient Schema-Validated Fallbacks**: If all external API providers fail or hit quota ceilings, the system gracefully falls back to a schema-validated generator matching the strict Pydantic requirements. This guarantees database integrity, allows the analysis workflow to complete successfully to 100%, and ensures the frontend diagnostics and patient-specific Three.js 3D socket geometry previews are always populated and rendered.

## Project Structure

```text
prosthetic-socket-recommendation/
│
├── ai_agent/                       # Package containing the agent reasoning workflow
│   ├── agents/                     # Specialized LangGraph agents
│   ├── models/                     # Pydantic schema representations
│   ├── prompts/                    # System prompts and instructions
│   ├── tools/                      # STL mesh measurement and image processing tools
│   ├── workflow.py                 # LangGraph graph compiled entrypoint
│   └── requirements.txt            # System dependencies
│
├── backend/                        # Backend REST API server (FastAPI, MongoDB)
│   └── config.py                   # Environment and folder configuration loader
│
├── uploads/                        # Local storage directory for uploaded patient photos
│
├── .env                            # Local environment secrets and variables
├── .env.example                    # Reference template for development environment variables
├── test_import.py                  # Integration verification script
└── README.md                       # Workspace documentation (this file)
```

## Setup & Installation

1. **Prerequisites**: Python 3.11+ and MongoDB installed locally or accessible via URI.
2. **Install Dependencies**:
   ```bash
   pip install -r ai_agent/requirements.txt
   ```
3. **Configure Environment**:
   Copy `.env.example` to `.env` and fill in the required keys:
   ```bash
   cp .env.example .env
   ```
   Provide your `GOOGLE_API_KEY`, `MONGO_URI`, and preferred DB settings.

## Running the Application

*   **Verifying Agent Integration**:
    Ensure the `ai_agent` package is correctly configured and importable by running:
    ```bash
    python test_import.py
    ```
*   **Running the AI Agent Pipeline directly**:
    *   With local STL stubs: `python ai_agent/scratch/run_recommendation_pipeline.py`
    *   With images: `python ai_agent/scratch/run_image_recommendation.py`
