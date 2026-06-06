# -*- coding: utf-8 -*-
"""
สร้างเอกสารโครงร่างวิทยานิพนธ์ (ภาษาไทย) เป็นไฟล์ .docx
โครงสร้างตามตัวอย่าง proposal/example/Theppasith-ThesisProposal (1).pdf
หัวข้อ: การแบ่งส่วนต้นไม้รายต้นจากกลุ่มจุดไลดาร์มือถือเพื่อประมาณค่า DBH ในสวนยางพารา ด้วย Multi-channel CNN
"""
from pathlib import Path
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "slide" / "fixed" / "assets"
OUT = HERE / "draft_thesis_proposal_th.docx"

THAI = "TH Sarabun New"   # ฟอนต์มาตรฐานเอกสารวิชาการไทย (ถ้าไม่มีให้ติดตั้ง หรือเปลี่ยนเป็น Angsana New)
PINK = RGBColor(0xA0, 0x00, 0x6D)
INK = RGBColor(0x22, 0x22, 0x22)

doc = Document()

# ---------- font / style setup ----------
def _set_run_fonts(run, name=THAI, size=None, bold=None, color=None):
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    if color is not None:
        run.font.color.rgb = color
    run.font.name = name
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts"); rpr.append(rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs"):
        rfonts.set(qn(attr), name)

# base styles
n = doc.styles["Normal"]
n.font.name = THAI; n.font.size = Pt(16)
n.paragraph_format.space_after = Pt(6); n.paragraph_format.line_spacing = 1.15
_rf = n.element.get_or_add_rPr().get_or_add_rFonts()
for a in ("w:ascii", "w:hAnsi", "w:cs"):
    _rf.set(qn(a), THAI)

for lvl, sz in [("Heading 1", 19), ("Heading 2", 17), ("Heading 3", 16), ("Title", 24)]:
    try:
        st = doc.styles[lvl]
        st.font.name = THAI; st.font.size = Pt(sz); st.font.bold = True
        st.font.color.rgb = PINK if lvl != "Title" else PINK
        rf = st.element.get_or_add_rPr().get_or_add_rFonts()
        for a in ("w:ascii", "w:hAnsi", "w:cs"):
            rf.set(qn(a), THAI)
    except KeyError:
        pass

_fig = {"n": 0}

def P(text="", size=16, bold=False, align=None, color=INK, after=6, before=0, italic=False):
    p = doc.add_paragraph()
    if align is not None:
        p.alignment = align
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.space_before = Pt(before)
    if text:
        r = p.add_run(text)
        _set_run_fonts(r, size=size, bold=bold, color=color)
        r.font.italic = italic
    return p

def bullet(text, size=16, level=0):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.left_indent = Inches(0.3 + 0.3 * level)
    p.paragraph_format.space_after = Pt(3)
    r = p.add_run(text)
    _set_run_fonts(r, size=size, color=INK)
    return p

def numbered(text, size=16):
    p = doc.add_paragraph(style="List Number")
    p.paragraph_format.space_after = Pt(3)
    r = p.add_run(text)
    _set_run_fonts(r, size=size, color=INK)
    return p

def H1(text):
    p = doc.add_heading(level=1)
    r = p.add_run(text); _set_run_fonts(r, size=19, bold=True, color=PINK)
    return p

def H2(text):
    p = doc.add_heading(level=2)
    r = p.add_run(text); _set_run_fonts(r, size=17, bold=True, color=PINK)
    return p

def H3(text):
    p = doc.add_heading(level=3)
    r = p.add_run(text); _set_run_fonts(r, size=16, bold=True, color=INK)
    return p

def figure(name, caption, width=4.7):
    path = ASSETS / name
    if path.exists():
        p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run().add_picture(str(path), width=Inches(width))
        _fig["n"] += 1
        cap = doc.add_paragraph(); cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap.paragraph_format.space_after = Pt(10)
        r = cap.add_run(f"ภาพที่ {_fig['n']}  {caption}")
        _set_run_fonts(r, size=14, color=RGBColor(0x55, 0x55, 0x55))

def page_break():
    doc.add_page_break()

def add_toc():
    p = doc.add_paragraph()
    run = p.add_run()
    fld = OxmlElement("w:fldSimple"); fld.set(qn("w:instr"), r'TOC \o "1-3" \h \z \u')
    t = OxmlElement("w:t"); t.text = "(คลิกขวาที่สารบัญนี้ใน Word แล้วเลือก Update Field เพื่อสร้างเลขหน้า)"
    r = OxmlElement("w:r"); r.append(t); fld.append(r)
    p._p.append(fld)

def shade(cell, hexcolor):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd"); shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), hexcolor)
    tcPr.append(shd)

# =====================================================================
# หน้าปก
# =====================================================================
P("โครงร่างวิทยานิพนธ์", size=22, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, color=PINK, before=36, after=2)
P("(THESIS PROPOSAL)", size=16, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, color=RGBColor(0x66,0x66,0x66), after=28)

P("การแบ่งส่วนต้นไม้รายต้นจากกลุ่มจุดข้อมูลไลดาร์แบบมือถือ", size=20, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, color=INK, after=2)
P("เพื่อประมาณค่าเส้นผ่านศูนย์กลางเพียงอก (DBH) ในสวนยางพารา ด้วยโครงข่ายประสาทเทียมแบบคอนโวลูชันหลายช่องสัญญาณ",
  size=20, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, color=INK, after=6)
