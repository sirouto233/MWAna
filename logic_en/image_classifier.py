import os
import shutil

def organize_images(source_dir, stop_event=None):
    """Copy -1/-2 TIFFs to sibling bri/flu folders; return both paths or (None, None) on cancellation."""
    if not source_dir or not os.path.exists(source_dir):
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    parent_dir = os.path.dirname(source_dir)
    bri_dir = os.path.join(parent_dir, "bri")
    flu_dir = os.path.join(parent_dir, "flu")

    os.makedirs(bri_dir, exist_ok=True)
    os.makedirs(flu_dir, exist_ok=True)

    print(f"Starting image organization...\nSource: {source_dir}\nBrightfield: {bri_dir}\nFluorescence: {flu_dir}")

    processed_count = 0

    for root, _, files in os.walk(source_dir):

        # Skip output directories during traversal.
        if root.startswith((bri_dir, flu_dir)):
            continue

        for file in files:
            if stop_event and stop_event.is_set():
                print("Operation aborted by user.")
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

            processed_count += 1

    print(f"Organization complete. Processed {processed_count} files.")
    return bri_dir, flu_dir
