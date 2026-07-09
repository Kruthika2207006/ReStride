"""Verification script for testing the Decision Synthesis Agent."""

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
from models.response import SocketRecommendationResponse, FinalReliefArea, FinalPressureArea
from agents.decision_agent import DecisionAgent


def create_test_request() -> SocketRecommendationRequest:
    """Creates a sample request for testing."""
    return SocketRecommendationRequest(
        patient_id="PAT-DECISION-TEST",
        age=58,
        weight_kg=84.5,
        activity_level="K3",
        amputation_level="transtibial",
        limb_details=ResidualLimbDetails(
            shape="conical",
            length_cm=15.0,
            proximal_circumference_cm=31.42,
            mid_limb_circumference_cm=25.13,
            distal_circumference_cm=18.85,
            skin_condition="fragile, diabetic neuropathy",
            prominent_bones=True,
            additional_notes="Active patient but high skin breakdown risk.",
        ),
        clinical_history=PatientClinicalHistory(
            amputation_reason="diabetes",
            has_diabetes=True,
            has_neuropathy=True,
            volume_fluctuations=True,
        ),
        stl_file_path="C:/ai_agent/scratch/scratch_limb_mesh.stl",
    )


def run_verification():
    """Runs the verification on DecisionAgent."""
    print("=== Decision Synthesis Agent Verification ===")

    request = create_test_request()

    # Geometry output
    geom_results = {
        "limb_length_cm": 15.0,
        "surface_area_cm2": 485.81,
        "volume_cm3": 764.75,
        "bounding_box_dims": [10.0, 10.0, 15.0],
        "cross_sectional_circumferences": {
            "20%": 21.33,
            "50%": 25.09,
            "80%": 28.86,
        },
        "shape_descriptor": "conical",
        "is_watertight": True,
        "num_vertices": 482,
        "num_triangles": 960,
        "mesh_status": "Clean",
        "errors": [],
    }

    # Clinical output (TSB recommended, neuropathy risks)
    clinical_results = {
        "limb_analysis_summary": (
            "Patient is active but diabetic with neuropathy. High risk of skin breakdown."
        ),
        "recommended_socket_type": "TSB",
        "recommended_socket_type_reasoning": (
            "Total Surface Bearing prevents high localized pressures over the tibia crest."
        ),
        "pressure_sensitive_regions": [
            {
                "region_name": "Tibial Crest",
                "risk_level": "High",
                "justification": "Bony ridge susceptible to friction.",
            }
        ],
        "design_considerations": [],
    }

    # Socket Agent output (Unsafe: PTB, direct hard socket, thin 2.0mm wall - conflicts!)
    socket_rec_unsafe = {
        "socket_design_type": "PTB",
        "socket_design_reasoning": "PTB allows focused loading.",
        "suspension_system": "Pin Lock",
        "liner_type": "None (Direct Hard Socket)",
        "socket_wall_thickness_mm": 2.0,
        "relief_regions": [],
        "pressure_regions": [],
        "trimline_recommendations": {},
        "material_recommendations": ["Copolymer Sheet"],
        "offset_values": {},
    }

    # Safety Agent output (FAILED check, mitigates: TSB, Silicone Liner, 4.5mm wall)
    safety_results = {
        "risk_score": "High",
        "risk_explanation": (
            "Critical violations: wall thickness < 3.0mm, neuropathic patient without a soft gel liner."
        ),
        "validated_constraints": [
            {
                "constraint_name": "Liner Check",
                "passed": False,
                "details": "Liner is missing for neuropathic patient.",
            },
            {
                "constraint_name": "Wall Thickness Limit",
                "passed": False,
                "details": "Wall thickness 2.0mm is below 3.0mm structural minimum.",
            },
        ],
        "detected_risks": [
            {
                "risk_category": "Skin Breakdown",
                "severity": "High",
                "description": "Lack of liner will cause skin failure.",
                "mitigation_action": "Incorporate Silicone Gel Liner and suction suspension.",
            },
            {
                "risk_category": "Structural Weakness",
                "severity": "High",
                "description": "Wall is too thin.",
                "mitigation_action": "Increase wall thickness to 4.5mm.",
            },
        ],
        "conflicting_recommendations": [
            {
                "conflict_description": "Clinical recommended TSB, but socket design is PTB.",
                "resolution_suggestion": "Override to TSB design.",
            }
        ],
        "is_safe_to_fabricate": False,
    }

    state = {
        "request": request,
        "geometry_analysis_results": geom_results,
        "clinical_analysis": clinical_results,
        "socket_recommendation": socket_rec_unsafe,
        "safety_analysis": safety_results,
        "final_response": None,
        "errors": [],
    }

    agent = DecisionAgent()

    # Check if Gemini API key exists, otherwise mock the output
    has_api_key = bool(
        os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    )

    if not has_api_key:
        print("[!] No Gemini API key detected. Using Mock Gemini Client for test.")

        # Create a mock consolidated response implementing safety overrides
        mock_response = SocketRecommendationResponse(
            patient_summary="58-year-old active K3 diabetic patient with transtibial amputation.",
            geometry_summary="Conical residual limb, length 15cm, watertight geometry scan.",
            clinical_findings="Diabetic neuropathy present, high risk of shear over tibial crest.",
            socket_design="TSB",  # Overridden from PTB to TSB based on safety mitigation
            suspension_system="Suction",  # Overridden from Pin Lock
            liner_recommendation="Silicone Gel Liner",  # Overridden from None (Direct)
            relief_areas=[
                FinalReliefArea(
                    region_name="Tibial Crest",
                    depth_mm=2.5,
                    reasoning="Relieves high pressure over neuropathic tibial crest.",
                )
            ],
            pressure_tolerant_areas=[
                FinalPressureArea(
                    region_name="Medial Flare",
                    depth_mm=1.5,
                    reasoning="Distributes weight bearing across stable bone flares.",
                )
            ],
            safety_warnings=[
                "Wall thickness corrected to 4.5mm due to structural weakness warning.",
                "Liner added due to neuropathy skin breakdown risk.",
            ],
            fabrication_approval=False,  # Fabrication blocked because safety checks failed
            final_confidence_score=0.90,
            ai_explanation=(
                "The final configuration overrides the proposed PTB design to a Total Surface Bearing (TSB) "
                "socket to resolve clinical conflicts and distribute pressure. A Silicone Gel Liner and suction "
                "suspension are enforced to protect neuropathic tissue. Structural wall thickness was increased "
                "to 4.5mm. Fabrication approval remains blocked until these parameters are regenerated."
            ),
            fabrication_parameters={
                "thickness_mm": 4.5,
                "materials": ["Carbon Fiber Composite"],
                "offset_values": {"radial_expansion_mm": 1.0},
            },
        )

        agent.client.generate_structured = MagicMock(
            return_value=mock_response
        )

    else:
        print("[+] API key detected. Running real query to Gemini model...")

    try:
        results = agent.run(state)
        print("\n=== Consensus Synthesis Executed Successfully ===")
        response = results["final_response"]

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

        # Assertions
        assert (
            response.socket_design == "TSB"
        ), "Failed to override design to TSB!"
        assert (
            response.liner_recommendation == "Silicone Gel Liner"
        ), "Failed to override liner!"
        assert (
            response.fabrication_parameters["thickness_mm"] == 4.5
        ), "Failed to override thickness!"
        assert (
            not response.fabrication_approval
        ), "Failed to map fabrication safety block!"

        print("\n[+] Verification PASSED!")

    except Exception as e:
        print(f"\n[-] Verification FAILED: {e}")
        raise e


if __name__ == "__main__":
    run_verification()