P("Individual Tree Segmentation from Handheld LiDAR Point Clouds for DBH Estimation in Rubber Plantations using Multi-channel CNN",
  size=16, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, color=RGBColor(0x44,0x44,0x44), after=40)

info = [
    ("ชื่อเรื่อง (ภาษาไทย)", "การแบ่งส่วนต้นไม้รายต้นจากกลุ่มจุดข้อมูลไลดาร์แบบมือถือเพื่อประมาณค่า DBH ในสวนยางพารา ด้วย Multi-channel CNN"),
    ("ชื่อเรื่อง (ภาษาอังกฤษ)", "Individual Tree Segmentation from Handheld LiDAR Point Clouds for DBH Estimation in Rubber Plantations using Multi-channel CNN"),
    ("เสนอโดย", "นายนิธิช งอนชัยภูมิ (Nitith Ngonchaiyaphum)"),
    ("รหัสนิสิต", "6872046721"),
    ("หลักสูตร", "วิศวกรรมศาสตรมหาบัณฑิต (วศ.ม.) สาขาวิชาวิศวกรรมคอมพิวเตอร์ แผน ก แบบ ก2"),
    ("ภาควิชา", "วิศวกรรมคอมพิวเตอร์ คณะวิศวกรรมศาสตร์ จุฬาลงกรณ์มหาวิทยาลัย"),
    ("อีเมล", "nitith88871@gmail.com"),
    ("อาจารย์ที่ปรึกษา", "ดร. สุขุม สัทธารัตน์ไพศาล (Dr. Sukhum Sattaratnamai)"),
]
tbl = doc.add_table(rows=len(info), cols=2)
tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
tbl.columns[0].width = Inches(2.2); tbl.columns[1].width = Inches(4.6)
for i, (k, v) in enumerate(info):
    c0, c1 = tbl.rows[i].cells
    c0.width = Inches(2.2); c1.width = Inches(4.6)
    r0 = c0.paragraphs[0].add_run(k); _set_run_fonts(r0, size=16, bold=True, color=INK)
    r1 = c1.paragraphs[0].add_run(v); _set_run_fonts(r1, size=16, color=INK)
page_break()

# =====================================================================
# สารบัญ
# =====================================================================
H1("สารบัญ")
add_toc()
page_break()

# =====================================================================
# 1. ที่มาและความสำคัญ
# =====================================================================
H1("1. ที่มาและความสำคัญ")
P("ค่าเส้นผ่านศูนย์กลางเพียงอก (Diameter at Breast Height หรือ DBH) ซึ่งวัดที่ระดับความสูงประมาณ 1.3 เมตร "
  "จากพื้นดิน เป็นตัวแปรระดับต้นไม้ที่สำคัญที่สุดตัวหนึ่งสำหรับงานสำรวจทรัพยากรป่าไม้ (forest inventory) "
  "การประมาณมวลชีวภาพและการกักเก็บคาร์บอน ตลอดจนการติดตามการเจริญเติบโตของต้นไม้ อย่างไรก็ตาม การวัด DBH "
  "ด้วยมือในภาคสนามต้องใช้แรงงานและเวลาสูงมาก โดยเฉพาะเมื่อต้องสำรวจสวนยางพาราหลายแปลงและทำซ้ำเป็นระยะ")
P("เทคโนโลยีไลดาร์แบบมือถือ (handheld/backpack LiDAR) ที่ทำงานร่วมกับการสร้างแผนที่แบบ SLAM ช่วยให้สามารถ"
  "เก็บข้อมูลโครงสร้างสามมิติของทั้งแปลงได้อย่างรวดเร็วในเวลาเพียงไม่กี่นาที แต่ข้อมูลที่ได้เป็น “กลุ่มจุด” "
  "(point cloud) ดิบ ซึ่งยังไม่ใช่คำตอบในตัวเอง จำเป็นต้องผ่านขั้นตอนการแบ่งกลุ่มจุดออกเป็นต้นไม้รายต้น "
  "(individual tree segmentation) ก่อน จึงจะนำไปประมาณค่า DBH รายต้นได้ ขั้นตอนการแยกต้นไม้รายต้นนี้จึงเป็น "
  "คอขวด (bottleneck) ที่สำคัญที่สุดของกระบวนการ เพราะหากแยกต้นผิด รวมหลายต้นเป็นต้นเดียว หรือตรวจไม่พบต้น "
  "ค่าความผิดพลาดจะส่งต่อไปยังค่า DBH และข้อมูลสำรวจทั้งหมด")
