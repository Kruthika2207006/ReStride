"""Verification script to test the Image Analysis Agent and workflow integration."""

import os
import sys
import json
from unittest.mock import patch, MagicMock

# Mock image processing dependencies to allow import/execution of tests
# in environments without heavy machine learning/computer vision libraries
sys.modules['rembg'] = MagicMock()
sys.modules['cv2'] = MagicMock()

# Add workspace directory to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.request import (
    SocketRecommendationRequest,
    ResidualLimbDetails,
    PatientClinicalHistory,
)
from agents.image_analysis_agent import ImageAnalysisAgent
from agents.geometry_agent import GeometryAgent
from workflow import recommendation_graph


def run_verification_tests():
    print("=== Image Analysis Agent & Integration Verification ===")

    # 1. Setup mock request referencing a dummy image folder path
    dummy_folder = "c:\\ai_agent\\scratch\\dummy_patient_images"
    os.makedirs(dummy_folder, exist_ok=True)
    
    # Write a dummy image file so the search inside loader doesn't complain
    dummy_image_path = os.path.join(dummy_folder, "view1.jpg")
    with open(dummy_image_path, "wb") as f:
        f.write(b"dummy image data")

    request = SocketRecommendationRequest(
        patient_id="PAT-IMAGE-TEST",
        age=52,
        weight_kg=75.5,
        activity_level="K3",
        amputation_level="transtibial",
        limb_details=ResidualLimbDetails(
            shape="conical",
            length_cm=16.0,
            proximal_circumference_cm=32.0,
            mid_limb_circumference_cm=26.0,
            distal_circumference_cm=20.0,
            skin_condition="healthy",
            prominent_bones=False,
            additional_notes="Testing image analysis integration.",
        ),
        clinical_history=PatientClinicalHistory(
            amputation_reason="trauma",
            has_diabetes=False,
            has_neuropathy=False,
            volume_fluctuations=False,
        ),
        image_folder_path=dummy_folder,
    )

    state = {
        "request": request,
        "image_analysis_results": None,
        "geometry_analysis_results": {},
        "clinical_analysis": {},
        "socket_recommendation": {},
        "safety_analysis": {},
        "final_response": None,
        "errors": [],
        "routing_loop_count": 0,
        "next_step": "orchestrator",
    }

    # Mock JSON output from the pipeline
    mock_pipeline_output = {
        "number_of_views": 4,
        "residual_limb_shape": "Conical",
        "average_width_ratio": 2.17,
        "average_contour_area": 64879.5,
        "average_width": 230.0,
        "average_height": 385.0,
        "view_agreement": 1.0,
        "confidence": 0.95,
        "analysis_quality": "High",
        "estimated_length_cm": None,
        "estimated_volume_cm3": None,
    }

    # Clean up any existing residual_limb_analysis.json in current directory
    output_json_path = "residual_limb_analysis.json"
    if os.path.exists(output_json_path):
        os.remove(output_json_path)

    # 2. Test ImageAnalysisAgent run in isolation with mocked pipeline
    print("\n[Step 1] Running ImageAnalysisAgent in isolation...")
    with patch("agents.image_analysis_agent.run_image_pipeline") as mock_run:
        # Mock loader function behavior: write the mock json to output_json_path
        def mock_run_side_effect(folder_path, output_json_name):
            with open(output_json_name, "w") as f_out:
                json.dump(mock_pipeline_output, f_out, indent=4)
            return mock_pipeline_output

        mock_run.side_effect = mock_run_side_effect

        agent = ImageAnalysisAgent()
        agent_output = agent.run(state)

        # Assert no errors and correct keys
        assert not agent_output.get("errors"), f"Agent failed with errors: {agent_output.get('errors')}"
        assert "image_analysis_results" in agent_output, "Image analysis results not in agent output!"
        
        results = agent_output["image_analysis_results"]
        print(f"Structured results: {json.dumps(results, indent=4)}")
        
        assert results["shape"] == "Conical"
        assert results["confidence"] == 0.95
        assert results["average_width_ratio"] == 2.17
        assert results["average_contour_area"] == 64879.5
        assert results["number_of_views"] == 4
        assert results["analysis_quality"] == "High"
        assert results["image_quality"] == "High"
        assert results["estimated_length_cm"] is None
        assert results["estimated_volume_cm3"] is None

        print("[+] ImageAnalysisAgent isolation test passed!")

        # 3. Test GeometryAgent run under Mode 1 (image results available)
        print("\n[Step 2] Running GeometryAgent under Mode 1 (image preferred)...")
        # Update state with the output from ImageAnalysisAgent
        state["image_analysis_results"] = results
        
        geom_agent = GeometryAgent()
        geom_output = geom_agent.run(state)
        
        assert not geom_output.get("errors"), f"GeometryAgent failed with errors: {geom_output.get('errors')}"
        assert "geometry_analysis_results" in geom_output
        
        geom_results = geom_output["geometry_analysis_results"]
        print(f"GeometryAgent mapped results: {json.dumps(geom_results, indent=4)}")
        
        assert geom_results["shape_descriptor"] == "Conical"
        assert geom_results["mesh_status"] == "Image Analyzed"
        assert geom_results["is_watertight"] is False
        assert geom_results["limb_length_cm"] == 16.0  # fallback to request
        assert geom_results["additional_metadata"]["average_contour_area"] == 64879.5
        assert geom_results["additional_metadata"]["average_width_ratio"] == 2.17
        assert geom_results["additional_metadata"]["confidence"] == 0.95
        assert geom_results["additional_metadata"]["number_of_views"] == 4
        assert geom_results["additional_metadata"]["analysis_quality"] == "High"
        
        print("[+] GeometryAgent Mode 1 test passed!")

    # 4. Test end-to-end workflow execution with images
    print("\n[Step 3] Running full LangGraph end-to-end workflow...")
    # Mock GeminiClient structure generator for clinical and socket design steps
    from scratch.run_recommendation_pipeline import setup_mock_gemini_client
    setup_mock_gemini_client()

    with patch("agents.image_analysis_agent.run_image_pipeline") as mock_run:
        def mock_run_side_effect(folder_path, output_json_name):
            with open(output_json_name, "w") as f_out:
                json.dump(mock_pipeline_output, f_out, indent=4)
            return mock_pipeline_output

        mock_run.side_effect = mock_run_side_effect

        # Initial state setup
        initial_state = {
            "request": request,
            "image_analysis_results": None,
            "geometry_analysis_results": {},
            "clinical_analysis": {},
            "socket_recommendation": {},
            "safety_analysis": {},
            "final_response": None,
            "errors": [],
            "routing_loop_count": 0,
            "next_step": "orchestrator",
        }

        final_state = recommendation_graph.invoke(initial_state)

        assert not final_state.get("errors"), f"Workflow failed with errors: {final_state.get('errors')}"
        assert final_state.get("final_response") is not None, "Workflow did not synthesize a final response!"
        
        response = final_state["final_response"]
        print("\n=== Final Response synthesized ===")
        print(f"Patient Summary:   {response.patient_summary}")
        print(f"Geometry Summary:  {response.geometry_summary}")
        print(f"Clinical Findings: {response.clinical_findings}")
        print(f"Socket Design:     {response.socket_design}")
        print(f"Suspension System: {response.suspension_system}")
        print(f"Fabrication App:   {response.fabrication_approval}")
        
        print("[+] End-to-end integration test passed!")

    # Clean up files and dummy folder
    import shutil
    if os.path.exists(output_json_path):
        os.remove(output_json_path)
    if os.path.exists(dummy_folder):
        shutil.rmtree(dummy_folder)

    print("\n[+] ALL TESTS PASSED!")


if __name__ == "__main__":
    run_verification_tests()
