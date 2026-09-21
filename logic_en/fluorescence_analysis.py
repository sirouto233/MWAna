import os
import cv2
import numpy as np
import pandas as pd
from scipy import ndimage
from scipy.stats import gaussian_kde
import matplotlib


# Render plots without opening GUI windows.
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def analyze_connected_components(image, mask):
    """Return labels, component count, and mean intensity per component."""
    labeled, num_features = ndimage.label(mask > 0)
    if num_features == 0:
        return labeled, 0, []

    mean_intensities = ndimage.mean(image, labels=labeled, index=np.arange(1, num_features + 1))
    return labeled, num_features, mean_intensities.tolist()


def generate_scatter_plot(mean_intensities, image_name, threshold, output_path):
    """Save an intensity scatter plot with the decision threshold."""
    plt.figure(figsize=(8, 6))
    plt.scatter(mean_intensities, range(len(mean_intensities)), color='green', alpha=0.5, s=10)
    plt.axvline(x=threshold, color='r', linestyle='--', label=f'Threshold = {threshold:.2f}')

    plt.title(f"Intensity Distribution - {image_name}")
    plt.xlabel("Mean Intensity")
    plt.ylabel("Index")
    plt.legend()
    plt.grid(True)

    scatter_path = os.path.join(output_path, f"scatter_{image_name}.png")
    plt.savefig(scatter_path)
    plt.close()
    return scatter_path


def find_kde_threshold(intensities):
    """Estimate a threshold from the steepest KDE decline plus an empirical offset."""
    if len(intensities) < 2:
        return 0

    try:
        kde = gaussian_kde(intensities)
        x_grid = np.linspace(min(intensities), max(intensities), 200)
        density = kde(x_grid)
        density_diff = np.diff(density) / np.diff(x_grid)

        decline_indices = np.where(density_diff < 0)[0]
        if len(decline_indices) == 0:
            return np.median(intensities)

        steepest_decline_idx = decline_indices[np.argmin(density_diff[decline_indices])]
        return x_grid[steepest_decline_idx] + 150
    except ValueError:
        return np.mean(intensities)


OUTLIER_Z_THRESHOLD = 3.5
OUTLIER_MIN_IMAGES = 5


