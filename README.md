# Prosthetic Socket Recommendation System

This workspace contains the agentic decision workflow and the web backend API for the Prosthetic Socket Recommendation System.

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
