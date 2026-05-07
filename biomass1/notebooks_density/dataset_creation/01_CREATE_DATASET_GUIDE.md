# 📊 คู่มือสร้าง YOLO Dataset

## 🎯 ขั้นตอนที่ 2: Create YOLO Dataset

หลังจากได้ไฟล์ `.las` จาก batch_process_plots แล้ว ขั้นตอนนี้จะแปลง point cloud เป็น YOLO format dataset

---

## 📁 โครงสร้าง Input ที่ต้องมี

```
yolov11/
├── processed/                         ← Output จากขั้นตอนที่ 1
│   ├── ska-ls-h201_scans_optimized_1m_rotated.las
│   ├── ska-ls-h202_scans_optimized_1m_rotated.las
│   └── ... (ไฟล์ .las อื่นๆ)
│
├── dataset/
│   └── ข้อมูลแปลง/
│       ├── ska-ls-h201/
│       │   └── DBHaverage.csv         ← Tree labels (X, Y coordinates)
│       ├── ska-ls-h202/
│       │   └── DBHaverage.csv
│       └── ...
│
└── scripts/
    └── python/
        └── tools/
            └── pointcloud_rasterization.py  ← Utility สำหรับ rasterization
```

---

## 📋 Input Files ที่จำเป็น

### 1. **LAS Files** (จากขั้นตอนที่ 1)
- **ไฟล์:** `*_scans_optimized_1m_rotated.las`
- **ตำแหน่ง:** `yolov11/processed/`
- **จำนวน:** ต้องมีอย่างน้อย 1 ไฟล์

### 2. **DBHaverage.csv** (Tree Labels)
- **ตำแหน่ง:** `yolov11/dataset/ข้อมูลแปลง/[plot_name]/`
- **รูปแบบข้อมูล:**
  ```csv
  TreeID,X,Y,DBH,Height
  1,105.234,203.456,25.5,15.2
  2,107.812,205.123,30.2,18.5
  3,110.543,202.891,28.7,16.8
  ```
- **คอลัมน์ที่จำเป็น:**
  - `X`: พิกัด X ของต้นไม้ (ตัวเลข)
  - `Y`: พิกัด Y ของต้นไม้ (ตัวเลข)
  - คอลัมน์อื่นๆ เป็น optional

---

## ⚙️ Parameters ที่สำคัญ

### Rasterization Parameters
```python
--image_size 320          # ขนาดภาพ output (pixels) - default: 320x320
--pixel_size 0.125        # ความละเอียดต่อ pixel (meters) - default: 0.125m
--area_size 40.0          # พื้นที่ความกว้าง (meters) - default: 40x40m
```

**การคำนวณ:**
- `area_size = image_size × pixel_size`
- ถ้า image_size=320 และ pixel_size=0.125 → area_size = 40m × 40m

### Bounding Box Parameters
```python
--box_size 2.0            # ขนาด bbox รอบต้นไม้ (meters) - default: 2.0m
```

**ความสัมพันธ์:**
- box_size = 2.0m → 16×16 pixels (ที่ pixel_size=0.125)
- box_size = 1.5m → 12×12 pixels
- box_size = 2.5m → 20×20 pixels

### Dataset Split Parameters
```python
--train_ratio 0.7         # สัดส่วน training set (70%)
--val_ratio 0.15          # สัดส่วน validation set (15%)
--test_ratio 0.15         # สัดส่วน test set (15%)
--seed 42                 # Random seed (สำหรับ reproducibility)
```

### Options
```python
--use_rotated             # ใช้ไฟล์ที่ rotate แล้ว (แนะนำ)
--create_variants         # สร้างภาพหลายแบบ (density, RGB, HAG)
--overwrite               # เขียนทับ dataset เก่า
```

---

## 🎨 Image Variants ที่สร้างได้

ถ้าใช้ `--create_variants` จะได้ภาพ 6 แบบ:

### 1. **density** (แนะนำ)
- **คำอธิบาย:** Point density map (จำนวนจุดต่อ pixel)
- **รูปแบบ:** Grayscale (0-255)
- **จุดเด่น:** Simple, fast, effective สำหรับ tree detection

### 2. **std** (z_std)
- **คำอธิบาย:** Standard deviation ของความสูง Z
- **จุดเด่น:** แสดงความผันผวนของความสูง

