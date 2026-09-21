import os
import shutil


def organize_images(source_dir, stop_event=None):
    """按 -1/-2 后缀复制 TIFF 至同级 bri/flu；返回两目录路径，中止时返回 (None, None)。"""
    if not source_dir or not os.path.exists(source_dir):
        raise FileNotFoundError("源文件夹不存在")

    parent_dir = os.path.dirname(source_dir)
    bri_dir = os.path.join(parent_dir, "bri")
    flu_dir = os.path.join(parent_dir, "flu")

    os.makedirs(bri_dir, exist_ok=True)
    os.makedirs(flu_dir, exist_ok=True)

    print(f"开始分类图像...\n源: {source_dir}\n目标: {bri_dir} & {flu_dir}")

    processed_count = 0

    for root, _, files in os.walk(source_dir):

        # 遍历时跳过输出目录。
        if root.startswith((bri_dir, flu_dir)):
            continue

        for file in files:
            if stop_event and stop_event.is_set():
                print("用户中止了图像分类操作。")
                return None, None

            if not file.lower().endswith(('.tif', '.tiff')):
                continue

            source_path = os.path.join(root, file)
            relative_path = os.path.relpath(root, source_dir)
            target_dir = None

            if file.lower().endswith(('-1.tif', '-1.tiff')):
                target_dir = os.path.join(bri_dir, relative_path)
            elif file.lower().endswith(('-2.tif', '-2.tiff')):
                target_dir = os.path.join(flu_dir, relative_path)

            if target_dir:
                os.makedirs(target_dir, exist_ok=True)
                target_path = os.path.join(target_dir, file)
                shutil.copy2(source_path, target_path)
                print(f"复制: {file}")

            processed_count += 1

    print("图像分类整理完成！")
    return bri_dir, flu_dir
