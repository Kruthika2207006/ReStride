import os
import json

from remove_background import remove_background
from image_feature_extractor import extract_features
from multi_image_analyzer import analyze_multiple_images


folder_path = input(
    "Enter folder path: "
).strip().strip('"')

if not os.path.exists(folder_path):
    print("Folder not found!")
    exit()

image_extensions = (
    ".png",
    ".jpg",
    ".jpeg"
)

image_files = [
    os.path.join(folder_path, f)
    for f in os.listdir(folder_path)
    if f.lower().endswith(image_extensions)
]

if len(image_files) == 0:
    print("No images found!")
    exit()

results = []

for image_path in image_files:

    print(
        f"\nProcessing: "
        f"{os.path.basename(image_path)}"
    )

    filename = os.path.basename(image_path)
    name, ext = os.path.splitext(filename)

    nobg_path = os.path.join(
        folder_path,
        f"{name}_nobg.png"
    )

    try:

        remove_background(
            image_path,
            nobg_path
        )

        features = extract_features(
            nobg_path
        )

        results.append(features)

    except Exception as e:

        print(
            f"Failed: {filename}"
        )

        print(e)

final_result = analyze_multiple_images(
    results
)

with open(
    "residual_limb_analysis.json",
    "w"
) as f:

    json.dump(
        final_result,
        f,
        indent=4
    )

print(
    "\nResidual Limb Analysis Complete\n"
)

print(
    json.dumps(
        final_result,
        indent=4
    )
)

print(
    "\nSaved: residual_limb_analysis.json"
)