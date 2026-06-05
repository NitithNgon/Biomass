# Thai Speaker Script

หัวข้อ: **Individual Tree Segmentation from Handheld LiDAR Point Clouds for DBH Estimation in Rubber Plantations using Multi-channel CNN**

แนวทางการใช้: สคริปต์นี้เขียนให้พูดคู่กับสไลด์ภาษาอังกฤษใน `draft_proposal_lidar_dbh_multichannel_en.md` โดยไม่ต้องอ่านทุกคำบนสไลด์ ให้ใช้เป็นโครงพูดหลักและปรับคำตามจังหวะจริงได้

---

## Slide 1: Title

สวัสดีครับ/ค่ะ วันนี้ผม/ดิฉันจะนำเสนอหัวข้อโครงร่างวิทยานิพนธ์เรื่อง **Individual Tree Segmentation from Handheld LiDAR Point Clouds for DBH Estimation in Rubber Plantations using Multi-channel CNN**

งานนี้สนใจการใช้ข้อมูล point cloud จาก handheld LiDAR หรือ mobile LiDAR ในสวนยางพารา เพื่อนำมาหาต้นไม้รายต้น และนำไปสู่การประเมินค่า DBH หรือเส้นผ่านศูนย์กลางลำต้นที่ระดับอกของต้นไม้แต่ละต้นครับ/ค่ะ

---

## Slide 2: Introduction

จุดเริ่มต้นของงานนี้คือ DBH เป็นตัวแปรที่สำคัญมากในงาน forest inventory และ biomass estimation เพราะเป็นค่าที่ใช้บอกขนาดและการเติบโตของต้นไม้ได้ค่อนข้างดี แต่การวัด DBH แบบภาคสนามด้วยมือจะใช้เวลาและแรงงานสูง โดยเฉพาะถ้าต้องทำหลายแปลงหรือทำซ้ำในอนาคต

ปัจจุบัน mobile LiDAR หรือ handheld LiDAR ช่วยให้เราเก็บข้อมูลสามมิติในสวนหรือป่าได้เร็วขึ้นมาก แต่ปัญหาคือ point cloud ที่ได้ยังเป็นข้อมูลดิบระดับแปลง เราต้องแปลงข้อมูลนี้ให้กลายเป็นข้อมูลระดับต้นไม้รายต้นก่อน จึงจะนำไปคำนวณ DBH ได้อย่างน่าเชื่อถือ

ข้อจำกัดของวิธีเดิมคือหลายวิธีต้องพึ่งพา rule-based processing เช่น การตัดลำต้น การ clustering หรือการ fit วงกลมและทรงกระบอก ซึ่งไวต่อ noise, occlusion, วัชพืช, กิ่งใบ และความหนาแน่นของจุดที่ไม่สม่ำเสมอ ส่วนวิธี 3D deep learning เช่น TreeLearn มีศักยภาพดี แต่ใช้ทรัพยากรสูงกว่า

ดังนั้น core problem ของงานนี้คือ เราจะเปลี่ยน point cloud จากสวนยางพาราให้เป็น segmentation รายต้นและ DBH estimate ที่แม่นยำได้อย่างไร โดยยังรักษา pipeline ให้เบาและเปรียบเทียบกับวิธี 3D ได้อย่างยุติธรรม

---

## Slide 3: Problem Statement

สไลด์นี้สรุปข้อจำกัดของเทคนิคปัจจุบันเป็นสองส่วนหลักครับ/ค่ะ

ข้อแรกคือ **lack of robust individual tree segmentation** หรือการแยกต้นไม้รายต้นยังไม่ robust พอ วิธีแบบ rule-based มักต้องเลือกค่าพารามิเตอร์ เช่น clustering radius, voxel size หรือ density threshold ซึ่งเมื่อเปลี่ยนสภาพแปลง เปลี่ยนแนวเดินสแกน หรือเจอจุดรบกวนมากขึ้น ผลลัพธ์อาจเปลี่ยนได้ง่าย ในสวนยางพาราแม้ต้นจะปลูกเป็นแถว แต่ก็ยังมีปัญหาจาก occlusion, ความหนาแน่นจุดไม่เท่ากัน และต้นที่อยู่ใกล้กันจนเกิดการ merge ได้

