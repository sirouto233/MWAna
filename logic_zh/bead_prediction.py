import os
import csv
import time

from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing

import cv2

# 限制批量预测时 OpenCV 的内部并行度。
cv2.setNumThreads(1)
import numpy as np
import torch
import torch.nn.functional as F
from scipy.ndimage import gaussian_filter1d
from scipy.spatial import cKDTree
import timm


BATCH_SIZE = 32
CONFIDENCE_THRESHOLD = 0.5
MODEL_NAME = 'swin_tiny_patch4_window7_224'


def adjust_contrast(image, saturation_percent=0.5):
    """根据平滑直方图分位点拉伸对比度。"""
    max_possible = 65535 if image.dtype == np.uint16 else 255
    min_val, max_val = np.min(image), np.max(image)
    if max_val == min_val:
        return image.copy()

    hist_src = image.flatten()[::4] if image.size > 5000000 else image.flatten()
    hist, _ = np.histogram(hist_src, bins=256 if max_possible == 255 else 65536, range=[0, max_possible + 1])

    hist_smooth = gaussian_filter1d(hist.astype(float), sigma=1)
    cum_hist = np.cumsum(hist_smooth)

    total = hist_src.size
    low_th = total * (saturation_percent / 100)
    high_th = total * (1 - saturation_percent / 100)

    min_gray = np.searchsorted(cum_hist, low_th)
    max_gray = np.searchsorted(cum_hist, high_th)

    if min_gray >= max_gray:
        min_gray, max_gray = min_val, max_val

    adjusted = np.zeros_like(image, dtype=np.float32)
    np.clip((image - min_gray) * (255.0 / (max_gray - min_gray + 1e-6)), 0, 255, out=adjusted)
    adjusted[image <= min_gray] = 0
    adjusted[image >= max_gray] = 255

    return adjusted.astype(np.uint8)


