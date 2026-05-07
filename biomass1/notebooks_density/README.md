# 📓 Jupyter Notebooks for Density Detection Pipeline

This directory contains Jupyter Notebooks converted from Python scripts for easier execution and modification on another machine. The notebooks are organized by workflow stage.

## 📁 Directory Structure

```
notebooks_density/
├── dataset_creation/        # Scripts for creating and preparing YOLO datasets
├── training/               # Scripts for training density detection models
├── testing/                # Scripts for testing and evaluating models
└── README.md              # This file
```

## 🎯 Workflow Overview

### 1. Dataset Creation (`dataset_creation/`)

Create and prepare datasets for training YOLOv11 density detection models.

**Notebooks:**
- **`create_yolo_dataset.ipynb`** - Main script to create YOLO format dataset from point cloud data
- **`batch_process_plots.ipynb`** - Process multiple plot files in batch
- **`augment_density_only.ipynb`** - Apply data augmentation specifically for density detection
- **`preview_density_labels.ipynb`** - Visualize dataset with bounding boxes to verify labels

**Recommended Order:**
1. Run `create_yolo_dataset.ipynb` to generate base dataset
2. Run `batch_process_plots.ipynb` if you have multiple plots to process
3. Run `augment_density_only.ipynb` to augment your training data
4. Run `preview_density_labels.ipynb` to verify your dataset

### 2. Training (`training/`)

Train YOLOv11 models for density detection.

**Notebooks:**
- **`train_density.ipynb`** - Standard training script for density detection
- **`train_density_fixed.ipynb`** - Training with fixed hyperparameters and settings

**Usage:**
1. Choose one of the training notebooks based on your needs
2. Adjust hyperparameters in the notebook cells
3. Run all cells to start training
4. Monitor training metrics and logs

### 3. Testing (`testing/`)

Evaluate trained models on test datasets.

**Notebooks:**
- **`test_density_v35.ipynb`** - Test script for density detection model v35

**Usage:**
1. Ensure you have a trained model checkpoint
2. Update the model path in the notebook
3. Run the notebook to generate evaluation metrics and visualizations

## 🚀 Getting Started

### Prerequisites

```bash
# Install required packages
pip install -r ../requirements.txt

# Additional packages you might need
pip install jupyter notebook
pip install laspy
pip install ultralytics
```

### Running Notebooks

1. **Start Jupyter Notebook/Lab:**
   ```bash
   cd /Users/songkarn/locarb/biomass/handheld-lidar-slam-toolbox/notebooks_density
   jupyter notebook
   ```

2. **Navigate to desired category folder**

3. **Open and run notebooks**

## 📝 Notes

- **Path Updates:** You may need to update file paths in the notebooks to match your machine's directory structure
- **Data Requirements:** Ensure you have the required input data (LAS files, CSV files, etc.) before running notebooks
- **GPU:** Training notebooks will benefit significantly from GPU acceleration (CUDA)
- **Intermediate Outputs:** Notebooks will save intermediate results to corresponding output directories

## 🔧 Customization

Each notebook can be modified to suit your specific needs:
- Adjust hyperparameters
- Change input/output paths
- Modify augmentation strategies
- Add custom metrics or visualizations

## 📚 Related Documentation

For more detailed information, refer to:
- `../yolov11/README.md` - Main YOLOv11 project documentation
- `../yolov11/DATASET_GENERATION_GUIDE.md` - Detailed dataset generation guide
- `../yolov11/AUGMENTATION_GUIDE_DENSITY.md` - Data augmentation guide

## 🤝 Usage Tips

1. **Run cells sequentially** - Don't skip cells as later cells may depend on earlier ones
2. **Check outputs** - Verify each step produces expected outputs before proceeding
3. **Save frequently** - Save notebook state regularly during long-running processes
4. **Document changes** - Add markdown cells to document any modifications you make

## 📦 Transferring to Another Machine

To transfer these notebooks to another machine:

1. **Copy the entire `notebooks_density` folder**
2. **Copy required dependencies:**
   - `../yolov11/scripts/` directory (contains shared utility scripts)
   - `../requirements.txt`
   - Any trained model checkpoints (`.pt files`)
3. **Update paths** in notebooks to match new machine's directory structure
4. **Install dependencies** on the new machine
5. **Prepare input data** (point clouds, labels, etc.)

---

**Generated:** 2025-12-11  
**Purpose:** Simplified workflow for density detection pipeline on new machines
