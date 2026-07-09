"""Decision Synthesis agent that aggregates and formulates final recommendations."""

from typing import Dict, Any
from tools.fallback_client import FallbackClient
from models.response import SocketRecommendationResponse


DECISION_AGENT_SYSTEM_PROMPT = """You are the Decision Synthesis Agent for a prosthetic socket design recommendation system.
Your job is to act as the final consensus arbiter. You must collect reports from all upstream agents:
- Geometry scan metrics.
- Clinical reasoning recommendations.
- Socket design parameters.
- Safety validation checks, warnings, and overrides.

You must:
1. Resolve conflicts: If there is a disagreement (e.g., Clinical Agent recommended TSB, but Socket Agent chose PTB), you must select the most appropriate configuration, favoring clinical-biomechanical soundness.
2. Prioritize safety: If the Safety Agent flagged an issue, raised a warning, or proposed a mitigation (e.g., changing the suspension or increasing wall thickness), you MUST override any previous recommendations with the Safety Agent's mitigation.
3. Consolidate fabrication parameters: Output the final materials, thickness, trimline heights, and mesh generation offsets in the fabrication_parameters dictionary.
4. Set fabrication_approval: Directly align this with the safety validation pass/fail flag. If the Safety Agent set is_safe_to_fabricate to False, fabrication_approval MUST be False.

Generate the final structured response matching the SocketRecommendationResponse schema.
"""


class DecisionAgent:
    """Consolidates inputs from clinical, geometry, socket, and safety analyses.

    Produces a final unified SocketRecommendationResponse model.
    """

    def __init__(self):
        """Initializes the Decision synthesis agent."""
        self.llm = FallbackClient()

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesizes agent inputs into a structured socket design recommendation.

        Args:
            state: The shared LangGraph state dictionary.

        Returns:
            State updates containing the final SocketRecommendationResponse object.
        """
        request = state.get("request")
        geometry = state.get("geometry_analysis_results") or {}
        clinical = state.get("clinical_analysis") or {}
        socket_rec = state.get("socket_recommendation") or {}
        safety = state.get("safety_analysis") or {}

        # Compile detailed prompt combining all upstream agent outputs
        prompt = f"""
### Consolidated Multi-Agent Reports

1. Patient Request:
- Amputation Level: {request.amputation_level}
- Activity Level: {request.activity_level}

2. Geometry Scan:
- shape: {geometry.get("shape_descriptor")}
- length: {geometry.get("limb_length_cm")} cm
- volume: {geometry.get("volume_cm3")} cm3

3. Clinical Reasoning:
- Summary: {clinical.get("limb_analysis_summary")}
- Target Socket: {clinical.get("recommended_socket_type")}
- Design Considerations: {clinical.get("design_considerations")}

4. Socket Design Agent:
- Socket Type: {socket_rec.get("socket_design_type")}
- Suspension: {socket_rec.get("suspension_system")}
- Liner: {socket_rec.get("liner_type")}
- Thickness: {socket_rec.get("socket_wall_thickness_mm")} mm
- Reliefs: {socket_rec.get("relief_regions")}
- Pressures: {socket_rec.get("pressure_regions")}
- Trimline: {socket_rec.get("trimline_recommendations")}
- Materials: {socket_rec.get("material_recommendations")}
- Offsets: {socket_rec.get("offset_values")}

5. Safety Validation Agent:
- Risk Score: {safety.get("risk_score")}
- Risk Explanation: {safety.get("risk_explanation")}
- Safety Checks: {safety.get("validated_constraints")}
- Detected Risks: {safety.get("detected_risks")}
- Conflicts Flagged: {safety.get("conflicting_recommendations")}
- Safe to Fabricate: {safety.get("is_safe_to_fabricate")}
"""

        # Generate structured final consensus response from FallbackClient
        final_result: SocketRecommendationResponse = (
            self.llm.generate_structured(
                prompt=prompt,
                response_schema=SocketRecommendationResponse,
                system_instruction=DECISION_AGENT_SYSTEM_PROMPT,
            )
        )

        return {"final_response": final_result}
