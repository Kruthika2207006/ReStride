"""Runner script to execute the recommendation workflow on real patient residual limb images."""

import os
import sys
import json

# Add workspace directory to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.request import (
    SocketRecommendationRequest,
    ResidualLimbDetails,
    PatientClinicalHistory,
)
from workflow import recommendation_graph
from scratch.run_recommendation_pipeline import setup_mock_gemini_client


def format_analysis_results_for_display(image_results, geometry_results):
    """Render the actual analysis payloads without inventing synthetic summaries."""
    image_payload = image_results or {}
    geometry_payload = geometry_results or {}

    return (
        "\n=== ReStride Residual Limb Analysis Results ===\n"
        + "image_analysis_results:\n"
        + json.dumps(image_payload, indent=2)
        + "\n\ngeometry_analysis_results:\n"
        + json.dumps(geometry_payload, indent=2)
    )


def run_real_image_pipeline(image_folder: str):
    """Executes the workflow on the actual image folder path.

    Args:
        image_folder: Local path containing patient residual limb images.
    """
    print(f"=== Running Real Image Recommendation Workflow ===")
    print(f"Target Image Folder: {image_folder}")

    # Validate that the folder exists
    if not os.path.exists(image_folder):
        print(f"[-] Error: Image folder not found at '{image_folder}'")
        sys.exit(1)

    # 1. Setup mock Gemini Client for offline clinical/recommendation agents
    setup_mock_gemini_client()

    # 2. Compile the request with the actual image folder path
    request = SocketRecommendationRequest(
        patient_id="PAT-REAL-IMAGE-RUN",
        age=58,
        weight_kg=79.2,
        activity_level="K3",
        amputation_level="transtibial",
        limb_details=ResidualLimbDetails(
            shape="conical",
            length_cm=15.0,
            proximal_circumference_cm=31.42,
            mid_limb_circumference_cm=25.13,
            distal_circumference_cm=18.85,
            skin_condition="fragile, diabetic neuropathy risk",
            prominent_bones=True,
            additional_notes="Running workflow on actual input images.",
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

    # 3. Define initial workflow state
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

    # 4. Invoke graph
    print("\nInvoking recommendation_graph.invoke() on real files...")
    final_state = recommendation_graph.invoke(state)

    if final_state.get("errors"):
        print(f"\n[-] Execution finished with errors: {final_state['errors']}")
        return

    # 5. Output real analysis results before the socket recommendation
    print(
        format_analysis_results_for_display(
            final_state.get("image_analysis_results"),
            final_state.get("geometry_analysis_results"),
        )
    )

    print("\n=== Final Consolidated Recommendation Response ===")
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


if __name__ == "__main__":
    image_folder = input("Enter image folder path: ").strip().strip('"')
    if not os.path.exists(image_folder):
        print("Folder not found!")
        sys.exit(1)
    run_real_image_pipeline(image_folder)
