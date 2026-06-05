from __future__ import annotations

import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "ChulaTemplate.pptx"
OUT = Path(__file__).with_name("draft_proposal_lidar_dbh_multichannel_en_chula.pptx")

REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
CP_NS = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
DC_NS = "http://purl.org/dc/elements/1.1/"
DCTERMS_NS = "http://purl.org/dc/terms/"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"

SLIDE_W = 12192000
SLIDE_H = 6858000

TITLE = (
    "Individual Tree Segmentation from Handheld LiDAR Point Clouds "
    "for DBH Estimation in Rubber Plantations using Multi-channel CNN"
)

SLIDES: list[dict] = [
    {
        "layout": 1,
        "kind": "title",
        "title": TITLE,
        "subtitle": "Draft Thesis Proposal",
        "bullets": [
            "[Student Name]  [Student ID]",
            "Advisor: [Advisor Name]",
            "Department of Computer Engineering, Chulalongkorn University",
        ],
    },
    {
        "layout": 2,
        "title": "Motivation",
        "subtitle": "Forest inventory needs reliable tree-level measurements.",
        "bullets": [
            "Diameter at breast height (DBH) is a core variable for forest inventory, biomass estimation, and growth monitoring.",
            "Manual DBH measurement is accurate but labor-intensive, especially across repeated surveys and multiple plots.",
            "Handheld LiDAR can rapidly capture 3D understory structure around tree stems.",
            "The bottleneck is robust individual tree segmentation before downstream DBH extraction.",
        ],
    },
    {
        "layout": 2,
        "title": "Problem Statement",
        "subtitle": "From 12 rubber plantation point clouds to individual trees and DBH.",
        "bullets": [
            "Input: 12 handheld/mobile LiDAR point clouds from rubber plantation plots.",
            "Ground truth: tree locations and DBH measurements for each plot.",
            "Output: tree-level detections or segments, then DBH estimated from points near breast height.",
            "Challenges include uneven point density, occlusion, understory clutter, and regularly spaced stems that may be merged.",
        ],
    },
    {
        "layout": 2,
        "title": "Related Work Landscape",
        "subtitle": "Most systems combine segmentation, stem mapping, and geometric fitting.",
        "bullets": [
            "Classical pipelines rely on ground filtering, trunk extraction, clustering, and circle or cylinder fitting.",
            "Mobile and handheld LiDAR DBH systems track individual trees and fit trunk models from accumulated scans.",
            "Large-scale MLS inventory uses semantic segmentation, stem mapping, and DBH measurement at the individual-tree level.",
            "TreeLearn performs 3D point-cloud tree instance segmentation using sparse convolutional neural networks.",
            "TreeScope and SLOAM provide robotics-oriented LiDAR datasets and mapping frameworks for tree inventory tasks.",
        ],
    },
    {
        "layout": 2,
        "title": "Research Gap",
        "subtitle": "There is an accuracy-efficiency gap between lightweight 2D models and heavy 3D point-cloud models.",
        "bullets": [
            "Rule-based point-cloud methods are sensitive to radius, density, voxel size, and fitting thresholds.",
            "DBH errors often originate from poor segmentation, occluded stems, incomplete breast-height slices, or branch/leaf contamination.",
            "TreeLearn is powerful but requires 3D sparse CNN inference, GPU memory, and possibly domain fine-tuning.",
            "A single-channel top-view density image is lightweight but discards vertical structure and breast-height evidence.",
            "It remains unclear whether physically meaningful multi-channel 2D features can improve accuracy while preserving efficiency.",
        ],
    },
    {
        "layout": 2,
        "title": "Research Objectives",
        "subtitle": "The proposal focuses on individual tree segmentation as the upstream step for DBH estimation.",
        "bullets": [
            "Develop a multi-channel CNN pipeline for individual tree segmentation from handheld LiDAR point clouds.",
            "Compare multi-channel CNN with a single-channel density baseline using the same plantation plots.",
            "Benchmark against 3D point-cloud-based methods such as TreeLearn on the same test data.",
            "Quantify how segmentation quality affects downstream DBH extraction accuracy.",
            "Evaluate runtime, memory/VRAM usage, model size, and deployment practicality.",
        ],
    },
    {
        "layout": 2,
        "title": "Research Questions",
        "subtitle": "Key questions and working hypotheses.",
        "bullets": [
            "RQ1: Does multi-channel CNN improve precision, recall, and F1-score over a density-only baseline?",
            "RQ2: How close is multi-channel CNN to TreeLearn when both are evaluated on the same rubber plantation plots?",
            "RQ3: Does multi-channel CNN reduce inference time and resource usage compared with 3D point-cloud segmentation?",
            "H1: Height-above-ground and breast-height density channels reduce false positives and false negatives.",
            "H2: Better individual tree segmentation reduces downstream DBH error.",
        ],
    },
    {
        "layout": 2,
        "title": "Dataset and Controls",
        "subtitle": "Rubber plantation data will be evaluated at the plot level.",
        "bullets": [
            "Main dataset: 12 rubber plantation point clouds.",
            "Labels: tree X/Y positions and field-measured DBH from CSV files.",
            "Preprocessing: PCD/LAS conversion, filtering, rotation, and coordinate alignment with labels.",
            "Train/validation/test split will be performed by plot to prevent leakage.",
            "The same split seed, image size, pixel size, bounding-box size, and augmentation policy will be used for fair comparison.",
        ],
    },
    {
        "layout": 2,
        "kind": "pipeline",
        "title": "Proposed System Overview",
        "subtitle": "Multi-channel CNN is used for individual tree segmentation before DBH fitting.",
        "bullets": [
            "Point cloud preprocessing normalizes the plot and aligns coordinates.",
            "Feature rasterization converts 3D points into physically meaningful 2D channels.",
            "CNN/YOLO predicts tree centers or tree-level regions in top-view space.",
            "Predicted trees are used to crop trunk points near breast height.",
            "DBH is estimated using circle/cylinder fitting and compared with field measurements.",
        ],
    },
    {
        "layout": 2,
        "title": "Multi-channel CNN Input",
        "subtitle": "Synthetic RGB channels encode LiDAR-derived physical features.",
        "bullets": [
            "R = density: number of points in each top-view grid cell.",
            "G = hag_p95: 95th percentile of height above local ground in each cell.",
            "B = dbh_band_density: number of points in the 1.0-1.6 m height-above-ground band.",
            "The representation reuses the existing CNN/YOLO workflow without changing the input layer.",
            "Color augmentation is disabled because channel colors represent physical features, not natural image color.",
        ],
    },
    {
        "layout": 2,
        "title": "Comparison Methods",
        "subtitle": "All methods will be evaluated on the same test plots.",
        "bullets": [
            "Single-channel CNN: top-view density image and YOLO/CNN detector.",
            "Proposed multi-channel CNN: density + height-above-ground + breast-height density.",
            "TreeLearn: 3D sparse CNN tree instance segmentation directly on point clouds.",
            "Point-cloud baseline: ground filtering, trunk extraction, clustering, and circle/cylinder fitting.",
            "Optional references: SLOAM and TreeScope-style metrics for stem mapping and diameter estimation.",
        ],
    },
    {
        "layout": 2,
        "title": "Experiment Design",
        "subtitle": "The experiments isolate representation quality, model accuracy, and efficiency.",
        "bullets": [
            "Experiment 1: density-only CNN versus multi-channel CNN.",
            "Experiment 2: channel ablation: density, density + hag_p95, density + dbh_band_density, and all channels.",
            "Experiment 3: multi-channel CNN versus TreeLearn on identical test plots.",
            "Experiment 4: DBH extraction from each method using single-slice and multi-height-bin fitting.",
            "Experiment 5: runtime and resource benchmark for preprocessing, inference, and DBH fitting.",
        ],
    },
    {
        "layout": 2,
        "title": "Evaluation Metrics",
        "subtitle": "Accuracy and efficiency will be reported separately.",
        "bullets": [
            "Tree detection: precision, recall, F1-score, tree detection rate, and plot-level count error.",
            "Localization: matched center error, omission error, and commission error.",
            "Instance quality: coverage, IoU, or point-level metrics if point-level instance labels are available.",
            "DBH extraction: MAE, RMSE, bias, relative error, and percentage of trees within +/- 2 cm or +/- 5 cm.",
            "Efficiency: runtime per plot, peak CPU memory, peak GPU memory, throughput, and model size.",
        ],
    },
    {
        "layout": 2,
        "title": "Expected Contributions",
        "subtitle": "The study aims to deliver a practical accuracy-efficiency benchmark.",
        "bullets": [
            "A reproducible pipeline for rubber-tree segmentation and DBH extraction from handheld LiDAR point clouds.",
            "A multi-channel raster representation that preserves useful vertical and breast-height information.",
            "A controlled benchmark comparing density-only CNN, multi-channel CNN, TreeLearn, and point-cloud baselines.",
            "An analysis of how segmentation errors propagate into DBH estimation errors.",
            "Practical guidance on when lightweight 2D multi-channel CNN is preferable to direct 3D point-cloud segmentation.",
        ],
    },
    {
        "layout": 2,
        "kind": "references",
        "title": "References: Individual Tree Segmentation",
        "subtitle": "Grouped references follow the same numbered style used in the example proposal.",
        "bullets": [
            '[1] Liu, Lulu, Aiwu Zhang, Shen Xiao, Shaoxing Hu, Nianpeng He, Haiyang Pang, Xizhen Zhang, and Shikai Yang. 2021. "Single Tree Segmentation and Diameter at Breast Height Estimation With Mobile LiDAR." IEEE Access 9: 24314-24325.',
            '[2] Henrich, Jonathan, Jan van Delden, Dominik Seidel, Thomas Kneib, and Alexander S. Ecker. 2024. "TreeLearn: A Deep Learning Method for Segmenting Individual Trees from Ground-Based LiDAR Forest Point Clouds." Ecological Informatics 84: 102888.',
            '[3] Shao, Jinyuan, Yi-Chun Lin, Cameron Wingren, Sang-Yeop Shin, William Fei, Joshua Carpenter, Ayman Habib, and Songlin Fei. 2024. "Large-Scale Inventory in Natural Forests with Mobile LiDAR Point Clouds." Science of Remote Sensing 10: 100168.',
            '[4] Li, Qiujie, and Yu Yan. 2024. "Street Tree Segmentation from Mobile Laser Scanning Data Using Deep Learning-Based Image Instance Segmentation." Urban Forestry & Urban Greening 92: 128200.',
            '[5] Cheng, Derek, Fernando Cladera Ojeda, Ankit Prabhu, Xu Liu, Alan Zhu, Patrick Corey Green, Reza Ehsani, Pratik Chaudhari, and Vijay Kumar. 2023. "TreeScope: An Agricultural Robotics Dataset for LiDAR-Based Mapping of Trees in Forests and Orchards." arXiv:2310.02162.',
        ],
    },
    {
        "layout": 2,
        "kind": "references",
        "title": "References: DBH Extraction",
        "subtitle": "DBH-focused references are separated from segmentation references.",
        "bullets": [
            '[1] Proudman, Alexander, Milad Ramezani, and Maurice Fallon. 2021. "Online Estimation of Diameter at Breast Height (DBH) of Forest Trees Using a Handheld LiDAR." 2021 European Conference on Mobile Robots (ECMR).',
            '[2] Sheng, Yuhao, Qingzhan Zhao, Xuewen Wang, Yihao Liu, and Xiaojun Yin. 2024. "Tree Diameter at Breast Height Extraction Based on Mobile Laser Scanning Point Cloud." Forests 15 (4): 590.',
            '[3] Liu, Lulu, Aiwu Zhang, Shen Xiao, Shaoxing Hu, Nianpeng He, Haiyang Pang, Xizhen Zhang, and Shikai Yang. 2021. "Single Tree Segmentation and Diameter at Breast Height Estimation With Mobile LiDAR." IEEE Access 9: 24314-24325.',
            '[4] Shao, Jinyuan, Yi-Chun Lin, Cameron Wingren, Sang-Yeop Shin, William Fei, Joshua Carpenter, Ayman Habib, and Songlin Fei. 2024. "Large-Scale Inventory in Natural Forests with Mobile LiDAR Point Clouds." Science of Remote Sensing 10: 100168.',
            '[5] Cheng, Derek, Fernando Cladera Ojeda, Ankit Prabhu, Xu Liu, Alan Zhu, Patrick Corey Green, Reza Ehsani, Pratik Chaudhari, and Vijay Kumar. 2023. "TreeScope: An Agricultural Robotics Dataset for LiDAR-Based Mapping of Trees in Forests and Orchards." arXiv:2310.02162.',
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
    font_size: int = 1900,
    color: str = "242424",
    bold_first: bool = False,
    bullet: bool = False,
    para_gap: int = 600,
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
        if bullet:
            ppr = f'<a:pPr marL="342900" indent="-228600" spcAft="{para_gap}"><a:buChar char="•"/></a:pPr>'
        else:
            ppr = f'<a:pPr spcAft="{para_gap}"/>'
        bold = ' b="1"' if (bold_first and idx == 0) else ""
        xml.append(
            f"<a:p>{ppr}<a:r><a:rPr lang=\"en-US\" sz=\"{font_size}\"{bold}>"
            f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'
            '<a:latin typeface="Arial"/><a:ea typeface="Arial"/><a:cs typeface="Arial"/></a:rPr>'
            f"<a:t>{escape(paragraph)}</a:t></a:r></a:p>"
        )
    xml.append("</p:txBody></p:sp>")
    return "".join(xml)


def rect(shape_id: int, x: int, y: int, w: int, h: int, fill: str, line: str = "FFFFFF", alpha: int | None = None) -> str:
    alpha_xml = f'<a:alpha val="{alpha}"/>' if alpha is not None else ""
    return (
        f'<p:sp><p:nvSpPr><p:cNvPr id="{shape_id}" name="Shape {shape_id}"/>'
        '<p:cNvSpPr/><p:nvPr/></p:nvSpPr><p:spPr>'
        f'<a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{w}" cy="{h}"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
        f'<a:solidFill><a:srgbClr val="{fill}">{alpha_xml}</a:srgbClr></a:solidFill>'
        f'<a:ln><a:solidFill><a:srgbClr val="{line}"/></a:solidFill></a:ln>'
        "</p:spPr></p:sp>"
    )


def line(shape_id: int, x: int, y: int, w: int, color: str = "A0006D") -> str:
    return (
        f'<p:sp><p:nvSpPr><p:cNvPr id="{shape_id}" name="Line {shape_id}"/>'
        '<p:cNvSpPr/><p:nvPr/></p:nvSpPr><p:spPr>'
        f'<a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{w}" cy="0"/></a:xfrm>'
        '<a:prstGeom prst="line"><a:avLst/></a:prstGeom>'
        f'<a:ln w="25400"><a:solidFill><a:srgbClr val="{color}"/></a:solidFill></a:ln>'
        "</p:spPr></p:sp>"
    )


def connector(shape_id: int, x1: int, y1: int, x2: int, y2: int, color: str = "A0006D") -> str:
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

    # A light translucent reading layer keeps Chula template artwork visible while improving text contrast.
    shapes.append(rect(sid, 410000, 270000, 11100000, 6150000, "FFFFFF", "FFFFFF", alpha=90000))
    sid += 1

    if data.get("kind") == "title":
        shapes.append(text_box(sid, 760000, 1050000, 10400000, 1350000, [data["title"]], 3000, "A0006D", True))
        sid += 1
        shapes.append(text_box(sid, 780000, 2520000, 9000000, 500000, [data["subtitle"]], 2100, "44546A", True))
        sid += 1
        shapes.append(line(sid, 780000, 3200000, 5100000))
        sid += 1
        shapes.append(text_box(sid, 800000, 4040000, 8700000, 1200000, data["bullets"], 1750, "242424"))
        sid += 1
    else:
        shapes.append(text_box(sid, 650000, 420000, 10200000, 520000, [data["title"]], 2650, "A0006D", True))
        sid += 1
        shapes.append(line(sid, 650000, 970000, 4500000))
        sid += 1
        shapes.append(text_box(sid, 670000, 1100000, 10100000, 450000, [data["subtitle"]], 1450, "44546A"))
        sid += 1

        if data.get("kind") == "pipeline":
            labels = ["Point cloud", "Feature raster", "CNN/YOLO", "Tree crop", "DBH fitting", "Metrics"]
            x0, y0 = 650000, 1840000
            box_w, box_h, gap = 1640000, 620000, 260000
            for i, label in enumerate(labels):
                x = x0 + i * (box_w + gap)
                shapes.append(rect(sid, x, y0, box_w, box_h, "F4EAF2", "D8A8CB"))
                sid += 1
                shapes.append(text_box(sid, x + 90000, y0 + 185000, box_w - 180000, box_h - 180000, [label], 1450, "242424", True))
                sid += 1
                if i < len(labels) - 1:
                    shapes.append(connector(sid, x + box_w + 30000, y0 + box_h // 2, x + box_w + gap - 30000, y0 + box_h // 2))
                    sid += 1
            shapes.append(text_box(sid, 790000, 3100000, 9700000, 2600000, data["bullets"], 1600, "242424", bullet=True))
            sid += 1
        elif data.get("kind") == "references":
            shapes.append(text_box(sid, 780000, 1710000, 10350000, 4200000, data["bullets"], 1150, "242424", bullet=False, para_gap=1000))
            sid += 1
        else:
            shapes.append(text_box(sid, 840000, 1740000, 9900000, 4200000, data["bullets"], 1650, "242424", bullet=True))
            sid += 1

    shapes.append(text_box(sid, 11100000, 6320000, 600000, 220000, [str(idx)], 1050, "7A7A7A"))
    sp_tree = "".join(shapes)
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="{A_NS}" xmlns:r="{R_NS}" xmlns:p="{P_NS}">
  <p:cSld><p:spTree>
    <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
    <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
    {sp_tree}
  </p:spTree></p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>'''


def slide_rels(layout_number: int) -> str:
    return (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<Relationships xmlns="{REL_NS}">'
        f'<Relationship Id="rId1" Type="{R_NS}/slideLayout" Target="../slideLayouts/slideLayout{layout_number}.xml"/>'
        "</Relationships>"
    )


def update_content_types(xml_bytes: bytes, slide_count: int) -> bytes:
    ET.register_namespace("", CT_NS)
    root = ET.fromstring(xml_bytes)
    for node in list(root):
        if node.tag == f"{{{CT_NS}}}Override" and node.attrib.get("PartName", "").startswith("/ppt/slides/"):
            root.remove(node)
    for i in range(1, slide_count + 1):
        ET.SubElement(
            root,
            f"{{{CT_NS}}}Override",
            {
                "PartName": f"/ppt/slides/slide{i}.xml",
                "ContentType": "application/vnd.openxmlformats-officedocument.presentationml.slide+xml",
            },
        )
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def update_presentation_xml(xml_bytes: bytes, slide_count: int) -> bytes:
    ET.register_namespace("a", A_NS)
    ET.register_namespace("r", R_NS)
    ET.register_namespace("p", P_NS)
    root = ET.fromstring(xml_bytes)
    sld_id_lst = root.find(f"{{{P_NS}}}sldIdLst")
    if sld_id_lst is None:
        sld_master = root.find(f"{{{P_NS}}}sldMasterIdLst")
        insert_idx = list(root).index(sld_master) + 1 if sld_master is not None else 0
        sld_id_lst = ET.Element(f"{{{P_NS}}}sldIdLst")
        root.insert(insert_idx, sld_id_lst)
    else:
        for child in list(sld_id_lst):
            sld_id_lst.remove(child)
    for i in range(1, slide_count + 1):
        ET.SubElement(
            sld_id_lst,
            f"{{{P_NS}}}sldId",
            {"id": str(255 + i), f"{{{R_NS}}}id": f"rId{100 + i}"},
        )
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def update_presentation_rels(xml_bytes: bytes, slide_count: int) -> bytes:
    ET.register_namespace("", REL_NS)
    root = ET.fromstring(xml_bytes)
    for node in list(root):
        if node.attrib.get("Type") == f"{R_NS}/slide":
            root.remove(node)
    for i in range(1, slide_count + 1):
        ET.SubElement(
            root,
            f"{{{REL_NS}}}Relationship",
            {"Id": f"rId{100 + i}", "Type": f"{R_NS}/slide", "Target": f"slides/slide{i}.xml"},
        )
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def core_props() -> bytes:
    ET.register_namespace("cp", CP_NS)
    ET.register_namespace("dc", DC_NS)
    ET.register_namespace("dcterms", DCTERMS_NS)
    ET.register_namespace("xsi", XSI_NS)
    root = ET.Element(f"{{{CP_NS}}}coreProperties")
    ET.SubElement(root, f"{{{DC_NS}}}title").text = TITLE
    ET.SubElement(root, f"{{{DC_NS}}}creator").text = "Codex"
    ET.SubElement(root, f"{{{CP_NS}}}lastModifiedBy").text = "Codex"
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    created = ET.SubElement(root, f"{{{DCTERMS_NS}}}created", {f"{{{XSI_NS}}}type": "dcterms:W3CDTF"})
    created.text = now
    modified = ET.SubElement(root, f"{{{DCTERMS_NS}}}modified", {f"{{{XSI_NS}}}type": "dcterms:W3CDTF"})
    modified.text = now
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def app_props() -> bytes:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
        'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
        '<Application>Codex</Application>'
        '<PresentationFormat>On-screen Show (16:9)</PresentationFormat>'
        f"<Slides>{len(SLIDES)}</Slides>"
        "<Company>Chulalongkorn University</Company>"
        "</Properties>"
    ).encode("utf-8")


def copy_template_with_new_slides() -> None:
    if not TEMPLATE.exists():
        raise FileNotFoundError(f"Missing template: {TEMPLATE}")

    skip_patterns = [
        re.compile(r"ppt/slides/slide\d+\.xml$"),
        re.compile(r"ppt/slides/_rels/slide\d+\.xml\.rels$"),
    ]

    with ZipFile(TEMPLATE, "r") as src, ZipFile(OUT, "w", ZIP_DEFLATED) as dst:
        for info in src.infolist():
            name = info.filename
            if any(pattern.match(name) for pattern in skip_patterns):
                continue
            data = src.read(name)
            if name == "[Content_Types].xml":
                data = update_content_types(data, len(SLIDES))
            elif name == "ppt/presentation.xml":
                data = update_presentation_xml(data, len(SLIDES))
            elif name == "ppt/_rels/presentation.xml.rels":
                data = update_presentation_rels(data, len(SLIDES))
            elif name == "docProps/core.xml":
                data = core_props()
            elif name == "docProps/app.xml":
                data = app_props()
            dst.writestr(info, data)

        for idx, slide in enumerate(SLIDES, 1):
            dst.writestr(f"ppt/slides/slide{idx}.xml", slide_xml(idx, slide))
            dst.writestr(f"ppt/slides/_rels/slide{idx}.xml.rels", slide_rels(int(slide["layout"])))


if __name__ == "__main__":
    copy_template_with_new_slides()
    print(OUT)
    print(OUT.stat().st_size)
