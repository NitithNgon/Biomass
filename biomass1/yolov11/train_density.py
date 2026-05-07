#!/usr/bin/env python3
"""
Train YOLOv11 on Density Variant Dataset
Run from yolov11/yolov11/ directory
"""

from ultralytics import YOLO
import os

# เปลี่ยน working directory ให้ชี้มาที่โฟลเดอร์ของสคริปต์
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# โหลดโมเดลเริ่มต้น (pretrained) - ใช้ yolo11n
model = YOLO("../../yolo11n.pt")

# เทรนโมเดล
results = model.train(
    # ----------------- Dataset config -----------------
    data="/home/pun/Desktop/notebooks_density/dataset_creation/yolov11/dataset/data.yaml",   # path จากตำแหน่งสคริปต์
    epochs=100,
    imgsz=320,                          # ถ้า RAM พอจะลอง 640 ทีหลังก็ได้
    batch=8,
    name="density_v5_lightaug",         # ชื่อ run ใหม่
    patience=30,                        # early stopping

    # ----------------- Light Augmentation -----------------
    # ใช้แค่ 3 อันนี้ เพื่อกัน overfit แต่ไม่ทำลาย pattern
    degrees=15.0,       # หมุน ±15 องศา
    translate=0.05,     # เลื่อนสูงสุด 5% ของภาพ
    scale=0.10,         # ย่อ/ขยาย ±10%

    # ----------------- ปิด Aug ที่แรง/ทำลาย grid pattern -----------------
    shear=0.0,
    perspective=0.0,
    flipud=0.0,         # ไม่กลับหัว (ถ้า data จริงไม่กลับหัว)
    fliplr=0.0,         # ถ้าคิดว่ามุมมองซ้าย/ขวาเหมือนกัน จะใส่ 0.5 ก็ได้
    mosaic=0.0,
    mixup=0.0,
    cutmix=0.0,
    copy_paste=0.0,
    auto_augment="",    # ปิด randaugment / auto policy
    erasing=0.0,
    hsv_h=0.0,
    hsv_s=0.0,
    hsv_v=0.0,
    bgr=0.0,

    # ----------------- Device & Runtime -----------------
    device="mps",       # ใช้ GPU M1
    workers=4,
    save=True,
    plots=True,
    verbose=True,

    # ----------------- Optimization -----------------
    # optimizer=auto จะเลือก AdamW ให้เอง ค่าเหล่านี้ยังใช้เป็น hint ได้
    lr0=0.01,
    lrf=0.01,
    momentum=0.937,
    weight_decay=0.0005,
    warmup_epochs=3.0,
    close_mosaic=10,    # ไม่มีผลมากเพราะ mosaic=0 อยู่แล้ว
)

print("\n" + "=" * 60)
print("Training Complete!")
print("=" * 60)
print("Run name     : density_v5_lightaug")
print("Logs dir     : runs/detect/density_v5_lightaug/")
print("Best weights : runs/detect/density_v5_lightaug/weights/best.pt")
