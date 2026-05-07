# 📦 คู่มือการโอนไฟล์ไปเครื่องอื่น

## 🎯 วัตถุประสงค์
คู่มือนี้อธิบายว่าต้องคัดลอกไฟล์อะไรบ้างเพื่อโอน notebooks และ dataset ไปใช้บนเครื่องอื่น

---

## 📋 รายการไฟล์ที่ต้องคัดลอก

### 1. โฟลเดอร์หลัก (บังคับ) ✅

```bash
notebooks_density/              # ← Jupyter notebooks ทั้งหมด
├── QUICK_START.md
├── README.md
├── TRANSFER_GUIDE.md          # ← ไฟล์นี้
├── dataset_creation/
├── training/
└── testing/
```

### 2. Scripts และ Utilities (บังคับ) ✅

```bash
yolov11/scripts/               # ← scripts ที่ notebooks ใช้
├── create_yolo_dataset.py
├── batch_process_plots.py
├── augment_density_only.py
├── preview_density_labels.py
└── ... (ไฟล์อื่นๆ)

scripts/python/core/           # ← core utilities
└── pjfunc.py

scripts/python/tools/          # ← additional tools
└── pointcloud_rasterization.py
```

### 3. Dataset (ถ้ามีแล้ว) 📊

**ตัวเลือก A: Dataset สำเร็จรูป (แนะนำ)**
```bash
yolov11/yolov11/dataset/       # ← Dataset ที่สร้างเสร็จแล้ว
├── data_density.yaml          # ← config file
├── images/
│   ├── train/density/         # ← รูป training
│   ├── val/density/           # ← รูป validation
│   └── test/density/          # ← รูป testing
└── labels/
    ├── train/density/         # ← label training
    ├── val/density/           # ← label validation
    └── test/density/          # ← label testing
```

**ตัวเลือก B: ไฟล์ต้นฉบับ (ถ้าจะสร้าง dataset ใหม่)**
```bash
input/                         # ← ไฟล์ input ต้นฉบับ
├── DBHaverage.csv            # ← ข้อมูลต้นไม้
└── [your_scan].las           # ← Point cloud files

yolov11/processed/            # ← ไฟล์ที่ประมวลผลแล้ว
└── *.las                     # ← LAS files ที่พร้อมใช้
```

### 4. Dependencies (บังคับ) ✅

```bash
requirements.txt              # ← Python packages ที่ต้องใช้
```

### 5. Pre-trained Models (ถ้าต้องการ) 🤖

```bash
yolo11n.pt                    # ← YOLOv11 nano model
yolo11s.pt                    # ← YOLOv11 small model

# หรือ trained models ของคุณ
runs/detect/density_v*/       # ← โมเดลที่เทรนแล้ว
└── weights/
    ├── best.pt
    └── last.pt
```

---

## 📦 วิธีการคัดลอก

### ขั้นตอนที่ 1: สร้างโฟลเดอร์ปลายทาง

```bash
# บนเครื่องต้นทาง (เครื่องปัจจุบัน)
cd /Users/songkarn/locarb/biomass/handheld-lidar-slam-toolbox

# สร้าง transfer package
mkdir -p transfer_package
```

### ขั้นตอนที่ 2: คัดลอกไฟล์ที่จำเป็น

```bash
# 1. Copy notebooks
cp -r notebooks_density transfer_package/

# 2. Copy scripts
mkdir -p transfer_package/yolov11/scripts
cp -r yolov11/scripts/*.py transfer_package/yolov11/scripts/

# 3. Copy core utilities
mkdir -p transfer_package/scripts/python/core
cp scripts/python/core/pjfunc.py transfer_package/scripts/python/core/

mkdir -p transfer_package/scripts/python/tools
cp scripts/python/tools/pointcloud_rasterization.py transfer_package/scripts/python/tools/

# 4. Copy requirements
cp requirements.txt transfer_package/

# 5. Copy YOLO models (ถ้ามี)
cp yolo11*.pt transfer_package/ 2>/dev/null || :
```