### 3. **mean** (z_mean)
- **คำอธิบาย:** ค่าเฉลี่ยของความสูง Z
- **จุดเด่น:** แสดงความสูงเฉลี่ยของพื้นที่

### 4. **density_std_mean**
- **คำอธิบาย:** RGB composite (R=density, G=std, B=mean)
- **จุดเด่น:** รวมข้อมูลหลายมิติ

### 5. **rgb_percentile**
- **คำอธิบาย:** RGB composite (R=z_p25, G=z_p50, B=z_p75)
- **จุดเด่น:** แสดง height percentiles

### 6. **hag** (Height Above Ground)
- **คำอธิบาย:** ความสูงเหนือพื้นดิน
- **จุดเด่น:** เหมาะสำหรับวิเคราะห์โครงสร้างต้นไม้

---

## 🚀 วิธีการรัน

### Option 1: Run with Default Settings (Density Only)
```bash
python create_yolo_dataset.ipynb \
  --plots_dir yolov11/processed \
  --csv_dir yolov11/dataset/ข้อมูลแปลง \
  --output_dir yolov11/dataset_output \
  --use_rotated
```

### Option 2: Run with All Variants
```bash
python create_yolo_dataset.ipynb \
  --plots_dir yolov11/processed \
  --csv_dir yolov11/dataset/ข้อมูลแปลง \
  --output_dir yolov11/dataset_output \
  --use_rotated \
  --create_variants
```

### Option 3: Custom Parameters
```bash
python create_yolo_dataset.ipynb \
  --plots_dir yolov11/processed \
  --csv_dir yolov11/dataset/ข้อมูลแปลง \
  --output_dir yolov11/dataset_output \
  --use_rotated \
  --image_size 640 \
  --pixel_size 0.0625 \
  --box_size 2.0 \
  --train_ratio 0.8 \
  --val_ratio 0.1 \
  --test_ratio 0.1 \
  --create_variants
```

---

## 📊 Output Structure

### Without Variants (Default)
```
yolov11/dataset_output/
├── images/
│   ├── train/
│   │   ├── ska-ls-h201.jpg
│   │   ├── ska-ls-h202.jpg
│   │   └── ...
│   ├── val/
│   │   └── ...
│   └── test/
│       └── ...
│
├── labels/
│   ├── train/
│   │   ├── ska-ls-h201.txt      ← YOLO format labels
│   │   ├── ska-ls-h202.txt
│   │   └── ...
│   ├── val/
│   │   └── ...
│   └── test/
│       └── ...
│
└── data.yaml                     ← YOLO config file
```

### With Variants (--create_variants)
```
yolov11/dataset_output/
├── images/
│   ├── train/
│   │   ├── density/
│   │   │   ├── ska-ls-h201.jpg
│   │   │   └── ...
│   │   ├── std/
│   │   ├── mean/
│   │   ├── density_std_mean/
│   │   ├── rgb_percentile/
│   │   └── hag/
│   ├── val/
│   │   └── (same structure)
│   └── test/
│       └── (same structure)
│
├── labels/
│   ├── train/
│   │   ├── density/
│   │   │   ├── ska-ls-h201.txt
│   │   │   └── ...
│   │   ├── std/
│   │   └── (same for other variants)
│   ├── val/
│   └── test/
│
├── data.yaml
├── data_density.yaml
├── data_std.yaml
├── data_mean.yaml
├── data_density_std_mean.yaml
├── data_rgb_percentile.yaml
└── data_hag.yaml
```

---

## 📝 YOLO Label Format

ไฟล์ `.txt` ในโฟลเดอร์ labels มีรูปแบบ:
```
<class_id> <x_center> <y_center> <width> <height>
```

**ตัวอย่าง:**
```
0 0.523456 0.678901 0.050000 0.050000
0 0.612345 0.734567 0.050000 0.050000
0 0.456789 0.512345 0.050000 0.050000
```

**คำอธิบาย:**
- `class_id`: 0 = tree (เริ่มที่ 0)
- `x_center, y_center`: พิกัดกึ่งกลาง bbox (normalized 0-1)
- `width, height`: ขนาด bbox (normalized 0-1)

---

## ✅ ตรวจสอบ Output

