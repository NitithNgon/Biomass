# 📋 คู่มือเตรียมไฟล์สำหรับ Dataset Creation

## 🎯 ขั้นตอนที่ 1: Batch Process Plots

ก่อนรัน `batch_process_plots.ipynb` ต้องเตรียมไฟล์และโครงสร้างโฟลเดอร์ดังนี้

---

## 📁 โครงสร้างโฟลเดอร์ที่ต้องการ

```
yolov11/
├── dataset/
│   └── ข้อมูลแปลง/
│       ├── ska-ls-h201/
│       │   ├── scans.pcd              ← ไฟล์ point cloud
│       │   ├── odom_ska-ls-h201.txt   ← ไฟล์ odometry
│       │   └── DBHaverage.csv         ← ไฟล์ tree labels (ใช้ในขั้นตอนถัดไป)
│       ├── ska-ls-h202/
│       │   ├── scans.pcd
│       │   ├── odom_ska-ls-h202.txt
│       │   └── DBHaverage.csv
│       └── ska-ls-hXXX/               ← แปลงอื่นๆ ตามรูปแบบเดียวกัน
│           ├── scans.pcd
│           ├── odom_ska-ls-hXXX.txt
│           └── DBHaverage.csv
│
├── processed/                         ← โฟลเดอร์ output (สร้างอัตโนมัติ)
│   ├── ska-ls-h201_scans_optimized_1m_rotated.las
│   ├── ska-ls-h202_scans_optimized_1m_rotated.las
│   └── ...
│
└── scripts/
    └── python/
        ├── tools/
        │   ├── convert_pcd_to_las.py
        │   └── rotate_pointcloud.py
        └── preprocessing/
            └── filter_pointcloud_by_odom_optimized.py
```

---

## 📦 ไฟล์ที่ต้องเตรียมสำหรับแต่ละแปลง

### 1. **scans.pcd** (Required)
- **คำอธิบาย:** Point cloud data ของแปลง
- **รูปแบบ:** PCD (Point Cloud Data) format
- **ขนาดโดยประมาณ:** ขึ้นอยู่กับขนาดแปลง (หลักสิบ MB - GB)
- **สร้างจาก:** LiDAR scanning device หรือ SLAM algorithm

### 2. **odom_[plot_name].txt** (Required)
- **คำอธิบาย:** Odometry trajectory (เส้นทางที่เดินสแกน)
- **รูปแบบ:** Text file ที่มีพิกัด XY ของเส้นทาง
- **ตัวอย่างข้อมูลใน file:**
  ```
  X,Y
  100.5,200.3
  100.7,200.5
  101.0,200.8
  ...
  ```
- **จุดประสงค์:** ใช้กรองจุดที่อยู่นอกเส้นทางสแกนออก

### 3. **DBHaverage.csv** (Required สำหรับขั้นตอน 2)
- **คำอธิบาย:** ตำแหน่งต้นไม้ (Tree positions)
- **รูปแบบ:** CSV file
- **คอลัมน์ที่ต้องมี:** `X`, `Y` (พิกัดของต้นไม้)
- **ตัวอย่าง:**
  ```csv
  TreeID,X,Y,DBH
  1,105.2,203.4,25.5
  2,107.8,205.1,30.2
  3,110.5,202.8,28.7
  ...
  ```

---

## ✅ Checklist การเตรียมข้อมูล

### ก่อนรัน batch_process_plots.ipynb:

- [ ] **สร้างโฟลเดอร์หลัก** `yolov11/dataset/ข้อมูลแปลง/`
- [ ] **จัดเรียงไฟล์แต่ละแปลง** ให้อยู่ในโฟลเดอร์ย่อยที่มีชื่อขึ้นต้นด้วย `ska-ls-`
- [ ] **ตรวจสอบ scans.pcd** ทุกแปลงว่ามีไฟล์และเปิดได้
- [ ] **ตรวจสอบ odom_*.txt** ว่าชื่อไฟล์ตรงกับชื่อแปลง
- [ ] **ติดตั้ง dependencies** ที่จำเป็น (laspy, numpy, pandas, etc.)
- [ ] **ตรวจสอบ Python scripts** ที่ notebook เรียกใช้ว่ามีอยู่ใน `scripts/python/`

