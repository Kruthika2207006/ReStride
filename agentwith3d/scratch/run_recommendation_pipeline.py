"""Runner script to execute the complete LangGraph recommendation workflow."""

import os
import sys
from unittest.mock import MagicMock

# Add workspace directory to python path for correct imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.request import (
    SocketRecommendationRequest,
    ResidualLimbDetails,
    PatientClinicalHistory,
)
from models.clinical import ClinicalAnalysis, PressureSensitiveRegion, ClinicalDesignConsideration
from models.socket_recommendation import (
    SocketRecommendation,
    ReliefRegion,
    PressureRegion,
    TrimlineRecommendations,
    OffsetValues,
)
from models.safety import SafetyAnalysis, SafetyCheck, DetectedRisk, AgentConflict
from models.response import SocketRecommendationResponse, FinalReliefArea, FinalPressureArea
from tools.gemini_client import GeminiClient
from workflow import recommendation_graph


def setup_mock_gemini_client():
    """Mocks the GeminiClient to return structured mock outputs based on the schema."""
    has_api_key = bool(
        os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    )

    if has_api_key:
        return

    print(
        "[!] No Gemini API key detected. Mocking GeminiClient for offline workflow run..."
    )

    def mock_generate_structured(self, prompt, response_schema, system_instruction=None):
        schema_name = response_schema.__name__

        if schema_name == "ClinicalAnalysis":
            return ClinicalAnalysis(
                limb_analysis_summary=(
                    "Limb is conical, length 15cm, with fragile skin. "
                    "Patient is diabetic with neuropathy, presenting extremely high risk of skin breakdown."
                ),
                pressure_sensitive_regions=[
                    PressureSensitiveRegion(
                        region_name="Fibular Head",
                        risk_level="High",
                        justification="Bony protrusion sensitive to friction.",
                    )
                ],
                design_considerations=[
                    ClinicalDesignConsideration(
                        consideration="Total Surface Bearing (TSB) Socket",
                        implication="Distribute pressure evenly.",
                        justification="Protects neuropathic tissue.",
                    )
                ],
                recommended_socket_type="TSB",
                recommended_socket_type_reasoning="TSB avoids localized stress.",
            )

        elif schema_name == "SocketRecommendation":
            return SocketRecommendation(
                socket_design_type="TSB",
                socket_design_reasoning="Uniform pressure distribution.",
                suspension_system="Suction",
                suspension_system_reasoning="Suction provides stable control.",
                liner_type="Silicone Gel Liner",
                liner_type_reasoning="Protects bony head and fragile skin.",
                socket_wall_thickness_mm=4.0,
                socket_wall_thickness_reasoning="Ensures structural integrity.",
                relief_regions=[
                    ReliefRegion(
                        region_name="Fibular Head",
                        depth_mm=3.0,
                        reasoning="Relieves pressure.",
                    )
                ],
                pressure_regions=[
                    PressureRegion(
                        region_name="Patellar Tendon",
                        depth_mm=2.0,
                        reasoning="Loads weight-tolerant tendon.",
                    )
                ],
                trimline_recommendations=TrimlineRecommendations(
                    description="Standard TSB profile",
                    anterior_trim_height_cm=4.5,
                    posterior_trim_height_cm=2.5,
                    reasoning="Allows knee flexion while providing support.",
                ),
                material_recommendations=["Carbon Fiber Composite"],
                material_recommendations_reasoning="Lightweight structural strength.",
                offset_values=OffsetValues(
                    radial_expansion_mm=1.0,
                    distal_clearance_mm=4.0,
                    ply_fit_compensation=1.0,
                ),
                offset_values_reasoning="Accommodates volume changes.",
            )

        elif schema_name == "SafetyAnalysis":
            return SafetyAnalysis(
                risk_score="Low",
                risk_explanation="The proposed design complies with all neuropathy and structural guidelines.",
                validated_constraints=[
                    SafetyCheck(
                        constraint_name="Liner Check",
                        passed=True,
                        details="Silicone Gel Liner provided.",
                    ),
                    SafetyCheck(
                        constraint_name="Wall Thickness Limit",
                        passed=True,
                        details="Thickness (4.0mm) is within safe limits (3.0-6.0mm).",
                    ),
                ],
                detected_risks=[],
                conflicting_recommendations=[],
                is_safe_to_fabricate=True,
            )

        elif schema_name == "SocketRecommendationResponse":
            return SocketRecommendationResponse(
                patient_summary="58-year-old active K3 diabetic patient with transtibial amputation.",
                geometry_summary="Conical residual limb, length 15cm, watertight geometry scan.",
                clinical_findings="Diabetic neuropathy present, high risk of shear over tibial crest.",
                socket_design="TSB",
                suspension_system="Suction",
                liner_recommendation="Silicone Gel Liner",
                relief_areas=[
                    FinalReliefArea(
                        region_name="Fibular Head",
                        depth_mm=3.0,
                        reasoning="Relieves pressure at the sensitive fibular head.",
                    )
                ],
                pressure_tolerant_areas=[
                    FinalPressureArea(
                        region_name="Patellar Tendon",
                        depth_mm=2.0,
                        reasoning="Loads the patellar tendon.",
                    )
                ],
                safety_warnings=[],
                fabrication_approval=True,
                final_confidence_score=0.95,
                ai_explanation=(
                    "The final recommendation leverages a Total Surface Bearing (TSB) design "
                    "with a Silicone Gel Liner and suction suspension to resolve clinical risks "
                    "and protect the patient's neuropathic tissue. Fabrication clearance is approved."
                ),
                fabrication_parameters={
                    "thickness_mm": 4.0,
                    "materials": ["Carbon Fiber Composite"],
                    "offset_values": {
                        "radial_expansion_mm": 1.0,
                        "distal_clearance_mm": 4.0,
                    },
                },
            )

        raise ValueError(f"Unknown mock response schema: {schema_name}")

    GeminiClient.generate_structured = mock_generate_structured
    GeminiClient.generate = MagicMock(return_value="Mocked text generation.")


