# Biomass2: Multi-Channel LiDAR Input for Rubber Tree Detection

โฟลเดอร์นี้เป็นเวอร์ชันทดลองต่อจาก `biomass1` โดยยังใช้ภาพ top-view grid เหมือนเดิม แต่เปลี่ยนจาก 1 channel เป็น 3 channel เพื่อทดสอบว่า feature จากโครงสร้างแนวดิ่งของ point cloud ช่วยแยกต้นยางรายต้นได้ดีขึ้นหรือไม่

## Feature ที่เลือกเพิ่ม

ช่องภาพเริ่มต้นคือ:

1. `density` - จำนวนจุดในแต่ละ grid cell เหมือนงานเดิม
2. `hag_p95` - ความสูงเหนือพื้นดิน percentile 95 ในแต่ละ cell ใช้แทน canopy/upper structure แบบทน outlier มากกว่า max height
3. `dbh_band_density` - จำนวนจุดที่อยู่ในช่วงความสูงเหนือพื้นดิน `1.0-1.6 m` เพื่อเน้นสัญญาณบริเวณ breast height ใกล้ DBH

เหตุผลของสอง feature ใหม่:

- `hag_p95` ช่วยให้โมเดลเห็นทรงพุ่มและความต่างเชิงความสูง ไม่ใช่แค่ความหนาแน่นของจุด
- `dbh_band_density` น่าจะช่วยกับสวนยาง เพราะต้นยางปลูกเป็นแถวและตำแหน่งลำต้นบริเวณช่วงอกมักเป็นสัญญาณสำคัญกว่าความหนาแน่นรวมของเรือนยอด

ภาพที่สร้างออกมาเป็น RGB synthetic image:

- R = `density`
- G = `hag_p95`
- B = `dbh_band_density`

จึงใช้กับ YOLO/CNN pipeline เดิมได้โดยไม่ต้องแก้ input layer ของโมเดล

## สร้างภาพ multi-channel จาก LAS ไฟล์เดียว

```bash
python biomass2/dataset_creation/scripts/pointcloud_multichannel.py path/to/plot.las \
  --output_dir biomass2/raster_output \
  --image_size 320 \
  --pixel_size 0.125 \
  --save_previews
```

ผลลัพธ์หลัก:

- `*_multichannel.jpg`
- `*_metadata.json`
- `channel_previews/*_density.png`, `*_hag_p95.png`, `*_dbh_band_density.png`

## สร้าง YOLO dataset

รูปแบบ input เหมือน `biomass1`: LAS อยู่ใน `--plots_dir` และ label CSV อยู่ที่ `--csv_dir/<plot_name>/DBHaverage.csv` โดย CSV ต้องมีคอลัมน์ `X` และ `Y`

```bash
python biomass2/dataset_creation/create_yolo_multichannel_dataset.py \
  --plots_dir path/to/processed_las \
  --csv_dir path/to/label_root \
  --output_dir biomass2/dataset_creation/yolov11/dataset_multichannel \
  --use_rotated \
  --overwrite
```

ถ้าชื่อไฟล์ LAS ไม่ใช่ `*_rotated.las` ให้ใช้:

```bash
python biomass2/dataset_creation/create_yolo_multichannel_dataset.py \
  --plots_dir path/to/processed_las \
  --csv_dir path/to/label_root \
  --las_pattern "*_optimized_*.las" \
  --overwrite
```

ถ้าต้องการเทียบกับ density baseline เดิมแบบใช้ train/val/test split ชุดเดียวกัน:

```bash
python biomass2/dataset_creation/create_yolo_multichannel_dataset.py \
  --plots_dir biomass1/notebooks_density/processed \
  --csv_dir biomass1/dataset/ข้อมูลแปลง \
  --output_dir biomass2/dataset_creation/yolov11/dataset_multichannel \
  --use_rotated \
  --split_from_dataset biomass1/notebooks_density/dataset_creation/yolov11/dataset \
  --overwrite

python biomass2/dataset_creation/create_yolo_multichannel_dataset.py \
  --plots_dir "biomass1/notebooks_density/processed" \
  --csv_dir "biomass1/dataset/ข้อมูลแปลง" \
  --output_dir "biomass2/dataset_creation/yolov11/dataset_multichannel" \
  --use_rotated \
  --split_from_dataset "biomass1/notebooks_density/dataset_creation/yolov11/dataset" \
  --image_size 320 \
  --pixel_size 0.125 \
  --box_size 2.0 \
  --overwrite \
```

## Train

```bash
python biomass2/yolov11/train_multichannel.py \
  --data biomass2/dataset_creation/yolov11/dataset_multichannel/data.yaml \
  --epochs 100 \
  --imgsz 320 \
  --batch 8 \
  --device 0 \
  --name "multichannel_density_hag_dbh"
```

ผลลัพธ์จะอยู่ที่:

```text
biomass2/yolov11/runs/detect/multichannel_density_hag_dbh/
```

ถ้าจะเทียบกับ `biomass1` ให้ใช้ split เดียวกัน, image size, box size, epochs และ augmentation ให้เหมือนกัน แล้วเปรียบเทียบ mAP, precision, recall และผลตำแหน่งต้นที่ตรวจเจอใน validation/test set เดียวกัน
