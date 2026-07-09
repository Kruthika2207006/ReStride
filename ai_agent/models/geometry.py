"""Structured schema definitions for the Geometry Analysis output."""

from typing import List, Dict, Any
from pydantic import BaseModel, Field


class GeometryAnalysis(BaseModel):
    """Output schema for the 3D geometry analysis of the residual limb."""

    limb_length_cm: float = Field(
        ...,
        description="Limb length in centimeters measured along the long axis.",
    )
    surface_area_cm2: float = Field(
        ...,
        description="Total surface area of the residual limb mesh in square centimeters.",
    )
    volume_cm3: float = Field(
        ...,
        description="Total volume of the watertight residual limb mesh in cubic centimeters.",
    )
    bounding_box_dims: List[float] = Field(
        ...,
        description="Bounding box dimensions [width, depth, height] in centimeters.",
    )
    cross_sectional_circumferences: Dict[str, float] = Field(
        ...,
        description="Calculated circumferences (in cm) at relative heights (e.g., '20%', '40%', '60%', '80%' from distal tip).",
    )
    shape_descriptor: str = Field(
        ...,
        description="Classification of shape (conical, cylindrical, or bulbous).",
    )
    is_watertight: bool = Field(
        ...,
        description="Indicates if the mesh is watertight (closed volume).",
    )
    num_vertices: int = Field(
        ...,
        description="Number of vertices in the analyzed mesh.",
    )
    num_triangles: int = Field(
        ...,
        description="Number of triangles/faces in the analyzed mesh.",
    )
    mesh_status: str = Field(
        ...,
        description="Verification state of the mesh (e.g., Clean, Repaired, Unrepairable).",
    )
    errors: List[str] = Field(
        default_factory=list,
        description="Validation errors or warnings encountered during processing.",
    )
    additional_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Raw or derived geometric properties from image/mesh parsing.",
    )
