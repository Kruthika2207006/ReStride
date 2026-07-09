"""Verification script for testing the Safety Validation Agent."""

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
from models.safety import SafetyAnalysis, SafetyCheck, DetectedRisk, AgentConflict
from agents.safety_agent import SafetyAgent


def create_test_request(has_neuropathy: bool) -> SocketRecommendationRequest:
    """Creates a sample request for testing."""
    return SocketRecommendationRequest(
        patient_id="PAT-5555",
        age=65,
        weight_kg=88.0,
        activity_level="K3",
        amputation_level="transtibial",
        limb_details=ResidualLimbDetails(
            shape="conical",
            length_cm=14.0,
            proximal_circumference_cm=33.0,
            mid_limb_circumference_cm=28.0,
            distal_circumference_cm=20.0,
            skin_condition="fragile, scar tissue",
            prominent_bones=True,
            additional_notes="Patient is diabetic with neuropathy.",
        ),
        clinical_history=PatientClinicalHistory(
            amputation_reason="diabetic peripheral vascular disease",
            has_diabetes=True,
            has_neuropathy=has_neuropathy,
            volume_fluctuations=True,
        ),
        stl_file_path="C:/ai_agent/scratch/scratch_limb_mesh.stl",
    )


def run_verification():
    """Runs the verification on SafetyAgent."""
    print("=== Safety Validation Agent Verification ===")

    request_unsafe = create_test_request(has_neuropathy=True)

    geom_results = {
        "limb_length_cm": 14.0,
        "surface_area_cm2": 450.0,
        "volume_cm3": 720.0,
        "bounding_box_dims": [10.0, 10.0, 14.0],
        "cross_sectional_circumferences": {
            "20%": 20.0,
            "50%": 28.0,
            "80%": 33.0,
        },
        "shape_descriptor": "conical",
        "is_watertight": True,
        "num_vertices": 300,
        "num_triangles": 600,
        "mesh_status": "Clean",
        "errors": ["Fibular Head", "Tibial Crest"],  # Bony prominences
    }

    clinical_results = {
        "limb_analysis_summary": "Diabetic patient with high neuropathy risk and prominent bones.",
        "recommended_socket_type": "TSB",
        "recommended_socket_type_reasoning": "TSB prevents point pressure.",
        "pressure_sensitive_regions": [
            {
                "region_name": "Fibular Head",
                "risk_level": "High",
                "justification": "Neuropathic risk.",
            }
        ],
        "design_considerations": [],
    }

    # UNSAFE proposed socket design parameters
    socket_rec_unsafe = {
        "socket_design_type": "PTB",  # Mismatch with clinical TSB
        "suspension_system": "Pin Lock",  # Pin lock pulls distal end; high risk for neuropathy
        "liner_type": "None (Direct Hard Socket)",  # Serious violation: no liner for neuropathic skin
        "socket_wall_thickness_mm": 2.0,  # Serious violation: thickness < 3.0mm
        "relief_regions": [],  # Serious violation: no reliefs for prominent bones
        "pressure_regions": [],
        "trimline_recommendations": {},
        "material_recommendations": ["Copolymer Sheet"],
        "offset_values": {},
    }

    state_unsafe = {
        "request": request_unsafe,
        "geometry_analysis_results": geom_results,
        "clinical_analysis": clinical_results,
        "socket_recommendation": socket_rec_unsafe,
        "safety_analysis": {},
        "errors": [],
    }

    agent = SafetyAgent()

    # Check if Gemini API key exists, otherwise mock the output
    has_api_key = bool(
        os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    )

    if not has_api_key:
        print("[!] No Gemini API key detected. Using Mock Gemini Client for test.")

        # Create a mock response for the unsafe configuration
        mock_response_unsafe = SafetyAnalysis(
            risk_score="High",
            risk_explanation=(
                "The proposed design has multiple critical safety violations: "
                "1. No gel liner for a patient with diabetic neuropathy (extreme risk of ulceration). "
                "2. Socket wall thickness of 2.0mm is below the 3.0mm minimum structural constraint. "
                "3. Direct pin-lock suspension without distal end protection introduces high shear."
            ),
            validated_constraints=[
                SafetyCheck(
                    constraint_name="Neuropathy Gel Liner Check",
                    passed=False,
                    details="Patient has neuropathy but 'liner_type' was set to 'None (Direct Hard Socket)'.",
                ),
                SafetyCheck(
                    constraint_name="Wall Thickness Limit",
                    passed=False,
                    details="Proposed wall thickness (2.0mm) is below the minimum safety limit (3.0mm).",
                ),
                SafetyCheck(
                    constraint_name="Bony Prominences Relief Check",
                    passed=False,
                    details="No relief regions provided for identified prominent bones (Fibular Head, Tibial Crest).",
                ),
            ],
            detected_risks=[
                DetectedRisk(
                    risk_category="Skin Breakdown",
                    severity="High",
                    description="Lack of liner and direct pin lock will cause localized skin breakdown over neuropathic tissue.",
                    mitigation_action="Change liner to Silicone Gel Liner and utilize suction suspension.",
                ),
                DetectedRisk(
                    risk_category="Structural Weakness",
                    severity="High",
                    description="2.0mm wall thickness is insufficient to support loading, risking mechanical socket cracking.",
                    mitigation_action="Increase wall thickness to at least 4.0mm.",
                ),
            ],
            conflicting_recommendations=[
                AgentConflict(
                    conflict_description="Clinical agent recommended TSB, but socket design type is set to PTB.",
                    resolution_suggestion="Change socket design to Total Surface Bearing (TSB) to distribute pressure uniformly.",
                )
            ],
            is_safe_to_fabricate=False,
        )

        agent.client.generate_structured = MagicMock(
            return_value=mock_response_unsafe
        )

    else:
        print("[+] API key detected. Running real query to Gemini model...")

    try:
        results = agent.run(state_unsafe)
        print("\n=== Unsafe Validation Executed Successfully ===")
        safety = results["safety_analysis"]

        print(f"Risk Score:              {safety['risk_score']}")
        print(f"Is Safe to Fabricate:    {safety['is_safe_to_fabricate']}")
        print(f"Explanation:             {safety['risk_explanation']}")

        print("\nValidated Constraints:")
        for check in safety["validated_constraints"]:
            status = "PASSED" if check["passed"] else "FAILED"
            print(f" - [{status}] {check['constraint_name']}: {check['details']}")

        print("\nDetected Risks:")
        for risk in safety["detected_risks"]:
            print(
                f" - [{risk['severity']}] {risk['risk_category']}: {risk['description']}"
            )
            print(f"   Mitigation: {risk['mitigation_action']}")

        print("\nConflicting Recommendations:")
        for conflict in safety["conflicting_recommendations"]:
            print(f" - {conflict['conflict_description']}")
            print(f"   Resolution: {conflict['resolution_suggestion']}")

        assert (
            not safety["is_safe_to_fabricate"]
        ), "Safety agent failed to catch unsafe design!"
        assert safety["risk_score"] == "High", "Safety agent failed to assign High risk!"

        print("\n[+] Verification PASSED!")

    except Exception as e:
        print(f"\n[-] Verification FAILED: {e}")
        raise e


if __name__ == "__main__":
    run_verification()