def build_amb_reports(results, z_threshold=OUTLIER_Z_THRESHOLD, min_images=OUTLIER_MIN_IMAGES):
    """Calculate image AMB and flag high outliers within each relative folder."""
    if not np.isfinite(z_threshold) or z_threshold <= 0:
        raise ValueError("z_threshold must be positive and finite")
    if not isinstance(min_images, int) or min_images < 3:
        raise ValueError("min_images must be an integer >= 3")

    columns = ['Subfolder', 'File', 'Total Beads', 'Positive Beads', 'Threshold',
               'Image', 'Fluorescence Path', 'Mask Path', 'Status', 'Error', 'AMB Raw']
    df = pd.DataFrame(results, columns=columns).copy()
    valid = ((df['Status'] == 'ok') & (df['Total Beads'] > 0)
             & (df['Positive Beads'] >= 0)
             & (df['Positive Beads'] <= df['Total Beads']))
    df['AMB Raw'] = np.nan
    df.loc[valid, 'AMB Raw'] = df.loc[valid, 'Positive Beads'] / df.loc[valid, 'Total Beads']
    df['Is Outlier'] = False
    df['Included Filtered'] = valid
    df['Outlier Score'] = np.nan
    df['AMB Upper Limit'] = np.nan
    df['Group Median AMB'] = np.nan
    df['Group MAD'] = np.nan
    df['Filter Status'] = 'invalid_image'
    df['Exclusion Reason'] = ''
    summaries = []

    for group, rows in df.groupby('Subfolder', sort=True):
        idx = rows.index[valid.loc[rows.index]]
        values = df.loc[idx, 'AMB Raw'].to_numpy(dtype=float)
        filter_status = 'insufficient_images'
        if len(idx):
            median = float(np.median(values))
            mad = float(np.median(np.abs(values - median)))
            df.loc[idx, 'Group Median AMB'] = median
            df.loc[idx, 'Group MAD'] = mad
            if len(idx) >= min_images:
                counts = df.loc[idx, 'Total Beads'].to_numpy(dtype=float)
                typical_count = float(np.median(counts))
                p_reference = (median * typical_count + 0.5) / (typical_count + 1.0)
                # A count-based floor limits unstable scores for tied ratios and small images.
                scale = np.maximum.reduce([
                    np.full(len(idx), mad / 0.6744897501960817),
                    np.sqrt(p_reference * (1.0 - p_reference) / counts),
                    1.0 / counts,
                ])
                scores = (values - median) / scale
                flagged = scores > z_threshold
                df.loc[idx, 'Outlier Score'] = scores
                df.loc[idx, 'AMB Upper Limit'] = median + z_threshold * scale
                df.loc[idx, 'Is Outlier'] = flagged
                df.loc[idx, 'Included Filtered'] = ~flagged
                df.loc[idx[flagged], 'Exclusion Reason'] = 'high_amb_robust_score'
                filter_status = 'screened_upper_mad_with_count_floor'
            df.loc[idx, 'Filter Status'] = filter_status

        kept = idx[df.loc[idx, 'Included Filtered'].to_numpy(dtype=bool)]
        total = int(df.loc[idx, 'Total Beads'].sum())
        positive = int(df.loc[idx, 'Positive Beads'].sum())
        kept_total = int(df.loc[kept, 'Total Beads'].sum())
        kept_positive = int(df.loc[kept, 'Positive Beads'].sum())
        summaries.append({
            'Subfolder': group,
            'Total Beads': total,
            'Positive Beads': positive,
            'Threshold': df.loc[idx, 'Threshold'].mean(),
            'AMB Raw': positive / total if total else np.nan,
            'Total Beads Filtered': kept_total,
            'Positive Beads Filtered': kept_positive,
            'AMB Filtered': kept_positive / kept_total if kept_total else np.nan,
            'Matched Images': len(rows),
            'Valid Images': len(idx),
            'Retained Images': len(kept),
            'Excluded Images': int(df.loc[rows.index, 'Is Outlier'].sum()),
            'Invalid Images': len(rows) - len(idx),
            'Filter Status': filter_status if len(idx) else 'no_valid_images',
            'Outlier Z Threshold': z_threshold,
            'Minimum Images': min_images,
        })

    df['AMB Filtered'] = df['AMB Raw'].where(df['Included Filtered'])
    excluded = df.loc[df['Is Outlier']].copy()
    summary_columns = ['Subfolder', 'Total Beads', 'Positive Beads', 'Threshold', 'AMB Raw',
                       'Total Beads Filtered', 'Positive Beads Filtered', 'AMB Filtered',
                       'Matched Images', 'Valid Images', 'Retained Images', 'Excluded Images',
                       'Invalid Images', 'Filter Status', 'Outlier Z Threshold', 'Minimum Images']
    return df, pd.DataFrame(summaries, columns=summary_columns), excluded


def export_amb_reports(results, output_dir, z_threshold=OUTLIER_Z_THRESHOLD, min_images=OUTLIER_MIN_IMAGES):
    """Preserve the Excel report and add raw, filtered, and excluded-image CSVs."""
    details, summary, excluded = build_amb_reports(results, z_threshold, min_images)
    os.makedirs(output_dir, exist_ok=True)
    with pd.ExcelWriter(os.path.join(output_dir, 'fluorescence_stats.xlsx')) as writer:
        details.to_excel(writer, sheet_name='Details', index=False)
        summary.to_excel(writer, sheet_name='Summary', index=False)
        excluded.to_excel(writer, sheet_name='Excluded', index=False)
    for name, frame in [('fluorescence_stats.csv', details),
                        ('amb_summary.csv', summary), ('excluded_images.csv', excluded)]:
        frame.to_csv(os.path.join(output_dir, name), index=False, encoding='utf-8-sig')
    return details, summary, excluded


