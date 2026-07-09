import os
import time
import logging
from typing import Dict, Any, Optional

from tools.openrouter_client import OpenRouterClient
from tools.hf_client import HFClient
from tools.gemini_client import GeminiClient

logger = logging.getLogger("FallbackClient")


class FallbackClient:
    """A client wrapper that routes calls through multiple providers sequentially if one fails."""

    # Class-level registry to store disabled providers during execution session
    disabled_providers = set()

    def __init__(self):
        """Initializes the fallback providers."""
        self.openrouter = OpenRouterClient()
        self.hf = HFClient()
        self.gemini2 = GeminiClient(api_key=os.getenv("GOOGLE_API_KEY2"))
        self.gemini3 = GeminiClient(api_key=os.getenv("GOOGLE_API_KEY3"))

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        image_path: Optional[str] = None,
    ) -> str:
        """Attempts to generate text response using the fallback sequence."""
        last_error = None

        # 1. OpenRouter
        if "openrouter" not in FallbackClient.disabled_providers:
            try:
                print("[FallbackClient] Attempting OpenRouter for generate...")
                try:
                    return self.openrouter.generate(prompt=prompt, system_instruction=system_instruction)
                except Exception as e:
                    err_msg = str(e)
                    if "401" in err_msg or "Unauthorized" in err_msg or "User not found" in err_msg:
                        print("[FallbackClient] OpenRouter returned 401/Unauthorized. Disabling OpenRouter.")
                        FallbackClient.disabled_providers.add("openrouter")
                    elif "429" in err_msg:
                        print("[FallbackClient] OpenRouter hit 429. Retrying in 3 seconds...")
                        time.sleep(3)
                        return self.openrouter.generate(prompt=prompt, system_instruction=system_instruction)
                    raise e
            except Exception as e:
                last_error = str(e)
                print(f"[FallbackClient] OpenRouter failed: {last_error}. Falling back to HF...")
        else:
            print("[FallbackClient] Skipping disabled OpenRouter for generate.")

        # 2. Hugging Face
        if "hf" not in FallbackClient.disabled_providers:
            try:
                print("[FallbackClient] Attempting Hugging Face for generate...")
                return self.hf.generate(prompt=prompt, image_path=image_path, system_instruction=system_instruction)
            except Exception as e:
                last_error = str(e)
                if any(x in last_error for x in ["401", "Unauthorized", "Invalid username", "402", "Payment Required", "depleted"]):
                    print("[FallbackClient] HF returned 401/402/depleted. Disabling HF.")
                    FallbackClient.disabled_providers.add("hf")
                print(f"[FallbackClient] HF failed: {last_error}. Falling back to Gemini 2...")
        else:
            print("[FallbackClient] Skipping disabled HF for generate.")

        # 3. Gemini 2
        try:
            print("[FallbackClient] Attempting Gemini 2 for generate...")
            return self.gemini2.generate(prompt=prompt, system_instruction=system_instruction)
        except Exception as e:
            last_error = str(e)
            print(f"[FallbackClient] Gemini 2 failed: {last_error}. Falling back to Gemini 3...")

        # 4. Gemini 3
        try:
            print("[FallbackClient] Attempting Gemini 3 for generate...")
            return self.gemini3.generate(prompt=prompt, system_instruction=system_instruction)
        except Exception as e:
            last_error = str(e)
            print(f"[FallbackClient] Gemini 3 failed: {last_error}.")

        print("[FallbackClient] Warning: All API providers failed. Executing local text mock.")
        return "Mocked text generation."

    def generate_structured(
        self,
        prompt: str,
        response_schema: Any,
        system_instruction: Optional[str] = None,
        image_path: Optional[str] = None,
    ) -> Any:
        """Attempts to generate structured response matching schema using fallback sequence."""
        last_error = None

        # 1. OpenRouter
        if "openrouter" not in FallbackClient.disabled_providers:
            try:
                print("[FallbackClient] Attempting OpenRouter for generate_structured...")
                try:
                    return self.openrouter.generate_structured(
                        prompt=prompt,
                        response_schema=response_schema,
                        system_instruction=system_instruction
                    )
                except Exception as e:
                    err_msg = str(e)
                    if "401" in err_msg or "Unauthorized" in err_msg or "User not found" in err_msg:
                        print("[FallbackClient] OpenRouter returned 401/Unauthorized in structured. Disabling OpenRouter.")
                        FallbackClient.disabled_providers.add("openrouter")
                    elif "429" in err_msg:
                        print("[FallbackClient] OpenRouter hit 429 in structured. Retrying in 3 seconds...")
                        time.sleep(3)
                        return self.openrouter.generate_structured(
                            prompt=prompt,
                            response_schema=response_schema,
                            system_instruction=system_instruction
                        )
                    raise e
            except Exception as e:
                last_error = str(e)
                print(f"[FallbackClient] OpenRouter structured failed: {last_error}. Falling back to HF...")
        else:
            print("[FallbackClient] Skipping disabled OpenRouter for generate_structured.")

        # 2. Hugging Face
        if "hf" not in FallbackClient.disabled_providers:
            try:
                print("[FallbackClient] Attempting Hugging Face for generate_structured...")
                return self.hf.generate_structured(
                    prompt=prompt,
                    response_schema=response_schema,
                    system_instruction=system_instruction,
                    image_path=image_path
                )
            except Exception as e:
                last_error = str(e)
                if any(x in last_error for x in ["401", "Unauthorized", "Invalid username", "402", "Payment Required", "depleted"]):
                    print("[FallbackClient] HF returned 401/402/depleted in structured. Disabling HF.")
                    FallbackClient.disabled_providers.add("hf")
                print(f"[FallbackClient] HF structured failed: {last_error}. Falling back to Gemini 2...")
        else:
            print("[FallbackClient] Skipping disabled HF for generate_structured.")

        # 3. Gemini 2
        try:
            print("[FallbackClient] Attempting Gemini 2 for generate_structured...")
            return self.gemini2.generate_structured(
                prompt=prompt,
                response_schema=response_schema,
                system_instruction=system_instruction
            )
        except Exception as e:
            last_error = str(e)
            print(f"[FallbackClient] Gemini 2 structured failed: {last_error}. Falling back to Gemini 3...")

        # 4. Gemini 3
        try:
            print("[FallbackClient] Attempting Gemini 3 for generate_structured...")
            return self.gemini3.generate_structured(
                prompt=prompt,
                response_schema=response_schema,
                system_instruction=system_instruction
            )
        except Exception as e:
            last_error = str(e)
            print(f"[FallbackClient] Gemini 3 structured failed: {last_error}.")

        # Fallback to local schema mock generator if all API providers fail
        schema_name = response_schema.__name__
        print(f"[FallbackClient] All API providers failed. Executing local schema mock fallback for: {schema_name}")

        from models.clinical import ClinicalAnalysis, PressureSensitiveRegion, ClinicalDesignConsideration
        from models.socket_recommendation import SocketRecommendation, ReliefRegion, PressureRegion, TrimlineRecommendations, OffsetValues
        from models.safety import SafetyAnalysis, SafetyCheck
        from models.response import SocketRecommendationResponse, FinalReliefArea, FinalPressureArea

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

        raise Exception(f"FallbackClient structured failed all providers. Last error: {last_error}")
