from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile


OUT = Path(__file__).with_name("draft_proposal_lidar_dbh_multichannel.pptx")
SLIDE_W = 12192000
SLIDE_H = 6858000
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

TITLE = (
    "การแบ่งแยกต้นไม้รายต้นจาก Handheld LiDAR Point Cloud "
    "สำหรับประเมิน DBH ในสวนยางพาราโดยใช้ Multi-channel CNN"
)

SLIDES = [
    {
        "title": TITLE,
        "subtitle": (
            "Individual Tree Segmentation from Handheld LiDAR Point Clouds "
            "for DBH Estimation in Rubber Plantations using Multi-channel CNN"
        ),
        "bullets": [
            "เสนอโดย: [ชื่อ-รหัสนิสิต]",
            "อาจารย์ที่ปรึกษา: [ชื่ออาจารย์]",
            "Department of Computer Engineering, Chulalongkorn University",
        ],
        "kind": "title",
    },
    {
        "title": "Motivation",
        "subtitle": "Forest inventory needs tree-level measurement",
        "bullets": [
            "DBH เป็นตัวแปรสำคัญของ forest inventory, biomass/carbon estimation และการติดตามการเติบโต",
            "การวัดด้วยมือใช้เวลาและแรงงานสูง โดยเฉพาะเมื่อต้องทำหลายแปลงหรือทำซ้ำ",
            "Handheld LiDAR เก็บข้อมูล 3D รอบลำต้นได้เร็วและเหมาะกับพื้นที่ใต้เรือนยอด",
            "คอขวดสำคัญคือการแยก point cloud ออกเป็นต้นไม้รายต้นอย่างถูกต้อง",
        ],
    },
    {
        "title": "Problem Statement",
        "subtitle": "จาก point cloud 12 แปลง ไปสู่ต้นไม้รายต้นและ DBH",
        "bullets": [
            "Input: point cloud ของสวนยางพารา 12 แปลง พร้อม ground truth ตำแหน่งต้นไม้และ DBH รายต้น",
            "Output: ตำแหน่ง/ขอบเขตของต้นไม้แต่ละต้น และค่า DBH ที่คำนวณจากจุดบริเวณ breast height",
            "Challenges: ความหนาแน่นจุดไม่สม่ำเสมอ, occlusion, วัชพืช/กิ่ง/ใบปะปน, ต้นยางเรียงใกล้กันเป็นแถว",
            "คำถามหลัก: จะแยกต้นไม้รายต้นให้แม่นขึ้น โดยยังประมวลผลเบากว่าวิธี 3D point-cloud-based ได้หรือไม่",
        ],
    },
    {
        "title": "Related Work Landscape",
        "subtitle": "แนวทางที่พบจากตาราง Sumarlize และ literature",
        "bullets": [
            "Classical pipeline: ground removal, trunk extraction, clustering, circle/cylinder fitting",
            "Handheld/mobile LiDAR DBH: segment/track trees, accumulate scans, fit DBH at breast height",
            "Large-scale MLS inventory: ForestSPG ทำ semantic segmentation แล้ว stem mapping และ circle fitting",
            "TreeLearn: 3D sparse CNN ทำนาย tree/non-tree และ offset เพื่อทำ instance segmentation",
            "TreeScope/SLOAM: robotics LiDAR datasets และ benchmark สำหรับ semantic/stem/diameter estimation",
        ],
    },
    {
        "title": "Research Gap",
        "subtitle": "ช่องว่างที่ proposal นี้ต้องการตอบ",
        "bullets": [
            "งานเดิมมักแยกเป็น semantic segmentation -> stem mapping/instance segmentation -> DBH fitting",
            "DBH error มักเกิดจาก segmentation ผิด, ลำต้นถูกบัง, slice ระดับอกมีจุดไม่ครบวง หรือมีกิ่ง/ใบปะปน",
            "Rule-based methods ต้องปรับ radius, density threshold, voxel size และ RANSAC setting ตามข้อมูล",
            "TreeLearn แม่นและอัตโนมัติ แต่ใช้ทรัพยากรสูงและอาจต้อง fine-tune เมื่อเปลี่ยน domain",
            "Single-channel density image เบา แต่ทิ้งข้อมูลแนวดิ่งและสัญญาณบริเวณ DBH",
        ],
    },
    {
        "title": "Research Objective",
        "subtitle": "วัตถุประสงค์ของงานวิจัย",
        "bullets": [
            "พัฒนา pipeline สำหรับ individual tree segmentation จาก handheld LiDAR point cloud ของสวนยางพาราโดยใช้ multi-channel CNN",
            "เปรียบเทียบ multi-channel CNN กับ single-channel CNN baseline และ TreeLearn บนข้อมูลชุดเดียวกัน",
            "ประเมินผลกระทบของ segmentation ต่อการประมาณค่า DBH รายต้น",
            "เปรียบเทียบ runtime, memory/VRAM usage, model size และความง่ายในการนำไปใช้งาน",
        ],
    },
    {
        "title": "Research Questions",
        "subtitle": "คำถามวิจัยและสมมติฐาน",
        "bullets": [
            "RQ1: multi-channel CNN ให้ Precision, Recall, F1 ดีกว่า density-only หรือไม่",
            "RQ2: เมื่อใช้ test plots เดียวกัน multi-channel CNN เทียบกับ TreeLearn ได้มากน้อยเพียงใด",
            "RQ3: multi-channel CNN ลด runtime และ resource usage เมื่อเทียบกับ 3D point-cloud-based method ได้หรือไม่",
            "H1: การเพิ่ม hag_p95 และ dbh_band_density ช่วยลด false positive/false negative",
            "H2: segmentation ที่ดีขึ้นจะลด DBH error ใน downstream fitting",
        ],
    },
    {
        "title": "Dataset and Ground Truth",
        "subtitle": "Rubber plantation point clouds",
        "bullets": [
            "ข้อมูลหลัก: สวนยางพารา 12 แปลง หรือ 12 point clouds",
            "Ground truth: ตำแหน่งต้นไม้ X/Y และค่า DBH รายต้นจาก CSV",
            "Preprocessing: PCD/LAS conversion, filtering, rotation และจัดระบบพิกัดให้ตรงกับ label",
            "Train/validation/test split ระดับ plot เพื่อป้องกัน leakage",
            "ควบคุม seed, image size, pixel size, box size และ augmentation ให้เทียบกันได้",
        ],
    },
    {
        "title": "Proposed System Overview",
        "subtitle": "ตำแหน่งของ multi-channel CNN ใน pipeline",
        "bullets": [
            "Handheld LiDAR scan -> Point cloud preprocessing",
            "Feature rasterization -> Multi-channel CNN/YOLO",
            "Tree centers/boxes -> Extract trunk points around each predicted tree",
            "DBH fitting at breast-height band -> Evaluation against ground truth",
        ],
        "kind": "pipeline",
    },
    {
        "title": "Multi-channel CNN Input",
        "subtitle": "Synthetic RGB from physical LiDAR features",
        "bullets": [
            "R = density: จำนวนจุดในแต่ละ top-view grid cell",
            "G = hag_p95: 95th percentile ของ height above ground ในแต่ละ cell",
            "B = dbh_band_density: จำนวนจุดในช่วง 1.0-1.6 m เหนือพื้น",
            "ใช้เป็น RGB image เพื่อ train กับ YOLO/CNN pipeline เดิมได้",
            "ปิด color augmentation เพราะสีเป็น feature channel ไม่ใช่ natural image color",
        ],
    },
    {
        "title": "Baselines and Comparison",
        "subtitle": "วิธีที่จะเปรียบเทียบ",
        "bullets": [
            "Single-channel CNN: top-view density image + YOLO/CNN",
            "Proposed multi-channel CNN: density + hag_p95 + dbh_band_density",
            "TreeLearn: deep learning instance segmentation บน 3D point cloud โดยตรง",
            "Point-cloud processing baseline: ground filtering + trunk extraction + clustering + circle fitting",
            "Optional reference: SLOAM/TreeScope-style evaluation for stem mapping and diameter estimation",
        ],
    },
    {
        "title": "Experiment Design",
        "subtitle": "Controlled experiments on the same plots",
        "bullets": [
            "Experiment 1: single-channel vs multi-channel CNN",
            "Experiment 2: channel ablation: density, density+hag_p95, density+dbh_band_density, all channels",
            "Experiment 3: multi-channel CNN vs TreeLearn on the same test plots",
            "Experiment 4: DBH fitting from each method: single slice vs multi-height bins + RANSAC/outlier rejection",
            "Experiment 5: efficiency benchmark: preprocessing, inference time, RAM/VRAM, model size",
        ],
    },
    {
        "title": "Evaluation Metrics",
        "subtitle": "Accuracy and efficiency",
        "bullets": [
            "Tree detection/segmentation: Precision, Recall, F1-score, Tree Detection Rate, count error",
            "Localization: center error after matching prediction to ground truth, omission error, commission error",
            "Instance quality: coverage / IoU / point-level metric if instance labels are available",
            "DBH: MAE, RMSE, bias, relative error, percent within ±2 cm or ±5 cm",
            "Efficiency: runtime per plot, peak CPU memory, peak GPU memory, throughput, model size",
        ],
    },
    {
        "title": "Expected Contributions",
        "subtitle": "สิ่งที่คาดว่าจะได้จากงานวิจัย",
        "bullets": [
            "Pipeline สำหรับแยกต้นยางรายต้นและประเมิน DBH จาก handheld LiDAR point cloud",
            "Multi-channel raster representation ที่เพิ่มข้อมูลความสูงและสัญญาณบริเวณ DBH แต่ยังใช้ CNN/YOLO ได้",
            "Benchmark เปรียบเทียบ single-channel CNN, multi-channel CNN และ TreeLearn บนข้อมูล 12 แปลงเดียวกัน",
            "ข้อเสนอแนะเชิงปฏิบัติว่าเมื่อใดควรใช้ 2D multi-channel CNN และเมื่อใดควรใช้ 3D point-cloud segmentation",
        ],
    },
    {
        "title": "Planning and References",
        "subtitle": "Tentative plan: May-Dec 2026",
        "bullets": [
            "May-Jun: literature review, finalize problem statement, inspect data/ground truth",
            "Jun-Jul: reproduce single-channel baseline and define evaluation protocol",
            "Jul-Aug: implement and train multi-channel CNN",
            "Aug-Sep: run TreeLearn / point-cloud baselines on same plots",
            "Sep-Oct: DBH fitting, ablation, resource benchmark, error analysis",
            "References: Liu 2021; Proudman 2021; Shao 2024; Cheng 2023/2024; Henrich 2024",
        ],
    },
]