figure("pc_height.png", "ตัวอย่างกลุ่มจุดไลดาร์ของสวนยางพาราหนึ่งแปลง (ระบายสีตามความสูง)", 4.8)
P("วิธีการเดิมในการแยกต้นไม้จากกลุ่มจุดส่วนใหญ่อาศัยกฎที่ออกแบบด้วยมือ (rule-based) เช่น การกรองพื้นดิน "
  "การสกัดลำต้น การจัดกลุ่ม (clustering) และการตัดชั้นความสูง ซึ่งไวต่อการบดบัง ความหนาแน่นของจุดที่ไม่สม่ำเสมอ "
  "วัชพืช และแนวทางการเดินสแกน ในทางกลับกัน วิธีการเรียนรู้เชิงลึกบนกลุ่มจุดสามมิติโดยตรง เช่น TreeLearn "
  "ให้ผลการแบ่งส่วนที่แม่นยำ แต่ต้องใช้โครงสร้างพื้นฐานการเรียนรู้เชิงลึกแบบ 3 มิติ หน่วยความจำ GPU จำนวนมาก "
  "และอาจต้องปรับจูนกับโดเมนใหม่ ส่วนวิธีการแปลงกลุ่มจุดเป็นภาพความหนาแน่นมุมมองบนลง (single-channel density "
  "image) แล้วใช้ CNN/YOLO นั้นเบาและรวดเร็ว แต่ทิ้งข้อมูลโครงสร้างแนวดิ่งและสัญญาณบริเวณระดับอกที่จำเป็นต่อ DBH")
P("งานวิจัยนี้จึงเสนอแนวทาง “ตรงกลางที่ขาดหายไป” (missing middle) คือการแปลงกลุ่มจุดเป็นภาพแรสเตอร์มุมมองบนลง"
  "แบบหลายช่องสัญญาณ (multi-channel raster) ที่ยังคงเก็บข้อมูลความหนาแน่น โครงสร้างแนวดิ่ง และสัญญาณบริเวณ"
  "ระดับอกไว้พร้อมกัน เพื่อให้ได้ความแม่นยำที่ดีขึ้นในขณะที่ยังคงความเบาและประสิทธิภาพในการประมวลผล โดยเน้น"
  "กรณีสวนยางพาราที่ปลูกเป็นแถวเป็นแนว ซึ่งโครงสร้างเชิงพื้นที่ที่เป็นระเบียบนี้เป็นข้อมูลเชิงบริบทที่แบบจำลองนำไปใช้ได้")

H2("ความสำคัญของปัญหา (Problem Statement)")
P("เราจะแปลงกลุ่มจุดไลดาร์แบบมือถือของสวนยางพาราที่ปลูกเป็นแถว ให้กลายเป็นการแบ่งส่วนต้นไม้รายต้นและ"
  "การประมาณค่า DBH ที่แม่นยำ ด้วยโครงข่ายประสาทเทียมแบบคอนโวลูชันหลายช่องสัญญาณบนภาพมุมมองบนลงที่มีน้ำหนักเบา "
  "ซึ่งยังคงรักษาข้อมูลโครงสร้างแนวดิ่งและสัญญาณบริเวณระดับอกไว้ ในขณะที่ใช้ทรัพยากรน้อยกว่าและให้ความแม่นยำ"
  "ไม่ด้อยไปกว่าวิธีการบนกลุ่มจุดสามมิติที่ใช้ทรัพยากรสูงอย่าง TreeLearn บนข้อมูลแปลงเดียวกันได้อย่างไร",
  bold=True, color=PINK)

H2("ผลลัพธ์ที่คาดหวัง")
P("ผลลัพธ์ของวิทยานิพนธ์นี้คือกระบวนการ (pipeline) ที่ตรวจสอบความถูกต้องแล้ว สำหรับการแปลงกลุ่มจุดไลดาร์มือถือ"
  "ของสวนยางพาราให้เป็นการตรวจจับ/แบ่งส่วนต้นไม้รายต้น โดยใช้ช่องสัญญาณความหนาแน่น ความสูงเหนือพื้นดิน และ"
  "สัญญาณบริเวณระดับอก ตามด้วยการประมาณค่า DBH และการเปรียบเทียบทั้งด้านความแม่นยำและประสิทธิภาพกับวิธี"
  "single-channel CNN, TreeLearn และวิธีประมวลผลกลุ่มจุดแบบดั้งเดิม บนชุดข้อมูลสวนยางพารา 12 แปลงชุดเดียวกัน")

page_break()

# =====================================================================
# 2. งานวิจัยและทฤษฎีที่เกี่ยวข้อง
# =====================================================================
H1("2. งานวิจัยและทฤษฎีที่เกี่ยวข้อง")

H2("2.1 ทฤษฎีและเทคโนโลยีพื้นฐาน")
H3("2.1.1 กลุ่มจุดไลดาร์และการเก็บข้อมูลด้วยไลดาร์มือถือ (Handheld LiDAR & SLAM)")
P("ไลดาร์ (LiDAR) วัดระยะด้วยแสงเลเซอร์เพื่อสร้างกลุ่มจุดสามมิติของสิ่งแวดล้อม ไลดาร์แบบมือถือที่ทำงานร่วมกับ "
  "SLAM (Simultaneous Localization and Mapping) ช่วยให้ผู้ปฏิบัติงานเดินเก็บข้อมูลทั้งแปลงได้อย่างรวดเร็ว "
  "เหมาะกับการเก็บข้อมูลบริเวณใต้เรือนยอดและรอบลำต้น ซึ่งเป็นข้อมูลตั้งต้นสำหรับการตรวจหาต้นไม้รายต้นและ"
  "การสกัดจุดบริเวณระดับอก")
