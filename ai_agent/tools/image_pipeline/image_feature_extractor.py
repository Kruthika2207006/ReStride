import numpy as np
import os


def extract_features(image_path):
    import cv2


    img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)

    if img is None:
        raise ValueError("Unable to load image")

    if len(img.shape) == 3 and img.shape[2] == 4:
        alpha = img[:, :, 3]
        mask = (alpha > 0).astype(np.uint8) * 255
    else:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Try Otsu's thresholding (Inverted for light background)
        _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        # If mask is mostly empty or solid, try non-inverted Otsu (for dark background)
        if np.sum(mask == 255) < mask.size * 0.05 or np.sum(mask == 255) > mask.size * 0.95:
            _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Pad mask with a 2-pixel black border to ensure contours are successfully closed and captured
    mask[0:2, :] = 0
    mask[-2:, :] = 0
    mask[:, 0:2] = 0
    mask[:, -2:] = 0

    contours, _ = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    if len(contours) == 0:
        raise ValueError("No contour found")

    largest = max(contours, key=cv2.contourArea)

    contour_area = float(cv2.contourArea(largest))
    contour_perimeter = float(cv2.arcLength(largest, True))

    x, y, w, h = cv2.boundingRect(largest)

    ys, xs = np.where(mask > 0)

    top = ys.min()
    bottom = ys.max()

    height = bottom - top

    slice_profile = []

    for i in range(10):

        y_slice = int(
            top + ((i + 0.5) / 10) * height
        )

        band = mask[
            max(0, y_slice - 2):
            min(mask.shape[0], y_slice + 3),
            :
        ]

        pixels = np.where(band > 0)[1]

        if len(pixels) > 0:
            width = int(
                pixels.max() - pixels.min()
            )
        else:
            width = 0

        slice_profile.append(width)

    valid_widths = [
        w for w in slice_profile if w > 0
    ]

    top_width = valid_widths[0]
    bottom_width = valid_widths[-1]

    ratio = top_width / max(bottom_width, 1)

    if ratio > 1.8:
        shape_type = "Conical"
    elif ratio > 1.3:
        shape_type = "Balanced"
    else:
        shape_type = "Bulbous"

    return {
        "image_name": os.path.basename(image_path),
        "contour_area": contour_area,
        "contour_perimeter": contour_perimeter,
        "bounding_box_width": w,
        "bounding_box_height": h,
        "top_width": top_width,
        "bottom_width": bottom_width,
        "width_ratio": round(ratio, 3),
        "shape_type": shape_type,
        "slice_profile": slice_profile
    }


if __name__ == "__main__":

    import json

    image_path = input(
        "Enter image path: "
    ).strip().strip('"')

    features = extract_features(image_path)

    print(
        json.dumps(
            features,
            indent=4
        )
    )