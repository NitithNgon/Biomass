# ปัญหาการตัด Point Cloud ด้วย Minkowski Sum

## สรุปปัญหา

เมื่อใช้สคริปต์ `filter_pointcloud_by_odom_optimized.py` กับ buffer 1m พบว่า:
- ✗ ผลลัพธ์ได้รูปร่างที่เป็น**สี่เหลี่ยมแหลม** (sharp, angular)
- ✗ ไม่ได้รูปร่างที่**กลมและเรียบ** (smooth, rounded) ตามที่ควรจะเป็น

## สาเหตุของปัญหา

สคริปต์ `filter_pointcloud_by_odom_optimized.py` ใช้วิธี **"Direct Normalization"** หรือ **"Edge Offset Method"**:

```
1. เลื่อนแต่ละขอบของ hull ออกไปตาม normal vector
2. หา intersection ของขอบที่ถูก offset
3. ได้รูปหลายเหลี่ยมใหม่ที่มีขนาดใหญ่ขึ้น
```

**ปัญหา:** วิธีนี้ไม่ใช่ Minkowski Sum แบบแท้จริง!
- มุมของรูปยังคงแหลม (sharp corners)
- ไม่มีส่วนโค้งมน (no arc segments)
- ผลลัพธ์ยังคงเป็นรูปหลายเหลี่ยมที่มีขอบตรง

## Minkowski Sum แบบแท้จริง

**True Minkowski Sum** ต้องมี:

1. **วงกลมที่ vertex แต่ละจุด** - วาดวงกลมรัศมี buffer_distance ที่ทุกจุดยอด
2. **Arc segments** - เชื่อมวงกลมด้วยส่วนโค้ง
3. **ผลลัพธ์กลมเรียบ** - ได้รูปร่างที่มีขอบโค้งมน

### ภาพเปรียบเทียบ

```
Direct Normalization (ผิด):          True Minkowski Sum (ถูก):
     /\                                   ___
    /  \                                 /   \
   /____\                               |     |
   แหลม                                 โค้งมน

   ___                                  ____
  |   |                                /    \
  |___|                               (      )
  มุมแหลม                              \____/
                                       มนเรียบ
```

## วิธีแก้ไข

### วิธีที่ 1: ใช้สคริปต์ใหม่ (แนะนำ)

ผมได้สร้างสคริปต์ใหม่ `filter_pointcloud_by_odom_minkowski.py` ที่ใช้ True Minkowski Sum:

```bash
# ติดตั้ง Shapely (ถ้ายังไม่มี)
pip install shapely

# ใช้สคริปต์ใหม่
python scripts/python/preprocessing/filter_pointcloud_by_odom_minkowski.py \
  input/scans_rotated.las \
  output/odom_ska-ls-h201.txt \
  -o output/scans_minkowski_1m.las \
  --buffer 1.0 \
  --arc-points 16 \
  -p
```

**พารามิเตอร์สำคัญ:**
- `--buffer`: ระยะขยาย (เมตร) - default: 0.5
- `--arc-points`: จำนวนจุดต่อส่วนโค้ง - ยิ่งมากยิ่งเรียบ (default: 16)
- `--grid-size`: ขนาด grid cell (เมตร) - default: 0.5
- `-p`: แสดงความคืบหน้า

### วิธีที่ 2: เปรียบเทียบผลลัพธ์

ทดสอบทั้งสองวิธีเพื่อเห็นความแตกต่าง:

```bash
# วิธีเดิม (Direct Normalization - แหลม)
python scripts/python/preprocessing/filter_pointcloud_by_odom_optimized.py \
  input/scans_rotated.las \
  output/odom_ska-ls-h201.txt \
  -o output/scans_direct_norm_1m.las \
  --buffer 1.0 -p

# วิธีใหม่ (True Minkowski - เรียบ)
python scripts/python/preprocessing/filter_pointcloud_by_odom_minkowski.py \
  input/scans_rotated.las \
  output/odom_ska-ls-h201.txt \
  -o output/scans_minkowski_1m.las \
  --buffer 1.0 --arc-points 16 -p
```

จากนั้นเปรียบเทียบใน CloudCompare หรือซอฟต์แวร์ดู point cloud อื่นๆ

## รายละเอียดทางเทคนิค

### Direct Normalization Method (วิธีเดิม)

