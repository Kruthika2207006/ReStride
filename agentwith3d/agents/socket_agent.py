"""Socket Recommendation Agent that synthesizes clinical and geometric data."""

from typing import Dict, Any
from tools.gemini_client import GeminiClient
from models.socket_recommendation import SocketRecommendation


SOCKET_AGENT_SYSTEM_PROMPT = """You are the Socket Design Expert Agent for a prosthetic socket design recommendation system.
Your job is to read the patient's 3D residual limb geometry metrics and the Clinical Reasoning analysis, and formulate the final, complete socket parameters.

These parameters will directly configure an automated 3D mesh generator. Ensure you:
1. Recommend socket design (TSB, PTB, etc.) and explain the clinical biomechanics.
2. Select appropriate suspension system and liner type based on activity level and skin status.
3. Recommend structural wall thickness in mm (standard range 3.0 to 6.0 mm).
4. Identify specific relief regions (channels where socket material is moved away from sensitive bones) and pressure regions (tight spots where weight bearing is safe).
5. Outline trimline height constraints in cm (front/anterior relative to patella center, back/posterior relative to popliteal fold).
6. Detail material recommendations (carbon fiber composite, copolymer check socket, etc.).
7. Specify exact offset parameters:
   - radial_expansion_mm: range -1.0 to +2.0 mm (expansion/contraction to fit limb volume changes).
   - distal_clearance_mm: range 2.0 to 6.0 mm (gap at the tip to insert a soft end pad).
   - ply_fit_compensation: range 0.0 to 2.0 (factor for prosthetic sock thickness).

Format the output strictly according to the requested Pydantic schema structure. Ensure every recommendation has a clear justification.
"""


class SocketAgent:
    """Recommends detailed prosthetic socket design parameters based on geometry and clinical reasoning."""

    def __init__(self):
        """Initializes the Socket Recommendation Agent."""
        self.client = GeminiClient()

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesizes clinical and geometric inputs to output a complete socket design.

        Args:
            state: The shared LangGraph state dictionary.

        Returns:
            State updates containing the socket_recommendation.
        """
        request = state.get("request")
        geometry = state.get("geometry_analysis_results") or {}
        clinical = state.get("clinical_analysis") or {}

        # Compile input details for LLM reasoning
        prompt = f"""
### Patient Profile
- Age: {request.age} years old
- Weight: {request.weight_kg} kg
- Activity Level: {request.activity_level}
- Amputation Level: {request.amputation_level}
- Skin Condition: {request.limb_details.skin_condition}
- Current Issues: {request.current_issues or "None reported"}

### 3D Geometry Metrics
- Shape: {geometry.get("shape_descriptor", "N/A")}
- Length: {geometry.get("limb_length_cm", "N/A")} cm
- Volume: {geometry.get("volume_cm3", "N/A")} cm3
- Surface Area: {geometry.get("surface_area_cm2", "N/A")} cm2
- Bounding Box Dims [W, D, H]: {geometry.get("bounding_box_dims", "N/A")}
- Circumferences: {geometry.get("cross_sectional_circumferences", "N/A")}

### Clinical Reasoning Analysis
- Clinical Summary: {clinical.get("limb_analysis_summary", "N/A")}
- Clinical Socket Base Recommendation: {clinical.get("recommended_socket_type", "N/A")}
- Socket Type Reasoning: {clinical.get("recommended_socket_type_reasoning", "N/A")}
- Identified Pressure Sensitive Regions: {clinical.get("pressure_sensitive_regions", [])}
- Clinical Design Considerations: {clinical.get("design_considerations", [])}
"""

        # Generate structured response from Gemini
        recommendation: SocketRecommendation = self.client.generate_structured(
            prompt=prompt,
            response_schema=SocketRecommendation,
            system_instruction=SOCKET_AGENT_SYSTEM_PROMPT,
        )

        return {"socket_recommendation": recommendation.dict()}