def text_box(
    shape_id: int,
    x: int,
    y: int,
    w: int,
    h: int,
    paragraphs: list[str],
    font_size: int = 2400,
    color: str = "24342f",
    bold_first: bool = False,
    bullet: bool = False,
) -> str:
    xml = [
        f'<p:sp><p:nvSpPr><p:cNvPr id="{shape_id}" name="TextBox {shape_id}"/>'
        '<p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>',
        (
            f'<p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{w}" cy="{h}"/>'
            '</a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
            '<a:noFill/><a:ln><a:noFill/></a:ln></p:spPr>'
        ),
        '<p:txBody><a:bodyPr wrap="square" rtlCol="0"/><a:lstStyle/>',
    ]
    for idx, paragraph in enumerate(paragraphs):
        ppr = '<a:pPr marL="342900" indent="-228600"><a:buChar char="•"/></a:pPr>' if bullet else "<a:pPr/>"
        bold = ' b="1"' if (bold_first and idx == 0) else ""
        xml.append(
            f"<a:p>{ppr}<a:r><a:rPr lang=\"th-TH\" sz=\"{font_size}\"{bold}>"
            f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'
            '<a:latin typeface="TH Sarabun New"/><a:ea typeface="TH Sarabun New"/>'
            '<a:cs typeface="TH Sarabun New"/></a:rPr>'
            f"<a:t>{escape(paragraph)}</a:t></a:r></a:p>"
        )
    xml.append("</p:txBody></p:sp>")
    return "".join(xml)


