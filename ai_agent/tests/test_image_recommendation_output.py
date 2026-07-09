import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scratch.run_image_recommendation import format_analysis_results_for_display


def test_format_analysis_results_uses_existing_analysis_fields():
    image_results = {
        "shape": "Conical",
        "confidence": 0.95,
        "average_width_ratio": 2.173,
        "average_contour_area": 64879.5,
        "estimated_length_cm": 15.0,
        "estimated_volume_cm3": 0.0,
        "image_quality": "High",
        "number_of_views": 4,
        "analysis_quality": "High",
    }
    geometry_results = {
        "limb_length_cm": 15.0,
        "surface_area_cm2": 0.0,
        "volume_cm3": 0.0,
        "bounding_box_dims": [0.0, 0.0, 0.0],
        "cross_sectional_circumferences": {"80%": 31.42, "50%": 25.13, "20%": 18.85},
        "shape_descriptor": "Conical",
        "is_watertight": False,
        "num_vertices": 0,
        "num_triangles": 0,
        "mesh_status": "Image Analyzed",
        "errors": [],
        "additional_metadata": {
            "average_contour_area": 64879.5,
            "average_width_ratio": 2.173,
            "confidence": 0.95,
            "number_of_views": 4,
            "analysis_quality": "High",
        },
    }

    output = format_analysis_results_for_display(image_results, geometry_results)

    assert "image_analysis_results" in output
    assert "shape" in output
    assert "confidence" in output
    assert "average_width_ratio" in output
    assert "estimated_length_cm" in output
    assert "estimated_volume_cm3" in output
    assert "number_of_views" in output
    assert "analysis_quality" in output

    assert "geometry_analysis_results" in output
    assert "limb_length_cm" in output
    assert "surface_area_cm2" in output
    assert "volume_cm3" in output
    assert "shape_descriptor" in output
    assert "cross_sectional_circumferences" in output
    assert "additional_metadata" in output

    assert "synthetic_summary" not in output
