"""Background tasks for executing the LangGraph socket recommendation agent workflow."""

import os
import sys
import logging
import asyncio

# Ensure project root is in the Python search path to resolve 'ai_agent' imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.database import get_patient, update_analysis
from ai_agent.workflow import create_graph
from ai_agent.models.request import (
    SocketRecommendationRequest,
    ResidualLimbDetails,
    PatientClinicalHistory,
)

logger = logging.getLogger("backend.tasks")


async def run_analysis(patient_id: str, image_folder_path: str):
    """Background task executing the LangGraph socket recommendation agent workflow.

    Args:
        patient_id: Unique identifier for the patient.
        image_folder_path: Absolute path to the folder containing residual limb images.
    """
    logger.info(f"Background task run_analysis triggered for patient ID: {patient_id}")
    logger.info(f"Image folder path provided: {image_folder_path}")

    try:
        # a. Set initial status - progress 5%
        await update_analysis(
            patient_id=patient_id,
            update_fields={"status": "processing", "progress": 5.0, "error": None},
        )
        logger.info(f"Set initial processing status for patient: {patient_id}")

        # b. Retrieve patient data
        patient = await get_patient(patient_id)
        if not patient:
            error_msg = f"Patient profile with ID '{patient_id}' not found."
            logger.error(error_msg)
            await update_analysis(
                patient_id=patient_id,
                update_fields={"status": "failed", "error": error_msg, "progress": 0.0},
            )
            return

        # c. Build the input request
        clinical_history_dict = patient.get("clinical_history") or {}
        clinical_history = PatientClinicalHistory(
            amputation_reason=clinical_history_dict.get("amputation_reason", "trauma") or "trauma",
            has_diabetes=bool(clinical_history_dict.get("has_diabetes", False)),
            has_neuropathy=bool(clinical_history_dict.get("has_neuropathy", False)),
            volume_fluctuations=bool(clinical_history_dict.get("volume_fluctuations", False)),
        )

        limb_details_dict = patient.get("limb_details") or {}
        limb_details = ResidualLimbDetails(
            shape=limb_details_dict.get("shape", "cylindrical") or "cylindrical",
            length_cm=float(limb_details_dict.get("length_cm", 15.0) or 15.0),
            proximal_circumference_cm=float(limb_details_dict.get("proximal_circumference_cm", 30.0) or 30.0),
            mid_limb_circumference_cm=float(limb_details_dict.get("mid_limb_circumference_cm", 25.0) or 25.0),
            distal_circumference_cm=float(limb_details_dict.get("distal_circumference_cm", 20.0) or 20.0),
            skin_condition=limb_details_dict.get("skin_condition", "healthy") or "healthy",
            prominent_bones=bool(limb_details_dict.get("prominent_bones", False)),
            additional_notes=limb_details_dict.get("additional_notes"),
        )

        request = SocketRecommendationRequest(
            patient_id=patient_id,
            age=int(patient["age"]),
            weight_kg=float(patient["weight_kg"]),
            activity_level=patient["activity_level"],
            amputation_level=patient.get("amputation_level", "transtibial") or "transtibial",
            clinical_history=clinical_history,
            limb_details=limb_details,
            image_folder_path=image_folder_path,
            stl_file_path=None,
        )

        # d. Update progress to 20%
        await update_analysis(
            patient_id=patient_id,
            update_fields={"progress": 20.0},
        )
        logger.info(f"Constructed input request and set progress to 20% for patient: {patient_id}")

        # Update progress to 40% after starting agent (we update before invoking the thread)
        await update_analysis(
            patient_id=patient_id,
            update_fields={"progress": 40.0},
        )
        logger.info(f"Starting agent execution and set progress to 40% for patient: {patient_id}")

        # e. Run the graph in a separate thread
        graph = create_graph()
        initial_state = {
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

        final_state = await asyncio.to_thread(graph.invoke, initial_state)
        logger.info(f"Agent execution completed for patient: {patient_id}")

        # After the agent finishes (before saving): progress = 90%
        await update_analysis(
            patient_id=patient_id,
            update_fields={"progress": 90.0},
        )
        logger.info(f"Set progress to 90% before saving results for patient: {patient_id}")

        # f. After the graph finishes, extract the relevant keys from the final state
        geometry_analysis_results = final_state.get("geometry_analysis_results") or {}
        clinical_analysis = final_state.get("clinical_analysis") or {}
        socket_recommendation = final_state.get("socket_recommendation") or {}
        safety_analysis = final_state.get("safety_analysis") or {}
        final_response = final_state.get("final_response")

        final_response_dict = None
        if final_response is not None:
            if hasattr(final_response, "dict"):
                final_response_dict = final_response.dict()
            else:
                final_response_dict = final_response

        # Log detailed Agent Output
        try:
            import json

            def safe_serialize(obj):
                if hasattr(obj, "dict"):
                    return obj.dict()
                elif isinstance(obj, dict):
                    return {k: safe_serialize(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [safe_serialize(x) for x in obj]
                return obj

            # Log the entire final_state keys
            logger.info("=== FINAL STATE KEYS ===")
            logger.info(list(final_state.keys()))

            # Log the geometry_analysis_results content
            logger.info("=== GEOMETRY_ANALYSIS_RESULTS ===")
            logger.info(json.dumps(safe_serialize(final_state.get("geometry_analysis_results", {})), indent=2))

            # Log all keys and their types for debugging
            for key, value in final_state.items():
                logger.info(f"{key}: {type(value)}")

            # Log update payload
            update_payload = {
                "status": "completed",
                "progress": 100,
                "geometry": final_state.get("geometry_analysis_results"),
                "clinical": final_state.get("clinical_analysis"),
                "socket": final_state.get("socket_recommendation"),
                "safety": final_state.get("safety_analysis"),
                "final_response": final_response_dict,
                "error": None
            }
            logger.info("=== UPDATE PAYLOAD ===")
            logger.info(json.dumps(safe_serialize(update_payload), indent=2))
        except Exception as log_ex:
            logger.warning(f"Failed to log agent output details: {log_ex}")

        # g. Update analysis document with results - progress = 100%
        await update_analysis(
            patient_id=patient_id,
            update_fields={
                "status": "completed",
                "progress": 100.0,
                "geometry": geometry_analysis_results,
                "clinical": clinical_analysis,
                "socket": socket_recommendation,
                "safety": safety_analysis,
                "final_response": final_response_dict,
                "error": None,
            },
        )
        logger.info(f"Successfully completed analysis and updated database for patient: {patient_id}")

    except Exception as exc:
        logger.exception(f"Error during analysis workflow execution for patient {patient_id}: {exc}")
        await update_analysis(
            patient_id=patient_id,
            update_fields={
                "status": "failed",
                "error": str(exc),
                "progress": 0.0,
            },
        )
