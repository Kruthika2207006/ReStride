"""Configuration module for the backend API server.

Loads environmental variables and exports constants.
"""

import os
from dotenv import load_dotenv

# Define the project root directory
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from the .env file at the project root
env_path = os.path.join(project_root, ".env")
load_dotenv(dotenv_path=env_path)

# Database Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "prosthetic_db")

# File Upload Configuration
raw_upload_folder = os.getenv("UPLOAD_FOLDER") or os.path.join(os.path.expanduser("~"), ".restride_uploads")
if not os.path.isabs(raw_upload_folder):
    UPLOAD_FOLDER = os.path.abspath(os.path.join(project_root, raw_upload_folder))
else:
    UPLOAD_FOLDER = os.path.abspath(raw_upload_folder)

# Constraints
MAX_IMAGE_SIZE_MB = 10
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}
MAX_FILES_PER_UPLOAD = 10

# Allowed CORS origins (comma-separated origins from environment)
raw_origins = os.getenv("ALLOWED_ORIGINS", "*")
if raw_origins == "*":
    ALLOWED_ORIGINS = ["*"]
else:
    ALLOWED_ORIGINS = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]

# API Key for authentication header (optional, empty value skips validation check)
API_KEY = os.getenv("API_KEY", "")

# Ensure that the absolute upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


import logging

# Configure Python's logging module for the backend application.
# The default log level is set to INFO. You can change this to DEBUG during development
# for more detailed logs (e.g. LOG_LEVEL = logging.DEBUG).
LOG_LEVEL = logging.INFO

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

# Root logger for the backend namespace
logger = logging.getLogger("backend")
logger.info(f"Structured logging initialized for backend at level: {logging.getLevelName(LOG_LEVEL)}")

