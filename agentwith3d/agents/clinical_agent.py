"""Clinical agent for checking medical considerations and biomechanics."""

from typing import Dict, Any
from tools.gemini_client import GeminiClient
from prompts.clinical_prompt import CLINICAL_AGENT_PROMPT
from models.clinical import ClinicalAnalysis


class ClinicalAgent:
    """Evaluates clinical patient factors for socket design.

    Analyzes conditions like diabetes, neuropathy, scar tissue,
    and bone structure to identify clinical constraints and load-bearing profiles.
    """

    def __init__(self):
        """Initializes the Clinical agent with a Gemini client."""
        # Initialize the Gemini client wrapper
        self.client = GeminiClient()

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Performs clinical reasoning based on request and geometry analysis.

        Args:
            state: The shared LangGraph state dictionary.

        Returns:
            State updates containing the structured clinical_analysis dict.
        """
        request = state["request"]
        geom_results = state.get("geometry_analysis_results") or {}

        # Sourced values from 3D scan geometry or fallback request
        shape = geom_results.get("shape_descriptor") or request.limb_details.shape
        length = geom_results.get("limb_length_cm") or request.limb_details.length_cm
        volume = geom_results.get("volume_cm3") or "N/A"
        surface_area = geom_results.get("surface_area_cm2") or "N/A"
        bbox = geom_results.get("bounding_box_dims") or "N/A"

        # Sourced circumferences from 3D scan or fallback request
        circumferences = geom_results.get("cross_sectional_circumferences") or {}
        c_prox = circumferences.get("80%") or request.limb_details.proximal_circumference_cm
        c_mid = circumferences.get("50%") or request.limb_details.mid_limb_circumference_cm
        c_dist = circumferences.get("20%") or request.limb_details.distal_circumference_cm

        # Scanner geometry bone prominences or fallback request
        bone_prominences = []
        if request.geometry_analysis:
            bone_prominences = request.geometry_analysis.bone_prominences
        # If geometry analysis has its own list, combine them
        mesh_status = geom_results.get("mesh_status", "N/A")
        mesh_errors = geom_results.get("errors", [])

        # Compile detailed clinical input parameters for the LLM
        prompt = f"""
### Patient Profile
- Age: {request.age} years old
- Weight: {request.weight_kg} kg
- Activity Level: {request.activity_level}
- Amputation Level: {request.amputation_level}

### Residual Limb Measurements & Physical Details (Sourced from 3D Scan / Manual input)
- Shape: {shape}
- Length: {length} cm
- Volume: {volume} cm3
- Surface Area: {surface_area} cm2
- Bounding Box Dimensions [W, D, H]: {bbox}
- Circumferences:
  - Proximal (80% height): {c_prox} cm
  - Mid-Limb (50% height): {c_mid} cm
  - Distal (20% height): {c_dist} cm
- Skin Condition: {request.limb_details.skin_condition}
- Bony Prominences (Observation): {"Yes" if request.limb_details.prominent_bones else "No"}
- Notes: {request.limb_details.additional_notes or "N/A"}

### Geometry Analysis Scanner Results
- Bone Prominences (Scanner): {", ".join(bone_prominences) or "None identified"}
- Mesh Status: {mesh_status}
- Mesh Errors/Warnings: {", ".join(mesh_errors) or "None"}

### Patient Clinical History
- Reason for Amputation: {request.clinical_history.amputation_reason}
- Diabetic: {"Yes" if request.clinical_history.has_diabetes else "No"}
- Neuropathy: {"Yes" if request.clinical_history.has_neuropathy else "No"}
- Volume Fluctuations: {"Yes" if request.clinical_history.volume_fluctuations else "No"}

### Current Device Issues
- Current Issues: {request.current_issues or "None reported"}
"""

        # Generate structured JSON matching the ClinicalAnalysis schema using Gemini
        clinical_result: ClinicalAnalysis = self.client.generate_structured(
            prompt=prompt,
            response_schema=ClinicalAnalysis,
            system_instruction=CLINICAL_AGENT_PROMPT,
        )

        # Convert to dictionary or store Pydantic model directly
        return {"clinical_analysis": clinical_result.dict()}