ข้อที่สองคือ **limited accuracy-efficiency bridge** หมายถึงวิธีที่แม่นมากมักจะหนัก เช่น direct 3D learning ส่วนวิธีที่เบา เช่น 2D density image อาจทิ้งข้อมูลสำคัญไป โดยเฉพาะข้อมูลแนวดิ่งและข้อมูลบริเวณความสูง DBH ดังนั้นงานนี้จึงพยายามหาแนวกลางระหว่างความแม่นยำและประสิทธิภาพ

---

## Slide 4: Background

ก่อนเข้า method ผม/ดิฉันขอปูคำสำคัญสี่คำก่อนครับ/ค่ะ

คำแรกคือ **DBH** หรือ diameter at breast height คือเส้นผ่านศูนย์กลางลำต้นที่ระดับอก โดยทั่วไปประมาณ 1.3 เมตรจากพื้นดิน ในงานนี้ DBH เป็นค่าปลายทางที่เราต้องการประเมินจาก point cloud

คำที่สองคือ **handheld หรือ mobile LiDAR point cloud** คือข้อมูลจุดสามมิติที่ได้จากการเดินสแกนในสวนหรือป่า โดยอาศัยระบบ LiDAR ร่วมกับ SLAM เพื่อสร้างแผนที่สามมิติของพื้นที่

คำที่สามคือ **individual tree segmentation** คือการแยก point cloud ระดับแปลงออกเป็นต้นไม้แต่ละต้น หรืออย่างน้อยต้องหา tree center หรือ tree region ของแต่ละต้นให้ได้ ขั้นตอนนี้สำคัญมาก เพราะถ้าแยกต้นผิด ค่า DBH ที่คำนวณต่อมาก็จะผิดตามไปด้วย

คำสุดท้ายคือ **multi-channel raster representation** ในงานนี้หมายถึงการเปลี่ยน point cloud สามมิติให้เป็นภาพ top-view หลาย channel เช่น density, height above ground และ density ในช่วง breast height เพื่อให้ CNN ใช้ข้อมูลได้มากกว่า density เพียงช่องเดียว

---

## Slide 5: Related Work Landscape

ตารางนี้สรุปงานที่เกี่ยวข้อง โดยแบ่งเป็น approach, key concept และ research gap ของแต่ละงาน

งานของ Liu et al. ใช้ relative-density segmentation และ multi-height DBH fitting ซึ่งตรงกับปัญหา single tree segmentation และ DBH estimation มาก แต่วิธีนี้ยังพึ่งพา handcrafted density scale และ assumption เกี่ยวกับลำต้น

งานของ Proudman et al. สนใจ online DBH estimation ด้วย handheld LiDAR ซึ่งช่วยให้เห็นว่า handheld LiDAR สามารถนำมาใช้ในงาน DBH ได้จริง แต่ปัญหา segmentation และ noisy trunk observation ยังเป็นข้อจำกัด

งานของ Shao et al. ใช้แนวทาง deep semantic segmentation และ stem mapping สำหรับ large-scale forest inventory ซึ่งมีประสิทธิภาพกับข้อมูลขนาดใหญ่ แต่ความซับซ้อนของระบบอาจมากเกินไปสำหรับ pipeline ที่ต้องการความเบา

TreeLearn เป็นตัวแทนของวิธี 3D deep learning ที่ทำ individual tree segmentation โดยตรงบน point cloud จุดเด่นคือ segmentation ดี แต่ต้องใช้ infrastructure และทรัพยากรมากกว่า