### ขั้นตอนที่ 3: คัดลอก Dataset (เลือกตัวเลือก)

**ตัวเลือก A: Copy Dataset สำเร็จรูป** (แนะนำ - ประหยัดเวลา)
```bash
# Copy dataset ที่สร้างเสร็จแล้ว
cp -r yolov11/yolov11/dataset transfer_package/yolov11/yolov11/
```

**ตัวเลือก B: Copy ไฟล์ต้นฉบับ** (ถ้าต้องการสร้าง dataset ใหม่)
```bash
# Copy input files
mkdir -p transfer_package/input
cp input/DBHaverage.csv transfer_package/input/
cp input/*.las transfer_package/input/

# Copy processed files
mkdir -p transfer_package/yolov11/processed
cp yolov11/processed/*.las transfer_package/yolov11/processed/
```

### ขั้นตอนที่ 4: คัดลอกโมเดลที่เทรนแล้ว (ถ้ามี)

```bash
# Copy trained models
cp -r runs/detect/density_v* transfer_package/ 2>/dev/null || :
```

### ขั้นตอนที่ 5: สร้างไฟล์ ZIP

```bash
# สร้าง zip file
cd transfer_package
zip -r ../density_notebooks_package.zip .
cd ..

echo "✅ Package created: density_notebooks_package.zip"
```

---

## 🚚 โอนไฟล์ไปเครื่องอื่น

### วิธีที่ 1: USB Drive
```bash
# Copy ไฟล์ zip ไปยัง USB
cp density_notebooks_package.zip /Volumes/YOUR_USB/
```

### วิธีที่ 2: Cloud Storage (Google Drive, Dropbox, etc.)
```bash
# Upload ไฟล์ zip ไปยัง cloud
# จากนั้น download บนเครื่องใหม่
```

### วิธีที่ 3: Network Transfer (SCP)
```bash
# Transfer ผ่าน network
scp density_notebooks_package.zip user@target-machine:/path/to/destination/
```

---

## 💻 ติดตั้งบนเครื่องใหม่

### ขั้นตอนที่ 1: แตกไฟล์

```bash
# บนเครื่องปลายทาง
mkdir density_project
cd density_project
unzip density_notebooks_package.zip
```

### ขั้นตอนที่ 2: ติดตั้ง Dependencies

```bash
# สร้าง virtual environment (แนะนำ)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# หรือ
venv\Scripts\activate     # Windows

# ติดตั้ง packages
pip install -r requirements.txt

# ติดตั้ง packages เพิ่มเติม
pip install jupyter notebook ipykernel
```

### ขั้นตอนที่ 3: ตรวจสอบโครงสร้าง

```bash
# ตรวจสอบว่าไฟล์ครบถ้วน
ls -la notebooks_density/
ls -la yolov11/scripts/
ls -la yolov11/yolov11/dataset/  # ถ้ามี dataset
```

### ขั้นตอนที่ 4: เริ่มใช้งาน

```bash
# เปิด Jupyter Notebook
cd notebooks_density
jupyter notebook

# เปิด QUICK_START.md แล้วเริ่มใช้งาน
```

---

## ⚙️ แก้ไข Paths ใน Notebooks

หลังจากโอนไปเครื่องใหม่ ต้องแก้ไข paths ในแต่ละ notebook:

### ใน Dataset Creation Notebooks:
```python
# แก้ไข paths เหล่านี้
BASE_DIR = "/NEW/PATH/TO/PROJECT"           # ← แก้เป็น path ใหม่
INPUT_LAS = "input/your_file.las"
CSV_FILE = "input/DBHaverage.csv"
OUTPUT_DIR = "yolov11/yolov11/dataset"
```

### ใน Training Notebooks:
```python
# แก้ไข paths เหล่านี้
DATASET_YAML = "yolov11/yolov11/dataset/data_density.yaml"  # ← แก้เป็น path ใหม่
MODEL_PATH = "yolo11n.pt"
PROJECT_NAME = "runs/detect"
```