H3("2.1.2 การประมาณพื้นดินและความสูงเหนือพื้นดิน (Ground Estimation & Height Above Ground)")
P("เนื่องจากพื้นดินในสวนยางพาราไม่ราบเรียบสม่ำเสมอ การคำนวณความสูงเหนือพื้นดิน (Height Above Ground หรือ HAG) "
  "ของแต่ละจุดจึงต้องประมาณผิวพื้นดินเฉพาะที่ก่อน งานนี้ประมาณพื้นดินจากค่าต่ำสุดของ Z ในแต่ละเซลล์ตาราง "
  "แล้วใช้ตัวกรองค่าต่ำสุด (minimum filter) จากนั้นนำ HAG ไปใช้แยกสัญญาณเรือนยอดออกจากสัญญาณลำต้น")
H3("2.1.3 การแปลงกลุ่มจุดเป็นภาพแรสเตอร์หลายช่องสัญญาณ (Multi-channel Rasterization)")
P("กลุ่มจุดจะถูกแปลงเป็นภาพมุมมองบนลง (top-view) บนตารางพิกเซล โดยแต่ละช่องสัญญาณเข้ารหัสคุณลักษณะทางกายภาพ "
  "ที่ต่างกัน ทำให้ได้ภาพแบบ RGB สังเคราะห์ที่ใช้กับกระบวนการ CNN/YOLO เดิมได้โดยไม่ต้องแก้ไขชั้นรับข้อมูล "
  "แต่ยังคงเก็บข้อมูลแนวดิ่งและบริเวณระดับอกไว้ (รายละเอียดของแต่ละช่องอยู่ในหัวข้อ 4)")
H3("2.1.4 โครงข่ายประสาทเทียมแบบคอนโวลูชันและตัวตรวจจับวัตถุ (CNN / YOLO)")
P("โครงข่ายประสาทเทียมแบบคอนโวลูชัน (CNN) เป็นแบบจำลองการเรียนรู้เชิงลึกที่มีประสิทธิภาพสูงในการตีความรูปภาพ "
  "งานนี้ใช้สถาปัตยกรรมตระกูล YOLO (You Only Look Once) รุ่น YOLOv11 ซึ่งเป็นตัวตรวจจับวัตถุแบบขั้นตอนเดียว "
  "เพื่อทำนายตำแหน่งศูนย์กลางของต้นไม้แต่ละต้นบนภาพแรสเตอร์หลายช่องสัญญาณ")
H3("2.1.5 การประมาณ DBH ด้วยการประกบวงกลม/ทรงกระบอก (Circle / Cylinder Fitting)")
P("เมื่อทราบตำแหน่งต้นไม้แล้ว จุดบริเวณลำต้นรอบระดับอก (ประมาณ 1.3 เมตร) จะถูกตัดออกมาเพื่อประกบเป็นวงกลม"
  "หรือทรงกระบอก โดยอาจใช้หลายช่วงความสูง (multi-height bins) ร่วมกับ RANSAC และการกำจัดค่าผิดปกติ เพื่อรับมือ"
  "กับจุดลำต้นที่ไม่ครบวงและสัญญาณรบกวน แล้วจึงได้ค่าเส้นผ่านศูนย์กลางเป็นค่าประมาณของ DBH")

def related(num, title_th, lines):
    H2(f"{num} {title_th}")
    for ln in lines:
        P(ln)

