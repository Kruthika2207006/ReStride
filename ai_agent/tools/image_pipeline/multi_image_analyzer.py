from collections import Counter


def analyze_multiple_images(results):

    if len(results) == 0:
        raise ValueError("No image results found")

    # -------------------------
    # Average Measurements
    # -------------------------

    avg_area = sum(
        r["contour_area"]
        for r in results
    ) / len(results)

    avg_ratio = sum(
        r["width_ratio"]
        for r in results
    ) / len(results)

    avg_width = sum(
        r["bounding_box_width"]
        for r in results
    ) / len(results)

    avg_height = sum(
        r["bounding_box_height"]
        for r in results
    ) / len(results)

    # -------------------------
    # Shape Voting
    # -------------------------

    shape_counts = Counter(
        r["shape_type"]
        for r in results
    )

    final_shape = (
        shape_counts
        .most_common(1)[0][0]
    )

    view_agreement = round(
        shape_counts[final_shape]
        / len(results),
        2
    )

    # -------------------------
    # Confidence Calculation
    # -------------------------

    confidence = round(
        min(
            0.95,
            0.60 + (view_agreement * 0.35)
        ),
        2
    )

    if confidence >= 0.85:
        analysis_quality = "High"

    elif confidence >= 0.70:
        analysis_quality = "Medium"

    else:
        analysis_quality = "Low"

    # -------------------------
    # Final Result
    # -------------------------

    final_result = {

        "number_of_views":
            len(results),

        "residual_limb_shape":
            final_shape,

        "average_width_ratio":
            round(avg_ratio, 3),

        "average_contour_area":
            round(avg_area, 2),

        "average_width":
            round(avg_width, 2),

        "average_height":
            round(avg_height, 2),

        "view_agreement":
            view_agreement,

        "confidence":
            confidence,

        "analysis_quality":
            analysis_quality
    }

    return final_result