ส่วน baseline ในโปรเจกต์ปัจจุบันคือ single-channel density image ร่วมกับ CNN/YOLO ซึ่งเบาและทำงานง่าย แต่ยังทิ้งข้อมูลแนวดิ่งและสัญญาณบริเวณ DBH ไป งานนี้จึงเสนอ multi-channel raster เป็นทางกลาง

---

## Slide 6: Research Gap

จาก related work จะเห็นช่องว่างหลักคือ เรายังขาดวิธีที่อยู่ตรงกลางระหว่างวิธีที่เบาแต่ข้อมูลน้อย กับวิธีที่แม่นแต่หนัก

ถ้าใช้ rule-based point cloud processing เราจะต้องปรับพารามิเตอร์ตามแปลง ตามความหนาแน่นของจุด และตามสภาพแวดล้อม ซึ่งทำให้ generalize ยาก

ถ้าใช้ 3D deep learning เช่น TreeLearn ก็ได้ประโยชน์ด้าน segmentation แต่ต้องใช้ GPU memory และ preprocessing มากกว่า อีกทั้งอาจต้อง fine-tune กับ domain ใหม่

ในขณะที่ single-channel CNN แบบ density image ใช้งานง่าย แต่ข้อมูลที่เกี่ยวข้องกับลำต้นและความสูงถูกลดทอนลง ดังนั้น research gap ของงานนี้คือการทดสอบว่า multi-channel raster จะเพิ่มความแม่นของการแยกต้นไม้ได้หรือไม่ โดยยังคงความเบาของ CNN/YOLO pipeline ไว้

---

## Slide 7: Proposed Method

ในงานนี้ผม/ดิฉันเสนอ pipeline ที่มี 4 components หลัก

ส่วนแรกคือ **Data Preparation** เป็นการเตรียม point cloud ทั้ง 12 แปลงให้มีรูปแบบเดียวกัน จัดระบบพิกัดให้ตรงกับ label และคำนวณ height above ground

ส่วนที่สองคือ **Feature Rasterization** คือการเปลี่ยน point cloud เป็นภาพ top-view หลาย channel เพื่อเก็บทั้งความหนาแน่นของจุด โครงสร้างแนวดิ่ง และสัญญาณบริเวณ breast height

ส่วนที่สามคือ **Individual Tree Segmentation** ใช้ CNN/YOLO เพื่อ detect tree center หรือ tree region จากภาพ multi-channel แล้วนำไปเปรียบเทียบกับ density-only baseline และวิธี 3D point cloud

ส่วนสุดท้ายคือ **DBH Extraction and Evaluation** เมื่อได้ต้นไม้รายต้นแล้ว จะ crop จุดบริเวณลำต้น นำไป fit DBH และประเมินทั้งความแม่นยำและประสิทธิภาพการประมวลผล

---

## Slide 8: System Architecture

ภาพรวมของ workflow คือเริ่มจาก point cloud จากนั้นแปลงเป็น feature raster แล้วส่งเข้า CNN/YOLO เพื่อ detect ต้นไม้ จากนั้น crop จุดของต้นไม้แต่ละต้น นำไปทำ DBH fitting และสุดท้ายเข้าสู่การ evaluation

ใน stage แรกคือ data preparation เราจะ standardize point cloud, align กับ ground truth, estimate local ground และคำนวณ height above ground

stage ที่สองคือ feature rasterization ซึ่งสร้าง channel หลักสามตัวคือ density, hag_p95 และ dbh_band_density

stage ที่สามคือ individual tree segmentation ใช้ multi-channel CNN/YOLO เพื่อหา tree center หรือ tree region และนำไปเปรียบเทียบกับ baseline

stage สุดท้ายคือ DBH extraction และ evaluation โดยจะวัดทั้ง segmentation metrics, DBH metrics และ efficiency metrics

---

## Slide 9: Dataset and Controls

ข้อมูลหลักของงานนี้คือ point cloud สวนยางพารา 12 แปลง โดยมี ground truth เป็นตำแหน่งต้นไม้และค่า DBH จากไฟล์ CSV

