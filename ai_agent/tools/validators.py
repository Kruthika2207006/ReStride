"""Validation helper functions for prosthetic socket designs and requests."""

from typing import Dict, Any, List, Tuple
from models.request import SocketRecommendationRequest


def validate_request_parameters(
    request: SocketRecommendationRequest,
) -> Tuple[bool, List[str]]:
    """Performs static checks on request fields to ensure logic consistency.

    Example check:
    - High-activity patients (K3/K4) shouldn't have incompatible conditions
      without special configurations.

    Args:
        request: The socket recommendation request data.

    Returns:
        A tuple of (is_valid, list of validation warning/error messages).
    """
    errors = []

    # TODO: Add specific mechanical or clinical sanity checks
    # e.g., if limb length is extremely short (e.g. < 5cm), flag it.
    if request.limb_details.length_cm <= 0:
        errors.append("Residual limb length must be greater than 0.")

    # Validate activity level options
    valid_k_levels = {"K1", "K2", "K3", "K4"}
    if request.activity_level.upper() not in valid_k_levels:
        errors.append(
            f"Invalid activity level: {request.activity_level}. Must be one of {valid_k_levels}"
        )

    return len(errors) == 0, errors


def check_materials_compatibility(
    socket_type: str, suspension: str, materials: List[str]
) -> List[str]:
    """Helper to check basic compatibility of recommended components.

    Args:
        socket_type: The proposed socket design type.
        suspension: The suspension system choice.
        materials: The proposed materials.

    Returns:
        List of conflict warning strings (empty list if no conflicts).
    """
    warnings = []
    # TODO: Implement compatibility rules logic
    return warnings
