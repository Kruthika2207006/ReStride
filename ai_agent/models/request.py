"""Request data models for the Prosthetic Socket Recommendation system."""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class ResidualLimbDetails(BaseModel):
    """Details regarding the patient's residual limb."""

    shape: str = Field(
        ...,
        description="Limb shape (e.g., conical, cylindrical, bulbous).",
    )
    length_cm: float = Field(
        ...,
        description="Limb length in centimeters.",
    )
    proximal_circumference_cm: float = Field(
        ...,
        description="Residual limb circumference at the proximal end in cm.",
    )
    mid_limb_circumference_cm: float = Field(
        ...,
        description="Residual limb circumference at mid-limb in cm.",
    )
    distal_circumference_cm: float = Field(
        ...,
        description="Residual limb circumference at the distal end in cm.",
    )
    skin_condition: str = Field(
        ...,
        description="Condition of the skin (e.g., healthy, scarred, fragile, ulcerated).",
    )
    prominent_bones: bool = Field(
        default=False,
        description="Whether there are bony prominences that require pressure relief.",
    )
    additional_notes: Optional[str] = Field(
        default=None,
        description="Any additional observation about the residual limb.",
    )


class PatientClinicalHistory(BaseModel):
    """Clinical history relevant to prosthetic design."""

    amputation_reason: str = Field(
        ...,
        description="Reason for amputation (e.g., trauma, diabetes, vascular disease).",
    )
    has_diabetes: bool = Field(
        default=False,
        description="Indicates if the patient is diabetic.",
    )
    has_neuropathy: bool = Field(
        default=False,
        description="Indicates if the patient has loss of sensation in the residual limb.",
    )
    volume_fluctuations: bool = Field(
        default=False,
        description="Indicates if the patient experiences significant daily limb volume changes.",
    )


class GeometryAnalysisResults(BaseModel):
    """Geometric scanner analysis results of the residual limb."""

    bone_prominences: List[str] = Field(
        default_factory=list,
        description="List of identified prominent bones (e.g., Fibular Head, Tibial Crest, Distal Tibia).",
    )
    soft_tissue_thickness: str = Field(
        ...,
        description="Classification of soft tissue coverage (e.g., thin, average, thick).",
    )
    tissue_mobility: str = Field(
        ...,
        description="Mobility of the tissue over bone (e.g., adherent, mobile, highly mobile).",
    )
    asymmetry_detected: bool = Field(
        default=False,
        description="Flag indicating if severe shape asymmetry was identified.",
    )
    additional_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Raw or derived geometric properties from scan parsing.",
    )


class SocketRecommendationRequest(BaseModel):
    """Input request schema for recommending a prosthetic socket design."""

    patient_id: str = Field(
        ...,
        description="Unique identifier for the patient.",
    )
    age: int = Field(
        ...,
        description="Patient age in years.",
    )
    weight_kg: float = Field(
        ...,
        description="Patient weight in kilograms.",
    )
    activity_level: str = Field(
        ...,
        description="Patient activity level (e.g., K1, K2, K3, K4).",
    )
    amputation_level: str = Field(
        ...,
        description="Amputation level (e.g., transtibial, transfemoral).",
    )
    limb_details: ResidualLimbDetails = Field(
        ...,
        description="Physical measurements and status of the residual limb.",
    )
    clinical_history: PatientClinicalHistory = Field(
        ...,
        description="Clinical history of the patient.",
    )
    geometry_analysis: Optional[GeometryAnalysisResults] = Field(
        default=None,
        description="Structural and geometry scanner results (optional, can be computed from STL).",
    )
    stl_file_path: Optional[str] = Field(
        default=None,
        description="Local path to the residual limb STL mesh file.",
    )
    image_folder_path: Optional[str] = Field(
        default=None,
        description="Local path to the folder containing residual limb images.",
    )
    current_issues: Optional[str] = Field(
        default=None,
        description="Current socket issues if patient is already using a prosthesis (e.g., skin breakdown, discomfort).",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional custom properties or context.",
    )