### 1. Check File Counts
```bash
# นับจำนวนภาพใน train/val/test
ls yolov11/dataset_output/images/train/*.jpg | wc -l
ls yolov11/dataset_output/images/val/*.jpg | wc -l
ls yolov11/dataset_output/images/test/*.jpg | wc -l

# ควรได้สัดส่วนตาม train_ratio, val_ratio, test_ratio
```

### 2. Verify Labels
```bash
# ตรวจสอบว่ามี label ครบทุกภาพ
diff <(ls images/train/*.jpg | wc -l) <(ls labels/train/*.txt | wc -l)
# ถ้าได้ 0 แสดงว่าจำนวนตรงกัน
```

### 3. Inspect Label Content
```bash
# ดู label ตัวอย่าง
head yolov11/dataset_output/labels/train/ska-ls-h201.txt
```

### 4. Check data.yaml
```bash
cat yolov11/dataset_output/data.yaml
```

---

## 📈 Statistics Example

หลังรันเสร็จจะแสดง statistics แบบนี้:

```
TRAIN:
  Plots: 14
  Trees: 234/250 (in bounds)
  Images: 14

VAL:
  Plots: 3
  Trees: 51/55 (in bounds)
  Images: 3

TEST:
  Plots: 3
  Trees: 48/52 (in bounds)
  Images: 3
```

**คำอธิบาย:**
- `234/250`: มี 250 ต้นไม้ทั้งหมด แต่ใน bbox เพียง 234 ต้น
- ต้นไม้ที่อยู่นอก bounds จะถูกข้ามไป

---

## ⚠️ ปัญหาที่อาจพบ

### ❌ "No matching LAS/CSV pairs found"
**สาเหตุ:** ชื่อแปลงใน LAS file ไม่ตรงกับชื่อโฟลเดอร์ใน csv_dir

**แก้ไข:**
- ตรวจสอบชื่อไฟล์: `ska-ls-h201_scans_optimized_1m_rotated.las`
- ต้องมีโฟลเดอร์: `ข้อมูลแปลง/ska-ls-h201/DBHaverage.csv`

### ❌ "No valid tree labels"
**สาเหตุ:** CSV file มี missing values หรือ format ไม่ถูกต้อง

**แก้ไข:**
```python
# ตรวจสอบ CSV
import pandas as pd
df = pd.read_csv('DBHaverage.csv')
print(df.head())
print(df.info())  # ดู data types และ missing values
```

### ❌ "All trees outside bounds"
**สาเหตุ:** ระบบพิกัดไม่ตรงกัน หรือ area_size เล็กเกินไป

**แก้ไข:**
- เพิ่ม `--area_size` เช่น จาก 40 เป็น 60
- ตรวจสอบระบบพิกัด LAS vs CSV ว่าตรงกันหรือไม่

---

## 💡 Tips & Best Practices

### 1. เลือก Image Variant ที่เหมาะสม
- **เริ่มต้น:** ใช้ `density` อย่างเดียวก่อน (simple & fast)
- **ทดลอง:** ถ้าผลลัพธ์ไม่ดี ลองใช้ variants อื่น
- **ประหยัด space:** ไม่ควร create_variants ทั้งหมดถ้าไม่ใช้

### 2. ปรับ Box Size ตามขนาดต้นไม้
- **ต้นเล็ก:** `--box_size 1.5` (12×12 px)
- **ต้นกลาง:** `--box_size 2.0` (16×16 px) ← default
- **ต้นใหญ่:** `--box_size 2.5` (20×20 px)

### 3. Dataset Split Ratio
- **มีข้อมูลน้อย (<20 plots):** 70/15/15 หรือ 70/20/10
- **มีข้อมูลปานกลาง (20-50 plots):** 70/15/15 ← default
- **มีข้อมูลเยอะ (>50 plots):** 80/10/10

### 4. Reproducibility
- ใช้ `--seed 42` เสมอเพื่อให้ split เหมือนเดิม
- บันทึก parameters ที่ใช้ไว้

---

## ➡️ ขั้นตอนถัดไป

เมื่อสร้าง dataset เสร็จแล้ว:

1. **ตรวจสอบ dataset** ด้วย `preview_density_labels.ipynb`
2. **Augment data** ด้วย `augment_density_only.ipynb`
3. **Train model** ด้วย `train_density.ipynb`

---

**อัปเดตล่าสุด:** 8 มกราคม 2026  
**เวอร์ชัน:** 1.0
