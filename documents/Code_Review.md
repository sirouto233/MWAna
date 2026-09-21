## 📝 Code Structure and Module Descriptions

The processing logic is organized in `logic_zh/` and `logic_en/`, called by the Chinese and English interfaces, respectively. The modules connect through image directories and intermediate results. They can run sequentially through the GUI, or selected steps can be run using existing outputs from preceding stages.

### `image_classifier.py`: Image Classification and Organization

This module recursively reads the source directory and distinguishes bright-field and fluorescent images by the channel suffix in each filename, copying them into `bri` and `flu`, respectively. It preserves sample subdirectories and original filenames so subsequent modules can pair images from the same field of view. Classification here refers to channel sorting and does not involve model-based prediction.

### `light_balance.py`: Bright-field Illumination Correction

This module first normalizes the bright-field grayscale range, then estimates the local illumination distribution through Gaussian smoothing and compensates for local brightness differences. Gamma correction and CLAHE are then applied to enhance microwell and bead contrast. The processed images are saved in `bri_sol` with the `_sol.tif` suffix. These outputs are used for microwell detection, training-set labeling, and bead occupancy prediction.

### `microwell_detection.py`: Microwell Detection and Mask Generation

This module reads the corrected bright-field images and applies contrast enhancement and smoothing before using the Hough circle transform to detect microwell centers. It draws a circular region of fixed radius at each center to generate a binary mask containing all candidate microwells, which is saved in `bri_mask`. This step locates the microwells to be classified individually in the next stage.

### `manual_labeling.py`: Labeling and Generation of Training-set

This module extracts individual microwell regions from a bright-field image and its microwell mask, then generates a 3×3 neighborhood preview for the central microwell selected by the operator. Based on the appearance of the central and surrounding reference microwells, the operator labels the center as an empty microwell (**bead-off well**) or a **well occupied by a bead (bead-on well)**. The program saves the assembled images and a CSV recording labels, center coordinates, and image paths, providing samples for supervised training.

### `train_model.py`: Swin-Transformer Model Training

This module reads the label CSV and corresponding neighborhood images, splits the data into training and validation sets, and applies resizing, radial intensity weighting, three-channel conversion, and normalization. It then loads a pretrained Swin-Tiny model and fine-tunes it for binary classification using samples labeled according to the central microwell. During training, it records loss and validation accuracy and saves model parameters based on improvement for use in batch prediction.

### `bead_prediction.py`: Bead-on Well Prediction

This module extracts candidate units from corrected bright-field images and all-microwell masks, constructs a 3×3 neighborhood image for each central microwell, and feeds the images in batches into the trained Swin-Tiny model. For units with a bead-on probability greater than 0.5, it retains the corresponding central microwell region and combines these regions into a valid-well mask saved with the `_bead.tif` suffix. Cached neighbor queries, normalization lookup tables, and patch prefetching improve batch processing efficiency.

### `fluorescence_analysis.py`: Fluorescence Signal and AMB Analysis

This module pairs each bead-on well mask with the fluorescent image from the same field of view, calculates the mean fluorescence intensity of each valid microwell, determines the positive-signal threshold, and generates a scatter plot. After obtaining the positive count and valid unit count, it calculates AMB for each image, combines results by sample directory, and screens for high-value outlier images. Finally, it exports per-image details, summaries before and after filtering, and a separate exclusion list.

### Launcher and Interfaces

`launcher.py` provides the language selection entry point, while `main_gui_zh.py` and `main_gui_en.py` provide the Chinese and English interfaces, respectively. The interfaces accept file paths, models, and task options, call the processing modules in sequence, and display progress, results, and errors. The `__init__.py` file in each logic directory declares it as a Python package.
