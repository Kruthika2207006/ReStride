"""Structured schema definitions for the Clinical Reasoning Agent output."""

from typing import List
from pydantic import BaseModel, Field


class PressureSensitiveRegion(BaseModel):
    """Identified pressure-sensitive area of the residual limb."""

    region_name: str = Field(
        ...,
        description="Name of the pressure sensitive region (e.g. Fibular Head, Distal Tibia).",
    )
    risk_level: str = Field(
        ...,
        description="Level of risk (e.g. High, Medium, Low).",
    )
    justification: str = Field(
        ...,
        description="Detailed medical or biomechanical rationale for this risk assessment.",
    )


class ClinicalDesignConsideration(BaseModel):
    """Clinical consideration and its implication on socket design."""

    consideration: str = Field(
        ...,
        description="The design consideration recommendation (e.g. Patellar Tendon Bearing load, Distal End Relief).",
    )
    implication: str = Field(
        ...,
        description="Direct physical implication/action for socket fabrication (e.g. build up tibial crest relief, add padding).",
    )
    justification: str = Field(
        ...,
        description="Clinical explanation justifying why this design consideration is recommended.",
    )


class ClinicalAnalysis(BaseModel):
    """Structured clinical reasoning and recommendation output."""

    limb_analysis_summary: str = Field(
        ...,
        description="Comprehensive summary analyzing the physical metrics, skin condition, and geometry of the limb.",
    )
    pressure_sensitive_regions: List[PressureSensitiveRegion] = Field(
        default_factory=list,
        description="Evaluated regions on the residual limb vulnerable to pressure or shear.",
    )
    design_considerations: List[ClinicalDesignConsideration] = Field(
        default_factory=list,
        description="Direct socket design adjustments and characteristics derived from the clinical analysis.",
    )
    recommended_socket_type: str = Field(
        ...,
        description="Suggested socket style base (e.g. Patellar Tendon Bearing - PTB, Total Surface Bearing - TSB, or Hybrid).",
    )
    recommended_socket_type_reasoning: str = Field(
        ...,
        description="Explicit reasoning justifying the chosen socket type based on the patient's medical and mechanical factors.",
    )
