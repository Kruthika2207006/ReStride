"""Pydantic request and response schemas for the backend application server."""

from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class StatusEnum(str, Enum):
    """Execution status states for the recommendation pipeline."""

    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class PatientCreate(BaseModel):
    """Schema representing patient demographics and history payload."""

    patient_id: str = Field(
        ...,
        pattern=r"^[a-zA-Z0-9\-]+$",
        description="Unique identifier containing only alphanumeric characters and hyphens."
    )
    full_name: str = Field(..., description="Patient's full name.")
    age: int = Field(..., gt=0, lt=120, description="Patient's age in years.")
    gender: str = Field(..., description="Patient's gender.")
    weight_kg: float = Field(..., gt=0.0, description="Patient's weight in kilograms.")
    height_cm: float = Field(..., gt=0.0, description="Patient's height in centimeters.")
    activity_level: str = Field(..., description="Patient's activity level (e.g. K1, K2, K3, K4).")
    amputation_level: str = Field(default="transtibial", description="Amputation level of the limb.")
    clinical_history: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Clinical attributes like has_diabetes, has_neuropathy, volume_fluctuations.",
    )
    limb_details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Physical characteristics of the residual limb (shape, length, circumferences, etc.).",
    )


class AnalysisStatus(BaseModel):
    """Schema tracking the execution status and incremental outputs of the AI Agent pipeline."""

    patient_id: str = Field(..., description="Unique identifier of the patient.")
    status: StatusEnum = Field(default=StatusEnum.PENDING, description="Current execution state.")
    progress: float = Field(default=0.0, ge=0.0, le=100.0, description="Percentage of pipeline completion (0-100).")
    error: Optional[str] = Field(default=None, description="Error message if the execution failed.")
    geometry: Optional[Dict[str, Any]] = Field(default=None, description="Results from GeometryAgent metric calculations.")
    clinical: Optional[Dict[str, Any]] = Field(default=None, description="Clinical evaluation and reasoning findings.")
    socket: Optional[Dict[str, Any]] = Field(default=None, description="Proposed prosthetic socket design configuration.")
    safety: Optional[Dict[str, Any]] = Field(default=None, description="Safety validator checks and risk classification.")
    final_response: Optional[Dict[str, Any]] = Field(default=None, description="Final consensus synthesis recommendation.")