class StitchingProcessor:
    """构建 3x3 邻域图，并施加固定径向亮度权重。"""

    def __init__(self, masked_image, components, kd_tree):
        self.masked_image = masked_image
        self.components = components
        self.tree = kd_tree
        self.h, self.w = masked_image.shape
        self.mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
        self.std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)


        # 固定径向权重，不属于可学习注意力层。
        x = np.linspace(-1, 1, 224)
        y = np.linspace(-1, 1, 224)
        xx, yy = np.meshgrid(x, y)
        r = np.sqrt(xx ** 2 + yy ** 2)
        self.vignette = np.clip(np.exp(-(r ** 2) / (2 * 1.2 ** 2)), 0.6, 1.0).astype(np.float32)

    def get_3x3_grid(self, center_idx):
        center_comp = self.components[center_idx]
        center_x, center_y = center_comp['center']
        grid_size = center_comp['grid_size']

        unified_grid = np.zeros((3 * grid_size, 3 * grid_size), dtype=np.uint8)

        c_img = center_comp['image']
        if c_img.shape != (grid_size, grid_size):
            try:
                c_img = cv2.resize(c_img, (grid_size, grid_size), interpolation=cv2.INTER_AREA)
            except cv2.error:
                c_img = np.zeros((grid_size, grid_size), dtype=np.uint8)
        unified_grid[grid_size:2 * grid_size, grid_size:2 * grid_size] = c_img

        offsets = [(-1, -1), (-1, 0), (-1, 1),
                   (0, -1), (0, 1),
                   (1, -1), (1, 0), (1, 1)]
        grid_coords = [(0, 0), (0, 1), (0, 2), (1, 0), (1, 2), (2, 0), (2, 1), (2, 2)]
        search_radius = grid_size * 1.5

        for idx, (dy, dx) in enumerate(offsets):
            gy, gx = grid_coords[idx]
            target_x = center_x + dx * grid_size
            target_y = center_y + dy * grid_size

            if hasattr(self, 'neighbor_cache'):
                neighbor_idx = self.neighbor_cache[center_idx, idx]
            else:
                _, neighbor_idx = self.tree.query([target_x, target_y], k=1, distance_upper_bound=search_radius)
            img_to_fill = None

            if neighbor_idx < len(self.components) and self.components[neighbor_idx]['id'] != center_comp['id']:
                img_to_fill = self.components[neighbor_idx]['image']
            else:
                mirror_x = -target_x if target_x < 0 else (
                    2 * self.w - target_x - 1 if target_x >= self.w else center_x)
                mirror_y = -target_y if target_y < 0 else (
                    2 * self.h - target_y - 1 if target_y >= self.h else center_y)

                mx_min, mx_max = max(0, int(mirror_x - grid_size // 2)), min(self.w, int(mirror_x + grid_size // 2 + 1))
                my_min, my_max = max(0, int(mirror_y - grid_size // 2)), min(self.h, int(mirror_y + grid_size // 2 + 1))

                if mx_max > mx_min and my_max > my_min:
                    img_to_fill = self.masked_image[my_min:my_max, mx_min:mx_max]

            if img_to_fill is not None and img_to_fill.shape[0] > 0 and img_to_fill.shape[1] > 0:
                if img_to_fill.shape != (grid_size, grid_size):
                    try:
                        img_to_fill = cv2.resize(img_to_fill, (grid_size, grid_size), interpolation=cv2.INTER_AREA)
                    except cv2.error:
                        continue
                unified_grid[gy * grid_size:(gy + 1) * grid_size, gx * grid_size:(gx + 1) * grid_size] = img_to_fill

        return cv2.resize(unified_grid, (224, 224), interpolation=cv2.INTER_LINEAR)

    def process_uint8_batch(self, indices):
        patches = np.empty((len(indices), 224, 224), dtype=np.uint8)
        for row, idx in enumerate(indices):
            patch = self.get_3x3_grid(idx)
            patches[row] = (patch.astype(np.float32) * self.vignette).astype(np.uint8)
        return torch.from_numpy(patches) if len(indices) else None

    def process_batch(self, indices):
        tensors = []
        for idx in indices:
            img_numpy = self.get_3x3_grid(idx)
            img_numpy = (img_numpy.astype(np.float32) * self.vignette).astype(np.uint8)
            tensors.append(img_numpy)

        if not tensors:
            return None

        batch_tensor = torch.from_numpy(np.stack(tensors)).float().div(255.0)
        batch_tensor = batch_tensor.unsqueeze(1).expand(-1, 3, -1, -1)
        return (batch_tensor - self.mean) / self.std



def prepare_neighbor_cache(processor):
    """Batch queries by radius while retaining the original k=1 selection."""
    offsets = np.array([(-1, -1), (0, -1), (1, -1),
                        (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)])
    centers = np.array([c['center'] for c in processor.components])
    sizes = np.array([c['grid_size'] for c in processor.components])
    neighbors = np.empty((len(sizes), 8), dtype=np.intp)
    for size in np.unique(sizes):
        indices = np.flatnonzero(sizes == size)
        targets = centers[indices, None, :] + offsets[None, :, :] * size
        _, found = processor.tree.query(targets.reshape(-1, 2), k=1,
                                        distance_upper_bound=float(size) * 1.5)
        neighbors[indices] = found.reshape(-1, 8)
    processor.neighbor_cache = neighbors


def normalization_table(processor, device):
    """Use the original CPU float32 arithmetic for all 256 input levels."""
    values = torch.arange(256, dtype=torch.float32).div(255.0).view(256, 1, 1, 1)
    values = values.expand(-1, 3, -1, -1)
    return ((values - processor.mean) / processor.std).view(256, 3).to(device)


def prepare_batches(processor, batches, fast, prefetch, pin_memory, stop_event):
    """Keep at most one future batch in a worker; always join it on exit."""
    def build(indices):
        if stop_event and stop_event.is_set():
            raise InterruptedError('Stopped by user')
        started = time.perf_counter()
        tensor = (processor.process_uint8_batch(indices) if fast
                  else processor.process_batch(indices))
        if tensor is not None and pin_memory:
            tensor = tensor.pin_memory()
        return tensor, time.perf_counter() - started

    if not prefetch:
        for indices in batches:
            tensor, seconds = build(indices)
            yield indices, tensor, seconds
        return

    with ThreadPoolExecutor(max_workers=1, thread_name_prefix='microwell-patches') as pool:
        iterator = iter(batches)
        indices = next(iterator, None)
        if indices is None:
            return
        pending = pool.submit(build, indices)
        while indices is not None:
            tensor, seconds = pending.result()
            next_indices = next(iterator, None)
            if next_indices is not None:
                pending = pool.submit(build, next_indices)
            yield indices, tensor, seconds
            indices = next_indices


def load_weights(model, weight_path, device):
    """使用现有 Swin 键名映射加载权重。"""
    print(f"正在加载权重: {weight_path}")
    checkpoint = torch.load(weight_path, map_location=device)
    state_dict = checkpoint.get('model', checkpoint.get('state_dict', checkpoint))

    new_state_dict = OrderedDict()
    for k, v in state_dict.items():
        name = k.replace('module.', '')
        if 'downsample' in name and 'layers.0.downsample' in name:
            parts = name.split('.')
            if parts[0] == 'layers' and parts[2] == 'downsample':
                try:
                    name = f"layers.{int(parts[1]) + 1}.{'.'.join(parts[2:])}"
                except ValueError:
                    pass
        new_state_dict[name] = v

    model.load_state_dict(new_state_dict, strict=False)
    return model


def run_prediction(image_dir, mask_dir, model_path, output_dir=None, stop_event=None, batch_size=None):
    """对微坑图块进行分类并保存含磁珠微坑掩码。"""
    batch_size = int(os.environ.get('MWBEAD_BATCH_SIZE', BATCH_SIZE)) if batch_size is None else int(batch_size)
    if batch_size <= 0:
        raise ValueError('batch_size must be positive')
    profile = os.environ.get('MWBEAD_PROFILE', '1') != '0'
    fast = os.environ.get('MWBEAD_FAST', '1') != '0'
    prefetch = fast and os.environ.get('MWBEAD_PREFETCH', '1') != '0'
    pin_memory = fast and torch.cuda.is_available() and os.environ.get('MWBEAD_PIN_MEMORY', '1') != '0'
    benchmark = os.environ.get('MWBEAD_CUDNN_BENCHMARK', '0') == '1'
    thread_count = os.environ.get('MWBEAD_TORCH_THREADS')
    if thread_count is not None:
        if int(thread_count) <= 0:
            raise ValueError('MWBEAD_TORCH_THREADS must be positive')
        torch.set_num_threads(int(thread_count))
    model_start = time.perf_counter()
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(image_dir), "bri_bead")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if torch.cuda.is_available():
        torch.backends.cudnn.benchmark = benchmark

    print(f"🚀 预测启动 | Device: {device}")

    try:
        model = timm.create_model(MODEL_NAME, pretrained=False, num_classes=2)
        model = load_weights(model, model_path, device)
        model.eval().to(device)
    except Exception as e:
        print(f"❌ 模型加载失败: {e}")
        return

    if device.type == 'cuda':
        torch.cuda.synchronize()
    model_load_s = time.perf_counter() - model_start
    os.makedirs(output_dir, exist_ok=True)
    timing_fields = ['Image', 'Wells', 'Bead Wells', 'Batch Size', 'Device', 'Model Setup s',
                     'Read and Components s', 'Patches and CPU Normalize s',
                     'Transfer Forward and Return Wall s', 'Forward GPU Event s',
                     'Mask Lookup s', 'Write s', 'Total Image s', 'Peak Allocated MiB',
                     'Profile Enabled', 'Fast Path', 'Prefetch', 'Pinned Memory',
                     'cuDNN Benchmark', 'Torch Threads', 'Batch Wait s', 'Neighbor Cache s',
                     'Normalize Setup s']
    timing_path = os.path.join(output_dir, f"prediction_timing_{time.time_ns()}.csv")
    with open(timing_path, 'w', newline='', encoding='utf-8-sig') as stream:
        csv.writer(stream).writerow(timing_fields)

    image_files = [
        os.path.relpath(os.path.join(root, file), image_dir)
        for root, _, files in os.walk(image_dir)
        for file in files if file.endswith('_sol.tif') or (file.endswith('.tif') and 'mask' not in file)
    ]

    total_files = len(image_files)
    print(f"待处理文件数: {total_files}")

    for i, image_rel_path in enumerate(image_files):
        if stop_event and stop_event.is_set():
            print("🛑 预测进程接收到中止信号，正在退出...")
            raise InterruptedError("Stopped by user")


        try:
            if device.type == 'cuda':
                torch.cuda.reset_peak_memory_stats(device)
            image_start = time.perf_counter()
            patch_s = gpu_wall_s = forward_s = batch_wait_s = 0.0
            base_name = os.path.splitext(image_rel_path)[0].replace('_sol', '')
            image_path = os.path.join(image_dir, image_rel_path)

            mask_path = next((os.path.join(mask_dir, f"{base_name}{ext}")
                              for ext in ['_mask.tif', '_mask.jpg']
                              if os.path.exists(os.path.join(mask_dir, f"{base_name}{ext}"))), None)

            if not mask_path:
                print(f"跳过无Mask文件: {base_name}")
                continue

            img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
            if img is None or mask is None:
                continue

            _, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
            masked_img = adjust_contrast(img)
            masked_img[mask == 0] = 0

            num, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
            valid_ids = np.where((stats[:, cv2.CC_STAT_WIDTH] > 0) & (stats[:, cv2.CC_STAT_AREA] > 10))[0]
            valid_ids = valid_ids[valid_ids != 0]

            if len(valid_ids) == 0:
                continue

            components, component_coords = [], []
            for comp_idx in valid_ids:
                x, y, w, h = stats[comp_idx, :4]
                cx, cy = int(centroids[comp_idx][0]), int(centroids[comp_idx][1])
                grid_size = max(w, h)
                components.append({
                    'id': comp_idx, 'center': (cx, cy),
                    'bbox': (x, x + w, y, y + h),
                    'image': masked_img[y:y + h, x:x + w], 'grid_size': grid_size
                })
                component_coords.append((cx, cy))

            tree = cKDTree(component_coords)
            processor = StitchingProcessor(masked_img, components, tree)
            cache_start = time.perf_counter()
            if fast:
                prepare_neighbor_cache(processor)
            cache_s = time.perf_counter() - cache_start
            normalize_start = time.perf_counter()
            table = normalization_table(processor, device) if fast else None
            if fast and device.type == 'cuda':
                torch.cuda.synchronize()
            normalize_setup_s = time.perf_counter() - normalize_start
            batches = np.array_split(np.arange(len(components)), np.ceil(len(components) / batch_size))

            label_lookup = np.zeros(num, dtype=np.uint8)
            prepare_s = time.perf_counter() - image_start
            bead_count = 0
            use_amp = torch.cuda.is_available()

            with closing(prepare_batches(processor, batches, fast, prefetch,
                                         pin_memory, stop_event)) as prepared:
                wait_start = time.perf_counter()
                for batch_indices, batch_tensors, build_s in prepared:
                    batch_wait_s += time.perf_counter() - wait_start
                    patch_s += build_s
                    if stop_event and stop_event.is_set():
                        raise InterruptedError('Stopped by user')
                    if batch_tensors is None:
                        wait_start = time.perf_counter()
                        continue
                    gpu_start = time.perf_counter()
                    batch_tensors = batch_tensors.to(device, non_blocking=True)
                    if fast:
                        batch_tensors = table[batch_tensors.long()].permute(0, 3, 1, 2).contiguous()
                    if use_amp and profile:
                        event_start = torch.cuda.Event(enable_timing=True)
                        event_end = torch.cuda.Event(enable_timing=True)
                        event_start.record()

                    with torch.inference_mode():
                        if use_amp:
                            with torch.amp.autocast('cuda'):
                                outputs = model(batch_tensors)
                        else:
                            outputs = model(batch_tensors)

                        if use_amp and profile:
                            event_end.record()
                        probs = F.softmax(outputs, dim=1)[:, 1]
                        preds_cpu = (probs > CONFIDENCE_THRESHOLD).cpu().numpy()

                    gpu_wall_s += time.perf_counter() - gpu_start
                    if use_amp and profile:
                        forward_s += event_start.elapsed_time(event_end) / 1000.0

                    for comp_idx, is_bead in zip(batch_indices, preds_cpu):
                        if is_bead:
                            label_lookup[components[comp_idx]['id']] = 255
                            bead_count += 1

                    del batch_tensors, outputs, probs, preds_cpu
                    wait_start = time.perf_counter()


            stage_start = time.perf_counter()
            bead_regions = label_lookup[labels]
            mask_s = time.perf_counter() - stage_start
            stage_start = time.perf_counter()
            output_path = os.path.join(output_dir, f"{base_name}_bead.tif")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            if not cv2.imwrite(output_path, bead_regions):
                raise OSError(f'Failed to write mask: {output_path}')
            write_s = time.perf_counter() - stage_start
            total_s = time.perf_counter() - image_start
            peak_mib = torch.cuda.max_memory_allocated(device) / 1024**2 if use_amp else 0
            measured_forward = forward_s if use_amp and profile else ''
            with open(timing_path, 'a', newline='', encoding='utf-8-sig') as stream:
                csv.writer(stream).writerow([
                    image_rel_path, len(components), bead_count, batch_size, str(device), model_load_s,
                    prepare_s, patch_s, gpu_wall_s, measured_forward, mask_s, write_s, total_s,
                    peak_mib, profile, fast, prefetch, pin_memory, benchmark,
                    torch.get_num_threads(), batch_wait_s, cache_s, normalize_setup_s])
            print(f"[{i + 1}/{len(image_files)}] {base_name}："
                  f"含磁珠微坑 {bead_count} 个 | 耗时 {total_s:.2f} 秒")

            components.clear()
            component_coords.clear()
            del img, mask, masked_img, processor, tree, bead_regions
            del labels, stats, centroids, valid_ids, label_lookup, table

        except InterruptedError:
            raise
        except Exception as e:
            print(f"处理错误 {image_rel_path}: {e}")
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    print("✅ 所有预测任务完成")
