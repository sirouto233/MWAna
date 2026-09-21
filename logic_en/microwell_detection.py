import cv2
import numpy as np
import os
from pathlib import Path


def detect_micropit_centers(image_path):
    """Return rounded microwell centers detected by the Hough circle transform."""
    image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        return np.array([])

    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(image)
    blurred = cv2.GaussianBlur(enhanced, (5, 5), 0)

    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1,
        minDist=20,
        param1=30,
        param2=14,
        minRadius=6,
        maxRadius=10
    )

    if circles is not None:
        return np.uint16(np.around(circles))[0, :, :2]
    return np.array([])


def generate_mask(image_path, centers, output_path, diameter=16):
    """Draw fixed-diameter disks around detected centers."""
    image = cv2.imread(str(image_path))
    if image is None or len(centers) == 0:
        return False

    height, width = image.shape[:2]
    mask = np.zeros((height, width), dtype=np.uint8)
    radius = diameter // 2

    for x, y in centers:
        if 0 <= x < width and 0 <= y < height:
            cv2.circle(mask, (x, y), radius, 255, -1)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cv2.imwrite(str(output_path), mask)
    return True


def run_detection(input_dir, output_dir=None):
    """Detect wells in _sol.tif images and save binary masks."""
    input_path = Path(input_dir)
    if not input_path.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    output_path = Path(output_dir) if output_dir else input_path.parent / "bri_mask"
    print(f"Starting microwell detection...\nInput: {input_path}\nOutput: {output_path}")

    processed_count = 0
    for root, _, files in os.walk(input_path):
        for file in files:
            if not file.endswith("_sol.tif"):
                continue

            img_path = Path(root) / file
            rel_path = img_path.relative_to(input_path)

            mask_filename = rel_path.name.replace("_sol.tif", "_mask.tif")
            mask_path = output_path / rel_path.parent / mask_filename

            centers = detect_micropit_centers(img_path)
            if len(centers) > 0:
                generate_mask(img_path, centers, mask_path)
                print(f"Generated mask: {file} ({len(centers)} wells)")
                processed_count += 1
            else:
                print(f"No microwells detected: {file}")

    print(f"Detection complete. Generated {processed_count} masks.")