def run_pipeline(stl_path: str):
    """Orchestrates and executes the recommendation workflow.

    Args:
        stl_path: Path to the residual limb STL mesh file.
    """
    print("=== Launching Socket Recommendation Agentic Pipeline ===")

    setup_mock_gemini_client()

    # 1. Compile the initial request
    request = SocketRecommendationRequest(
        patient_id="PAT-PIPELINE-DEMO",
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
            additional_notes="Patient is active but volume fluctuates significantly.",
        ),
        clinical_history=PatientClinicalHistory(
            amputation_reason="diabetic complications",
            has_diabetes=True,
            has_neuropathy=True,
            volume_fluctuations=True,
        ),
        stl_file_path=stl_path,
        current_issues="Discomfort over fibular head.",
    )

    # 2. Define initial workflow state
    state = {
        "request": request,
        "geometry_analysis_results": {},
        "clinical_analysis": {},
        "socket_recommendation": {},
        "safety_analysis": {},
        "final_response": None,
        "errors": [],
        "routing_loop_count": 0,
        "next_step": "geometry_agent",
    }

    # 3. Execute the LangGraph StateGraph
    print("Invoking recommendation_graph.invoke()...")
    final_state = recommendation_graph.invoke(state)

    if final_state.get("errors"):
        print(f"\n[-] Execution finished with errors: {final_state['errors']}")
        return

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
    # If a test stl file path doesn't exist, we can stub it to run the pipeline
    test_stl = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "scratch_limb_mesh_pipeline.stl")
    )

    # Create dummy file if not existing just to let loader execute
    if not os.path.exists(test_stl):
        with open(test_stl, "wb") as f:
            f.write(b"Solid dummy\nfacet normal 0 0 0\nouter loop\n")
            f.write(b"vertex 0 0 0\nvertex 0 0 1\nvertex 0 1 0\n")
            f.write(b"endloop\nendfacet\nendsolid dummy\n")

    try:
        run_pipeline(test_stl)
    finally:
        # Clean up
        if os.path.exists(test_stl):
            os.remove(test_stl)
