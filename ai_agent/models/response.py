"""Response data models for the Prosthetic Socket Recommendation system."""

from typing import List, Dict, Any
from pydantic import BaseModel, Field


class FinalReliefArea(BaseModel):
    """Anatomical region designated for material relief (carve-out)."""

    region_name: str = Field(
        ...,
        description="Name of the relief region (e.g. Fibular Head, Tibial Crest).",
    )
    depth_mm: float = Field(
        ...,
        description="Depth of relief relief channel in millimeters (e.g. 1.5, 3.0).",
    )
    reasoning: str = Field(
        ...,
        description="Reasoning explaining why this relief is applied.",
    )


class FinalPressureArea(BaseModel):
    """Anatomical region designated for weight-bearing pressure loading."""

    region_name: str = Field(
        ...,
        description="Name of the load region (e.g. Patellar Tendon, Medial Flare).",
    )
    depth_mm: float = Field(
        ...,
        description="Depth of inward model compression in millimeters (e.g. 2.0, 4.0).",
    )
    reasoning: str = Field(
        ...,
        description="Reasoning explaining why this loading is applied.",
    )


class SocketRecommendationResponse(BaseModel):
    """Final aggregated response schema representing the complete design recommendation."""

    patient_summary: str = Field(
        ...,
        description="Brief summary of the patient's demographics, K-level, and pathology context.",
    )
    geometry_summary: str = Field(
        ...,
        description="Brief summary of the 3D geometry scan metrics (length, shape, volume, watertightness).",
    )
    clinical_findings: str = Field(
        ...,
        description="Key findings from the Clinical reasoning agent (skin condition, risk of ulcers, tissue tolerance).",
    )
    socket_design: str = Field(
        ...,
        description="Final selected socket design type (e.g. Total Surface Bearing - TSB, Patellar Tendon Bearing - PTB, or Hybrid).",
    )
    suspension_system: str = Field(
        ...,
        description="Final selected suspension system (e.g. Suction, Pin Lock, Elevated Vacuum).",
    )
    liner_recommendation: str = Field(
        ...,
        description="Final selected liner type and material guidelines (e.g. Silicone Gel Liner, Polyurethane).",
    )
    relief_areas: List[FinalReliefArea] = Field(
        default_factory=list,
        description="List of finalized regions requiring material relief in the fabricated mold.",
    )
    pressure_tolerant_areas: List[FinalPressureArea] = Field(
        default_factory=list,
        description="List of finalized regions requiring loading compressions in the fabricated mold.",
    )
    safety_warnings: List[str] = Field(
        default_factory=list,
        description="Aggregated risk warning and mitigation notifications.",
    )
    fabrication_approval: bool = Field(
        ...,
        description="Pass/fail safety clearance flag. Must be False if safety violations remain unmitigated.",
    )
    final_confidence_score: float = Field(
        ...,
        description="Self-assessed system confidence score (0.0 to 1.0) for this final configuration.",
    )
    ai_explanation: str = Field(
        ...,
        description="Detailed text explaining why this specific final configuration was chosen, resolving any agent conflicts.",
    )
    fabrication_parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Key parameters for geometric mesh generators: includes thickness_mm, offsets, and material choices.",
    )
