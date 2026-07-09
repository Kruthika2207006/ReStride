"""Demo script to execute the integrated LangGraph workflow with patient limb images."""

import os
import sys
import json
from unittest.mock import patch, MagicMock

# Mock image processing dependencies to allow execution of tests
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
from workflow import recommendation_graph
from scratch.run_recommendation_pipeline import setup_mock_gemini_client


def run_image_demo():
    print("=== LangGraph AI Socket Recommendation System (Image Mode Demo) ===")

    # 1. Prompt user for a real image folder path at runtime
    image_folder = input("Enter image folder path: ").strip().strip('"')
    if not os.path.exists(image_folder):
        print("Folder not found!")
        sys.exit(1)

    # 2. Setup mock Gemini LLM responses for downstream agents (Clinical, Socket, Safety, Decision)
    setup_mock_gemini_client()

    # 3. Compile the initial request with the provided image folder path
    request = SocketRecommendationRequest(
        patient_id="PAT-DEMO-IMAGE-TSB",
        age=58,
        weight_kg=79.2,
        activity_level="K3",
        amputation_level="transtibial",
        limb_details=ResidualLimbDetails(
            shape="conical",  # manual observation baseline
            length_cm=15.0,
            proximal_circumference_cm=31.42,
            mid_limb_circumference_cm=25.13,
            distal_circumference_cm=18.85,
            skin_condition="fragile, diabetic neuropathy risk",
            prominent_bones=True,
            additional_notes="Patient has active volume fluctuations. Preferring image analysis input.",
        ),
        clinical_history=PatientClinicalHistory(
            amputation_reason="diabetic complications",
            has_diabetes=True,
            has_neuropathy=True,
            volume_fluctuations=True,
        ),
        image_folder_path=image_folder,
        current_issues="Discomfort over fibular head.",
    )

    # 4. Define initial workflow state
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

    # Realistic mock pipeline results from image folder scan
    mock_pipeline_output = {
        "number_of_views": 4,
        "residual_limb_shape": "Conical",
        "average_width_ratio": 2.17,
        "average_contour_area": 64879.5,
        "average_width": 230.0,
        "average_height": 385.0,
        "view_agreement": 0.95,
        "confidence": 0.92,
        "analysis_quality": "High",
        "estimated_length_cm": None,
        "estimated_volume_cm3": None,
    }

    # Patch the pipeline loader function to return the mock values and write JSON
    patcher = patch("agents.image_analysis_agent.run_image_pipeline")
    mock_run = patcher.start()
    
    def mock_run_side_effect(folder_path, output_json_name):
        with open(output_json_name, "w") as f_out:
            json.dump(mock_pipeline_output, f_out, indent=4)
        return mock_pipeline_output

    mock_run.side_effect = mock_run_side_effect

    try:
        # 5. Run the StateGraph compiled graph
        print("\nInvoking recommendation_graph.invoke() in image mode...")
        final_state = recommendation_graph.invoke(state)

        # 6. Print the details of execution
        print("\n=== Graph State after execution ===")
        print(f"Routing Loop Count: {final_state['routing_loop_count']}")
        print(f"Errors Logged:      {final_state['errors']}")
        
        print("\n=== Image Analysis Results in State ===")
        print(json.dumps(final_state.get("image_analysis_results"), indent=4))

        print("\n=== Geometry Mapped Results ===")
        print(json.dumps(final_state.get("geometry_analysis_results"), indent=4))

        print("\n=== Synthesis response from Decision Agent ===")
        response = final_state["final_response"]
        print(f"Patient Summary:   {response.patient_summary}")
        print(f"Geometry Summary:  {response.geometry_summary}")
        print(f"Clinical Findings: {response.clinical_findings}")
        print(f"Socket Design:     {response.socket_design}")
        print(f"Suspension System: {response.suspension_system}")
        print(f"Liner Rec:         {response.liner_recommendation}")
        print(f"Fabrication App:   {response.fabrication_approval}")
        print(f"Confidence Score:  {response.final_confidence_score}")
        print(f"AI Explanation:    {response.ai_explanation}")
        print(f"Parameters:        {response.fabrication_parameters}")

    finally:
        # Clean up patcher
        patcher.stop()

        # Clean up generated JSON artifact from the image pipeline run
        output_json_path = "residual_limb_analysis.json"
        if os.path.exists(output_json_path):
            os.remove(output_json_path)


if __name__ == "__main__":
    run_image_demo()