เพื่อให้การเปรียบเทียบยุติธรรม จะทำ train, validation และ test split ในระดับ plot ไม่ใช่สุ่มจุดหรือสุ่มภาพจากแปลงเดียวกัน เพื่อป้องกัน data leakage

นอกจากนี้ในการเปรียบเทียบระหว่าง density-only และ multi-channel CNN จะควบคุมค่า image size, pixel size, bounding box size, split seed และ augmentation policy ให้เหมือนกัน เพื่อให้ผลต่างที่ได้มาจาก representation จริง ๆ

---

## Slide 10: Methodology - Data Preparation

ขั้นตอน data preparation มีสองส่วนย่อยครับ/ค่ะ

ส่วนแรกคือ **point cloud standardization** รับข้อมูลดิบที่อาจเป็น PCD หรือ LAS พร้อม label CSV แล้วแปลงให้เข้าสู่ workflow ที่มีรูปแบบเดียวกัน มีการ filter, rotate และ align coordinate ให้ตรงกับตำแหน่งต้นไม้ใน ground truth

ส่วนที่สองคือ **ground normalization and dataset split** เราจะ estimate local ground surface แล้วคำนวณ height above ground ของแต่ละจุด ซึ่งข้อมูลนี้สำคัญต่อการสร้าง channel เชิงความสูง หลังจากนั้นจะแบ่งข้อมูลเป็น train, validation และ test ในระดับ plot

---

## Slide 11: Methodology - Feature Rasterization

ขั้นตอนนี้เป็นหัวใจของ multi-channel representation ครับ/ค่ะ

channel แรกคือ **density** นับจำนวนจุดในแต่ละ grid cell จากมุม top-view ซึ่งช่วยบอกโครงสร้างการกระจายตัวของจุด

channel ที่สองคือ **hag_p95** หรือ percentile ที่ 95 ของ height above ground ในแต่ละ cell เพื่อให้โมเดลเห็นข้อมูลแนวดิ่งของพุ่มและลำต้น ไม่ใช่เห็นแค่ความหนาแน่น

channel ที่สามคือ **dbh_band_density** โดยนับจำนวนจุดในช่วงความสูง 1.0 ถึง 1.6 เมตรเหนือพื้น ซึ่งเป็นช่วงรอบ ๆ breast height จุดประสงค์คือเน้นสัญญาณบริเวณที่เกี่ยวข้องกับ DBH โดยตรง

เมื่อรวมสาม channel นี้เข้าด้วยกัน เราจะได้ synthetic RGB image ที่ CNN/YOLO ใช้ได้ โดยไม่ต้องแก้ architecture ของโมเดลมากนัก

---

## Slide 12: Methodology - Individual Tree Segmentation

ในขั้นตอน segmentation เราจะใช้ synthetic RGB raster และ label ตำแหน่งต้นไม้ เพื่อ train CNN/YOLO ให้ทำนาย tree center หรือ tree-level region

สิ่งที่ต้องการทดสอบคือ เมื่อเพิ่มข้อมูลเชิงความสูงและข้อมูลบริเวณ DBH เข้าไป โมเดลจะแยกต้นไม้ได้ดีขึ้นกว่าการใช้ density-only image หรือไม่

นอกจากนี้จะเปรียบเทียบกับ baseline อื่น เช่น single-channel density CNN, TreeLearn และ point-cloud processing baseline โดยใช้ test plots เดียวกัน เพื่อให้ผลการประเมินเปรียบเทียบกันได้ตรง ๆ

---

## Slide 13: Methodology - DBH Extraction

หลังจากได้ผลตรวจจับต้นไม้รายต้นแล้ว ขั้นตอนถัดไปคือ crop point cloud รอบต้นที่โมเดลทำนาย เพื่อดึง candidate trunk points ออกมา

จากนั้นจะเลือกจุดบริเวณ breast-height band หรือใกล้ความสูง 1.3 เมตรเหนือพื้น แล้วใช้วิธี circle fitting หรือ cylinder fitting เพื่อประมาณเส้นผ่านศูนย์กลางลำต้น

