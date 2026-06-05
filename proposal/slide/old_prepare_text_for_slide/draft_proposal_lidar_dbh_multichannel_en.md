# Draft Thesis Proposal Presentation

Title: **Individual Tree Segmentation from Handheld LiDAR Point Clouds for DBH Estimation in Rubber Plantations using Multi-channel CNN**

This English version is the working content draft for the Chula-theme proposal deck. References are separated into individual tree segmentation and DBH extraction.

---

## Slide 1: Title

**Individual Tree Segmentation from Handheld LiDAR Point Clouds for DBH Estimation in Rubber Plantations using Multi-channel CNN**

Draft Thesis Proposal

Presented by: [Student Name] [Student ID]  
Advisor: [Advisor Name]  
Department of Computer Engineering, Chulalongkorn University

---

## Slide 2: Introduction

**The proposal starts from the bottleneck between LiDAR capture and tree-level forest inventory.**

**The Challenge:** DBH is one of the most important variables for forest monitoring and biomass estimation, but manual DBH measurement requires substantial labor and time. Handheld or backpack LiDAR can capture dense 3D data more efficiently, yet the raw point cloud still has to be converted into reliable tree-level measurements.

**The Limitation:** Existing LiDAR-based workflows often depend on rule-based trunk extraction, clustering, and circle/cylinder fitting. These methods are sensitive to shrubs, deadwood, leaves, uneven ground, occlusion, scan path, and variable point density. Heavy 3D learning methods can improve segmentation, but they may require high GPU memory and domain-specific fine-tuning.

**Core Problem:** How can we automatically transform handheld LiDAR point clouds of rubber plantations into accurate individual-tree segments and DBH estimates, while keeping the model lightweight enough to run efficiently and compare fairly against 3D point-cloud methods such as TreeLearn?

Speaker note:
This introduction follows the same logic as Liu et al. (2021): DBH is important, mobile LiDAR improves data acquisition, but segmentation and noisy trunk points remain the main barriers to accurate DBH extraction.

---

## Slide 3: Problem Statement

**Limitations of Current Techniques**

While mobile and handheld LiDAR workflows can collect 3D forest point clouds more efficiently than manual field surveys, current techniques still struggle to transform raw plot-level point clouds into reliable tree-level DBH measurements under real plantation conditions.

**Lack of Robust Individual Tree Segmentation**

Most rule-based point-cloud pipelines depend on trunk extraction, clustering radius, voxel size, density thresholds, or slice-level assumptions. In rubber plantations, occlusion, uneven point density, shrubs, deadwood, and nearby stems can cause merged trees, missed trees, or false tree detections.

**Limited Accuracy-Efficiency Bridge**

Direct 3D learning methods such as TreeLearn can improve individual tree segmentation, but they may require GPU memory, long preprocessing time, and domain-specific fine-tuning. Lightweight 2D density-image CNNs are more efficient, but they discard vertical structure and breast-height evidence needed for accurate DBH extraction.

Speaker note:
This slide frames the problem as two limitations: current lightweight methods lose useful 3D evidence, while stronger 3D methods may be too resource-demanding for a practical pipeline.

---

## Slide 4: Background

**Diameter at Breast Height (DBH)**

**Definition:** The trunk diameter measured at breast height, commonly around 1.3 m above the ground surface.

**Role in Research:** DBH is the target tree-level inventory variable used for biomass estimation, forest monitoring, and evaluation of downstream measurement accuracy.

**Handheld / Mobile LiDAR Point Clouds**

**Definition:** Three-dimensional point measurements collected while an operator walks through a forest or plantation using handheld or backpack LiDAR with SLAM-based mapping.

**Role in Research:** Provides the raw 3D data source for detecting individual rubber trees and extracting trunk points near breast height.

**Individual Tree Segmentation**

**Definition:** The task of separating a plot-level forest point cloud into individual tree instances or tree centers.

