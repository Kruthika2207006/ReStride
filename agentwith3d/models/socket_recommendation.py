"""Structured schemas representing complete socket recommendation design parameters."""

from typing import List, Dict
from pydantic import BaseModel, Field


class ReliefRegion(BaseModel):
    """Region where material is carved out to reduce local pressure."""

    region_name: str = Field(
        ...,
        description="Name of the relief zone (e.g. Tibial Crest, Fibular Head, Distal Tibia).",
    )
    depth_mm: float = Field(
        ...,
        description="Depth of relief relief channel in millimeters (e.g. 1.5, 3.0).",
    )
    reasoning: str = Field(
        ...,
        description="Clinical reasoning for applying relief to this specific region.",
    )


class PressureRegion(BaseModel):
    """Region where pressure is safely loaded to improve weight bearing."""

    region_name: str = Field(
        ...,
        description="Name of the pressure loading zone (e.g. Patellar Tendon, Medial Tibial Flare).",
    )
    depth_mm: float = Field(
        ...,
        description="Amount of model compression/inward offset in millimeters (e.g. 2.0, 4.0).",
    )
    reasoning: str = Field(
        ...,
        description="Clinical reasoning for loading weight onto this specific region.",
    )


class TrimlineRecommendations(BaseModel):
    """Recommended height constraints and boundary trimlines for the socket."""

    description: str = Field(
        ...,
        description="Qualitative description of trimline path (e.g. standard PTB profile, mid-patella cut).",
    )
    anterior_trim_height_cm: float = Field(
        ...,
        description="Trimline height at the front in cm relative to the patellar center.",
    )
    posterior_trim_height_cm: float = Field(
        ...,
        description="Trimline height at the back in cm relative to the popliteal crease.",
    )
    reasoning: str = Field(
        ...,
        description="Clinical logic supporting the anterior/posterior boundary profile heights.",
    )


class OffsetValues(BaseModel):
    """Offset parameters used directly by Open3D mesh generation algorithms."""

    radial_expansion_mm: float = Field(
        ...,
        description="Uniform expansion/contraction offset (in mm) applied to the internal socket wall.",
    )
    distal_clearance_mm: float = Field(
        ...,
        description="Clearance gap left at the distal end tip (in mm) for distal pad cushioning.",
    )
    ply_fit_compensation: float = Field(
        ...,
        description="Compensation factor for socket socks (ply size, e.g. 0.0 for 0-ply, 1.0 for 1-3 ply).",
    )


class SocketRecommendation(BaseModel):
    """Output recommendation response containing all parameterization data for socket design."""

    socket_design_type: str = Field(
        ...,
        description="Recommended socket type (e.g. Total Surface Bearing - TSB, Patellar Tendon Bearing - PTB, or Hybrid).",
    )
    socket_design_reasoning: str = Field(
        ...,
        description="Clinical analysis justifying this socket design type.",
    )
    suspension_system: str = Field(
        ...,
        description="Recommended suspension (e.g. Suction, Pin Lock, Elevated Vacuum).",
    )
    suspension_system_reasoning: str = Field(
        ...,
        description="Clinical analysis justifying this suspension system choice.",
    )
    liner_type: str = Field(
        ...,
        description="Liner material recommendation (e.g. Silicone Gel, Polyurethane, Copolymer Gel).",
    )
    liner_type_reasoning: str = Field(
        ...,
        description="Clinical reason supporting the selected liner material.",
    )
    socket_wall_thickness_mm: float = Field(
        ...,
        description="Recommended structural socket wall thickness in millimeters.",
    )
    socket_wall_thickness_reasoning: str = Field(
        ...,
        description="Safety and mechanical rationale for socket wall thickness selection.",
    )
    relief_regions: List[ReliefRegion] = Field(
        default_factory=list,
        description="List of specific locations requiring pressure relief modifications.",
    )
    pressure_regions: List[PressureRegion] = Field(
        default_factory=list,
        description="List of specific locations requiring weight loading modifications.",
    )
    trimline_recommendations: TrimlineRecommendations = Field(
        ...,
        description="Boundary guidelines and dimensions for trimming the fabricated socket.",
    )
    material_recommendations: List[str] = Field(
        ...,
        description="Recommended materials (e.g. Carbon Fiber Composite, Copolymer Sheet).",
    )
    material_recommendations_reasoning: str = Field(
        ...,
        description="Mechanical reasoning for selecting these fabrication materials.",
    )
    offset_values: OffsetValues = Field(
        ...,
        description="Exact geometric parameters for 3D socket mesh generation.",
    )
    offset_values_reasoning: str = Field(
        ...,
        description="Biomechanical logic for the geometric offset parameters.",
    )
