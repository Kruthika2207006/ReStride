"""Verification script for testing the Socket Recommendation Agent."""

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
from agents.socket_agent import SocketAgent


def create_test_request() -> SocketRecommendationRequest:
    """Creates a sample request for testing."""
    return SocketRecommendationRequest(
        patient_id="PAT-4321",
        age=52,
        weight_kg=82.0,
        activity_level="K3",
        amputation_level="transtibial",
        limb_details=ResidualLimbDetails(
            shape="conical",
            length_cm=15.0,
            proximal_circumference_cm=31.42,
            mid_limb_circumference_cm=25.13,
            distal_circumference_cm=18.85,
            skin_condition="healthy, minor scarring",
            prominent_bones=True,
            additional_notes="Patient is very active but has pressure issues.",
        ),
        clinical_history=PatientClinicalHistory(
            amputation_reason="trauma",
            has_diabetes=False,
            has_neuropathy=False,
            volume_fluctuations=True,
        ),
        stl_file_path="C:/ai_agent/scratch/scratch_limb_mesh.stl",
    )


def run_verification():
    """Runs the verification on SocketAgent."""
    print("=== Socket Recommendation Agent Verification ===")

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

    # Clinical output
    clinical_results = {
        "limb_analysis_summary": (
            "Limb shape is conical (length 15cm) with healthy skin and some volume fluctuations. "
            "Patient is high activity (K3). Standard bony prominences (fibular head, tibial crest) are present."
        ),
        "pressure_sensitive_regions": [
            {
                "region_name": "Fibular Head",
                "risk_level": "Medium",
                "justification": "Bony projection susceptible to pressure and shear.",
            },
            {
                "region_name": "Tibial Crest",
                "risk_level": "Medium",
                "justification": "Thin tissue coverage, patient has minor volume fluctuations.",
            },
        ],
        "design_considerations": [
            {
                "consideration": "TSB socket",
                "implication": "Uniform loading",
                "justification": "TSB is better suited for conical active limbs to distribute loading.",
            }
        ],
        "recommended_socket_type": "TSB",
        "recommended_socket_type_reasoning": "TSB distributes pressure evenly.",
    }

    state = {
        "request": request,
        "geometry_analysis_results": geom_results,
        "clinical_analysis": clinical_results,
        "socket_recommendation": {},
        "errors": [],
    }

    agent = SocketAgent()

    # Check if Gemini API key exists, otherwise mock the output
    has_api_key = bool(
        os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    )

    if not has_api_key:
        print("[!] No Gemini API key detected. Using Mock Gemini Client for test.")

        # Create a mock response matching the structured schema
        mock_response = SocketRecommendation(
            socket_design_type="TSB",
            socket_design_reasoning=(
                "Total Surface Bearing distributes weight uniformly across the residual limb, "
                "which is ideal for conical shapes and active K3 users."
            ),
            suspension_system="Suction",
            suspension_system_reasoning=(
                "Suction suspension provides high stability and control during gait cycles for active patients "
                "while minimizing socket movement/pistoning."
            ),
            liner_type="Silicone Gel Liner",
            liner_type_reasoning=(
                "Cushions the bony prominences and distributes pressure, ideal for K3 active patients."
            ),
            socket_wall_thickness_mm=4.0,
            socket_wall_thickness_reasoning=(
                "A 4.0mm carbon wall provides standard structural strength and durability for active patients."
            ),
            relief_regions=[
                ReliefRegion(
                    region_name="Fibular Head",
                    depth_mm=3.0,
                    reasoning="Relieves pressure at the sensitive fibular head area.",
                ),
                ReliefRegion(
                    region_name="Tibial Crest",
                    depth_mm=2.5,
                    reasoning="Relieves shear force on the anterior crest.",
                ),
            ],
            pressure_regions=[
                PressureRegion(
                    region_name="Patellar Tendon",
                    depth_mm=2.0,
                    reasoning="Loads the patellar tendon which is a primary load-bearing anatomical region.",
                ),
                PressureRegion(
                    region_name="Medial Tibial Flare",
                    depth_mm=1.5,
                    reasoning="Distributes weight loading across the medial tibial bone surface.",
                ),
            ],
            trimline_recommendations=TrimlineRecommendations(
                description="Standard TSB transtibial trimline profile",
                anterior_trim_height_cm=4.5,
                posterior_trim_height_cm=2.5,
                reasoning=(
                    "Anterior trimline extends to mid-patella to provide stability, "
                    "while posterior cut allows full knee flexion to 90 degrees."
                ),
            ),
            material_recommendations=["Carbon Fiber Composite"],
            material_recommendations_reasoning=(
                "High strength-to-weight ratio to support active walking and running cycles."
            ),
            offset_values=OffsetValues(
                radial_expansion_mm=1.0,
                distal_clearance_mm=4.0,
                ply_fit_compensation=1.0,
            ),
            offset_values_reasoning=(
                "Radial expansion accommodates limb volume changes, and 4mm distal gap allows space for the distal end pad."
            ),
        )

        agent.client.generate_structured = MagicMock(
            return_value=mock_response
        )

    else:
        print("[+] API key detected. Running real query to Gemini model...")

    try:
        results = agent.run(state)
        print("\n=== Analysis Executed Successfully ===")
        recommendation = results["socket_recommendation"]

        print(f"Recommended Socket Design: {recommendation['socket_design_type']}")
        print(f"Design Reasoning:        {recommendation['socket_design_reasoning']}")
        print(f"Suspension System:       {recommendation['suspension_system']}")
        print(f"Liner Type:              {recommendation['liner_type']}")
        print(f"Wall Thickness:          {recommendation['socket_wall_thickness_mm']} mm")

        print("\nRelief Regions:")
        for r in recommendation["relief_regions"]:
            print(f" - {r['region_name']} (depth={r['depth_mm']}mm): {r['reasoning']}")

        print("\nPressure/Weight-Bearing Regions:")
        for p in recommendation["pressure_regions"]:
            print(f" - {p['region_name']} (depth={p['depth_mm']}mm): {p['reasoning']}")

        print("\nTrimlines:")
        trim = recommendation["trimline_recommendations"]
        print(f" - Description: {trim['description']}")
        print(f" - Anterior Height: {trim['anterior_trim_height_cm']} cm")
        print(f" - Posterior Height: {trim['posterior_trim_height_cm']} cm")

        print("\nOffset parameters (for mesh generation):")
        offsets = recommendation["offset_values"]
        print(f" - Radial Expansion: {offsets['radial_expansion_mm']} mm")
        print(f" - Distal Clearance: {offsets['distal_clearance_mm']} mm")
        print(f" - Ply Compensation: {offsets['ply_fit_compensation']}")

        print("\n[+] Verification PASSED!")

    except Exception as e:
        print(f"\n[-] Verification FAILED: {e}")
        raise e


if __name__ == "__main__":
    run_verification()
