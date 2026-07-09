"""Loader and runner for the residual limb image analysis pipeline."""

import os
import sys
import json
from typing import Dict, Any

# Add the directory containing this script to sys.path to resolve imports correctly
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from remove_background import remove_background
from image_feature_extractor import extract_features
from multi_image_analyzer import analyze_multiple_images


def run_image_pipeline(folder_path: str, output_json_name: str = "residual_limb_analysis.json") -> Dict[str, Any]:
    """Executes the complete image analysis pipeline on a folder of patient limb images.

    Args:
        folder_path: Path to the directory containing 1-4 residual limb images.
        output_json_name: Name of the output JSON file to generate.

    Returns:
        The dictionary containing the consolidated multi-image analysis.
    """
    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"Folder not found: {folder_path}")

    image_extensions = (".png", ".jpg", ".jpeg")
    image_files = [
        os.path.join(folder_path, f)
        for f in os.listdir(folder_path)
        if f.lower().endswith(image_extensions)
    ]

    if not image_files:
        raise ValueError(f"No images found in folder: {folder_path}")

    results = []
    errors = []

    for image_path in image_files:
        filename = os.path.basename(image_path)
        name, ext = os.path.splitext(filename)
        
        # Avoid processing already background-removed images
        if name.endswith("_nobg"):
            continue

        nobg_path = os.path.join(folder_path, f"{name}_nobg.png")

        try:
            # 1. Remove background
            remove_background(image_path, nobg_path)

            # 2. Extract features
            features = extract_features(nobg_path)
            results.append(features)

        except Exception as e:
            errors.append(f"Failed to process image {filename}: {str(e)}")

    if not results:
        raise ValueError(f"Failed to extract features from any image. Errors: {errors}")

    # 3. Analyze multiple images to get consolidated metrics
    final_result = analyze_multiple_images(results)

    # 4. Save to JSON in the current working directory
    with open(output_json_name, "w") as f:
        json.dump(final_result, f, indent=4)

    return final_result


if __name__ == "__main__":
    # Allow command line execution if needed
    if len(sys.argv) > 1:
        path = sys.argv[1].strip().strip('"')
        try:
            res = run_image_pipeline(path)
            print(json.dumps(res, indent=4))
        except Exception as err:
            print(f"Error executing pipeline: {err}")
            sys.exit(1)
    else:
        print("Usage: python image_analysis_loader.py <folder_path>")