def process_image(args):
    """Measure fluorescence in one paired effective-well mask."""
    fluorescence_path, mask_path, output_dir, subfolder_name = args
    record = {
        'Subfolder': subfolder_name,
        'File': os.path.basename(fluorescence_path),
        'Total Beads': 0,
        'Positive Beads': 0,
        'Threshold': np.nan,
        'Image': os.path.join(subfolder_name, os.path.basename(fluorescence_path)).replace('\\', '/'),
        'Fluorescence Path': os.path.abspath(fluorescence_path),
        'Mask Path': os.path.abspath(mask_path),
        'Status': 'ok',
        'Error': '',
        'AMB Raw': np.nan,
    }

    try:
        mask = cv2.imread(mask_path, cv2.IMREAD_UNCHANGED)
        fluo_img = cv2.imread(fluorescence_path, cv2.IMREAD_UNCHANGED)
        if mask is None or fluo_img is None:
            record.update(Status='read_error', Error='Image or mask could not be read')
            return record
        if mask.ndim != 2 or fluo_img.ndim != 2 or mask.shape != fluo_img.shape:
            raise ValueError('Expected aligned single-channel image and mask with equal shapes')

        masked_img = fluo_img * (mask > 0)
        _, total_beads, mean_intensities = analyze_connected_components(masked_img, mask)

        if not mean_intensities:
            record['Status'] = 'no_valid_units'
            return record

        intensities = np.array(mean_intensities)
        initial_threshold = find_kde_threshold(intensities)

        low_values = intensities[intensities <= np.percentile(intensities, 25)]
        low_values = low_values[low_values > 50]
        low_std = np.std(low_values) if len(low_values) > 1 else 0


        # Empirical intensity thresholds depend on acquisition settings.
        final_threshold = 1000 if low_std > 200 else initial_threshold
        positive_count = sum(1 for i in mean_intensities if i > final_threshold)

        f_file = os.path.basename(fluorescence_path)
        sub_output_dir = os.path.join(output_dir, subfolder_name)
        os.makedirs(sub_output_dir, exist_ok=True)
        generate_scatter_plot(mean_intensities, f_file, final_threshold, sub_output_dir)

        print(f"Processed: {f_file} | Threshold: {final_threshold:.1f} | Positives: {positive_count}/{total_beads}")

        record.update({
            'Total Beads': total_beads,
            'Positive Beads': positive_count,
            'Threshold': final_threshold,
            'AMB Raw': positive_count / total_beads,
        })
        return record

    except Exception as e:
        print(f"Analysis error on {fluorescence_path}: {e}")
        record.update(Status='analysis_error', Error=str(e))
        return record


def analyze_fluorescence(fluorescence_dir, mask_dir, z_threshold=OUTLIER_Z_THRESHOLD, min_images=OUTLIER_MIN_IMAGES):
    """Pair fluorescence images with bead masks and export counts and plots."""
    if not fluorescence_dir or not mask_dir:
        print("Error: Invalid directory paths provided.")
        return

    output_dir = os.path.join(os.path.dirname(fluorescence_dir), "Analysis_Results")
    os.makedirs(output_dir, exist_ok=True)

    print(f"Starting fluorescence analysis...\nInputs: {fluorescence_dir}\nOutputs: {output_dir}")

    tasks = []
    for root, _, files in os.walk(fluorescence_dir):
        fluo_files = [f for f in files if f.endswith('-0-2.tif')]
        if not fluo_files:
            continue

        rel_path = os.path.relpath(root, fluorescence_dir)
        mask_subfolder = os.path.join(mask_dir, rel_path)

        if not os.path.exists(mask_subfolder):
            continue

        mask_map = {f: os.path.join(mask_subfolder, f) for f in os.listdir(mask_subfolder) if f.endswith('_bead.tif')}

        for f_file in sorted(fluo_files):
            mask_target = f"{f_file.replace('-0-2.tif', '')}-0-1_bead.tif"
            if mask_target in mask_map:
                tasks.append((
                    os.path.join(root, f_file),
                    mask_map[mask_target],
                    output_dir,
                    rel_path.replace("\\", "/")
                ))

    print(f"Matched {len(tasks)} image pairs. Beginning processing...")


    results = [res for task in tasks if (res := process_image(task)) is not None]

    if not results:
        print("Analysis completed, but no valid data was generated.")

    _, summary, excluded = export_amb_reports(results, output_dir, z_threshold, min_images)
    print(f"AMB reports saved: {output_dir} | Excluded images: {len(excluded)}")
    return summary
