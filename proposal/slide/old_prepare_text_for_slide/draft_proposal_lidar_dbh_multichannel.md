# Draft Proposal Presentation

หัวข้อเสนอ: **การแบ่งแยกต้นไม้รายต้นจากข้อมูล Handheld LiDAR Point Cloud สำหรับประเมินค่า DBH ในสวนยางพาราโดยใช้ Multi-channel CNN**

เวอร์ชันนี้จัดเป็นโครงสไลด์ 15 หน้า ตามแนวตัวอย่าง proposal presentation: เริ่มจากที่มา, literature, research gap, objective, methodology, experiment, evaluation, planning

---

## Slide 1: Title

**การแบ่งแยกต้นไม้รายต้นจากข้อมูล Handheld LiDAR Point Cloud สำหรับประเมินค่า DBH ในสวนยางพาราโดยใช้ Multi-channel CNN**

Individual Tree Segmentation from Handheld LiDAR Point Clouds for DBH Estimation in Rubber Plantations using Multi-channel CNN

เสนอโดย: [ชื่อ-รหัสนิสิต]  
อาจารย์ที่ปรึกษา: [ชื่ออาจารย์]  
Department of Computer Engineering, Chulalongkorn University

Speaker note:
งานนี้สนใจขั้นตอน individual tree segmentation เพราะเป็นขั้นตอนต้นน้ำของการหาค่า DBH รายต้น หากแยกต้นผิดหรือรวมหลายต้นเป็นต้นเดียว ค่า DBH และข้อมูล inventory ต่อจากนั้นจะผิดตามไปด้วย

---

## Slide 2: Motivation

**Forest inventory needs tree-level measurement**

- ค่า DBH เป็นข้อมูลสำคัญสำหรับ forest inventory, biomass/carbon estimation และการติดตามการเติบโตของต้นไม้
- การวัดด้วยมือใช้เวลาและแรงงานสูง โดยเฉพาะเมื่อมีหลายแปลง
- Handheld LiDAR เก็บข้อมูล 3D รอบลำต้นได้เร็ว และเหมาะกับพื้นที่ใต้เรือนยอด
- bottleneck สำคัญคือการแยก point cloud ออกเป็นต้นไม้รายต้นอย่างถูกต้อง

Speaker note:
จุดขายของงานไม่ใช่แค่เอา deep learning มาใช้ แต่คือการทำให้กระบวนการจากการสแกนสวนยางไปสู่ DBH รายต้นมีความอัตโนมัติและวัดผลได้ชัดเจน

---

## Slide 3: Problem Statement

**จาก point cloud 12 แปลง ไปสู่ต้นไม้รายต้นและ DBH**

Input:

- point cloud ของสวนยางพารา 12 แปลง
- ground truth ตำแหน่งต้นไม้และค่า DBH รายต้น

Output:

- ตำแหน่ง/ขอบเขตของต้นไม้แต่ละต้น
- ค่า DBH ที่คำนวณจากจุดบริเวณ breast height

Challenges:

- ความหนาแน่นของจุดไม่สม่ำเสมอจากแนวการเดินสแกน
- ลำต้นถูกบังบางส่วนจากกิ่ง ใบ วัชพืช หรือการสแกนไม่ครบด้าน
- ต้นยางเรียงเป็นแถว ทำให้ตำแหน่งใกล้กันและเกิดการรวมต้นได้
- วิธีที่ทำงานดีในป่าธรรมชาติอาจไม่เหมาะกับสวนยางพารา

---

## Slide 4: Related Work Overview

**กลุ่มวิธีที่เกี่ยวข้อง**

- Classical point-cloud processing: ground removal, trunk extraction, clustering, circle/cylinder fitting
- Handheld/mobile LiDAR DBH: segment/track trees, accumulate scans, fit circle/cylinder at breast height
- Large-scale MLS inventory: semantic segmentation เช่น ForestSPG ตามด้วย stem mapping และ circle fitting
- Change detection / occupancy grid: แยกต้นไม้รายต้นก่อน แล้วประเมิน DBH/height และการเปลี่ยนแปลงรายต้น
- Deep learning on 3D point cloud: TreeLearn ทำ semantic + instance segmentation โดยตรงบน forest point cloud
- Agricultural/forestry benchmark: TreeScope ให้ LiDAR data, semantic labels และ field-measured tree diameters

Key references:

- Proudman et al. (2021), Online DBH estimation using handheld LiDAR
- Liu et al. (2021), Single tree segmentation and DBH estimation with mobile LiDAR
- Shao et al. (2024), Large-scale inventory in natural forests with mobile LiDAR point clouds
- Cheng et al. (2023), TreeScope dataset
- Henrich et al. (2024), TreeLearn

---

## Slide 5: Research Gap

**ช่องว่างที่งานนี้ต้องการตอบ**