related("2.2", "Liu et al. (2021) — Single Tree Segmentation and DBH Estimation With Mobile LiDAR", [
    "งานวิจัยอ้างอิงหลักของวิทยานิพนธ์นี้ ใช้ความหนาแน่นเชิงสัมพัทธ์ของจุด (relative density) ในการสกัดลำต้นจาก"
    "กลุ่มจุด mobile LiDAR แล้วประมาณ DBH ด้วยการประกบวงกลมหลายระดับความสูงร่วมกับการกำจัดค่าผิดปกติ "
    "ใช้ตรรกะสองขั้นตอน (แบ่งต้น → ประมาณ DBH) เช่นเดียวกับงานนี้ แต่ยังพึ่งพาเกณฑ์ความหนาแน่นและสมมติฐาน"
    "เรื่องลำต้นที่ออกแบบด้วยมือ ซึ่งงานนี้เสนอให้แทนที่ขั้นตอนการแบ่งส่วนด้วย CNN หลายช่องสัญญาณที่เรียนรู้ได้ [1]",
])
related("2.3", "Proudman et al. (2021) — Online DBH Estimation Using a Handheld LiDAR", [
    "แสดงให้เห็นว่าไลดาร์แบบมือถือเพียงพอต่อการประมาณ DBH แบบออนไลน์ ด้วยการประมวลผลรายต้นระหว่าง/หลังการสแกน "
    "สนับสนุนเป้าหมายด้านประสิทธิภาพของงานนี้ แต่การแยกต้นยังคงไวต่อลำต้นที่ถูกบดบังและสัญญาณรบกวน [2]",
])
related("2.4", "Henrich et al. (2024) — TreeLearn", [
    "เสนอโครงข่าย sparse convolution แบบ 3 มิติที่ทำนายคะแนนความเป็นต้นไม้และเวกเตอร์ออฟเซ็ตรายจุด แล้วจัดกลุ่ม"
    "เป็นต้นไม้รายต้นแบบอัตโนมัติ ให้ผลการแบ่งส่วนที่แข็งแรงและทั่วไป แต่ต้องใช้โครงสร้างพื้นฐานการเรียนรู้เชิงลึก 3 มิติ "
    "หน่วยความจำ GPU สูง และอาจต้อง fine-tune เมื่อเปลี่ยนโดเมน เป็นวิธีเปรียบเทียบ 3 มิติหลักของงานนี้ [3]",
])
related("2.5", "Shao et al. (2024) — Large-Scale Inventory in Natural Forests with Mobile LiDAR", [
    "ใช้การแบ่งส่วนเชิงความหมายเชิงลึกร่วมกับการทำแผนที่ลำต้นสำหรับการสำรวจป่าธรรมชาติขนาดใหญ่ แล้วประมาณ DBH "
    "จากลำต้นที่ตรวจพบ แสดงว่าการแบ่งส่วนแบบเรียนรู้ขยายสู่งานสำรวจจริงได้ แต่ถูกออกแบบมาสำหรับป่าธรรมชาติที่"
    "ซับซ้อนและมีภาระการคำนวณสูงกว่าที่จำเป็นสำหรับสวนยางพาราที่เป็นระเบียบ [4]",
])
related("2.6", "Sheng et al. (2024) — Tree DBH Extraction Based on Mobile Laser Scanning Point Cloud", [
    "นำเสนอกระบวนการสกัดค่า DBH จากกลุ่มจุด mobile laser scanning โดยเน้นการคัดเลือกจุดลำต้นและการประกบรูปทรง"
    "บริเวณระดับอก ใช้เป็นแนวทางอ้างอิงสำหรับขั้นตอนการประมาณ DBH ปลายน้ำของงานนี้ [5]",
])
related("2.7", "Cheng et al. (2023) — TreeScope: Agricultural Robotics LiDAR Dataset", [
    "ชุดข้อมูลไลดาร์สำหรับการทำแผนที่ต้นไม้ในป่าและสวนผลไม้ พร้อม label เชิงความหมายและค่าเส้นผ่านศูนย์กลางลำต้น"
    "ที่วัดในสนาม มีความเกี่ยวข้องเพราะสวนผลไม้/สวนยางมีลักษณะการปลูกเป็นแถวคล้ายกัน ใช้อ้างอิงระเบียบวิธีวัดผล [6]",
])
related("2.8", "Chen et al. (2020) — SLOAM: Semantic LiDAR Odometry and Mapping for Forest Inventory", [
    "เสนอกรอบการทำ odometry และ mapping เชิงความหมายสำหรับการสำรวจป่าด้วยไลดาร์ ใช้เป็นบริบทด้านการทำแผนที่"
    "และการสำรวจต้นไม้ในเชิงหุ่นยนต์ [7]",
])

H2("2.9 สรุปการศึกษาวรรณกรรม")
P("จากการทบทวนวรรณกรรมพบช่องว่างการวิจัยที่เป็นการแลกเปลี่ยนระหว่างความแม่นยำกับการใช้ทรัพยากร กล่าวคือ วิธี"
  "ประมวลผลกลุ่มจุดแบบกฎมือทำงานได้แต่ต้องตั้งค่าพารามิเตอร์จำนวนมากให้เหมาะกับสภาพข้อมูล วิธี 3 มิติเชิงลึกอย่าง "
  "TreeLearn แม่นยำแต่ใช้ทรัพยากรสูง ส่วนภาพความหนาแน่นช่องเดียวเบาแต่ทิ้งข้อมูลแนวดิ่งและบริเวณระดับอก จึงยังไม่"
  "ชัดเจนว่าภาพแรสเตอร์หลายช่องสัญญาณแบบ 2 มิติจะเพิ่มความแม่นยำได้เพียงใดโดยยังคงความเบา ซึ่งเป็นช่องว่างที่"
  "วิทยานิพนธ์นี้มุ่งตอบ")
page_break()

# =====================================================================
# 3. แนวคิดของการวิจัยและวิธีการดำเนินงาน
# =====================================================================
H1("3. แนวคิดของการวิจัยและวิธีการดำเนินงาน")

H2("3.1 วัตถุประสงค์ของงานวิจัย")
for t in [
    "พัฒนากระบวนการแบ่งส่วนต้นไม้รายต้นจากกลุ่มจุดไลดาร์มือถือของสวนยางพารา โดยใช้ CNN แบบหลายช่องสัญญาณ",
    "เปรียบเทียบความถูกต้องของ multi-channel CNN กับ single-channel CNN baseline และวิธีบนกลุ่มจุดเช่น TreeLearn บนข้อมูลแปลงเดียวกัน",
    "ประเมินผลกระทบของคุณภาพการแบ่งส่วนต่อความแม่นยำในการประมาณค่า DBH รายต้น",
    "เปรียบเทียบประสิทธิภาพด้านเวลาในการประมวลผล หน่วยความจำ/VRAM และความง่ายในการนำไปใช้งานจริง",
]:
    numbered(t)