**Role in Research:** Acts as the upstream step before DBH extraction; missed, merged, or false tree instances directly affect DBH estimation.

**Multi-channel Raster Representation**

**Definition:** A 2D top-view image representation where each channel encodes a LiDAR-derived feature such as point density, height above ground, or breast-height density.

**Role in Research:** Converts 3D point-cloud evidence into CNN-compatible input while preserving more physical information than a single density image.

Speaker note:
This slide provides the vocabulary needed for the rest of the proposal: what is being measured, where the data comes from, what segmentation means, and why multi-channel input is proposed.

---

## Slide 5: Related Work Landscape

**Individual Tree Segmentation and DBH Extraction**

| Approach | Key Concept | Critical Limitation (Research Gap) |
|---|---|---|
| Relative-density segmentation + multi-height DBH fitting (Liu et al., 2021) | Segments trunks from MLS point clouds using relative density, then estimates DBH from multi-height circle fitting with outlier removal. | Still relies on handcrafted density scales and trunk assumptions; robustness may drop when point density, scan path, or plantation structure changes. |
| Handheld LiDAR online DBH estimation (Proudman et al., 2021) | Uses handheld LiDAR mapping and tree-level processing to estimate DBH during or after field scanning. | Focuses on DBH extraction pipeline, but individual tree segmentation remains sensitive to occlusion and noisy trunk observations. |
| ForestSPG / large-scale MLS inventory (Shao et al., 2024) | Applies deep semantic segmentation and stem mapping for large natural forest inventory, then fits DBH from detected stems. | Designed for large-scale forest inventory; computational complexity and platform generalization can be difficult for a lightweight rubber-plantation pipeline. |
| TreeLearn (Henrich et al., 2024) | Uses 3D sparse CNN to predict tree/non-tree scores and offsets for individual tree instance segmentation. | Strong segmentation performance, but requires 3D deep learning infrastructure, GPU memory, and possible domain fine-tuning. |
| Single-channel top-view CNN baseline (Current project) | Rasterizes the point cloud into a density image and trains a CNN/YOLO detector for tree centers. | Efficient and simple, but discards vertical structure and breast-height evidence that may help separate individual trees and support DBH estimation. |

Speaker note:
The table shows why this proposal tests a middle path: richer than a single density image, but lighter than direct 3D point-cloud instance segmentation.

---

## Slide 6: Research Gap

**The missing middle is an efficient segmentation method that still preserves DBH-relevant 3D evidence.**

- Rule-based point-cloud methods can work well, but they often require handcrafted parameters that change with plot structure, point density, and scan path.
- Direct 3D deep learning methods such as TreeLearn provide strong instance segmentation, but they may require higher GPU memory, long preprocessing time, and domain fine-tuning.
- Single-channel density CNNs are lightweight and easy to train, but they discard vertical structure and breast-height trunk evidence.
- This proposal investigates whether multi-channel raster features can improve individual tree segmentation while keeping the CNN/YOLO pipeline efficient.


---

## Slide 7: Proposed Method

We propose four components: **Data Preparation**, **Feature Rasterization**, **Individual Tree Segmentation**, and **DBH Extraction & Evaluation**.

**Data Preparation:** Convert and standardize the 12 rubber-plantation point clouds, align them with field labels, and compute height-above-ground information.

**Feature Rasterization:** Transform each 3D point cloud into multi-channel top-view feature images that preserve density, vertical structure, and breast-height stem evidence.

**Individual Tree Segmentation:** Train a CNN/YOLO model to detect tree instances from the multi-channel raster, then compare it with density-only CNN and 3D point-cloud methods.

**DBH Extraction & Evaluation:** Crop tree-level trunk points, estimate DBH using circle/cylinder fitting, and evaluate both accuracy and computational efficiency.

---

## Slide 8: System Architecture

**The workflow operates in 4 distinct stages.**

`Point cloud -> Feature raster -> CNN/YOLO -> Tree crop -> DBH fitting -> Evaluation`

