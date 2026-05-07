# 🔄 คู่มือ Data Augmentation

## 🎯 ขั้นตอนที่ 3: Augment Dataset

หลังจากสร้าง YOLO dataset แล้ว ขั้นตอนนี้จะเพิ่มจำนวนข้อมูล training ด้วย data augmentation

---

## 📌 ทำไมต้อง Augment?

### ปัญหาที่แก้ไข:
1. **ข้อมูล training น้อย** → เพิ่มจำนวนตัวอย่าง
2. **Model overfitting** → เพิ่มความหลากหลาย
3. **ทำนายไม่ดีในมุมมองต่างๆ** → ทำให้ robust มากขึ้น

### ผลลัพธ์ที่ได้:
- ✅ เพิ่มจำนวนตัวอย่าง training 4-8 เท่า
- ✅ Model เรียนรู้จากมุมมองและ orientation ที่หลากหลาย
- ✅ Accuracy และ generalization ดีขึ้น

---

## 📁 Input Structure

```
yolov11/dataset_output/
├── images/
│   ├── train/
│   │   └── density/              ← Augment เฉพาะ density variant
│   │       ├── ska-ls-h201.jpg
│   │       ├── ska-ls-h202.jpg
│   │       └── ...
│   ├── val/                      ← ไม่ augment
│   └── test/                     ← ไม่ augment
│
└── labels/
    ├── train/
    │   └── density/
    │       ├── ska-ls-h201.txt
    │       ├── ska-ls-h202.txt
    │       └── ...
    ├── val/
    └── test/
```

**หมายเหตุ:** Augment เฉพาะ **train set** เท่านั้น (ไม่ augment val/test)

---

## 🔧 Augmentation Techniques

### 1. **Rotation** (การหมุน)
- **องศา:** 90°, 180°, 270°
- **จุดประสงค์:** ทำให้โมเดลเรียนรู้ต้นไม้ในทุกมุม
- **ตัวอย่าง:**
  ```
  Original      → 0°
  Rotation 90°  → 90°
  Rotation 180° → 180°
  Rotation 270° → 270°
  ```

### 2. **Flip** (การพลิก)
- **แนวพลิก:** Horizontal, Vertical, Both
- **จุดประสงค์:** สร้างภาพสะท้อน
- **ตัวอย่าง:**
  ```
  Original           → Original image
  Horizontal flip    → ซ้าย-ขวาพลิก
  Vertical flip      → บน-ล่างพลิก
  Both flips         → พลิกทั้งสองแนว
  ```

---

## 📊 Augmentation Strategy

### Default Strategy (แนะนำ)
```python
augmentation_types = ['rotation', 'flip']
```

**ผลลัพธ์:**
- Original: 1 image
- Rotation (90°, 180°, 270°): +3 images
- Flip (H, V, Both): +3 images
- **Total:** 7 augmented versions ต่อ 1 original image

**ตัวอย่าง:**
```
Input:  14 training images
Output: 14 + (14 × 6) = 98 total images
```

---

## 🚀 วิธีการรัน

### ในโฟลเดอร์ scripts:
```bash
cd yolov11/scripts
python augment_density_only.py
```

### หรือใน Jupyter Notebook:
```python
# ใน augment_density_only.ipynb
dataset_dir = Path('dataset_0m_rotated')  # ← แก้ path นี้
img_dir = dataset_dir / 'images' / 'train' / 'density'
label_dir = dataset_dir / 'labels' / 'train' / 'density'

# Run augmentation
augmenter = YOLOAugmenter(preserve_originals=False)
for img_path in img_files:
    augmenter.augment_sample(
        img_path, label_path,
        img_dir, label_dir,
        ['rotation', 'flip']
    )
```

---

## ⚙️ Configuration

### Important Parameters

```python
preserve_originals = False    # False = เก็บ original (แนะนำ)
                             # True = ลบ original, เก็บแต่ augmented
```

**แนะนำ:** ใช้ `preserve_originals=False` เพื่อเก็บ original images ไว้

---

## 📊 Output Structure

### ก่อน Augmentation:
```
images/train/density/
├── ska-ls-h201.jpg                  (1 file)
└── ska-ls-h202.jpg                  (1 file)

labels/train/density/
├── ska-ls-h201.txt
└── ska-ls-h202.txt
```

### หลัง Augmentation:
```
images/train/density/
├── ska-ls-h201.jpg                  ← Original
├── ska-ls-h201_rot90.jpg            ← Rotation 90°
├── ska-ls-h201_rot180.jpg           ← Rotation 180°
├── ska-ls-h201_rot270.jpg           ← Rotation 270°
├── ska-ls-h201_fliph.jpg            ← Horizontal flip
├── ska-ls-h201_flipv.jpg            ← Vertical flip
├── ska-ls-h201_fliphv.jpg           ← Both flips
├── ska-ls-h202.jpg
├── ska-ls-h202_rot90.jpg
└── ... (same pattern for h202)

labels/train/density/
├── ska-ls-h201.txt                  ← Labels adjusted for each augmentation
├── ska-ls-h201_rot90.txt
├── ska-ls-h201_rot180.txt
├── ska-ls-h201_rot270.txt
├── ska-ls-h201_fliph.txt
├── ska-ls-h201_flipv.txt
├── ska-ls-h201_fliphv.txt
├── ska-ls-h202.txt
└── ... (same pattern for h202)
```

---

## 📈 Expected Results

### Example Output:
```
==========================================================
AUGMENTING DENSITY VARIANT - TRAIN SPLIT
==========================================================

Found 14 images in dataset_output/images/train/density

Processing: ska-ls-h201.jpg
  Created 6 augmented samples
Processing: ska-ls-h202.jpg
  Created 6 augmented samples
...

==========================================================
AUGMENTATION COMPLETE
==========================================================
Original samples: 14
Total samples created: 84
Final total: 98

✓ Density variant augmented successfully!
```

**คำอธิบาย:**
- Original: 14 images
- Created: 84 augmented images (14 × 6)
- **Final total:** 98 images (14 + 84)

---

## 🔍 Label Transformation

### Bounding Box Transformation

Labels ถูก transform ตาม augmentation:

#### Rotation 90°:
```
Original: x_center=0.5, y_center=0.3
After:    x_center=0.7, y_center=0.5
```

#### Horizontal Flip:
```
Original: x_center=0.3, y_center=0.5
After:    x_center=0.7, y_center=0.5  (x flipped)
```

#### Vertical Flip:
```
Original: x_center=0.5, y_center=0.3
After:    x_center=0.5, y_center=0.7  (y flipped)
```

**YOLOAugmenter จัดการ transformation อัตโนมัติ** ✅

---

## ✅ ตรวจสอบผลลัพธ์

### 1. นับจำนวนไฟล์
```bash
# ก่อน augmentation
ls images/train/density/*.jpg | wc -l
# Expected: ~14-20 images

# หลัง augmentation
ls images/train/density/*.jpg | wc -l
# Expected: ~98-140 images (7x original)
```

### 2. ตรวจสอบชื่อไฟล์
```bash
ls images/train/density/*.jpg | head -10
```

ต้องเห็นไฟล์ที่มี suffix:
- `_rot90.jpg`, `_rot180.jpg`, `_rot270.jpg`
- `_fliph.jpg`, `_flipv.jpg`, `_fliphv.jpg`

### 3. ตรวจสอบ labels
```bash
# ตรวจสอบว่ามี label ครบทุกภาพ