H2("3.2 ขอบเขตของงานวิจัย (Scope)")
H3("3.2.1 ลักษณะของชุดข้อมูล (Dataset)")
bullet("กลุ่มจุดไลดาร์มือถือจากสวนยางพารา 12 แปลง")
bullet("ป้ายกำกับ (ground truth): ตำแหน่งต้นไม้ (พิกัด X/Y) และค่า DBH ที่วัดในสนาม จากไฟล์ CSV ต่อแปลง")
bullet("แต่ละแปลงถูกแปลงเป็นภาพมุมมองบนลงขนาด 320×320 พิกเซล (0.125 ม./พิกเซล ครอบคลุมพื้นที่ ~40 ม.)")
H3("3.2.2 ลักษณะการเตรียมและเก็บข้อมูล")
bullet("แปลงรูปแบบข้อมูล PCD/LAS การกรองสัญญาณรบกวน การหมุน และการจัดแนวพิกัดให้ตรงกับป้ายกำกับ")
bullet("ประมาณพื้นดินเฉพาะที่และคำนวณความสูงเหนือพื้นดิน (HAG) ของทุกจุด")
bullet("แบ่งชุด train/validation/test ระดับแปลง (per-plot) เพื่อป้องกันการรั่วไหลของข้อมูลระหว่างแปลง")
H3("3.2.3 อุปกรณ์ที่ใช้")
bullet("ไลดาร์แบบมือถือพร้อมระบบ SLAM สำหรับเก็บกลุ่มจุด")
bullet("เครื่องคอมพิวเตอร์ที่มี GPU สำหรับการฝึกและอนุมานแบบจำลอง")
H3("3.2.4 พื้นที่และข้อจำกัด (Assumptions)")
bullet("เน้นเฉพาะสวนยางพาราที่ปลูกเป็นแถวเป็นแนวอย่างเป็นระเบียบ ไม่ครอบคลุมป่าธรรมชาติหรือการปลูกแบบไม่เป็นแถว")
bullet("ไม่รวมการอนุมานแบบเรียลไทม์บนอุปกรณ์ และไม่รวมการออกแบบฮาร์ดแวร์ไลดาร์หรืออัลกอริทึม SLAM เอง")

H2("3.3 การทดลองเบื้องต้น (Preliminary Work)")
P("ปัจจุบันได้ดำเนินการในส่วนต้นน้ำของกระบวนการแล้ว ได้แก่ การเตรียมข้อมูล การสร้างภาพแรสเตอร์หลายช่องสัญญาณ "
  "และการฝึกตัวตรวจจับ YOLOv11 บนทั้ง 12 แปลง โดยได้ฝึกและเปรียบเทียบแบบจำลอง multi-channel จำนวน 4 รูปแบบ "
  "เทียบกับ baseline ช่องเดียว บนการแบ่งชุดข้อมูลเดียวกัน")
bullet("แบบจำลอง multi-channel ที่ดีที่สุดได้ค่า mAP50-95 ≈ 0.61 (mAP50 ≈ 0.99)")
bullet("ข้อค้นพบสำคัญ: การเริ่มจากน้ำหนักที่ฝึกมาก่อนบนงานความหนาแน่น (transfer learning) ให้ผลดีกว่าการเริ่มจาก yolo11n ทั่วไปอย่างชัดเจน (≈0.61 เทียบกับ ≈0.36)")
bullet("ส่วนที่เหลือ: โมดูลประมาณค่า DBH และการรัน TreeLearn/วิธีกลุ่มจุดบนแปลงเดียวกัน รวมถึงการวัดประสิทธิภาพ")
figure("results_table.png", "ผลการเปรียบเทียบแบบจำลองเบื้องต้น (เรียงตาม mAP50-95)", 6.2)
page_break()

# =====================================================================
# 4. ภาพรวมของระบบ
# =====================================================================
H1("4. ภาพรวมของระบบ (System Overview)")
P("กระบวนการของงานวิจัยนี้แบ่งออกเป็น 4 โมดูลหลัก ตามลำดับการไหลของข้อมูลจากกลุ่มจุดไปสู่ค่า DBH ดังนี้")
P("กลุ่มจุด → ภาพแรสเตอร์หลายช่องสัญญาณ → ตรวจจับต้นไม้ด้วย CNN/YOLO → ตัดจุดลำต้นรายต้น → ประกบวง/ทรงกระบอกหา DBH → วัดผล",
  bold=True, color=PINK)
tbl = doc.add_table(rows=5, cols=3); tbl.style = "Light Grid Accent 1"
hdr = ["โมดูล", "หน้าที่", "สถานะ"]
for j, h in enumerate(hdr):
    c = tbl.rows[0].cells[j]; r = c.paragraphs[0].add_run(h); _set_run_fonts(r, size=15, bold=True, color=RGBColor(0xFF,0xFF,0xFF)); shade(c, "A0006D")
rows = [
    ("1. การเตรียมข้อมูล", "ทำให้กลุ่มจุดเป็นมาตรฐาน จัดแนวป้ายกำกับ ประมาณพื้นดินและคำนวณ HAG", "เสร็จแล้ว"),
    ("2. การสร้างภาพแรสเตอร์", "สร้างภาพ RGB สังเคราะห์ 3 ช่อง (density / hag_p95 / dbh_band_density)", "เสร็จแล้ว"),
    ("3. การแบ่งส่วนต้นไม้รายต้น", "ฝึก YOLOv11 บนภาพหลายช่องเพื่อทำนายตำแหน่งต้นไม้ และเปรียบเทียบกับ baseline", "เสร็จแล้ว"),
    ("4. การประมาณ DBH และวัดผล", "ตัดจุดลำต้น ประกบวง/ทรงกระบอกหา DBH และเปรียบเทียบกับค่าจริง", "อยู่ระหว่างดำเนินการ"),
]
for i, (m, f, s) in enumerate(rows, 1):
    cells = tbl.rows[i].cells
    for j, txt in enumerate((m, f, s)):
        r = cells[j].paragraphs[0].add_run(txt); _set_run_fonts(r, size=14, color=INK)
    if rows[i-1][2].startswith("เสร็จ"):
        shade(cells[2], "E6F4EA")
    else:
        shade(cells[2], "FDEAEA")
