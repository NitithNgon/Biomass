#!/bin/bash
# Example: Rasterization of Point Cloud to Multi-Channel Images
# 
# จุดประสงค์: แปลง Point Cloud (.las) เป็นภาพหลายแชนเนล (320×320×6)
# - ไม่ได้ทำ tree detection
# - เพียงแค่สกัดฟีเจอร์ออกมาเป็นรูปภาพ
#
# Output:
# - Multi-channel array (.npy)
# - Individual channel images (PNG)
# - RGB composite
# - Visualization

set -e

# Configuration
INPUT_LAS="output/scans_test_optimized_1m.las"
OUTPUT_DIR="output/rasterization_result"
IMAGE_SIZE=320
PIXEL_SIZE=0.125  # 0.125 m/pixel

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Point Cloud Rasterization Example${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if input file exists
if [ ! -f "$INPUT_LAS" ]; then
    echo "Error: Input file not found: $INPUT_LAS"
    echo "Please check the file path"
    exit 1
fi

echo -e "${GREEN}Configuration:${NC}"
echo "  Input: $INPUT_LAS"
echo "  Output Directory: $OUTPUT_DIR"
echo "  Image Size: ${IMAGE_SIZE}×${IMAGE_SIZE} pixels"
echo "  Pixel Size: $PIXEL_SIZE m/pixel"
echo ""

# Run rasterization
echo -e "${GREEN}Running rasterization...${NC}"
python scripts/python/tools/pointcloud_rasterization.py \
    "$INPUT_LAS" \
    --output_dir "$OUTPUT_DIR" \
    --image_size $IMAGE_SIZE \
    --pixel_size $PIXEL_SIZE \
    --visualize

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ Rasterization Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Output files:"
echo "  📁 $OUTPUT_DIR/"
echo "     ├── scans_test_optimized_1m_raster.npy          (Multi-channel data)"
echo "     ├── scans_test_optimized_1m_raster_metadata.json"
echo "     ├── scans_test_optimized_1m_rgb.png             (RGB composite)"
echo "     ├── scans_test_optimized_1m_visualization.png   (All channels)"
echo "     └── scans_test_optimized_1m_raster_channels/"
echo "         ├── density.png    (Channel 0: จำนวนจุด)"
echo "         ├── z_max.png      (Channel 1: ความสูงสูงสุด)"
echo "         ├── z_min.png      (Channel 2: ความสูงต่ำสุด)"
echo "         ├── z_range.png    (Channel 3: ช่วงความสูง)"
echo "         ├── z_mean.png     (Channel 4: ความสูงเฉลี่ย)"
echo "         └── hag_mean.png   (Channel 5: ความสูงเหนือพื้น)"
echo ""
echo "Next steps:"
echo "  1. ตรวจสอบรูปภาพที่ได้"
echo "  2. ปรับพารามิเตอร์ตามต้องการ (image_size, pixel_size)"
echo "  3. เมื่อมี Ground Truth แล้ว จึงค่อยทำ tree detection และ YOLO"
echo ""