---

## 🔧 การติดตั้ง Dependencies

```bash
# ติดตั้ง packages ที่จำเป็น
pip install laspy
pip install numpy pandas
pip install open3d  # สำหรับประมวลผล point cloud

# หรือติดตั้งจาก requirements.txt (ถ้ามี)
pip install -r requirements.txt
```

---

## 🚀 การรัน batch_process_plots.ipynb

เมื่อเตรียมไฟล์เรียบร้อยแล้ว:

1. **เปิด Jupyter Notebook:**
   ```bash
   jupyter notebook batch_process_plots.ipynb
   ```

2. **ปรับ parameters (ถ้าต้องการ):**
   - `buffer`: ระยะ buffer สำหรับ Minkowski expansion (default: 1.0m)
   - `grid_size`: ขนาด grid สำหรับ filtering (default: 0.5m)

3. **Run ทุก cells** ตามลำดับ

4. **ตรวจสอบ output** ใน `yolov11/processed/`:
   - จะได้ไฟล์ `*_scans_optimized_1m_rotated.las` สำหรับแต่ละแปลง

---

## 📊 Output ที่ได้

หลังจากรัน batch_process_plots.ipynb จะได้:

```
yolov11/processed/
├── ska-ls-h201_scans_optimized_1m_rotated.las
├── ska-ls-h202_scans_optimized_1m_rotated.las
├── ska-ls-h203_scans_optimized_1m_rotated.las
└── ... (ไฟล์อื่นๆ ตามจำนวนแปลง)
```

**ไฟล์ .las เหล่านี้จะใช้ในขั้นตอนถัดไป (create_yolo_dataset.ipynb)**

---

## ⚠️ ข้อควรระวัง

1. **ชื่อไฟล์ต้องตรงกัน:**
   - โฟลเดอร์: `ska-ls-h201`
   - Odometry: `odom_ska-ls-h201.txt`
   - ต้องตรงกันทุกตัวอักษร

2. **ขนาดไฟล์:**
   - Point cloud files อาจมีขนาดใหญ่ (หลาย GB)
   - ต้องมี disk space เพียงพอ

3. **Memory:**
   - การประมวลผล point cloud ใช้ RAM ค่อนข้างมาก
   - แนะนำให้มี RAM อย่างน้อย 8GB

4. **เวลาในการประมวลผล:**
   - แต่ละแปลงอาจใช้เวลา 2-5 นาที
   - ถ้ามีหลายแปลงอาจใช้เวลานาน

---

## 🔍 ตรวจสอบความถูกต้อง

หลังจากรันเสร็จ ควรตรวจสอบ:

✅ **มีไฟล์ output ครบทุกแปลงหรือไม่**
```bash
ls yolov11/processed/*.las | wc -l
```

✅ **ขนาดไฟล์ไม่ผิดปกติ (ไม่เป็น 0 KB)**
```bash
ls -lh yolov11/processed/*.las
```

✅ **เปิดไฟล์ .las ได้ด้วย CloudCompare หรือ software อื่น**

---

## 📞 หากมีปัญหา

### ❌ Error: "Missing scans.pcd"
- **สาเหตุ:** ไม่มีไฟล์ scans.pcd ในโฟลเดอร์แปลง
- **แก้ไข:** ตรวจสอบว่าได้วางไฟล์ไว้ถูกที่แล้ว

### ❌ Error: "Missing odom_*.txt"
- **สาเหตุ:** ชื่อไฟล์ odometry ไม่ตรงกับชื่อแปลง
- **แก้ไข:** เปลี่ยนชื่อไฟล์ให้ตรงรูปแบบ `odom_[plot_name].txt`

### ❌ Error: "Module not found"
- **สาเหตุ:** ยังไม่ได้ติดตั้ง dependencies
- **แก้ไข:** รัน `pip install [package_name]`

---

## ➡️ ขั้นตอนถัดไป

เมื่อได้ไฟล์ `.las` แล้ว พร้อมไปขั้นตอนที่ 2:
👉 **`01_create_yolo_dataset.ipynb`**

---

**อัปเดตล่าสุด:** 8 มกราคม 2026  
**เวอร์ชัน:** 1.0
