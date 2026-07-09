"""Verification script for testing the Clinical Reasoning Agent."""

import os
import sys
from unittest.mock import MagicMock

# Add workspace directory to python path for correct imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.request import (
    SocketRecommendationRequest,
    ResidualLimbDetails,
    PatientClinicalHistory,
    GeometryAnalysisResults,
)
from models.clinical import ClinicalAnalysis, PressureSensitiveRegion, ClinicalDesignConsideration
from agents.clinical_agent import ClinicalAgent


def create_test_request() -> SocketRecommendationRequest:
    """Creates a sample socket recommendation request for clinical testing."""
    return SocketRecommendationRequest(
        patient_id="PAT-9876",
        age=62,
        weight_kg=78.5,
        activity_level="K3",
        amputation_level="transtibial",
        limb_details=ResidualLimbDetails(
            shape="conical",
            length_cm=14.5,
            proximal_circumference_cm=36.0,
            mid_limb_circumference_cm=32.5,
            distal_circumference_cm=27.0,
            skin_condition="fragile, slight scar tissue at distal end",
            prominent_bones=True,
            additional_notes="Patient complains of minor pressure pain when weight bearing.",
        ),
        clinical_history=PatientClinicalHistory(
            amputation_reason="diabetic vasculopathy",
            has_diabetes=True,
            has_neuropathy=True,
            volume_fluctuations=True,
        ),
        geometry_analysis=GeometryAnalysisResults(
            bone_prominences=["Fibular Head", "Tibial Crest", "Distal Tibia"],
            soft_tissue_thickness="thin",
            tissue_mobility="adherent",
            asymmetry_detected=False,
            additional_metadata={"surface_area_cm2": 240.5},
        ),
        current_issues="Frequent red marks over the tibial crest.",
    )


def run_verification():
    """Runs the verification on ClinicalAgent."""
    print("=== Clinical Agent Verification ===")

    request = create_test_request()
    state = {"request": request, "clinical_analysis": {}, "errors": []}

    agent = ClinicalAgent()

    # Check if Gemini API key exists, otherwise mock the output
    has_api_key = bool(
        os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    )

    if not has_api_key:
        print("[!] No Gemini API key detected. Using Mock Gemini Client for test.")

        # Create a mock response matching the structured schema
        mock_response = ClinicalAnalysis(
            limb_analysis_summary=(
                "Limb is conical, length 14.5cm, with thin soft tissue coverage and adherent skin. "
                "The patient has diabetes and neuropathy, indicating extremely high risk of skin breakdown."
            ),
            pressure_sensitive_regions=[
                PressureSensitiveRegion(
                    region_name="Fibular Head",
                    risk_level="High",
                    justification="Thin soft tissue coverage and prominent bone structure increases friction.",
                ),
                PressureSensitiveRegion(
                    region_name="Tibial Crest",
                    risk_level="High",
                    justification="Site of reported red marks and thin tissue coverage.",
                ),
                PressureSensitiveRegion(
                    region_name="Distal Tibia",
                    risk_level="Medium",
                    justification="Vulnerable to end-bearing pressure, but protected if pressure is distributed.",
                ),
            ],
            design_considerations=[
                ClinicalDesignConsideration(
                    consideration="Total Surface Bearing (TSB) Socket",
                    implication="Distribute pressure evenly across the entire residual limb surface.",
                    justification="Reduces localized load on sensitive bony prominences like the tibial crest.",
                ),
                ClinicalDesignConsideration(
                    consideration="Fibular Head and Tibial Crest Relief",
                    implication="Introduce channels/recesses in the socket mold at those precise locations.",
                    justification="Mitigates high shearing forces and prevents skin breakdown.",
                ),
                ClinicalDesignConsideration(
                    consideration="Cushioned Gel Liner (Silicone/Polyurethane)",
                    implication="Provide a thick soft interface layer between limb and hard socket shell.",
                    justification="Compensates for thin soft tissue thickness and diabetic neuropathy.",
                ),
            ],
            recommended_socket_type="TSB",
            recommended_socket_type_reasoning=(
                "A Total Surface Bearing (TSB) socket design is highly recommended over Patellar Tendon Bearing (PTB) "
                "because it distributes weight uniformly, protecting the vulnerable diabetic and neuropathic tissue "
                "from isolated load concentrations."
            ),
        )

        # Mock the client's generate_structured call
        agent.client.generate_structured = MagicMock(
            return_value=mock_response
        )

    else:
        print("[+] API key detected. Running real query to Gemini model...")

    try:
        results = agent.run(state)
        print("\n=== Analysis Executed Successfully ===")
        analysis = results["clinical_analysis"]

        print(f"Recommended Socket: {analysis['recommended_socket_type']}")
        print(f"Reasoning: {analysis['recommended_socket_type_reasoning']}")

        print("\nPressure Sensitive Regions:")
        for region in analysis["pressure_sensitive_regions"]:
            print(
                f" - {region['region_name']} ({region['risk_level']}): {region['justification']}"
            )

        print("\nDesign Considerations:")
        for consideration in analysis["design_considerations"]:
            print(
                f" - {consideration['consideration']}:"
            )
            print(f"   Implication: {consideration['implication']}")
            print(f"   Justification: {consideration['justification']}")

        print("\n[+] Verification PASSED!")

    except Exception as e:
        print(f"\n[-] Verification FAILED: {e}")
        raise e


if __name__ == "__main__":
    run_verification()