ในกรณีที่ point cloud มี noise หรือเห็นลำต้นไม่ครบด้าน อาจใช้ multi-height bins ร่วมกับ RANSAC หรือ outlier removal เพื่อเพิ่มความ robust ของการ fitting

จุดสำคัญคือ DBH extraction ในงานนี้ใช้เป็น downstream evaluation ด้วย เพราะถ้า segmentation ดีขึ้น ค่า DBH ที่คำนวณได้ควรมี error ลดลง

---

## Slide 14: Expected Outcome and Contribution

ผลลัพธ์ที่คาดหวังจากงานนี้มีสี่ส่วนหลักครับ/ค่ะ

อย่างแรกคือได้ **multi-channel tree segmentation pipeline** ที่เปลี่ยน point cloud จาก handheld LiDAR ให้เป็น tree-level detections หรือ crops โดยใช้ทั้ง density, height above ground และ breast-height evidence

อย่างที่สองคือได้ **DBH-ready tree crops** หมายถึงผล segmentation ที่สามารถนำไป crop จุดลำต้น เพื่อใช้ fit DBH ได้โดยตรง

อย่างที่สามคือได้ **accuracy-efficiency benchmark** ที่เปรียบเทียบ density-only CNN, multi-channel CNN, TreeLearn และ point-cloud baseline บนข้อมูลสวนยางพาราชุดเดียวกัน

อย่างสุดท้ายคือได้ **segmentation-to-DBH error analysis** เพื่อแสดงให้เห็นว่า error แบบ missed tree, merged tree หรือ false detection ส่งผลต่อค่า DBH อย่างไร

metric for success จะดูจากสามส่วน คือ segmentation F1 หรือ TDR ต้องดีขึ้น, DBH MAE หรือ RMSE ต้องลดลงเมื่อเทียบกับ field measurement และ runtime หรือ memory usage ควรต่ำกว่าวิธี 3D point-cloud segmentation โดยตรง

---

## Slide 15: References - Individual Tree Segmentation

สไลด์นี้เป็น references กลุ่ม individual tree segmentation ซึ่งใช้เป็นฐานในการออกแบบและเปรียบเทียบวิธีของงานนี้

งานหลักที่เกี่ยวข้องคือ Liu et al. สำหรับ segmentation และ DBH จาก mobile LiDAR, TreeLearn สำหรับ 3D deep learning instance segmentation, Shao et al. สำหรับ large-scale MLS inventory, TreeScope สำหรับ dataset ด้าน robotics และ SLOAM สำหรับ semantic LiDAR odometry and mapping ในงาน forest inventory

ตอนพูดจริงไม่จำเป็นต้องอ่าน reference ทีละบรรทัดทั้งหมด แค่ชี้ว่ากลุ่มนี้เป็น literature ที่รองรับฝั่ง segmentation และ stem mapping ก็พอครับ/ค่ะ

---

## Slide 16: References - DBH Extraction

สไลด์สุดท้ายเป็น references กลุ่ม DBH extraction ซึ่งเกี่ยวข้องกับการนำ point cloud ของลำต้นไปคำนวณ DBH

ตัวอย่างงานหลักคือ Proudman et al. ที่ใช้ handheld LiDAR เพื่อประเมิน DBH, Sheng et al. ที่ใช้ mobile laser scanning point cloud สำหรับ DBH extraction, และ Liu et al. ที่รวมทั้ง segmentation และ multi-height DBH fitting

ส่วน Shao et al. และ TreeScope ช่วยเชื่อมงาน DBH เข้ากับภาพรวมของ forest inventory และ robotics dataset

โดยสรุป literature สองกลุ่มนี้จะรองรับทั้งสองด้านของงาน คือด้านการแยกต้นไม้รายต้น และด้านการวัด DBH จากผล segmentation ครับ/ค่ะ