### ใน Testing Notebooks:
```python
# แก้ไข paths เหล่านี้
MODEL_PATH = "runs/detect/density_v*/weights/best.pt"  # ← แก้เป็น path ใหม่
TEST_IMAGES = "yolov11/yolov11/dataset/images/test/density"
```

---

## 📊 ขนาดไฟล์โดยประมาณ

| รายการ | ขนาด | จำเป็น |
|--------|------|--------|
| notebooks_density/ | ~100 KB | ✅ บังคับ |
| yolov11/scripts/ | ~500 KB | ✅ บังคับ |
| scripts/python/core/ | ~50 KB | ✅ บังคับ |
| requirements.txt | ~5 KB | ✅ บังคับ |
| yolo11n.pt | ~6 MB | ⚠️ แนะนำ |
| yolo11s.pt | ~22 MB | ⚠️ แนะนำ |
| Dataset (images + labels) | ~100-500 MB | 📊 ถ้ามี |
| Input LAS files | ~50-200 MB/file | 📊 ถ้าจะสร้างใหม่ |
| Trained models | ~6-25 MB/model | 🤖 ถ้ามี |

**รวมทั้งหมด (ประมาณการ):** 200 MB - 1 GB

---

## ✅ Checklist การโอนไฟล์

ใช้ checklist นี้เพื่อตรวจสอบว่าคัดลอกไฟล์ครบถ้วน:

### ไฟล์พื้นฐาน (บังคับ)
- [ ] `notebooks_density/` ทั้งโฟลเดอร์
- [ ] `yolov11/scripts/` ทั้งโฟลเดอร์
- [ ] `scripts/python/core/pjfunc.py`
- [ ] `scripts/python/tools/pointcloud_rasterization.py`
- [ ] `requirements.txt`

### Dataset (เลือก 1 ใน 2)
- [ ] **ตัวเลือก A:** `yolov11/yolov11/dataset/` ทั้งโฟลเดอร์ (dataset สำเร็จรูป)
- [ ] **ตัวเลือก B:** `input/` และ `yolov11/processed/` (สร้าง dataset ใหม่)

### Pre-trained Models (แนะนำ)
- [ ] `yolo11n.pt` หรือ `yolo11s.pt`

### Trained Models (ถ้ามี)
- [ ] `runs/detect/density_v*/weights/best.pt`

### บนเครื่องใหม่
- [ ] แตกไฟล์ zip เรียบร้อย
- [ ] ติดตั้ง dependencies เรียบร้อย
- [ ] แก้ไข paths ใน notebooks แล้ว
- [ ] ทดสอบเปิด Jupyter Notebook ได้
- [ ] ทดสอบรัน notebook ตัวอย่างได้

---

## 🔧 Tips & Troubleshooting

### 1. ไฟล์ใหญ่เกินไป
```bash
# ถ้าไฟล์ zip ใหญ่เกิน ให้แยก dataset ออกมา
zip -r notebooks_only.zip notebooks_density/ yolov11/scripts/ scripts/ requirements.txt
zip -r dataset_only.zip yolov11/yolov11/dataset/
```

### 2. ลืมคัดลอกไฟล์บางอัน
```bash
# ตรวจสอบว่าขาดไฟล์อะไร
ls -R notebooks_density/
ls -R yolov11/scripts/
```

### 3. Import Error บนเครื่องใหม่
```bash
# ติดตั้ง package ที่ขาด
pip install laspy numpy pandas ultralytics opencv-python
```

---

## 📞 ติดต่อ / ช่วยเหลือ

หากมีปัญหาการโอนไฟล์:
1. ตรวจสอบ checklist ข้างบน
2. อ่าน QUICK_START.md
3. ตรวจสอบ paths ใน notebooks ทุกไฟล์

---

**สร้างเมื่อ:** 2025-12-11  
**เวอร์ชัน:** 1.0  
**วัตถุประสงค์:** โอน notebooks และ dataset ไปใช้บนเครื่องอื่น
