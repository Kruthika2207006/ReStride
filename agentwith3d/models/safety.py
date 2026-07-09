"""Structured schemas representing socket design safety validation results."""

from typing import List
from pydantic import BaseModel, Field


class SafetyCheck(BaseModel):
    """Result of validation against a specific safety constraint."""

    constraint_name: str = Field(
        ...,
        description="Name of the constraint check (e.g. Neuropathic Liner Check, Wall Thickness Limit).",
    )
    passed: bool = Field(
        ...,
        description="True if the constraint was successfully met; False otherwise.",
    )
    details: str = Field(
        ...,
        description="Detailed description of the check outcome and values evaluated.",
    )


class DetectedRisk(BaseModel):
    """Specific hazard or risk identified in the socket design."""

    risk_category: str = Field(
        ...,
        description="Category of risk (e.g. Skin Breakdown, Structural Weakness, Soft Tissue Compression).",
    )
    severity: str = Field(
        ...,
        description="Risk severity level: Low, Medium, or High.",
    )
    description: str = Field(
        ...,
        description="Explanation of the risk and how the current parameters trigger it.",
    )
    mitigation_action: str = Field(
        ...,
        description="Recommended design modification to resolve this risk (e.g. increase wall thickness, add distal relief).",
    )


class AgentConflict(BaseModel):
    """Contradiction or mismatch identified between the clinical recommendations and socket design choices."""

    conflict_description: str = Field(
        ...,
        description="Description of the conflict (e.g., Clinical Agent recommends TSB but Socket Agent chose PTB).",
    )
    resolution_suggestion: str = Field(
        ...,
        description="Proposed change to reconcile the differences.",
    )


class SafetyAnalysis(BaseModel):
    """Structured report produced by the Safety Validation Agent."""

    risk_score: str = Field(
        ...,
        description="Overall risk classification score (Low, Medium, or High).",
    )
    risk_explanation: str = Field(
        ...,
        description="General summary explaining the assigned risk score based on patient profile and socket design.",
    )
    validated_constraints: List[SafetyCheck] = Field(
        default_factory=list,
        description="List of standardized check-list validations run on the design.",
    )
    detected_risks: List[DetectedRisk] = Field(
        default_factory=list,
        description="List of potential clinical or structural risks discovered in the socket parameters.",
    )
    conflicting_recommendations: List[AgentConflict] = Field(
        default_factory=list,
        description="Discrepancies found between clinical design recommendations and geometric socket parameterization.",
    )
    is_safe_to_fabricate: bool = Field(
        ...,
        description="Ultimate pass/fail flag. If False, the design must not be sent for fabrication or mesh generation.",
    )
