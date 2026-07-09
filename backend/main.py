import os
import sys

# Ensure project root is in the Python search path to resolve 'ai_agent' imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import time
from typing import List, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, status, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
import uuid
import logging

from backend.config import ALLOWED_EXTENSIONS, MAX_IMAGE_SIZE_MB, UPLOAD_FOLDER, ALLOWED_ORIGINS, API_KEY, MAX_FILES_PER_UPLOAD
from backend.models import PatientCreate
from backend.database import get_patient, insert_patient, init_analysis, get_analysis, patients_collection, analysis_collection
from backend.tasks import run_analysis

logger = logging.getLogger("backend.main")

# Declare Security API Key header dependency
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(request: Request, api_key: Optional[str] = Depends(api_key_header)):
    """Verifies the X-API-Key request header if configured in environment."""
    if API_KEY:
        # Bypass API key validation for pre-flight and Swagger UI docs
        if request.method == "OPTIONS" or request.url.path in ["/docs", "/redoc", "/openapi.json"]:
            return
        if not api_key or api_key != API_KEY:
            logger.warning(f"Unauthorized API access attempt blocked. Path: {request.url.path}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API Key in X-API-Key header.",
            )

app = FastAPI(
    title="Prosthetic Socket AI Backend",
    description="REST API service for registering patients, uploading residual limb photos, and orchestrating socket designs.",
    version="1.0",
    dependencies=[Depends(verify_api_key)],
)

# Enable CORS with whitelist configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False if "*" in ALLOWED_ORIGINS else True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(f"HTTPException: status_code={exc.status_code}, detail={exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"RequestValidationError: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    correlation_id = str(uuid.uuid4())
    logger.exception(f"Unhandled exception occurred (correlation_id={correlation_id}): {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error. Please contact support.",
            "correlation_id": correlation_id
        },
    )


@app.post(
    "/api/patient",
    status_code=status.HTTP_201_CREATED,
    summary="Register a new patient profile",
    description="Ingests demographics and clinical history, creates a database record, and initializes pipeline tracker.",
)
async def create_patient(patient: PatientCreate):
    existing = await get_patient(patient.patient_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Patient profile with ID '{patient.patient_id}' already exists.",
        )

    # Save demographics and clinical history to patients collection
    try:
        await insert_patient(patient.dict())
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database insertion failed: {str(e)}",
        )

    # Initialize analysis tracking state
    init_success = await init_analysis(patient.patient_id)
    if not init_success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize analysis tracker document in collection.",
        )

    return {
        "message": "Patient created successfully",
        "patient_id": patient.patient_id,
    }


@app.post(
    "/api/upload/{patient_id}",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload patient residual limb images",
    description="Validates image file sizes and extensions, writes them to disk, and triggers the AI Agent analysis pipeline in a background task.",
)
async def upload_images(
    patient_id: str,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
):
    # Verify that the target patient profile exists
    patient = await get_patient(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient profile with ID '{patient_id}' does not exist.",
        )

    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files uploaded. Provide at least one image file.",
        )

    # 1. Enforce file upload count limits
    if len(files) > MAX_FILES_PER_UPLOAD:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too many files uploaded. Maximum files allowed per upload: {MAX_FILES_PER_UPLOAD}",
        )

    saved_files = []
    upload_dir = os.path.join(UPLOAD_FOLDER, patient_id)
    os.makedirs(upload_dir, exist_ok=True)

    for file in files:
        # 2. Validate file extension
        _, ext = os.path.splitext(file.filename.lower())
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File extension '{ext}' is not supported. Supported extensions: {ALLOWED_EXTENSIONS}",
            )

        # 3. Validate file size
        content = await file.read()
        size_bytes = len(content)
        size_mb = size_bytes / (1024 * 1024)
        if size_mb > MAX_IMAGE_SIZE_MB:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{file.filename}' size ({size_mb:.2f} MB) exceeds maximum allowed limit of {MAX_IMAGE_SIZE_MB} MB.",
            )

        # Reset pointer for completeness
        await file.seek(0)

        # 4. Prevent path traversal attacks and save file with a unique timestamp
        safe_filename = os.path.basename(file.filename)
        timestamp = int(time.time() * 1000)
        unique_filename = f"{timestamp}_{safe_filename}"

        file_path = os.path.abspath(os.path.join(upload_dir, unique_filename))
        if not file_path.startswith(os.path.abspath(upload_dir)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid upload filename detected (Path traversal attempt).",
            )

        try:
            with open(file_path, "wb") as f_out:
                f_out.write(content)
            saved_files.append(unique_filename)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to write file '{file.filename}' to disk: {str(e)}",
            )

    # 4. Trigger the AI recommendation analysis in the background
    background_tasks.add_task(run_analysis, patient_id, str(upload_dir))

    return {
        "message": "Images uploaded. Analysis started.",
        "patient_id": patient_id,
        "uploaded_files": saved_files,
    }


