"""Safety Validation Agent for assessing prosthetic socket design constraints."""

from typing import Dict, Any
from tools.fallback_client import FallbackClient
from models.safety import SafetyAnalysis


SAFETY_AGENT_SYSTEM_PROMPT = """You are the Safety Validation Agent for a prosthetic socket design recommendation system.
Your job is to perform a rigorous safety verification of proposed socket design parameters against the patient's clinical profile and 3D geometry scan.

Evaluate the following rules:
1. Neuropathy & Diabetes Check: Patients with neuropathy or diabetes are highly vulnerable to skin ulceration. They MUST use soft gel liners (Silicone/Polyurethane) and avoid direct hard socket interfaces or thin suspensions.
2. Wall Thickness Check: Socket wall thickness must be structurally sound. Thickness below 3.0 mm presents high risk of structural cracking under loading. Thickness above 6.0 mm is excessive, adding unnecessary weight.
3. Bony Prominences & Reliefs: Check that all prominent bones identified in the geometry analysis have corresponding relief regions with adequate relief depth (minimum 1.5mm to 3.5mm depending on bone prominence).
4. Mechanical Constraints: Ensure that high-activity patients (K3/K4) have strong structural materials (e.g., carbon fiber composite) rather than fragile check materials, and check that offset values (radial expansion, distal clearance) are biomechanically safe.
5. Mismatched Choices: Identify contradictions between clinical suggestions and socket parameters (e.g., Clinical Agent recommended Patellar Tendon loading but Socket Agent failed to define a Patellar Tendon pressure region).

Assign a risk score (Low, Medium, or High). If critical safety violations exist (e.g. wall thickness < 3.0mm, or active diabetic neuropathy patient without a liner), set is_safe_to_fabricate to False.
Format the output strictly according to the requested Pydantic schema structure.
"""


class SafetyAgent:
    """Performs safety verification on socket design parameters."""

    def __init__(self):
        """Initializes the Safety Agent with a Fallback client."""
        self.llm = FallbackClient()

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Validates recommended design configurations against medical risk rules.

        Args:
            state: The shared LangGraph state dictionary.

        Returns:
            State updates containing the safety_analysis dict.
        """
        request = state["request"]
        geometry = state.get("geometry_analysis_results") or {}
        clinical = state.get("clinical_analysis") or {}
        socket_rec = state.get("socket_recommendation") or {}

        # Compile detailed prompt combining all upstream agent outputs
        prompt = f"""
### Patient Profile
- Age: {request.age} years old
- Weight: {request.weight_kg} kg
- Activity Level: {request.activity_level}
- Amputation Level: {request.amputation_level}
- Skin Condition: {request.limb_details.skin_condition}
- Diabetic: {"Yes" if request.clinical_history.has_diabetes else "No"}
- Neuropathy: {"Yes" if request.clinical_history.has_neuropathy else "No"}
- Volume Fluctuations: {"Yes" if request.clinical_history.volume_fluctuations else "No"}

### 3D Scan Geometry
- Shape: {geometry.get("shape_descriptor", "N/A")}
- Length: {geometry.get("limb_length_cm", "N/A")} cm
- Volume: {geometry.get("volume_cm3", "N/A")} cm3
- Bounding Box Dims: {geometry.get("bounding_box_dims", "N/A")}
- Scanner Bony Prominences: {geometry.get("errors", []) or "None"}

### Clinical Reasoning Analysis
- Clinical Summary: {clinical.get("limb_analysis_summary", "N/A")}
- Recommended Socket Type: {clinical.get("recommended_socket_type", "N/A")}
- Pressure Sensitive Regions: {clinical.get("pressure_sensitive_regions", [])}
- Clinical Design Considerations: {clinical.get("design_considerations", [])}

### Proposed Socket Design Parameters
- Socket Design Type: {socket_rec.get("socket_design_type", "N/A")}
- Suspension System: {socket_rec.get("suspension_system", "N/A")}
- Liner Type: {socket_rec.get("liner_type", "N/A")}
- Wall Thickness: {socket_rec.get("socket_wall_thickness_mm", "N/A")} mm
- Relief Regions: {socket_rec.get("relief_regions", [])}
- Pressure Regions: {socket_rec.get("pressure_regions", [])}
- Trimline: {socket_rec.get("trimline_recommendations", {})}
- Material: {socket_rec.get("material_recommendations", [])}
- Offsets: {socket_rec.get("offset_values", {})}
"""

        # Generate structured safety report from FallbackClient
        safety_result: SafetyAnalysis = self.llm.generate_structured(
            prompt=prompt,
            response_schema=SafetyAnalysis,
            system_instruction=SAFETY_AGENT_SYSTEM_PROMPT,
        )

        return {"safety_analysis": safety_result.dict()}
