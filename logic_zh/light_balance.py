import cv2
import numpy as np
import os


def adjust_illumination_brightest(img):
    """依次进行局部亮度缩放、伽马校正和 CLAHE。"""
    height, width = img.shape
    normalized_img = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX)

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


def process_single_folder(input_dir, output_dir):
    """对单个目录中的 TIFF 图像进行光照校正。"""
    os.makedirs(output_dir, exist_ok=True)

    tiff_files = [f for f in os.listdir(input_dir) if f.lower().endswith(('.tif', '.tiff'))]
    if not tiff_files:
        print(f"文件夹 {input_dir} 中没有 TIFF 文件")
        return

    print(f"处理文件夹: {input_dir}")

    for filename in tiff_files:
        input_path = os.path.join(input_dir, filename)
        output_filename = f"{os.path.splitext(filename)[0]}_sol.tif"
        output_path = os.path.join(output_dir, output_filename)

        img = cv2.imread(input_path, cv2.IMREAD_GRAYSCALE)
        if img is not None:
            cv2.imwrite(output_path, adjust_illumination_brightest(img))
        else:
            print(f"无法读取 {filename}，跳过")


def run_balance(bri_folder):
    """递归校正明场图像并保存至 bri_sol。"""
    if not bri_folder or not os.path.exists(bri_folder):
        print("错误：明场文件夹不存在。")
        return

    output_base_folder = os.path.join(os.path.dirname(bri_folder), 'bri_sol')
    print(f"开始光场平衡处理...\n输入: {bri_folder}\n输出: {output_base_folder}")

    processed_count = 0
    for root, _, files in os.walk(bri_folder):
        if any(f.lower().endswith(('.tif', '.tiff')) for f in files):
            relative_path = os.path.relpath(root, bri_folder)
            process_single_folder(root, os.path.join(output_base_folder, relative_path))
            processed_count += 1

    print(f"光场平衡完成，共处理了 {processed_count} 个文件夹。")