- งานเดิมมักแยก pipeline เป็น 3 ขั้น: semantic segmentation, stem mapping/instance segmentation และ DBH fitting
- error ของ DBH มักเกิดจากการแยกต้นผิด, ลำต้นถูกบัง, slice ที่ระดับอกมีจุดไม่ครบวง หรือมีกิ่ง/ใบปะปน
- วิธี rule-based ต้องตั้งค่า radius, density threshold, voxel size หรือ RANSAC setting ให้เหมาะกับสภาพข้อมูล
- TreeLearn มี performance ดีและลดการพึ่งกฎมือ แต่ต้องใช้ 3D sparse CNN, GPU/VRAM และข้อมูล fine-tuning เมื่อ domain เปลี่ยน
- baseline แบบ single-channel density image เบาและใช้กับ YOLO/CNN ได้ง่าย แต่ทิ้งข้อมูลแนวดิ่งและสัญญาณบริเวณ DBH
- ยังไม่ชัดเจนว่า multi-channel 2D CNN จะเพิ่ม accuracy ได้แค่ไหนโดยยังคง runtime/resource ต่ำในสวนยางพารา

Speaker note:
research gap หลักคือ trade-off ระหว่าง accuracy กับ resource usage: วิธี 3D โดยตรงอาจแม่นกว่าแต่หนักกว่า ส่วน 2D density เบากว่าแต่ข้อมูลหาย จึงเสนอ multi-channel เป็นทางกลาง

---

## Slide 6: Research Objective

**วัตถุประสงค์ของงานวิจัย**

1. พัฒนา pipeline สำหรับ individual tree segmentation จาก handheld LiDAR point cloud ของสวนยางพาราโดยใช้ multi-channel CNN
2. เปรียบเทียบความถูกต้องของ multi-channel CNN กับ single-channel CNN baseline และวิธี point-cloud-based เช่น TreeLearn
3. ประเมินผลกระทบต่อการประมาณค่า DBH รายต้นเมื่อใช้ผล segmentation จากแต่ละวิธี
4. เปรียบเทียบประสิทธิภาพด้าน runtime, memory/VRAM usage และความง่ายในการนำไปใช้งาน

---

## Slide 7: Research Questions and Hypotheses

**Research questions**

- RQ1: multi-channel CNN ให้ precision, recall และ F1 ของการตรวจจับต้นไม้รายต้นดีกว่า single-channel density image หรือไม่
- RQ2: เมื่อใช้ข้อมูลชุดเดียวกัน multi-channel CNN มี accuracy เทียบกับ TreeLearn ได้มากน้อยเพียงใด
- RQ3: multi-channel CNN ลด runtime และการใช้ทรัพยากรเมื่อเทียบกับวิธี 3D point-cloud-based ได้หรือไม่
- RQ4: segmentation error ส่งผลต่อ DBH error มากน้อยเพียงใด

**Hypotheses**

- H1: การเพิ่มช่อง `hag_p95` และ `dbh_band_density` จะช่วยลด false positive/false negative เมื่อเทียบกับ density-only
- H2: multi-channel CNN จะใช้ทรัพยากรน้อยกว่า TreeLearn ในขั้น inference
- H3: DBH error จะลดลงเมื่อ segmentation แยกต้นถูกต้องมากขึ้น

---

## Slide 8: Dataset and Ground Truth

**Rubber plantation point clouds**

- จำนวนข้อมูล: 12 point clouds จากสวนยางพารา 12 แปลง
- รูปแบบข้อมูล: LAS/PCD ที่ผ่าน preprocessing เช่น filtering และ rotation
- ground truth: ตำแหน่งต้นไม้ X/Y และค่า DBH รายต้นจากไฟล์ CSV
- data split: แบ่ง train/validation/test ระดับ plot เพื่อป้องกัน leakage ระหว่างแปลง

Planned controls:

- ใช้ split seed เดียวกันทุกวิธี
- ใช้ image size, pixel size, box size และ augmentation setting เดียวกันระหว่าง single-channel และ multi-channel
- ประเมินทุกวิธีบน test plots ชุดเดียวกัน

---

## Slide 9: Proposed System Overview

**ภาพรวม pipeline**

1. Handheld LiDAR scan
2. Point cloud preprocessing
3. Feature rasterization
4. Individual tree detection/segmentation
5. Extract points around each predicted tree
6. DBH estimation by fitting circle/cylinder at breast height band
7. Evaluation against ground truth

Text diagram:

`Point cloud -> Raster features -> CNN/YOLO -> tree centers/boxes -> trunk point crop -> DBH fitting -> metrics`

Speaker note:
ใน proposal ควรชี้ให้เห็นว่า multi-channel CNN อยู่ตรงส่วน segmentation เท่านั้น ส่วน DBH fitting เป็น downstream step ที่ใช้เปรียบเทียบผลกระทบของ segmentation

---

## Slide 10: Multi-channel CNN Input

**Synthetic RGB from physical LiDAR features**

Current design:

- R = `density`: จำนวนจุดในแต่ละ top-view grid cell
- G = `hag_p95`: 95th percentile ของ height above ground ใน cell
- B = `dbh_band_density`: จำนวนจุดในช่วงความสูงเหนือพื้น 1.0-1.6 m

Why these channels:

- `density` แทน spatial occupancy และแนวลำต้น/เรือนยอด
- `hag_p95` เพิ่มบริบทโครงสร้างแนวดิ่งและความสูงของพุ่ม/ลำต้น
- `dbh_band_density` เน้นสัญญาณบริเวณ breast height ที่เกี่ยวข้องกับ DBH โดยตรง

Implementation note:

- ใช้เป็น RGB image เพื่อ train กับ YOLO/CNN pipeline เดิมได้
- ปิด color augmentation เพราะสีไม่ใช่สีภาพจริง แต่เป็น feature channel
- ช่วง 1.0-1.6 m เป็นช่วงกว้างรอบ breast height เพื่อรองรับความคลาดเคลื่อนของ ground estimation และความต่างของมาตรฐาน DBH 1.3-1.4 m

---

## Slide 11: Baselines and Comparison Methods

**Methods to compare**

1. Single-channel CNN baseline
   - top-view density image
   - YOLO/CNN detection เหมือนงานเดิม

2. Proposed multi-channel CNN
   - density + height feature + DBH-band feature
   - train/evaluate ด้วย split และ hyperparameters ที่ควบคุมให้เหมือน baseline

3. TreeLearn
   - deep learning instance segmentation บน point cloud โดยตรง
   - ใช้ pretrained model หรือ fine-tune หาก annotation เพียงพอ

4. Point-cloud processing baseline
   - ground filtering + trunk extraction + clustering + circle/cylinder fitting
   - อ้างอิงแนวคิดจากงาน mobile LiDAR / RMLS / occupancy-grid literature

5. Optional comparison from TreeScope/SLOAM literature
   - ใช้เป็น reference ว่าวิธีด้าน robotics/forest inventory ประเมิน stem mapping และ DBH อย่างไร

---

## Slide 12: Experiment Design

**Controlled experiments**

- Experiment 1: single-channel vs multi-channel CNN
- Experiment 2: channel ablation
  - density only
  - density + hag_p95
  - density + dbh_band_density
  - density + hag_p95 + dbh_band_density
- Experiment 3: multi-channel CNN vs TreeLearn on the same test plots
- Experiment 4: DBH estimation using segmented/detected trees from each method
  - single slice circle fitting
  - multi-height bins + RANSAC/outlier rejection
- Experiment 5: efficiency benchmark
  - preprocessing time
  - inference time per plot
  - peak RAM/VRAM
  - model size

---

## Slide 13: Evaluation Metrics

**Tree detection / individual tree segmentation**

- Precision, Recall, F1-score
- Tree Detection Rate (TDR)
- tree count error per plot
- center localization error after matching prediction to ground truth
- omission error: ต้นจริงที่ตรวจไม่พบ
- commission error: ต้นที่โมเดลตรวจเกิน
- instance IoU / coverage metric หากมี ground-truth point-level instance labels

**DBH estimation**

- MAE, RMSE, Bias
- MAPE หรือ relative error
- percent of trees within error thresholds เช่น ±2 cm, ±5 cm

**Efficiency**

- runtime per plot
- peak CPU memory และ GPU memory
- model size และ inference throughput
- optional field/processing productivity: m²/min และ trees/min หากมีข้อมูลเวลาการสแกน

---

## Slide 14: Expected Contributions

**สิ่งที่คาดว่าจะได้จากงานวิจัย**

- pipeline ที่ใช้ handheld LiDAR point cloud เพื่อแยกต้นยางรายต้นและประเมิน DBH
- multi-channel raster representation ที่เพิ่มข้อมูลความสูงและสัญญาณบริเวณ DBH โดยยังใช้ CNN/YOLO pipeline ได้
- benchmark เปรียบเทียบ single-channel CNN, multi-channel CNN และ TreeLearn บนข้อมูลสวนยางพารา 12 แปลงเดียวกัน
- ข้อเสนอแนะเชิงปฏิบัติว่าเมื่อใดควรใช้ 2D multi-channel CNN และเมื่อใดควรใช้ 3D point-cloud segmentation

---

## Slide 15: Planning and References

**Tentative plan: May-Dec 2026**

- May 2026: literature review, finalize problem statement, inspect data/ground truth
- Jun 2026: reproduce single-channel baseline and define evaluation protocol
- Jul 2026: implement and train multi-channel CNN
- Aug 2026: run TreeLearn/classical baselines on same plots
- Sep 2026: DBH fitting and error analysis
- Oct 2026: efficiency benchmarking and ablation study
- Nov-Dec 2026: thesis/proposal writing and final presentation

**References**

- Proudman, A., Ramezani, M., & Fallon, M. (2021). Online Estimation of Diameter at Breast Height (DBH) of Forest Trees Using a Handheld LiDAR.
- Liu et al. (2021). Single Tree Segmentation and Diameter at Breast Height Estimation With Mobile LiDAR. IEEE Access.
- Cheng et al. (2023). TreeScope: An Agricultural Robotics Dataset for LiDAR-Based Mapping of Trees in Forests and Orchards.
- Henrich et al. (2024). TreeLearn: A deep learning method for segmenting individual trees from ground-based LiDAR forest point clouds.