def make_component_response(component_key: str, analysis: dict):
    """Helper to formulate a standardized response for individual screens."""
    current_status = analysis.get("status")
    field_value = analysis.get(component_key)

    if current_status in ["pending", "processing"]:
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "detail": "Analysis not yet complete, please poll status endpoint",
                "status": current_status,
            },
        )
    elif current_status == "failed":
        return {
            component_key: field_value if field_value is not None else {},
            "status": "failed",
            "error": analysis.get("error") or "Unknown background error",
        }
    else:
        return {
            component_key: field_value if field_value is not None else {}
        }


@app.get(
    "/api/analysis/{patient_id}",
    tags=["Analysis"],
    summary="Get patient analysis progress and status",
    description="Retrieves the current execution state and accumulated results of the recommendation pipeline.",
)
async def get_patient_analysis(patient_id: str):
    analysis = await get_analysis(patient_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis tracking record with ID '{patient_id}' not found.",
        )
    # Remove _id field from response
    if "_id" in analysis:
        analysis.pop("_id")
    return analysis


@app.get(
    "/api/analysis/{patient_id}/geometry",
    tags=["Analysis"],
    summary="Get patient geometry analysis results",
)
async def get_analysis_geometry(patient_id: str):
    analysis = await get_analysis(patient_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis tracking record with ID '{patient_id}' not found.",
        )
    return make_component_response("geometry", analysis)


@app.get(
    "/api/analysis/{patient_id}/clinical",
    tags=["Analysis"],
    summary="Get patient clinical analysis results",
)
async def get_analysis_clinical(patient_id: str):
    analysis = await get_analysis(patient_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis tracking record with ID '{patient_id}' not found.",
        )
    return make_component_response("clinical", analysis)


@app.get(
    "/api/analysis/{patient_id}/socket",
    tags=["Analysis"],
    summary="Get patient socket recommendation results",
)
async def get_analysis_socket(patient_id: str):
    analysis = await get_analysis(patient_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis tracking record with ID '{patient_id}' not found.",
        )
    return make_component_response("socket", analysis)


@app.get(
    "/api/analysis/{patient_id}/safety",
    tags=["Analysis"],
    summary="Get patient safety validation results",
)
async def get_analysis_safety(patient_id: str):
    analysis = await get_analysis(patient_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis tracking record with ID '{patient_id}' not found.",
        )
    return make_component_response("safety", analysis)


@app.get(
    "/api/analysis/{patient_id}/final",
    tags=["Analysis"],
    summary="Get patient final consensus recommendation results",
)
async def get_analysis_final(patient_id: str):
    analysis = await get_analysis(patient_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis tracking record with ID '{patient_id}' not found.",
        )
    return make_component_response("final_response", analysis)


@app.get(
    "/api/test-error",
    tags=["Testing"],
    summary="Simulate an unhandled server error for exception handler testing",
)
async def simulate_unhandled_error():
    raise Exception("Simulated unhandled server error")


@app.get(
    "/api/analyses",
    response_model=List[dict],
    tags=["Analysis"],
    summary="Get recent analysis records with patient summary",
)
async def list_analyses(limit: int = 10):
    """Get recent analysis records with patient summary."""
    cursor = analysis_collection.find().sort("_id", -1).limit(limit)
    results = []
    async for doc in cursor:
        # Fetch patient name from patients collection
        patient = await patients_collection.find_one({"patient_id": doc["patient_id"]})
        
        # Determine case date
        created_at = doc.get("created_at")
        if not created_at:
            if hasattr(doc.get("_id"), "generation_time"):
                created_at = doc["_id"].generation_time.strftime("%Y-%m-%d")
            else:
                created_at = "2026-01-01"
                
        results.append({
            "patient_id": doc["patient_id"],
            "patient_name": patient.get("full_name", "Unknown") if patient else "Unknown",
            "status": doc.get("status", "pending"),
            "date": created_at,
            "amputation_level": patient.get("amputation_level", "Transtibial") if patient else "Transtibial",
            "age": patient.get("age", 0) if patient else 0,
            "gender": patient.get("gender", "Unknown") if patient else "Unknown",
            "activity_level": patient.get("activity_level", "K3") if patient else "K3",
            "conditions": [],  # optional
        })
    return results