- **Stage 1 - Data Preparation:** Standardize point clouds, align ground-truth labels, estimate local ground, and compute height above ground.
- **Stage 2 - Feature Rasterization:** Generate synthetic RGB channels: `density`, `hag_p95`, and `dbh_band_density`.
- **Stage 3 - Individual Tree Segmentation:** Detect tree centers or tree-level regions using multi-channel CNN/YOLO and compare against baseline methods.
- **Stage 4 - DBH Extraction & Evaluation:** Crop trunk points, fit DBH, and report segmentation, DBH, and efficiency metrics.

Speaker note:
This architecture keeps the research focused: the proposed contribution is the multi-channel representation and segmentation pipeline, while DBH fitting is used to measure the downstream impact.

---

## Slide 9: Dataset and Controls
Rubber plantation data will be evaluated at the plot level.
- Main dataset: 12 rubber plantation point clouds.
- Labels: tree X/Y positions and field-measured DBH from CSV files.
- Preprocessing: PCD/LAS conversion, filtering, rotation, and coordinate alignment with labels.
- Train/validation/test split will be performed by plot to prevent leakage.
- The same split seed, image size, pixel size, bounding-box size, and augmentation policy will be used for fair comparison.


---

## Slide 10: Methodology: Data Preparation

**1.1 Point Cloud Standardization**

**Input:** Raw PCD/LAS point clouds and ground-truth CSV files.

Convert source scans into a consistent LAS-based workflow, apply filtering and rotation, and align the coordinate system with tree-location labels.

**1.2 Ground Normalization and Dataset Split**

**Input:** Standardized plot point clouds.

Estimate the local ground surface, compute height above ground for each point, and split the 12 plots into train/validation/test sets at plot level.

---

## Slide 11: Methodology: Feature Rasterization

**2.1 Density and Height Channels**

**Input:** Ground-normalized point cloud.

Rasterize the plot into a top-view grid. The density channel counts points per cell, while the `hag_p95` channel captures the 95th percentile of height above ground.

**2.2 Breast-height Evidence Channel**

**Input:** Height-above-ground point cloud.

Count points in the 1.0-1.6 m band to create `dbh_band_density`, emphasizing stem evidence near breast height.

---

## Slide 12: Methodology: Individual Tree Segmentation

**3.1 Multi-channel CNN/YOLO**

**Input:** Synthetic RGB raster and tree-location labels.

Train a CNN/YOLO detector to predict tree centers or tree-level regions from density, vertical structure, and breast-height evidence.

**3.2 Baseline and 3D Comparison**

**Input:** The same plot split and ground-truth labels.

Compare the proposed multi-channel CNN with a single-channel density CNN, TreeLearn, and a point-cloud processing baseline.

---

## Slide 13: Methodology: DBH Extraction

**4.1 Tree-level Point Crop**

**Input:** Predicted tree center/box and original point cloud.

Collect candidate trunk points around each predicted tree, focusing on the breast-height band and nearby stem structure.

**4.2 Circle/Cylinder Fitting**

**Input:** Tree-level trunk points near 1.3 m height above ground.

Estimate DBH using circle or cylinder fitting, and test multi-height bins with RANSAC/outlier removal for noisy trunk observations.

---

## Slide 14: Expected Outcome & Contribution

- **Multi-channel tree segmentation pipeline:** a validated workflow that transforms handheld LiDAR point clouds into tree-level detections/crops using density, height-above-ground, and breast-height evidence.

- **DBH-ready tree crops:** extracted trunk point subsets for each predicted tree, enabling DBH fitting from breast-height slices or multi-height fitting.

- **Accuracy-efficiency benchmark:** a controlled comparison between density-only CNN, multi-channel CNN, TreeLearn, and point-cloud baselines on the same rubber-plantation plots.

- **Segmentation-to-DBH error analysis:** evidence showing how missed, merged, and false tree detections affect downstream DBH estimation.

