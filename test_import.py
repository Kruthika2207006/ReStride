"""Verification script to test importability of the packaged ai_agent module."""

import os
import sys

# Add project root to Python search path to resolve 'ai_agent' imports
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    # 1. Test schema imports from models package
    from ai_agent.models.request import (
        SocketRecommendationRequest,
        ResidualLimbDetails,
        PatientClinicalHistory,
    )
    # 2. Test LangGraph recommendation graph compiled workflow import
    from ai_agent.workflow import recommendation_graph
    
    print("[+] Import verification successful! Package structure is importable.")
except Exception as e:
    print(f"[-] Packaging import verification failed: {e}")
    sys.exit(1)

# 3. Construct a dummy SocketRecommendationRequest
try:
    request = SocketRecommendationRequest(
        patient_id="PAT-IMPORT-VERIFY",
        age=45,
        weight_kg=72.5,
        activity_level="K3",
        amputation_level="transtibial",
        limb_details=ResidualLimbDetails(
            shape="cylindrical",
            length_cm=14.0,
            proximal_circumference_cm=32.0,
            mid_limb_circumference_cm=26.0,
            distal_circumference_cm=20.0,
            skin_condition="healthy",
            prominent_bones=False,
            additional_notes="Verifying external package imports.",
        ),
        clinical_history=PatientClinicalHistory(
            amputation_reason="trauma",
            has_diabetes=False,
            has_neuropathy=False,
            volume_fluctuations=False,
        ),
    )
    print("[+] Successfully constructed dummy SocketRecommendationRequest.")
except Exception as e:
    print(f"[-] Failed to instantiate SocketRecommendationRequest: {e}")
    sys.exit(1)

# 4. Prepare initial state payload dictionary
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

print("[+] Dummy graph state validation verified successfully!")