```python
def expand_hull_direct_normalization(hull_vertices, buffer):
    # 1. สำหรับแต่ละขอบ:
    for edge in hull_edges:
        # คำนวณ normal vector
        normal = perpendicular(edge)
        # เลื่อนขอบออกไป
        offset_edge = edge + normal * buffer
    
    # 2. หา intersection ของขอบที่ offset
    # ได้รูปหลายเหลี่ยมใหม่ที่ยังคงแหลม
```

### True Minkowski Sum Method (วิธีใหม่)

```python
def expand_hull_minkowski_sum(hull_vertices, buffer, arc_points):
    # ใช้ Shapely's buffer method
    poly = Polygon(hull_vertices)
    
    # Buffer = Minkowski sum กับวงกลม
    buffered = poly.buffer(
        buffer,
        resolution=arc_points,  # จุดต่อส่วนโค้ง
        cap_style=1,   # round caps (ปลายโค้ง)
        join_style=1   # round joins (มุมโค้ง)
    )
    
    # ได้รูปร่างที่เรียบและมีส่วนโค้ง
```

### Shapely's Buffer Algorithm

Shapely ใช้อัลกอริทึมที่:
1. วางวงกลมที่ทุกจุดยอด
2. สร้างส่วนโค้งเชื่อมระหว่างวงกลม
3. รวมทุกอย่างเป็นรูปเดียว (union)
4. สร้างเส้นขอบที่เรียบ

## ประสิทธิภาพ

| วิธี | ความเร็ว | รูปร่างผลลัพธ์ | ความถูกต้อง |
|------|----------|----------------|-------------|
| Direct Normalization | ⚡ เร็ว | ❌ แหลม | ❌ ไม่ใช่ Minkowski แท้ |
| True Minkowski (Shapely) | ⚡ เร็ว | ✅ เรียบ | ✅ Minkowski Sum แท้ |
| Manual Minkowski | 🐌 ช้ากว่า | ✅ เรียบ | ✅ Minkowski Sum แท้ |

**คำแนะนำ:** ใช้ Shapely เพราะเร็วและถูกต้อง

## การควบคุมความเรียบ

พารามิเตอร์ `--arc-points` ควบคุมความเรียบของส่วนโค้ง:

- **8 จุด/โค้ง**: เห็นเป็นส่วนๆ เล็กน้อย (เร็ว)
- **16 จุด/โค้ง**: เรียบดี (แนะนำ, default)
- **32 จุด/โค้ง**: เรียบมาก (ช้ากว่า)
- **64 จุด/โค้ง**: เกินความจำเป็น

```bash
# ทดลองค่าต่างๆ
python scripts/python/preprocessing/filter_pointcloud_by_odom_minkowski.py \
  input.las odom.txt -o output_smooth.las \
  --buffer 1.0 --arc-points 32 -p
```

## สรุปและข้อแนะนำ

### สิ่งที่ผิดพลาด
- ❌ ชื่อ "Direct Normalization" ทำให้เข้าใจผิดว่าเป็น Minkowski Sum
- ❌ วิธี offset edges ไม่สร้างส่วนโค้งที่มุม
- ❌ ผลลัพธ์ยังคงเป็นรูปหลายเหลี่ยมแหลม

### วิธีแก้ที่ถูกต้อง
- ✅ ใช้ `filter_pointcloud_by_odom_minkowski.py`
- ✅ ใช้ Shapely's buffer() ที่เป็น True Minkowski Sum
- ✅ ได้รูปร่างกลมเรียบตามที่ควรจะเป็น

### การใช้งานในอนาคต
```bash
# สำหรับ processed files ใหม่ๆ
python scripts/python/preprocessing/filter_pointcloud_by_odom_minkowski.py \
  yolov11/processed/ska-ls-h201_scans_optimized_0m_rotated.las \
  output/odom_ska-ls-h201.txt \
  -o yolov11/processed/ska-ls-h201_scans_optimized_1m_minkowski.las \
  --buffer 1.0 \
  --arc-points 16 \
  -p
```

## อ้างอิง

- Shapely Documentation: https://shapely.readthedocs.io/
- Minkowski Sum: https://en.wikipedia.org/wiki/Minkowski_addition
- Convex Hull: https://en.wikipedia.org/wiki/Convex_hull

---

**หมายเหตุ:** ถ้าต้องการความเร็วสูงสุดและยอมรับรูปร่างที่แหลมได้ ใช้ `filter_pointcloud_by_odom_optimized.py` 
ถ้าต้องการรูปร่างที่เรียบและถูกต้องทางคณิตศาสตร์ ใช้ `filter_pointcloud_by_odom_minkowski.py`