def rect(shape_id: int, x: int, y: int, w: int, h: int, fill: str, line: str, radius: bool = False) -> str:
    prst = "roundRect" if radius else "rect"
    return (
        f'<p:sp><p:nvSpPr><p:cNvPr id="{shape_id}" name="Shape {shape_id}"/>'
        '<p:cNvSpPr/><p:nvPr/></p:nvSpPr><p:spPr>'
        f'<a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{w}" cy="{h}"/></a:xfrm>'
        f'<a:prstGeom prst="{prst}"><a:avLst/></a:prstGeom>'
        f'<a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>'
        f'<a:ln><a:solidFill><a:srgbClr val="{line}"/></a:solidFill></a:ln>'
        "</p:spPr></p:sp>"
    )


def connector(shape_id: int, x1: int, y1: int, x2: int, y2: int, color: str = "2F6F5E") -> str:
    w = max(1, x2 - x1)
    h = max(1, y2 - y1)
    return (
        f'<p:cxnSp><p:nvCxnSpPr><p:cNvPr id="{shape_id}" name="Connector {shape_id}"/>'
        '<p:cNvCxnSpPr/><p:nvPr/></p:nvCxnSpPr><p:spPr>'
        f'<a:xfrm><a:off x="{x1}" y="{y1}"/><a:ext cx="{w}" cy="{h}"/></a:xfrm>'
        '<a:prstGeom prst="straightConnector1"><a:avLst/></a:prstGeom>'
        f'<a:ln w="25400"><a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'
        '<a:tailEnd type="none"/><a:headEnd type="triangle"/></a:ln>'
        "</p:spPr></p:cxnSp>"
    )


