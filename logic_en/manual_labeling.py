import os
import cv2
import numpy as np
import pandas as pd
from scipy import ndimage
from scipy.ndimage import gaussian_filter1d


mouse_state = {'x': 0, 'y': 0, 'selected': None}


def load_image(image_path, is_mask=False):
    """Read an 8-bit grayscale image; optionally threshold it as a mask."""
    img = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(f"Failed to load image: {image_path}")
    if is_mask:
        _, img = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY)
    return img


def adjust_contrast(image, saturation_percent=0.5):
    """Stretch contrast using smoothed histogram percentiles."""
    max_possible = 65535 if image.dtype == np.uint16 else 255
    min_val, max_val = np.min(image), np.max(image)
    if max_val == min_val:
        return image.copy()

    hist, _ = np.histogram(image.flatten(), bins=256 if max_possible == 255 else 65536, range=[0, max_possible + 1])
    cum_hist = np.cumsum(gaussian_filter1d(hist.astype(float), sigma=1))

    total_pixels = image.size
    lower_limit = total_pixels * (saturation_percent / 100.0)
    upper_limit = total_pixels * (1 - saturation_percent / 100.0)

    min_gray = np.searchsorted(cum_hist, lower_limit)
    max_gray = np.searchsorted(cum_hist, upper_limit)

    if min_gray >= max_gray:
        min_gray, max_gray = min_val, max_val

    adjusted = np.zeros_like(image, dtype=np.float32)
    mask_val = (image > min_gray) & (image < max_gray)
    adjusted[mask_val] = (image[mask_val] - min_gray) * 255.0 / (max_gray - min_gray)
    adjusted[image <= min_gray] = 0
    adjusted[image >= max_gray] = 255

    return np.clip(adjusted, 0, 255).astype(np.uint8)