**Metric for Success**

Success will be measured by improved tree segmentation F1/TDR, reduced DBH MAE/RMSE against field measurements, and lower runtime or memory usage compared with direct 3D point-cloud segmentation.

---

## Slide 15: References - Individual Tree Segmentation

Grouped references are selected from the literature files and summary table in `proposal/iterature`.

[1] Liu, Lulu, Aiwu Zhang, Shen Xiao, Shaoxing Hu, Nianpeng He, Haiyang Pang, Xizhen Zhang, and Shikai Yang. 2021. "Single Tree Segmentation and Diameter at Breast Height Estimation With Mobile LiDAR." *IEEE Access* 9: 24314-24325.

[2] Henrich, Jonathan, Jan van Delden, Dominik Seidel, Thomas Kneib, and Alexander S. Ecker. 2024. "TreeLearn: A Deep Learning Method for Segmenting Individual Trees from Ground-Based LiDAR Forest Point Clouds." *Ecological Informatics* 84: 102888.

[3] Shao, Jinyuan, Yi-Chun Lin, Cameron Wingren, Sang-Yeop Shin, William Fei, Joshua Carpenter, Ayman Habib, and Songlin Fei. 2024. "Large-Scale Inventory in Natural Forests with Mobile LiDAR Point Clouds." *Science of Remote Sensing* 10: 100168.

[4] Cheng, Derek, Fernando Cladera Ojeda, Ankit Prabhu, Xu Liu, Alan Zhu, P. Corey Green, Reza Ehsani, Pratik Chaudhari, and Vijay Kumar. 2024. "TreeScope: An Agricultural Robotics Dataset for LiDAR-Based Mapping of Trees in Forests and Orchards." *2024 IEEE International Conference on Robotics and Automation (ICRA)*.

[5] Chen, Steven W., Guilherme V. Nardari, Elijah S. Lee, Chao Qu, Xu Liu, Roseli A. F. Romero, and Vijay Kumar. 2020. "SLOAM: Semantic Lidar Odometry and Mapping for Forest Inventory." *IEEE Robotics and Automation Letters* 5 (2): 612-619.

---

## Slide 16: References - DBH Extraction

DBH-focused references are selected from the literature files and summary table in `proposal/iterature`.

[1] Proudman, Alexander, Milad Ramezani, and Maurice Fallon. 2021. "Online Estimation of Diameter at Breast Height (DBH) of Forest Trees Using a Handheld LiDAR." *2021 European Conference on Mobile Robots (ECMR)*: 1-7.

[2] Sheng, Yuhao, Qingzhan Zhao, Xuewen Wang, Yihao Liu, and Xiaojun Yin. 2024. "Tree Diameter at Breast Height Extraction Based on Mobile Laser Scanning Point Cloud." *Forests* 15 (4): 590.

[3] Liu, Lulu, Aiwu Zhang, Shen Xiao, Shaoxing Hu, Nianpeng He, Haiyang Pang, Xizhen Zhang, and Shikai Yang. 2021. "Single Tree Segmentation and Diameter at Breast Height Estimation With Mobile LiDAR." *IEEE Access* 9: 24314-24325.

[4] Shao, Jinyuan, Yi-Chun Lin, Cameron Wingren, Sang-Yeop Shin, William Fei, Joshua Carpenter, Ayman Habib, and Songlin Fei. 2024. "Large-Scale Inventory in Natural Forests with Mobile LiDAR Point Clouds." *Science of Remote Sensing* 10: 100168.

[5] Cheng, Derek, Fernando Cladera Ojeda, Ankit Prabhu, Xu Liu, Alan Zhu, P. Corey Green, Reza Ehsani, Pratik Chaudhari, and Vijay Kumar. 2024. "TreeScope: An Agricultural Robotics Dataset for LiDAR-Based Mapping of Trees in Forests and Orchards." *2024 IEEE International Conference on Robotics and Automation (ICRA)*.