P("", after=4)
figure("raster_multi_blue.png", "ตัวอย่างภาพ RGB สังเคราะห์ 3 ช่องที่ป้อนเข้าสู่ CNN (R=density, G=hag_p95, B=dbh_band_density)", 3.2)
page_break()

# =====================================================================
# 5. การทดลอง
# =====================================================================
H1("5. การทดลอง (Experiment)")

H2("5.1 การวัดผล (Evaluation)")
P("งานนี้วัดผล 3 มิติ คือ ความแม่นยำของการแบ่งส่วน ความแม่นยำของค่า DBH และประสิทธิภาพ", bold=True)
H3("ความแม่นยำของการตรวจจับ/แบ่งส่วนต้นไม้")
bullet("Precision, Recall, F1-score และอัตราการตรวจพบต้นไม้ (Tree Detection Rate, TDR)")
bullet("mAP50, mAP50-95 และความผิดพลาดของจำนวนต้นต่อแปลง")
bullet("ความผิดพลาดของตำแหน่งศูนย์กลางหลังจับคู่กับค่าจริง, omission error และ commission error")
H3("ความแม่นยำของค่า DBH")
bullet("MAE, RMSE, Bias และ MAPE/ค่าความผิดพลาดสัมพัทธ์")
bullet("สัดส่วนต้นไม้ที่อยู่ในเกณฑ์ความผิดพลาด เช่น ±2 ซม. และ ±5 ซม.")
H3("ประสิทธิภาพ (Efficiency)")
bullet("เวลาประมวลผลต่อแปลง (preprocessing + inference) หน่วยความจำ CPU/GPU สูงสุด และขนาดแบบจำลอง")

H2("5.2 ภาพรวมการทดลอง (Experiment Overview)")
P("การทดลองทั้งหมดใช้การแบ่งชุดข้อมูลระดับแปลง ขนาดภาพ ขนาดกล่อง จำนวนรอบการฝึก และนโยบาย augmentation เดียวกัน"
  "ทุกวิธีเพื่อความเป็นธรรม โดยแบ่งออกเป็น 5 การทดลองดังนี้")

exps = [
    ("5.3 การทดลองที่ 1 — Single-channel เทียบกับ Multi-channel CNN",
     "การเพิ่มช่อง hag_p95 และ dbh_band_density ช่วยลด false positive/false negative และเพิ่ม F1 เมื่อเทียบกับภาพความหนาแน่นช่องเดียว",
     "ฝึกและประเมินทั้งสองแบบบนการแบ่งชุดและไฮเปอร์พารามิเตอร์เดียวกัน แล้วเปรียบเทียบ Precision/Recall/F1 และ mAP บน test plots ชุดเดียวกัน"),
    ("5.4 การทดลองที่ 2 — การศึกษาเชิงตัดทอนช่องสัญญาณ (Channel Ablation)",
     "แต่ละช่องสัญญาณมีส่วนช่วยต่อความแม่นยำ และการรวมทุกช่องให้ผลดีที่สุด",
     "เปรียบเทียบ density อย่างเดียว, density+hag_p95, density+dbh_band_density และครบทั้งสามช่อง โดยควบคุมตัวแปรอื่นให้คงที่"),
    ("5.5 การทดลองที่ 3 — Multi-channel CNN เทียบกับ TreeLearn และ baseline กลุ่มจุด",
     "multi-channel CNN ให้ความแม่นยำเทียบเคียง TreeLearn ได้ในขณะที่ใช้ทรัพยากรน้อยกว่า",
     "รัน TreeLearn และวิธีประมวลผลกลุ่มจุดแบบดั้งเดิม (ground filtering + trunk extraction + clustering + fitting) บนแปลงทดสอบชุดเดียวกัน แล้วเทียบทั้งความแม่นยำและประสิทธิภาพ"),
    ("5.6 การทดลองที่ 4 — การประมาณค่า DBH จากผลการแบ่งส่วน",
     "การประกบหลายช่วงความสูงร่วมกับ RANSAC ให้ค่า DBH ที่ผิดพลาดน้อยกว่าการใช้ slice เดียว และคุณภาพการแบ่งส่วนส่งผลโดยตรงต่อ DBH error",
     "ใช้ผลการตรวจจับจากแต่ละวิธี ตัดจุดลำต้นรอบระดับอก ประกบวง/ทรงกระบอกทั้งแบบ single-slice และ multi-height bins + RANSAC แล้ววัด MAE/RMSE เทียบค่าจริง"),
    ("5.7 การทดลองที่ 5 — การวัดประสิทธิภาพ (Efficiency Benchmark)",
     "multi-channel CNN ใช้เวลาและหน่วยความจำในการอนุมานน้อยกว่าวิธีบนกลุ่มจุดสามมิติอย่างมีนัยสำคัญ",
     "วัดเวลาประมวลผลต่อแปลง หน่วยความจำ CPU/GPU สูงสุด และขนาดแบบจำลองของแต่ละวิธีบนเครื่องเดียวกัน"),
]
for title, hyp, design in exps:
    H2(title)
    P("สมมติฐาน: " + hyp, bold=True)
    P("ลักษณะการทดลอง: " + design)
