"""Geometry Agent for loading, validating, and extracting limb 3D scan metrics."""

from typing import Dict, Any
from tools.mesh_loader import MeshLoader
from tools.measurements import (
    compute_length,
    compute_surface_area,
    compute_volume,
    compute_bounding_box,
    compute_cross_sectional_circumferences,
    classify_shape,
)
from models.geometry import GeometryAnalysis


class GeometryAgent:
    """Loads, cleans, and measures the residual limb 3D STL mesh file.

    Extracts metrics needed for clinical and feature reasoning.
    """

    def __init__(self):
        """Initializes the Geometry Agent."""
        pass

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Runs the 3D analysis on the residual limb STL file.

        Args:
            state: The shared LangGraph state dictionary.

        Returns:
            State updates containing the geometry_analysis_results.
        """
        request = state.get("request")
        if not request:
            return {"errors": state.get("errors", []) + ["No request found in state."]}

        # Retrieve STL file path from request (metadata or top-level)
        stl_path = getattr(request, "stl_file_path", None)
        if not stl_path:
            # Check metadata as fallback
            metadata = getattr(request, "metadata", {}) or {}
            stl_path = metadata.get("stl_file_path")

        if not stl_path:
            return {
                "errors": state.get("errors", [])
                + ["No STL file path provided in request."]
            }

        try:
            # 1. Load the mesh
            raw_mesh = MeshLoader.load_stl(stl_path)

            # 2. Validate and repair
            repaired_mesh, is_watertight, mesh_status, warnings = (
                MeshLoader.validate_and_repair(raw_mesh)
            )

            # 3. Compute structural metrics
            length = compute_length(repaired_mesh)
            area = compute_surface_area(repaired_mesh)
            volume = compute_volume(repaired_mesh)
            bbox = compute_bounding_box(repaired_mesh)
            circumferences = compute_cross_sectional_circumferences(
                repaired_mesh
            )
            shape = classify_shape(circumferences)

            # 4. Construct response model
            analysis = GeometryAnalysis(
                limb_length_cm=round(length, 2),
                surface_area_cm2=round(area, 2),
                volume_cm3=round(volume, 2),
                bounding_box_dims=[round(d, 2) for d in bbox],
                cross_sectional_circumferences={
                    k: round(v, 2) for k, v in circumferences.items()
                },
                shape_descriptor=shape,
                is_watertight=is_watertight,
                num_vertices=repaired_mesh.num_vertices,
                num_triangles=repaired_mesh.num_triangles,
                mesh_status=mesh_status,
                errors=warnings,
            )

            return {
                "geometry_analysis_results": analysis.dict(),
                "next_step": "clinical_agent",
            }

        except Exception as e:
            return {
                "errors": state.get("errors", [])
                + [f"Geometry analysis failed: {str(e)}"],
                "next_step": "clinical_agent",  # Proceed to clinical agent so it can handle errors clinical-wise
            }
