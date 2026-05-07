# Point Cloud Rasterization for YOLO Training

เครื่องมือสำหรับแปลง Point Cloud เป็น 2D Multi-Channel Grid เพื่อเทรน YOLO

## Overview

แปลง Point Cloud (.las) เป็นภาพ 2D หลายแชนเนล (320×320×6) พร้อม features:
- **Channel 0**: density (จำนวนจุด)
- **Channel 1**: z_max (ความสูงสูงสุด)
- **Channel 2**: z_min (ความสูงต่ำสุด)
- **Channel 3**: z_range (ความแตกต่างความสูง)
- **Channel 4**: z_mean (ความสูงเฉลี่ย)
- **Channel 5**: hag_mean (ความสูงเหนือพื้นเฉลี่ย)

## Configuration

- **ขนาดภาพ**: 320×320 pixels
- **ขนาด pixel**: 0.125 m/pixel
- **พื้นที่ครอบคลุม**: 40×40 m (≈ 1 ไร่)

## Installation

```bash
pip install laspy opencv-python numpy scipy matplotlib
```

## Usage

### 1. Basic Rasterization

```bash
python pointcloud_rasterization.py output/scans_test_optimized_1m.las \
    --output_dir ./raster_output
```

### 2. Custom Parameters

```bash
python pointcloud_rasterization.py input.las \
    --output_dir ./custom_output \
    --image_size 640 \
    --pixel_size 0.0625 \
    --area_size 40.0 \
    --visualize
```

### 3. Without Normalization

```bash
python pointcloud_rasterization.py input.las \
    --output_dir ./output \
    --no_normalize
```

## Output Files

```
raster_output/
├── scans_test_optimized_1m_raster.npy          # Multi-channel array (H×W×6)
├── scans_test_optimized_1m_raster_metadata.json # Grid metadata
├── scans_test_optimized_1m_rgb.png              # RGB composite visualization
├── scans_test_optimized_1m_visualization.png    # All channels visualization
└── scans_test_optimized_1m_raster_channels/     # Individual channel images
    ├── density.png
    ├── z_max.png
    ├── z_min.png
    ├── z_range.png
    ├── z_mean.png
    └── hag_mean.png
```

## Python API

```python
from pointcloud_rasterization import PointCloudRasterizer

# Initialize
rasterizer = PointCloudRasterizer(
    image_size=320,
    pixel_size=0.125,
    area_size=40.0
)

# Load point cloud
points, metadata = rasterizer.load_pointcloud('input.las')

# Rasterize to multi-channel
grid, grid_meta = rasterizer.rasterize_multi_channel(points)

# Resize to target size
resized = rasterizer.resize_to_target(grid, target_size=320)

# Save results
rasterizer.save_multi_channel(resized, 'output/raster', grid_meta)

# Create RGB composite
rgb = rasterizer.create_rgb_composite(
    resized,
    channels=(0, 4, 5),  # density, z_mean, hag_mean
    output_path='output/rgb.png'
)
```

## Features Explanation

### 1. Density (Channel 0)
- จำนวนจุดที่ตกอยู่ในแต่ละ pixel
- ใช้แยกพื้นที่ที่มีข้อมูลหนาแน่นกับพื้นที่ว่าง

### 2. Z Statistics (Channels 1-4)
- **z_max**: ความสูงสูงสุดในแต่ละ pixel (เช่น ยอดต้นไม้)
- **z_min**: ความสูงต่ำสุด (เช่น พื้นดิน)
- **z_range**: ความแตกต่างความสูง (z_max - z_min)
- **z_mean**: ความสูงเฉลี่ย

### 3. Height Above Ground (Channel 5)
- ความสูงเหนือพื้นเฉลี่ย (HAG)
- คำนวณจาก ground estimation (5th percentile)
- ใช้แยกต้นไม้จากพื้นดิน

## Next Steps

### 1. Tree Detection & Patch Extraction
```bash
python tree_patch_extractor.py \
    raster_output/scans_test_optimized_1m_raster.npy \
    --patch_size 1.1 \
    --output_dir ./patches
```

### 2. YOLO Dataset Generation
```bash
python create_yolo_dataset.py \
    raster_output/scans_test_optimized_1m_raster.npy \
    --tree_positions tree_positions.json \
    --output_dir ./yolo_dataset
```

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--image_size` | 320 | Target image size (pixels) |
| `--pixel_size` | 0.125 | Pixel resolution (m/pixel) |
| `--area_size` | 40.0 | Area coverage (meters) |
| `--no_normalize` | False | Skip channel normalization |
| `--visualize` | False | Create visualization plots |

## Troubleshooting

### Memory Issues
ถ้า point cloud ใหญ่เกินไป ลองลด `image_size` หรือแบ่งพื้นที่ออกเป็นส่วนๆ:

```python
# Split large point cloud
def split_pointcloud(points, grid_size=40.0):
    x_min, y_min = points[:, :2].min(axis=0)
    x_max, y_max = points[:, :2].max(axis=0)
    
    for x in np.arange(x_min, x_max, grid_size):
        for y in np.arange(y_min, y_max, grid_size):
            mask = ((points[:, 0] >= x) & (points[:, 0] < x + grid_size) &
                   (points[:, 1] >= y) & (points[:, 1] < y + grid_size))
            yield points[mask]
```

### Empty Channels
ถ้ามี channels ที่เป็น 0 ทั้งหมด อาจเกิดจาก:
- Point cloud มีจุดน้อยเกินไป
- Grid resolution สูงเกินไป (ลอง increase `pixel_size`)

## Examples

### Example 1: Process Multiple Files
```bash
#!/bin/bash
for las_file in output/*.las; do
    echo "Processing $las_file..."
    python pointcloud_rasterization.py "$las_file" \
        --output_dir "./raster_$(basename $las_file .las)" \
        --visualize
done
```

### Example 2: Batch Processing with Different Resolutions
```bash
#!/bin/bash
INPUT="output/scans_test_optimized_1m.las"

for size in 160 320 640; do
    python pointcloud_rasterization.py "$INPUT" \
        --image_size $size \
        --output_dir "./raster_${size}x${size}"
done
```

## Citation

หากใช้เครื่องมือนี้ในงานวิจัย โปรดอ้างอิง:
```
@software{pointcloud_rasterization,
  title = {Point Cloud Rasterization for YOLO Training},
  author = {Lo-Carb Biomass Team},
  year = {2025},
  url = {https://github.com/Lo-Carb/handheld-lidar-slam-toolbox}
}
```

## Related Tools

1. `tree_patch_extractor.py` - Extract patches around detected trees
2. `create_yolo_dataset.py` - Generate YOLO training dataset
3. `pointcloud_to_yolo_dataset.py` - End-to-end pipeline

## Contact

สำหรับคำถามและปัญหา:
- GitHub Issues: https://github.com/Lo-Carb/handheld-lidar-slam-toolbox/issues
- Email: [your-email@example.com]