page_break()

# =====================================================================
# 6. ขั้นตอนการดำเนินงาน
# =====================================================================
H1("6. ขั้นตอนการดำเนินงาน (Planning)")
P("แผนการดำเนินงานประมาณ 4 เดือนสำหรับงานวิจัย (ตั้งแต่การทบทวนวรรณกรรมจนถึงการเผยแพร่ผลงาน) "
  "บวกอีก 1–2 เดือนสำหรับการนำเสนอและสอบ ดังตารางต่อไปนี้ (เซลล์ที่แรเงาคือช่วงเวลาที่วางแผนไว้)")
months = ["มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]
tasks = [
    ("ทบทวนวรรณกรรมและงานที่เกี่ยวข้อง", [1,1,0,0,0,0,0]),
    ("เตรียมข้อมูลและสร้างภาพแรสเตอร์ (เสร็จแล้ว)", [1,0,0,0,0,0,0]),
    ("แบ่งส่วนต้นไม้รายต้น + เทียบ baseline/TreeLearn", [1,1,1,0,0,0,0]),
    ("ประมาณค่า DBH และวัดผล", [0,0,1,1,1,0,0]),
    ("การทดลองและวิเคราะห์ความแม่นยำ–ประสิทธิภาพ", [0,0,0,1,1,1,0]),
    ("เขียนวิทยานิพนธ์และเผยแพร่ผลงาน", [0,0,0,0,1,1,1]),
    ("นำเสนอโครงร่าง/สอบป้องกัน", [0,0,0,0,0,1,1]),
]
gt = doc.add_table(rows=len(tasks)+1, cols=len(months)+1)
gt.style = "Table Grid"
hc = gt.rows[0].cells
r = hc[0].paragraphs[0].add_run("งาน / เดือน (พ.ศ. 2569)"); _set_run_fonts(r, size=13, bold=True, color=RGBColor(0xFF,0xFF,0xFF)); shade(hc[0], "A0006D")
for j, m in enumerate(months):
    rr = hc[j+1].paragraphs[0]; rr.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = rr.add_run(m); _set_run_fonts(run, size=13, bold=True, color=RGBColor(0xFF,0xFF,0xFF)); shade(hc[j+1], "A0006D")
for i, (name, spans) in enumerate(tasks, 1):
    cells = gt.rows[i].cells
    r = cells[0].paragraphs[0].add_run(name); _set_run_fonts(r, size=13, color=INK)
    for j, on in enumerate(spans):
        if on:
            shade(cells[j+1], "C77DAE")
page_break()

# =====================================================================
# 7. รายการอ้างอิง
# =====================================================================
H1("7. รายการอ้างอิง")
refs = [
    '[1] Liu, L., Zhang, A., Xiao, S., Hu, S., He, N., Pang, H., Zhang, X., & Yang, S. (2021). "Single Tree Segmentation and Diameter at Breast Height Estimation With Mobile LiDAR." IEEE Access, 9, 24314–24325.',
    '[2] Proudman, A., Ramezani, M., & Fallon, M. (2021). "Online Estimation of Diameter at Breast Height (DBH) of Forest Trees Using a Handheld LiDAR." 2021 European Conference on Mobile Robots (ECMR), 1–7.',
    '[3] Henrich, J., van Delden, J., Seidel, D., Kneib, T., & Ecker, A. S. (2024). "TreeLearn: A Deep Learning Method for Segmenting Individual Trees from Ground-Based LiDAR Forest Point Clouds." Ecological Informatics, 84, 102888.',
    '[4] Shao, J., Lin, Y.-C., Wingren, C., Shin, S.-Y., Fei, W., Carpenter, J., Habib, A., & Fei, S. (2024). "Large-Scale Inventory in Natural Forests with Mobile LiDAR Point Clouds." Science of Remote Sensing, 10, 100168.',
    '[5] Sheng, Y., Zhao, Q., Wang, X., Liu, Y., & Yin, X. (2024). "Tree Diameter at Breast Height Extraction Based on Mobile Laser Scanning Point Cloud." Forests, 15(4), 590.',
    '[6] Cheng, D., Cladera Ojeda, F., Prabhu, A., Liu, X., Zhu, A., Green, P. C., Ehsani, R., Chaudhari, P., & Kumar, V. (2023). "TreeScope: An Agricultural Robotics Dataset for LiDAR-Based Mapping of Trees in Forests and Orchards." arXiv:2310.02162.',
    '[7] Chen, S. W., Nardari, G. V., Lee, E. S., Qu, C., Liu, X., Romero, R. A. F., & Kumar, V. (2020). "SLOAM: Semantic Lidar Odometry and Mapping for Forest Inventory." IEEE Robotics and Automation Letters, 5(2), 612–619.',
    '[8] Jocher, G., et al. (2024). "Ultralytics YOLO (YOLOv11)." https://github.com/ultralytics/ultralytics',
]
for rtext in refs:
    p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.left_indent = Inches(0.4); p.paragraph_format.first_line_indent = Inches(-0.4)
    run = p.add_run(rtext); _set_run_fonts(run, size=15, color=INK)

doc.save(str(OUT))
print("Saved:", OUT)
print("Paragraphs:", len(doc.paragraphs))
