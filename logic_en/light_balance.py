import cv2
import numpy as np
import os


def adjust_illumination(image):
    """Apply local brightness scaling, gamma correction, and CLAHE."""
    height, width = image.shape
    normalized_img = cv2.normalize(image, None, 0, 255, cv2.NORM_MINMAX)

    blurred_img = cv2.GaussianBlur(normalized_img.astype(float), (51, 51), 0)
    _, _, _, max_loc = cv2.minMaxLoc(blurred_img)

    region_h, region_w = height // 4, width // 4
    y_start, y_end = max(0, max_loc[1] - region_h), min(height, max_loc[1] + region_h)
    x_start, x_end = max(0, max_loc[0] - region_w), min(width, max_loc[0] + region_w)

    target_brightness = np.mean(normalized_img[y_start:y_end, x_start:x_end])

    local_brightness = cv2.GaussianBlur(normalized_img.astype(float), (51, 51), 0)
    adjustment_factor = cv2.GaussianBlur(target_brightness / (local_brightness + 1e-6), (51, 51), 0)

    adjusted_img = np.clip(normalized_img.astype(float) * adjustment_factor, 0, 255)


    gamma_corrected = np.power(adjusted_img / 255.0, 0.5) * 255.0
    gamma_corrected = gamma_corrected.astype(np.uint8)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gamma_corrected)


def process_directory(input_dir, output_dir):
    """Balance TIFF images in one directory."""
    os.makedirs(output_dir, exist_ok=True)

    tiff_files = [f for f in os.listdir(input_dir) if f.lower().endswith(('.tif', '.tiff'))]
    if not tiff_files:
        return

    for filename in tiff_files:
        input_path = os.path.join(input_dir, filename)
        output_filename = f"{os.path.splitext(filename)[0]}_sol.tif"
        output_path = os.path.join(output_dir, output_filename)

        img = cv2.imread(input_path, cv2.IMREAD_GRAYSCALE)
        if img is not None:
            cv2.imwrite(output_path, adjust_illumination(img))


def run_balance(bri_dir):
    """Balance brightfield images recursively and save them under bri_sol."""
    if not bri_dir or not os.path.exists(bri_dir):
        raise FileNotFoundError(f"Directory not found: {bri_dir}")

    output_base_dir = os.path.join(os.path.dirname(bri_dir), 'bri_sol')
    print(f"Starting illumination balance...\nInput: {bri_dir}\nOutput: {output_base_dir}")

    processed_folders = 0
    for root, _, files in os.walk(bri_dir):
        if any(f.lower().endswith(('.tif', '.tiff')) for f in files):
            rel_path = os.path.relpath(root, bri_dir)
            process_directory(root, os.path.join(output_base_dir, rel_path))
            processed_folders += 1

    print(f"Illumination balance complete. Processed {processed_folders} directories.")