def slide_xml(idx: int, data: dict) -> str:
    shapes: list[str] = []
    sid = 2
    shapes.append(rect(sid, 0, 0, SLIDE_W, SLIDE_H, "F7FAF8", "F7FAF8"))
    sid += 1
    shapes.append(rect(sid, 0, 0, 190000, SLIDE_H, "2F6F5E", "2F6F5E"))
    sid += 1
    shapes.append(rect(sid, 190000, 0, SLIDE_W - 190000, 105000, "88B04B", "88B04B"))
    sid += 1

    if data.get("kind") == "title":
        shapes.append(text_box(sid, 600000, 820000, 10600000, 1800000, [data["title"]], 3100, "17352c", True))
        sid += 1
        shapes.append(text_box(sid, 650000, 2700000, 10400000, 900000, [data["subtitle"]], 1800, "47645b"))
        sid += 1
        shapes.append(text_box(sid, 700000, 4300000, 8500000, 1200000, data["bullets"], 1900, "24342f"))
        sid += 1
    else:
        shapes.append(text_box(sid, 580000, 360000, 10400000, 650000, [data["title"]], 3100, "17352c", True))
        sid += 1
        shapes.append(text_box(sid, 600000, 1030000, 10400000, 380000, [data["subtitle"]], 1650, "5a6d66"))
        sid += 1
        if data.get("kind") == "pipeline":
            labels = ["Point cloud", "Feature\nraster", "CNN/YOLO", "Trunk crop", "DBH fitting", "Metrics"]
            x0, y0 = 620000, 1750000
            box_w, box_h, gap = 1680000, 760000, 240000
            for i, label in enumerate(labels):
                x = x0 + i * (box_w + gap)
                shapes.append(rect(sid, x, y0, box_w, box_h, "EAF2EA", "9BBF9D", True))
                sid += 1
                shapes.append(text_box(sid, x + 100000, y0 + 160000, box_w - 200000, box_h - 180000, label.split("\n"), 1700, "17352c", True))
                sid += 1
                if i < len(labels) - 1:
                    shapes.append(connector(sid, x + box_w + 25000, y0 + box_h // 2, x + box_w + gap - 25000, y0 + box_h // 2))
                    sid += 1
            shapes.append(text_box(sid, 750000, 3050000, 10400000, 2600000, data["bullets"], 1800, "24342f", bullet=True))
            sid += 1
        else:
            shapes.append(text_box(sid, 760000, 1660000, 10300000, 4700000, data["bullets"], 1850, "24342f", bullet=True))
            sid += 1

    shapes.append(text_box(sid, 11100000, 6400000, 700000, 220000, [str(idx)], 1300, "6d7c76"))
    sp_tree = "".join(shapes)
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld><p:spTree>
    <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
    <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
    {sp_tree}
  </p:spTree></p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>'''


def content_types(nslides: int) -> str:
    overrides = [
        '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>',
        '<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>',
        '<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>',
        '<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>',
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>',
        '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>',
    ]
    for i in range(1, nslides + 1):
        overrides.append(
            f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        + "".join(overrides)
        + "</Types>"
    )


def presentation_xml(nslides: int) -> str:
    ids = "".join(f'<p:sldId id="{255 + i}" r:id="rId{i + 1}"/>' for i in range(1, nslides + 1))
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>
  <p:sldIdLst>{ids}</p:sldIdLst>
  <p:sldSz cx="{SLIDE_W}" cy="{SLIDE_H}" type="screen16x9"/>
  <p:notesSz cx="6858000" cy="9144000"/>
  <p:defaultTextStyle/>
</p:presentation>'''


def presentation_rels(nslides: int) -> str:
    rels = [
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>'
    ]
    for i in range(1, nslides + 1):
        rels.append(
            f'<Relationship Id="rId{i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{i}.xml"/>'
        )
    return f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="{REL_NS}">' + "".join(rels) + "</Relationships>"


def root_rels() -> str:
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="{REL_NS}">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>'''


SLIDE_MASTER = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld>
<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>
<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>
<p:txStyles><p:titleStyle/><p:bodyStyle/><p:otherStyle/></p:txStyles>
</p:sldMaster>'''

SLIDE_LAYOUT = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank" preserve="1">
<p:cSld name="Blank"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sldLayout>'''

THEME = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="BiomassProposal"><a:themeElements><a:clrScheme name="Biomass"><a:dk1><a:srgbClr val="17352C"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1><a:dk2><a:srgbClr val="24342F"/></a:dk2><a:lt2><a:srgbClr val="F7FAF8"/></a:lt2><a:accent1><a:srgbClr val="2F6F5E"/></a:accent1><a:accent2><a:srgbClr val="88B04B"/></a:accent2><a:accent3><a:srgbClr val="D89A3A"/></a:accent3><a:accent4><a:srgbClr val="4C7A93"/></a:accent4><a:accent5><a:srgbClr val="A65D5D"/></a:accent5><a:accent6><a:srgbClr val="7B6D8D"/></a:accent6><a:hlink><a:srgbClr val="2F6F5E"/></a:hlink><a:folHlink><a:srgbClr val="7B6D8D"/></a:folHlink></a:clrScheme><a:fontScheme name="TH"><a:majorFont><a:latin typeface="TH Sarabun New"/><a:ea typeface="TH Sarabun New"/><a:cs typeface="TH Sarabun New"/></a:majorFont><a:minorFont><a:latin typeface="TH Sarabun New"/><a:ea typeface="TH Sarabun New"/><a:cs typeface="TH Sarabun New"/></a:minorFont></a:fontScheme><a:fmtScheme name="Default"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst><a:lnStyleLst><a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst><a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst><a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst></a:fmtScheme></a:themeElements><a:objectDefaults/><a:extraClrSchemeLst/></a:theme>'''


def write_pptx() -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    core = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>{escape(TITLE)}</dc:title><dc:creator>Codex</dc:creator><cp:lastModifiedBy>Codex</cp:lastModifiedBy><dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created><dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified></cp:coreProperties>'''
    app = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
        'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
        f"<Application>Codex</Application><PresentationFormat>On-screen Show (16:9)</PresentationFormat><Slides>{len(SLIDES)}</Slides><Company></Company></Properties>"
    )

    with ZipFile(OUT, "w", ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types(len(SLIDES)))
        z.writestr("_rels/.rels", root_rels())
        z.writestr("docProps/core.xml", core)
        z.writestr("docProps/app.xml", app)
        z.writestr("ppt/presentation.xml", presentation_xml(len(SLIDES)))
        z.writestr("ppt/_rels/presentation.xml.rels", presentation_rels(len(SLIDES)))
        z.writestr("ppt/slideMasters/slideMaster1.xml", SLIDE_MASTER)
        z.writestr(
            "ppt/slideMasters/_rels/slideMaster1.xml.rels",
            f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="{REL_NS}"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/></Relationships>',
        )
        z.writestr("ppt/slideLayouts/slideLayout1.xml", SLIDE_LAYOUT)
        z.writestr(
            "ppt/slideLayouts/_rels/slideLayout1.xml.rels",
            f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="{REL_NS}"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/></Relationships>',
        )
        z.writestr("ppt/theme/theme1.xml", THEME)
        for i, slide in enumerate(SLIDES, 1):
            z.writestr(f"ppt/slides/slide{i}.xml", slide_xml(i, slide))
            z.writestr(
                f"ppt/slides/_rels/slide{i}.xml.rels",
                f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="{REL_NS}"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/></Relationships>',
            )


if __name__ == "__main__":
    write_pptx()
    print(OUT)
    print(OUT.stat().st_size)
