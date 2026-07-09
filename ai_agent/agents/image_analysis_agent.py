"""Image Analysis Agent for orchestrating the residual limb image processing pipeline."""

import os
import json
from typing import Dict, Any, List

from tools.image_pipeline.image_analysis_loader import run_image_pipeline


class ImageAnalysisAgent:
    """Orchestrates the image processing pipeline to analyze residual limb images.

    Accepts an image folder path, calls the pipeline loader, and validates
    the resulting JSON output.
    """

    def __init__(self):
        """Initializes the Image Analysis Agent."""
        pass

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Runs the image analysis pipeline on the input folder path.

        Args:
            state: The shared LangGraph state dictionary.

        Returns:
            State updates containing image_analysis_results and/or errors.
        """
        request = state.get("request")
        if not request:
            return {"errors": state.get("errors", []) + ["No request found in state."]}

        # Accept image folder path from request (metadata or top-level)
        image_folder_path = getattr(request, "image_folder_path", None)
        if not image_folder_path:
            # Check metadata as fallback
            metadata = getattr(request, "metadata", {}) or {}
            image_folder_path = metadata.get("image_folder_path")

        if not image_folder_path:
            return {
                "errors": state.get("errors", [])
                + ["No image folder path provided in request."]
            }

        try:
            # Call image_analysis_loader to execute the existing image pipeline.
            # It will write "residual_limb_analysis.json" to the current working directory.
            output_json_path = "residual_limb_analysis.json"

            # Execute pipeline
            run_image_pipeline(image_folder_path, output_json_path)

            # Read the generated JSON file explicitly
            if not os.path.exists(output_json_path):
                raise FileNotFoundError(
                    f"Expected output file not generated: {output_json_path}"
                )

            with open(output_json_path, "r") as f:
                analysis_data = json.load(f)

            # Validate the JSON content
            required_keys = [
                "residual_limb_shape",
                "confidence",
                "average_width_ratio",
                "average_contour_area",
                "number_of_views",
                "analysis_quality",
            ]
            missing_keys = [k for k in required_keys if k not in analysis_data]
            if missing_keys:
                raise ValueError(
                    f"Invalid JSON: missing required keys: {missing_keys}"
                )

            # Return structured dictionary
            # Mapped to expected schema
            structured_results = {
                "shape": analysis_data.get("residual_limb_shape"),
                "confidence": analysis_data.get("confidence"),
                "average_width_ratio": analysis_data.get("average_width_ratio"),
                "average_contour_area": analysis_data.get("average_contour_area"),
                "estimated_length_cm": analysis_data.get("estimated_length_cm", None),
                "estimated_volume_cm3": analysis_data.get(
                    "estimated_volume_cm3", None
                ),
                "image_quality": analysis_data.get("image_quality", "High"),
                "number_of_views": analysis_data.get("number_of_views"),
                "analysis_quality": analysis_data.get("analysis_quality"),
            }

            return {
                "image_analysis_results": structured_results,
                "next_step": "geometry_agent",
            }

        except Exception as e:
            # Continue workflow execution even if image processing fails, returning the error in the state.
            return {
                "errors": state.get("errors", [])
                + [f"Image analysis agent failed: {str(e)}"],
                "next_step": "geometry_agent",
            }