def extract_components(masked_image, mask):
    """Extract component patches, bounding boxes, and display coordinates."""
    labeled, num_features = ndimage.label(mask > 0)
    components = []

    for i, region in enumerate(ndimage.find_objects(labeled), start=1):
        if region is None:
            continue
        ys, xs = region
        y_min, y_max = ys.start, ys.stop - 1
        x_min, x_max = xs.start, xs.stop - 1
        radius = max(x_max - x_min, y_max - y_min) // 2 + 10

        components.append({
            'id': i,
            'image': masked_image[y_min:y_max + 1, x_min:x_max + 1].copy(),
            'center': ((x_min + x_max) // 2, (y_min + y_max) // 2),
            'radius': radius,
            'bounding_box': (x_min, x_max, y_min, y_max),
            'label': None
        })

    return components


def generate_grid_context(center_comp, components, image, shape):
    """Assemble a 3x3 patch from the target well and nearby components."""
    cx, cy = center_comp['center']
    x_min, x_max, y_min, y_max = center_comp['bounding_box']
    grid_size = max(x_max - x_min + 1, y_max - y_min + 1)
    h, w = shape

    grid = [[None] * 3 for _ in range(3)]
    grid[1][1] = center_comp['image']

    offsets = [(-1, -1), (-1, 0), (-1, 1),
               (0, -1), (0, 1),
               (1, -1), (1, 0), (1, 1)]

    for dy, dx in offsets:
        tx, ty = cx + dx * grid_size, cy + dy * grid_size


        nearest = min(
            (c for c in components if c['id'] != center_comp['id']),
            key=lambda c: (tx - c['center'][0]) ** 2 + (ty - c['center'][1]) ** 2,
            default=None
        )

        dist_sq = (tx - nearest['center'][0]) ** 2 + (ty - nearest['center'][1]) ** 2 if nearest else float('inf')


        if nearest and dist_sq < (grid_size * 1.5) ** 2:
            grid[1 + dy][1 + dx] = nearest['image']
        else:
            mx = -tx if tx < 0 else (2 * w - tx - 1 if tx >= w else cx)
            my = -ty if ty < 0 else (2 * h - ty - 1 if ty >= h else cy)

            mx_min, mx_max = max(0, mx - grid_size // 2), min(w, mx + grid_size // 2 + 1)
            my_min, my_max = max(0, my - grid_size // 2), min(h, my + grid_size // 2 + 1)

            grid[1 + dy][1 + dx] = image[my_min:my_max, mx_min:mx_max]


    unified_grid = np.zeros((3 * grid_size, 3 * grid_size), dtype=np.uint8)
    for i in range(3):
        for j in range(3):
            img = grid[i][j]
            if img is None:
                img = np.zeros((grid_size, grid_size), dtype=np.uint8)
            elif img.shape != (grid_size, grid_size):
                try:
                    img = cv2.resize(img, (grid_size, grid_size), interpolation=cv2.INTER_AREA)
                except cv2.error:
                    img = np.zeros((grid_size, grid_size), dtype=np.uint8)

            unified_grid[i * grid_size:(i + 1) * grid_size, j * grid_size:(j + 1) * grid_size] = img

    return unified_grid


def component_at(components, x, y):
    """Choose the closest well when selection circles overlap."""
    nearest = min(
        components,
        key=lambda c: (x - c['center'][0]) ** 2 + (y - c['center'][1]) ** 2,
        default=None,
    )
    if nearest is not None:
        cx, cy = nearest['center']
        if (x - cx) ** 2 + (y - cy) ** 2 <= nearest['radius'] ** 2:
            return nearest
    return None


def mouse_callback(event, x, y, flags, param):
    mouse_state['x'], mouse_state['y'] = x, y
    if event == cv2.EVENT_LBUTTONDOWN:
        mouse_state['selected'] = component_at(param['components'], x, y)


def window_is_open(name):
    try:
        return cv2.getWindowProperty(name, cv2.WND_PROP_VISIBLE) >= 1
    except cv2.error:
        return False


def close_window(name):
    if name is not None:
        try:
            cv2.destroyWindow(name)
        except cv2.error:
            pass


def run_labeling(image_path, mask_path, output_dir, custom_csv_path=""):
    """Label selected wells and append patch metadata to CSV."""
    os.makedirs(output_dir, exist_ok=True)

    try:
        image_name = os.path.splitext(os.path.basename(image_path))[0]
        masked_img = adjust_contrast(load_image(image_path))
        mask = load_image(mask_path, is_mask=True)
        if masked_img.shape != mask.shape:
            raise ValueError(f"Image/mask size mismatch: {masked_img.shape} vs {mask.shape}")
        masked_img[mask == 0] = 0

        print("Extracting microwells...", flush=True)
        components = extract_components(masked_img, mask)
        if not components:
            raise ValueError("No microwells found in the mask.")
        print(f"Found {len(components)} microwells. Opening labeling window...", flush=True)
    except Exception as e:
        print(f"Initialization error: {e}")
        return

    mouse_state.update(x=-10000, y=-10000, selected=None)
    window_name = "Labeling Mode (Press 'q' to exit)"
    preview_win = None
    active_comp = None
    grid_img = None
    labels = []

    # Draw overlays on a display copy; saved patches remain grayscale.
    base_display = cv2.cvtColor(masked_img, cv2.COLOR_GRAY2BGR)
    print("\n[Interactive Labeling Started]")
    print("Click a well; press 0 (Empty), 1 (Bead), or q/Esc (Cancel preview).")
    print("Closing the preview cancels selection. Close the main window to save and exit.")

    try:
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.imshow(window_name, base_display)
        cv2.setMouseCallback(window_name, mouse_callback, {'components': components})

        while True:
            display_img = base_display.copy()
            for comp in components:
                if comp['label'] is not None:
                    color = (0, 255, 0) if comp['label'] == "empty" else (0, 0, 255)
                    cv2.circle(display_img, comp['center'], comp['radius'], color, 2, cv2.LINE_AA)

            hovered = component_at(components, mouse_state['x'], mouse_state['y'])
            for comp in (hovered, active_comp):
                if comp is not None:
                    cv2.circle(display_img, comp['center'], comp['radius'],
                               (255, 255, 255), 2, cv2.LINE_4)
            cv2.imshow(window_name, display_img)
            key = cv2.waitKey(20) & 0xFF

            if not window_is_open(window_name):
                break
            if preview_win is not None and not window_is_open(preview_win):
                close_window(preview_win)
                preview_win = active_comp = grid_img = None
                mouse_state['selected'] = None
                continue

            selected = mouse_state['selected']
            mouse_state['selected'] = None
            if selected is not None:
                close_window(preview_win)
                active_comp = selected
                grid_img = generate_grid_context(selected, components, masked_img, masked_img.shape)
                preview_win = f"Component Preview [ID: {selected['id']}]"
                cv2.namedWindow(preview_win, cv2.WINDOW_NORMAL)
                cv2.imshow(preview_win, grid_img)
                cv2.resizeWindow(preview_win, 360, 360)
                continue

            if active_comp is not None:
                if key in (ord('0'), ord('1')):
                    label_str = "empty" if key == ord('0') else "bead"
                    out_name = f"{image_name}_comp{active_comp['id']:03d}_{label_str}_3x3.tif"
                    out_path = os.path.join(output_dir, out_name)
                    ok, encoded = cv2.imencode('.tif', grid_img)
                    if not ok:
                        raise OSError(f"Failed to encode patch: {out_path}")
                    encoded.tofile(out_path)
                    active_comp['label'] = label_str
                    labels = [row for row in labels if row['component_id'] != active_comp['id']]
                    labels.append({
                        "image_path": image_path, "component_id": active_comp['id'],
                        "label": label_str, "output_path": out_path,
                        "center_x": active_comp['center'][0], "center_y": active_comp['center'][1],
                    })
                    print(f"Registered -> Component {active_comp['id']}: [{label_str}]")
                elif key not in (ord('q'), 27):
                    continue
                close_window(preview_win)
                preview_win = active_comp = grid_img = None
            elif key in (ord('q'), 27):
                break
    finally:
        close_window(preview_win)
        close_window(window_name)
        mouse_state.update(x=-10000, y=-10000, selected=None)
        save_labels(labels, output_dir, custom_csv_path)


def save_labels(labels, output_dir, custom_csv_path=""):
    """Save completed annotations when the session ends."""
    if labels:
        csv_path = custom_csv_path if custom_csv_path else os.path.join(output_dir, "labels.csv")
        df = pd.DataFrame(labels)

        try:
            os.makedirs(os.path.dirname(os.path.abspath(csv_path)), exist_ok=True)
            if os.path.exists(csv_path):
                pd.concat([pd.read_csv(csv_path), df], ignore_index=True).to_csv(csv_path, index=False)
            else:
                df.to_csv(csv_path, index=False)
            print(f"Exported {len(labels)} label records to {csv_path}")
        except Exception as e:
            fallback = os.path.join(output_dir, "labels_new.csv")
            df.to_csv(fallback, index=False)
            print(f"Primary export failed. Saved to fallback location: {fallback}")


if __name__ == "__main__":
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    try:
        image_path = filedialog.askopenfilename(title="Select balanced brightfield image (bri_sol)")
        mask_path = filedialog.askopenfilename(title="Select corresponding all-well mask") if image_path else ""
        output_dir = filedialog.askdirectory(title="Select dataset output folder") if mask_path else ""
    finally:
        root.destroy()
    if image_path and mask_path and output_dir:
        run_labeling(image_path, mask_path, output_dir)