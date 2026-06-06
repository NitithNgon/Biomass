#!/usr/bin/env python3
"""
Build the FIXED thesis-proposal deck following proposal/slide/fixed/instruction.md.

Design goals (from adviser feedback):
- Story-driven Introduction, ending with a single ~3-line Problem Statement.
- No Background / Research Objectives / Related-Work overview table / References section.
- One literature per slide (citation lives on its own slide).
- Scope of Work, Methodology (colored System Overview + one module per slide + Preliminary Work),
  Experimental Design (+ Dataset), Expected Outcome (no "Contribution", no success metrics), Milestones.
- All slides English, page numbers on every slide, full speaker script in HIDDEN notes,
  light on-slide text, image-forward.
"""
import os
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE, PP_PLACEHOLDER
from pptx.oxml.ns import qn
from PIL import Image as PILImage

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"

# Theme: "green" (default, v1) or "chula" (v2, Chulalongkorn template).
THEME = os.environ.get("DECK_THEME", "green").lower()
CHULA_BASE = HERE.parent / "old_prepare_text_for_slide" / "draft_proposal_lidar_dbh_multichannel_en_chula.pptx"

_NAME = "Individual Tree Segmentation from Handheld LiDAR Point Clouds for DBH Estimation using Multi-channel CNN"
OUT = HERE / (f"{_NAME} (v2 Chula).pptx" if THEME == "chula" else f"{_NAME}.pptx")

# ---- palette (green default) ----
GREEN_D = RGBColor(0x14, 0x53, 0x2D)   # deep forest green (titles)
GREEN_M = RGBColor(0x2E, 0x7D, 0x32)   # medium green (accents / done)
INK = RGBColor(0x22, 0x2B, 0x2E)       # body text
GRAY_T = RGBColor(0x60, 0x6A, 0x6E)    # muted text
RULE = RGBColor(0x2E, 0x7D, 0x32)      # title underline
BLUE_FILL = RGBColor(0xDD, 0xEC, 0xF7)
BLUE_LINE = RGBColor(0x2F, 0x6F, 0xAD)
BLUE_TXT = RGBColor(0x14, 0x3A, 0x5C)
GRAY_FILL = RGBColor(0xE2, 0xE4, 0xE6)
GRAY_LINE = RGBColor(0x9A, 0x9F, 0xA3)
RED_DOT = RGBColor(0xC6, 0x28, 0x2D)
GREEN_DOT = RGBColor(0x2E, 0x7D, 0x32)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
CARD = RGBColor(0xF2, 0xF6, 0xF3)
CARD_LINE = RGBColor(0xCF, 0xDD, 0xD3)
TINT_FILL = RGBColor(0xEC, 0xF4, 0xEE)   # soft highlight behind key statements

if THEME == "chula":
    # Chulalongkorn University magenta theme (heading/accent = Chula pink).
    GREEN_D = RGBColor(0xA0, 0x00, 0x6D)
    GREEN_M = RGBColor(0xA0, 0x00, 0x6D)
    RULE = RGBColor(0xA0, 0x00, 0x6D)
    CARD = RGBColor(0xF7, 0xEC, 0xF3)
    CARD_LINE = RGBColor(0xD8, 0xA8, 0xCB)
    TINT_FILL = RGBColor(0xF7, 0xE8, 0xF1)

FONT = "Arial"
SW, SH = Inches(13.333), Inches(7.5)

if THEME == "chula":
    prs = Presentation(str(CHULA_BASE))
    # Drop the template's sample slides; keep masters / layouts / theme / Chula art.
    _ids = prs.slides._sldIdLst
    for _sid in list(_ids):
        try:
            prs.part.drop_rel(_sid.get(qn("r:id")))
        except Exception:
            pass
        _ids.remove(_sid)
    SW, SH = prs.slide_width, prs.slide_height
else:
    prs = Presentation()
    prs.slide_width = SW
    prs.slide_height = SH
BLANK = prs.slide_layouts[6]

# Chula layout indices (resolved by name to be robust).
def _layout(name):
    for l in prs.slide_layouts:
        if l.name == name:
            return l
    return prs.slide_layouts[6]

_TITLE_TYPES = (PP_PLACEHOLDER.TITLE, PP_PLACEHOLDER.CENTER_TITLE)

def _strip_placeholders(s, keep=_TITLE_TYPES):
    for ph in list(s.placeholders):
        if ph.placeholder_format.type in keep:
            continue
        ph._element.getparent().remove(ph._element)

def _ph(s, types):
    for ph in s.placeholders:
        if ph.placeholder_format.type in types:
            return ph
    return None

_page = 0

def slide():
    global _page
    _page += 1
    if THEME == "chula":
        s = prs.slides.add_slide(_layout("Title and Content"))  # pink banner + Chula logo
        _strip_placeholders(s)  # keep only the title placeholder (sits in the banner)
        return s
    return prs.slides.add_slide(BLANK)

def _set(run, size, bold=False, color=INK, italic=False, name=FONT):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.name = name
    run.font.color.rgb = color

def textbox(s, l, t, w, h, anchor=None, wrap=True):
    tb = s.shapes.add_textbox(l, t, w, h)
    tf = tb.text_frame
    tf.word_wrap = wrap
    tf.margin_left = Pt(2); tf.margin_right = Pt(2)
    tf.margin_top = Pt(1); tf.margin_bottom = Pt(1)
    if anchor:
        tf.vertical_anchor = anchor
    return tb, tf

def para(tf, text, size=16, bold=False, color=INK, align=PP_ALIGN.LEFT,
         space_after=6, space_before=0, italic=False, first=False, name=FONT, line=None):
    p = tf.paragraphs[0] if (first and not tf.paragraphs[0].runs) else tf.add_paragraph()
    p.alignment = align
    p.space_after = Pt(space_after)
    p.space_before = Pt(space_before)
    if line is not None:
        p.line_spacing = line
    r = p.add_run(); r.text = text
    _set(r, size, bold, color, italic, name)
    return p

def page_number(s, dark_bg=False):
    tb, tf = textbox(s, SW - Inches(0.9), SH - Inches(0.5), Inches(0.7), Inches(0.35))
    para(tf, str(_page), size=12, color=(WHITE if dark_bg else GRAY_T),
         align=PP_ALIGN.RIGHT, first=True, space_after=0)

def title_block(s, text, sub=None):
    if THEME == "chula":
        # Fill the Chula banner title placeholder (white text on the pink banner).
        ph = _ph(s, _TITLE_TYPES)
        if ph is not None:
            tf = ph.text_frame; tf.word_wrap = True
            tf.vertical_anchor = MSO_ANCHOR.MIDDLE
            p = tf.paragraphs[0]
            for r in list(p.runs):
                r.text = ""
            r = p.add_run(); r.text = text
            _set(r, 21 if len(text) < 44 else 18, True, WHITE)
        return
    tb, tf = textbox(s, Inches(0.55), Inches(0.42), Inches(12.2), Inches(1.0))
    para(tf, text, size=27, bold=True, color=GREEN_D, first=True, space_after=2, line=1.0)
    if sub:
        para(tf, sub, size=14, color=GRAY_T, space_after=0)
    # underline rule
    ln = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.57), Inches(1.42), Inches(2.4), Pt(3))
    ln.fill.solid(); ln.fill.fore_color.rgb = RULE
    ln.line.fill.background()
    ln.shadow.inherit = False

def notes(s, text):
    s.notes_slide.notes_text_frame.text = text.strip()

def bullets(s, l, t, w, h, items, size=16, gap=8, color=INK, anchor=MSO_ANCHOR.TOP):
    tb, tf = textbox(s, l, t, w, h, anchor=anchor)
    for i, it in enumerate(items):
        if isinstance(it, tuple):
            txt, lvl = it
        else:
            txt, lvl = it, 0
        pad = "      " * lvl
        mark = "•  " if lvl == 0 else "–  "
        p = para(tf, f"{pad}{mark}{txt}", size=size if lvl == 0 else size-1,
                 color=color if lvl == 0 else GRAY_T, space_after=gap, first=(i == 0), line=1.05)
    return tb

def card(s, l, t, w, h, fill=CARD, line=CARD_LINE):
    sh = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, l, t, w, h)
    sh.fill.solid(); sh.fill.fore_color.rgb = fill
    sh.line.color.rgb = line; sh.line.width = Pt(1)
    sh.shadow.inherit = False
    # soften corner radius
    try:
        sh.adjustments[0] = 0.06
    except Exception:
        pass
    return sh

def picture(s, path, l, t, w=None, h=None, border=True):
    pic = s.shapes.add_picture(str(path), l, t, width=w, height=h)
    if border:
        pic.line.color.rgb = RGBColor(0xBB, 0xC4, 0xBD)
        pic.line.width = Pt(0.75)
    return pic

def fit_picture(s, path, bl, bt, bw, bh, border=True):
    """Place an image scaled to fit inside box (bl,bt,bw,bh), centered. Returns (l,t,w,h) EMU."""
    iw, ih = PILImage.open(str(path)).size
    ar = iw / ih
    box_ar = bw / bh
    if ar >= box_ar:
        w = bw; h = int(round(bw / ar))
    else:
        h = bh; w = int(round(bh * ar))
    l = bl + (bw - w) // 2
    t = bt + (bh - h) // 2
    pic = s.shapes.add_picture(str(path), l, t, width=w, height=h)
    if border:
        pic.line.color.rgb = RGBColor(0xBB, 0xC4, 0xBD); pic.line.width = Pt(0.75)
    return l, t, w, h

def fig_with_caption(s, path, bl, bt, bw, bh, cap):
    l, t, w, h = fit_picture(s, path, bl, bt, bw, bh)
    cy = t + h + Inches(0.04)
    caption(s, bl, cy, bw, cap)
    return l, t, w, h

def caption(s, l, t, w, text):
    tb, tf = textbox(s, l, t, w, Inches(0.32))
    para(tf, text, size=11, color=GRAY_T, align=PP_ALIGN.CENTER, first=True, space_after=0)

# =====================================================================
# SLIDE 1 — TITLE
# =====================================================================
if THEME == "chula":
    _page += 1
    s = prs.slides.add_slide(_layout("Title Slide"))  # Chula pink background + crest
    _strip_placeholders(s, keep=())  # draw our own white text over the pink art
    TXT = WHITE
    tb, tf = textbox(s, Inches(1.1), Inches(1.45), Inches(11.1), Inches(2.2), anchor=MSO_ANCHOR.MIDDLE)
    para(tf, "Individual Tree Segmentation from Handheld LiDAR Point Clouds",
         size=29, bold=True, color=TXT, align=PP_ALIGN.CENTER, first=True, space_after=4, line=1.05)
    para(tf, "for DBH Estimation in Rubber Plantations using Multi-channel CNN",
         size=29, bold=True, color=TXT, align=PP_ALIGN.CENTER, space_after=0, line=1.05)
    tb, tf = textbox(s, Inches(2.0), Inches(3.95), Inches(9.3), Inches(0.5))
    para(tf, "THESIS PROPOSAL", size=16, bold=True, color=TXT, align=PP_ALIGN.CENTER, first=True, space_after=0)
    tb, tf = textbox(s, Inches(2.0), Inches(4.7), Inches(9.3), Inches(2.0), anchor=MSO_ANCHOR.TOP)
    para(tf, "Nitith Ngonchaiyaphum   6872046721", size=17, bold=True, color=TXT, align=PP_ALIGN.CENTER, first=True, space_after=4)
    para(tf, "Master of Engineering: Computer Engineering (CM)  Plan A2", size=15, color=TXT, align=PP_ALIGN.CENTER, space_after=4)
    para(tf, "Advisor:  Dr. Sukhum Sattaratnamai", size=15, color=TXT, align=PP_ALIGN.CENTER, space_after=10)
    para(tf, "Department of Computer Engineering, Faculty of Engineering", size=13, color=TXT, align=PP_ALIGN.CENTER, space_after=2)
    para(tf, "Chulalongkorn University", size=13, color=TXT, align=PP_ALIGN.CENTER, space_after=0)
    page_number(s, dark_bg=True)
else:
    s = slide()
    # top accent band
    band = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SW, Inches(0.28))
    band.fill.solid(); band.fill.fore_color.rgb = GREEN_M; band.line.fill.background(); band.shadow.inherit = False
    bb = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, SH - Inches(0.28), SW, Inches(0.28))
    bb.fill.solid(); bb.fill.fore_color.rgb = GREEN_M; bb.line.fill.background(); bb.shadow.inherit = False

    tb, tf = textbox(s, Inches(0.9), Inches(1.55), Inches(11.5), Inches(2.2), anchor=MSO_ANCHOR.MIDDLE)
    para(tf, "Individual Tree Segmentation from Handheld LiDAR Point Clouds",
         size=30, bold=True, color=GREEN_D, align=PP_ALIGN.CENTER, first=True, space_after=4, line=1.05)
    para(tf, "for DBH Estimation in Rubber Plantations using Multi-channel CNN",
         size=30, bold=True, color=GREEN_D, align=PP_ALIGN.CENTER, space_after=0, line=1.05)

    tb, tf = textbox(s, Inches(2.0), Inches(3.95), Inches(9.3), Inches(0.5))
    para(tf, "THESIS PROPOSAL", size=16, bold=True, color=GREEN_M, align=PP_ALIGN.CENTER, first=True, space_after=0)

    tb, tf = textbox(s, Inches(2.0), Inches(4.7), Inches(9.3), Inches(2.0), anchor=MSO_ANCHOR.TOP)
    para(tf, "Nitith Ngonchaiyaphum   6872046721", size=17, bold=True, color=INK, align=PP_ALIGN.CENTER, first=True, space_after=4)
    para(tf, "Master of Engineering: Computer Engineering (CM)  Plan A2", size=15, color=INK, align=PP_ALIGN.CENTER, space_after=4)
    para(tf, "Advisor:  Dr. Sukhum Sattaratnamai", size=15, color=INK, align=PP_ALIGN.CENTER, space_after=10)
    para(tf, "Department of Computer Engineering, Faculty of Engineering", size=13, color=GRAY_T, align=PP_ALIGN.CENTER, space_after=2)
    para(tf, "Chulalongkorn University", size=13, color=GRAY_T, align=PP_ALIGN.CENTER, space_after=0)
    page_number(s)
notes(s, """
Good morning / afternoon, advisor and committee. My name is Nitith Ngonchaiyaphum, a Master of
Engineering student in Computer Engineering, Plan A2. Today I will present my thesis proposal:
"Individual Tree Segmentation from Handheld LiDAR Point Clouds for DBH Estimation in Rubber
Plantations using a Multi-channel CNN." My advisor is Dr. Sukhum Sattaratnamai.
""")

# =====================================================================
# SLIDE 2 — AGENDA  (no per-item page numbers)
# =====================================================================
s = slide()
title_block(s, "Agenda")
items = [
    "Introduction  (motivation → problem statement)",
    "Literature Review & Related Work",
    "Scope of Work",
    "Methodology  (system overview, modules, preliminary work)",
    "Experimental Design & Dataset",
    "Expected Outcome",
    "Milestones",
]
tb, tf = textbox(s, Inches(1.3), Inches(1.9), Inches(10.5), Inches(5.0))
for i, it in enumerate(items):
    p = para(tf, f"{i+1}.   {it}", size=20, color=INK, first=(i == 0), space_after=14)
page_number(s)
notes(s, """
Here is the outline. I will start with the introduction and the problem statement, review the
most relevant prior work, define the scope, then walk through the methodology and what I have
already done. Finally I will cover the experimental design, the expected outcome, and the timeline.
Every slide is numbered to make questions easy during Q&A.
""")

# =====================================================================
# SLIDE 3 — INTRODUCTION (story 1)
# =====================================================================
s = slide()
title_block(s, "Introduction")
bullets(s, Inches(0.6), Inches(1.85), Inches(6.4), Inches(4.8), [
    "DBH (diameter at breast height, ~1.3 m) is a key tree-level variable for biomass and forest inventory.",
    "Measuring DBH by hand over a whole plantation is slow and labor-intensive.",
    "Handheld / backpack LiDAR with SLAM captures dense 3D structure of a plot in minutes.",
    "But a raw point cloud is not an answer yet — it must become per-tree measurements.",
], size=17, gap=14)
fig_with_caption(s, ASSETS / "pc_height.png", Inches(7.2), Inches(1.95), Inches(5.6), Inches(3.4),
                 "Handheld-LiDAR point cloud of one rubber plot (colored by height)")
page_number(s)
notes(s, """
DBH, the trunk diameter at breast height, is one of the most important variables for estimating
biomass and for forest inventory. Traditionally it is measured by hand, tree by tree, which is
slow and labor-intensive across a whole plantation. Handheld or backpack LiDAR changes the data
side of this problem: walking through a plot with SLAM mapping, we capture a dense 3D point cloud
in just minutes. The remaining challenge is turning that raw point cloud into reliable, per-tree
DBH measurements.
""")

# =====================================================================
# SLIDE 4 — INTRODUCTION (story 2: the gap / missing middle)
# =====================================================================
s = slide()
title_block(s, "Introduction — The Gap")
bullets(s, Inches(0.6), Inches(1.8), Inches(6.5), Inches(2.6), [
    "Getting per-tree DBH needs two steps: separate individual trees, then fit the trunk.",
    "Rule-based point-cloud pipelines (trunk extraction, clustering, slicing) are sensitive to occlusion, uneven density, shrubs, and scan path.",
    "3D deep methods (e.g. TreeLearn) segment well but need GPU memory and domain fine-tuning.",
], size=15.5, gap=9)
# missing middle visual
y = Inches(4.7)
labels = [("Single-channel\ndensity CNN", "light, but loses 3D evidence", GRAY_FILL, GRAY_LINE),
          ("Multi-channel CNN\n(this work)", "light + keeps vertical / breast-height", BLUE_FILL, BLUE_LINE),
          ("3D point-cloud\n(TreeLearn)", "accurate, but heavy", GRAY_FILL, GRAY_LINE)]
bw, bh, gap = Inches(3.7), Inches(1.55), Inches(0.45)
x = Inches(0.85)
for txt, sub, fill, line in labels:
    c = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, bw, bh)
    c.fill.solid(); c.fill.fore_color.rgb = fill; c.line.color.rgb = line; c.line.width = Pt(1.25)
    c.shadow.inherit = False
    tf = c.text_frame; tf.word_wrap = True
    para(tf, txt, size=14, bold=True, color=BLUE_TXT if fill == BLUE_FILL else INK, align=PP_ALIGN.CENTER, first=True, space_after=3, line=0.95)
    para(tf, sub, size=11, color=GRAY_T if fill != BLUE_FILL else BLUE_TXT, align=PP_ALIGN.CENTER, space_after=0, line=0.95)
    x = x + bw + gap
tb, tf = textbox(s, Inches(0.85), Inches(4.35), Inches(11.6), Inches(0.35))
para(tf, "The “missing middle”: an efficient method that still preserves DBH-relevant 3D evidence.",
     size=13, italic=True, color=GREEN_M, first=True, space_after=0)
page_number(s)
notes(s, """
To get DBH per tree we really need two things: first separate the plot into individual trees, then
fit the trunk near breast height. Classical point-cloud pipelines do this with hand-tuned rules —
trunk extraction, clustering radius, height slicing — and they break down with occlusion, uneven
point density, shrubs, and different scan paths. On the other end, 3D deep-learning methods such as
TreeLearn segment very well, but they need a lot of GPU memory and domain-specific fine-tuning.
So there is a missing middle: a method that stays lightweight like a 2D density CNN, yet keeps the
vertical and breast-height evidence that the density-only image throws away. That gap is what this
thesis targets.
""")

# =====================================================================
# SLIDE 5 — PROBLEM STATEMENT  (last slide of Introduction)
# =====================================================================
s = slide()
title_block(s, "Problem Statement")
c = card(s, Inches(1.0), Inches(2.2), Inches(11.3), Inches(2.7), fill=TINT_FILL, line=GREEN_M)
tf = c.text_frame; tf.word_wrap = True
tf.vertical_anchor = MSO_ANCHOR.MIDDLE
tf.margin_left = Pt(18); tf.margin_right = Pt(18)
para(tf,
     "How can we transform handheld-LiDAR point clouds of row-planted rubber plantations into "
     "accurate individual-tree segments and breast-height (DBH) estimates using a lightweight "
     "multi-channel top-view CNN that preserves vertical and breast-height evidence — while "
     "staying more efficient than, and at least as accurate as, heavy 3D point-cloud methods "
     "such as TreeLearn on the same plots?",
     size=20, bold=True, color=GREEN_D, align=PP_ALIGN.CENTER, first=True, space_after=0, line=1.18)
tb, tf = textbox(s, Inches(1.0), Inches(5.25), Inches(11.3), Inches(0.5))
para(tf, "This single question defines what the thesis will build, compare, and measure.",
     size=14, italic=True, color=GRAY_T, align=PP_ALIGN.CENTER, first=True, space_after=0)
page_number(s)
notes(s, """
I can compress the whole thesis into one question: How can we transform handheld-LiDAR point clouds
of row-planted rubber plantations into accurate individual-tree segments and breast-height DBH
estimates, using a lightweight multi-channel top-view CNN that preserves vertical and breast-height
evidence — while staying more efficient than, and at least as accurate as, heavy 3D methods such as
TreeLearn on the same plots? Everything after this slide — scope, method, experiments — is in service
of answering this one question.
""")

# =====================================================================
# LITERATURE SLIDES (one paper per slide)
# =====================================================================
def lit_slide(short_title, citation, did, relation, img=None, img_cap=None):
    s = slide()
    title_block(s, short_title)
    text_w = Inches(6.4) if img else Inches(11.8)
    bullets(s, Inches(0.6), Inches(1.85), text_w, Inches(3.6), [
        ("What they do:", 0),
        (did, 1),
        ("Relation to this work:", 0),
        (relation, 1),
    ], size=16, gap=9)
    if img:
        fig_with_caption(s, img, Inches(7.2), Inches(1.95), Inches(5.55), Inches(3.6), img_cap or "")
    # citation strip
    cstrip = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.6), Inches(6.45), Inches(12.1), Inches(0.62))
    cstrip.fill.solid(); cstrip.fill.fore_color.rgb = CARD; cstrip.line.color.rgb = CARD_LINE
    cstrip.line.width = Pt(0.75); cstrip.shadow.inherit = False
    tf = cstrip.text_frame; tf.word_wrap = True; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = Pt(8); tf.margin_right = Pt(8)
    para(tf, citation, size=10.5, color=GRAY_T, italic=True, first=True, space_after=0, line=0.95)
    page_number(s)
    return s

s = lit_slide(
    "Related Work — Liu et al. 2021  (main reference)",
    "[1] Liu, L., Zhang, A., Xiao, S., Hu, S., He, N., Pang, H., Zhang, X., Yang, S. 2021. "
    "“Single Tree Segmentation and Diameter at Breast Height Estimation With Mobile LiDAR.” IEEE Access 9: 24314–24325.",
    "Segment trunks from mobile-LiDAR point clouds using relative point density, then estimate DBH by multi-height circle fitting with outlier removal.",
    "Closest pipeline to ours (segment → DBH). It relies on hand-crafted density scales and trunk assumptions — we replace the segmentation front-end with a learned multi-channel CNN.",
    img=ASSETS / "raster_density.png",
    img_cap="Top-view density raster of one rubber plot — rows of trees are clearly visible",
)
notes(s, """
Liu and colleagues, 2021, is my main reference because it follows the same two-stage logic I use:
first segment individual trunks, then estimate DBH. They segment trunks from mobile-LiDAR point
clouds using relative point density, and then fit circles at multiple heights with outlier removal
to get DBH. The weakness is that the segmentation step depends on hand-crafted density scales and
trunk assumptions that change with plot structure and scan path. My work keeps their segment-then-fit
idea but replaces the rule-based front-end with a learned multi-channel CNN.
""")

s = lit_slide(
    "Related Work — Proudman et al. 2021",
    "[2] Proudman, A., Ramezani, M., Fallon, M. 2021. “Online Estimation of Diameter at Breast Height (DBH) "
    "of Forest Trees Using a Handheld LiDAR.” 2021 European Conference on Mobile Robots (ECMR): 1–7.",
    "Estimate DBH online from a handheld-LiDAR SLAM map with per-tree trunk processing during/after scanning.",
    "Confirms handheld LiDAR is enough for DBH and motivates the efficiency goal; their tree separation is still sensitive to occluded / noisy trunks — our learned segmentation aims to be more robust.",
    img=ASSETS / "breast_slice.png",
    img_cap="Breast-height slice (1.0–1.6 m) across the rows — the trunk evidence used for DBH",
)
notes(s, """
Proudman and colleagues, 2021, show that a handheld LiDAR is sufficient to estimate DBH online,
processing each tree trunk during or just after scanning. This supports my efficiency motivation —
we do not need a heavy survey-grade setup. However, their per-tree separation still struggles with
occluded and noisy trunk observations. The figure shows the breast-height slice between one and one
point six meters, which is the trunk evidence both they and I rely on for DBH.
""")

s = lit_slide(
    "Related Work — Henrich et al. 2024  (TreeLearn)",
    "[3] Henrich, J., van Delden, J., Seidel, D., Kneib, T., Ecker, A. S. 2024. “TreeLearn: A Deep Learning Method "
    "for Segmenting Individual Trees from Ground-Based LiDAR Forest Point Clouds.” Ecological Informatics 84: 102888.",
    "A 3D sparse-convolution network predicts tree/non-tree scores and per-point offsets, then clusters points into individual-tree instances (fully automatic).",
    "This is my main 3D comparison — strong, general segmentation, but needs 3D DL infrastructure, GPU memory, and possible fine-tuning. I benchmark accuracy AND efficiency against it on the same plots.",
    img=ASSETS / "pc_segmented.png",
    img_cap="3D point cloud segmented into individual trees (each color = one tree instance)",
)
notes(s, """
Henrich and colleagues, 2024, propose TreeLearn, which is my main 3D comparison. It uses a 3D
sparse-convolution network to predict, for every point, whether it belongs to a tree and an offset
toward the tree center, then clusters those points into individual-tree instances. It is fully
automatic and very accurate, but it needs 3D deep-learning infrastructure, significant GPU memory,
and may need fine-tuning for a new domain. I will run TreeLearn on my rubber plots and compare both
accuracy and efficiency against my lightweight 2D approach. The figure shows a plot segmented into
individual trees, one color per tree.
""")

s = lit_slide(
    "Related Work — Shao et al. 2024",
    "[4] Shao, J., Lin, Y.-C., Wingren, C., Shin, S.-Y., Fei, W., Carpenter, J., Habib, A., Fei, S. 2024. "
    "“Large-Scale Inventory in Natural Forests with Mobile LiDAR Point Clouds.” Science of Remote Sensing 10: 100168.",
    "Deep semantic segmentation + stem mapping for large-scale natural-forest inventory, fitting DBH from detected stems.",
    "Shows learned segmentation scales to inventory, but is built for large, complex natural forests — heavier than needed for structured, row-planted rubber plots, which is exactly our lighter niche.",
    img=ASSETS / "stems_topdown.png",
    img_cap="Top-down view of detected stem positions used as tree-location labels",
)
notes(s, """
Shao and colleagues, 2024, perform large-scale forest inventory with mobile LiDAR using deep
semantic segmentation and stem mapping, then fit DBH from the detected stems. It demonstrates that
learned segmentation scales up to real inventory. But it is designed for large and complex natural
forests, which makes it computationally heavy and harder to generalize to a small, structured,
row-planted rubber plantation. That contrast is exactly the lighter niche my method aims for.
The figure shows detected stem positions from a top-down view, which is also how I build my labels.
""")

# =====================================================================
# SCOPE OF WORK
# =====================================================================
s = slide()
title_block(s, "Scope of Work")
bullets(s, Inches(0.6), Inches(1.8), Inches(6.5), Inches(4.9), [
    ("Target area:", 0),
    ("Row-planted rubber plantations (trees already grow in regular rows).", 1),
    ("Sensor:", 0),
    ("Handheld LiDAR point clouds with SLAM mapping (12 plots).", 1),
    ("Approach:", 0),
    ("Multi-channel top-view raster + CNN/YOLO for tree detection; DBH by circle/cylinder fitting.", 1),
    ("Compared against:", 0),
    ("Single-channel density CNN, TreeLearn (3D), and a point-cloud baseline — on accuracy and efficiency.", 1),
], size=15.5, gap=7)
# out-of-scope card
oc = card(s, Inches(7.35), Inches(1.95), Inches(5.4), Inches(2.2), fill=RGBColor(0xF7,0xEE,0xEE), line=RGBColor(0xCC,0x9A,0x9A))
tf = oc.text_frame; tf.word_wrap = True; tf.margin_left = Pt(12); tf.margin_right = Pt(12)
para(tf, "Out of scope", size=14, bold=True, color=RED_DOT, first=True, space_after=5)
for t in ["Other species / natural-forest or non-row layouts",
          "Real-time / on-device inference",
          "LiDAR hardware and SLAM algorithm design"]:
    para(tf, "–  " + t, size=13, color=GRAY_T, space_after=4, line=1.0)
fig_with_caption(s, ASSETS / "raster_density.png", Inches(8.35), Inches(4.35), Inches(3.4), Inches(2.25),
                 "Row structure of a rubber plot (density raster)")
page_number(s)
notes(s, """
The scope is deliberately narrow. The target is row-planted rubber plantations, where trees already
grow in regular rows — this structure is something the method can exploit. The sensor is handheld
LiDAR with SLAM, and I have twelve plots. The approach is a multi-channel top-view raster fed to a
CNN/YOLO detector for tree locations, followed by circle or cylinder fitting for DBH. I compare
against a single-channel density CNN, against TreeLearn as the 3D method, and against a point-cloud
baseline, measuring both accuracy and efficiency. Out of scope: other species or natural forests
and non-row layouts, real-time on-device inference, and designing the LiDAR hardware or the SLAM
algorithm themselves.
""")

# =====================================================================
# METHODOLOGY — SYSTEM OVERVIEW (colored diagram)
# =====================================================================
s = slide()
title_block(s, "Methodology — System Overview")

# modules: (label, kind, status)  kind: 'blue' or 'gray'; status: 'done','todo',None
modules = [
    ("LiDAR Capture\n& SLAM", "gray", None),
    ("1  Data\nPreparation", "blue", "done"),
    ("2  Feature\nRasterization", "blue", "done"),
    ("3  Individual Tree\nSegmentation", "blue", "done"),
    ("4  DBH Extraction\n& Evaluation", "blue", "todo"),
    ("Biomass\nEstimation", "gray", None),
]
n = len(modules)
bw = Inches(1.83); bh = Inches(1.45)
total_w = Inches(12.4)
gap = (total_w - bw * n) / (n - 1)
x = Inches(0.5); y = Inches(2.5)
centers = []
for label, kind, status in modules:
    fill, line, txt = (BLUE_FILL, BLUE_LINE, BLUE_TXT) if kind == "blue" else (GRAY_FILL, GRAY_LINE, GRAY_T)
    box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, bw, bh)
    box.fill.solid(); box.fill.fore_color.rgb = fill; box.line.color.rgb = line; box.line.width = Pt(1.5)
    box.shadow.inherit = False
    try: box.adjustments[0] = 0.10
    except Exception: pass
    tf = box.text_frame; tf.word_wrap = True; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    para(tf, label, size=12.5, bold=(kind == "blue"), color=txt, align=PP_ALIGN.CENTER, first=True, space_after=0, line=0.95)
    # status dot
    if status:
        dot_c = GREEN_DOT if status == "done" else RED_DOT
        d = s.shapes.add_shape(MSO_SHAPE.OVAL, x + bw - Inches(0.32), y + Inches(0.08), Inches(0.24), Inches(0.24))
        d.fill.solid(); d.fill.fore_color.rgb = dot_c; d.line.color.rgb = WHITE; d.line.width = Pt(1)
        d.shadow.inherit = False
    centers.append((x, x + bw))
    x = x + bw + gap

# arrows between boxes
ay = y + bh / 2 - Inches(0.12)
for i in range(n - 1):
    ax = Emu(centers[i][1]) + Emu(int(gap * 0.12))
    aw = Emu(int(gap * 0.76))
    ar = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, ax, ay, aw, Inches(0.24))
    ar.fill.solid(); ar.fill.fore_color.rgb = RGBColor(0x8A,0x97,0x8C); ar.line.fill.background(); ar.shadow.inherit = False

# legend
ly = Inches(4.7)
legend = [("Our modules", BLUE_FILL, BLUE_LINE, None),
          ("Completed", WHITE, None, GREEN_DOT),
          ("Not done yet", WHITE, None, RED_DOT),
          ("Out of scope", GRAY_FILL, GRAY_LINE, None)]
lx = Inches(1.0)
for text, fill, line, dot in legend:
    if dot:
        d = s.shapes.add_shape(MSO_SHAPE.OVAL, lx, ly + Inches(0.03), Inches(0.22), Inches(0.22))
        d.fill.solid(); d.fill.fore_color.rgb = dot; d.line.fill.background(); d.shadow.inherit = False
    else:
        sw_ = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, lx, ly, Inches(0.34), Inches(0.28))
        sw_.fill.solid(); sw_.fill.fore_color.rgb = fill
        if line: sw_.line.color.rgb = line; sw_.line.width = Pt(1)
        else: sw_.line.fill.background()
        sw_.shadow.inherit = False
    tb, tf = textbox(s, lx + Inches(0.42), ly - Inches(0.02), Inches(2.3), Inches(0.35))
    para(tf, text, size=13, color=INK, first=True, space_after=0)
    lx = lx + Inches(3.0)

tb, tf = textbox(s, Inches(0.6), Inches(5.5), Inches(12.1), Inches(1.4))
para(tf, "Pipeline:  point cloud → multi-channel raster → CNN/YOLO tree detection → trunk crop → DBH fitting → evaluation.",
     size=15, bold=True, color=GREEN_D, first=True, space_after=8)
para(tf, "Modules 1–3 are implemented; module 4 (DBH extraction & evaluation) and the TreeLearn / baseline comparison are the remaining work.",
     size=14, color=GRAY_T, space_after=0)
page_number(s)
notes(s, """
This is the overall system. Reading left to right: the gray boxes — LiDAR capture with SLAM, and the
downstream biomass estimation — are out of scope; I use the captured clouds and stop at DBH. The blue
boxes are my four modules. Green dots mean a module is already implemented: data preparation, feature
rasterization, and individual-tree segmentation are done. The red dot on module four means DBH
extraction and evaluation is the main remaining work, together with running the TreeLearn and
point-cloud baselines for the comparison. The next slides describe each module one at a time.
""")

# =====================================================================
# MODULE 1 — DATA PREPARATION
# =====================================================================
def module_slide(title, status, parts, img, img_cap, ours):
    s = slide()
    title_block(s, title)
    # status chip
    chip_txt, chip_col = ("Completed", GREEN_DOT) if status == "done" else ("Remaining work", RED_DOT)
    chip = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(10.6), Inches(0.55), Inches(2.15), Inches(0.5))
    chip.fill.solid(); chip.fill.fore_color.rgb = chip_col; chip.line.fill.background(); chip.shadow.inherit = False
    tf = chip.text_frame; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    para(tf, chip_txt, size=13, bold=True, color=WHITE, align=PP_ALIGN.CENTER, first=True, space_after=0)
    y = Inches(1.85)
    for head, body in parts:
        cc = card(s, Inches(0.6), y, Inches(6.6), Inches(1.45))
        tf = cc.text_frame; tf.word_wrap = True; tf.margin_left = Pt(12); tf.margin_right = Pt(10); tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        para(tf, head, size=15, bold=True, color=GREEN_D, first=True, space_after=3, line=1.0)
        para(tf, body, size=13, color=INK, space_after=0, line=1.05)
        y = y + Inches(1.62)
    fig_with_caption(s, img, Inches(7.45), Inches(1.95), Inches(5.3), Inches(3.25), img_cap)
    ob = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.6), y + Inches(0.05), Inches(6.6), Inches(0.95))
    ob.fill.solid(); ob.fill.fore_color.rgb = TINT_FILL; ob.line.color.rgb = GREEN_M; ob.line.width = Pt(1); ob.shadow.inherit = False
    tf = ob.text_frame; tf.word_wrap = True; tf.margin_left = Pt(12); tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    para(tf, "Our part:  " + ours, size=13, bold=True, color=GREEN_D, first=True, space_after=0, line=1.05)
    page_number(s)
    return s

s = module_slide(
    "Module 1 — Data Preparation", "done",
    [("1.1  Point-cloud standardization",
      "Convert source scans (PCD/LAS), filter, rotate, and align coordinates to the tree-location labels."),
     ("1.2  Ground normalization & split",
      "Estimate local ground, compute height-above-ground (HAG) per point, split the 12 plots by plot.")],
    ASSETS / "pc_height.png",
    "Standardized plot point cloud (height-colored) ready for rasterization",
    "Built the full standardize → align → ground/HAG → per-plot split workflow over all 12 plots.",
)
notes(s, """
Module one, data preparation, is done. First I standardize the raw scans — convert PCD or LAS,
filter noise, rotate, and align the coordinate frame to the field tree-location labels. Second I
estimate the local ground surface, compute height-above-ground for every point, and split the twelve
plots at the plot level so no plot leaks between train, validation, and test. My contribution here
is the complete, repeatable preparation workflow across all twelve plots.
""")

s = module_slide(
    "Module 2 — Feature Rasterization", "done",
    [("2.1  Density & height channels",
      "Top-view grid: R = point density, G = hag_p95 (95th-pct height above ground)."),
     ("2.2  Breast-height evidence channel",
      "B = dbh_band_density: point count in the 1.0–1.6 m band, emphasizing stem evidence.")],
    ASSETS / "raster_multi_blue.png",
    "Synthetic 3-channel image (R=density, G=hag_p95, B=dbh-band) fed to the CNN",
    "Implemented the rasterizer producing the 3-channel image used by the detector.",
)
notes(s, """
Module two, feature rasterization, is also done. I turn each 3D plot into a top-view image with
three physically meaningful channels. Red is point density, like the old single-channel work. Green
is the ninety-fifth percentile of height above ground, capturing canopy and vertical structure
robustly. Blue counts points in the one-to-one-point-six-meter band, emphasizing trunk evidence near
breast height. The result is an ordinary RGB image, so the existing CNN pipeline works unchanged, but
now it carries vertical and breast-height information, not just density.
""")

s = module_slide(
    "Module 3 — Individual Tree Segmentation", "done",
    [("3.1  Multi-channel CNN / YOLO",
      "Train a YOLOv11 detector on the 3-channel raster to predict tree centers (2 m boxes)."),
     ("3.2  Baseline & 3D comparison",
      "Same plot split vs. single-channel density CNN, TreeLearn, and a point-cloud baseline.")],
    ASSETS / "pc_segmented.png",
    "Goal: each tree separated as its own instance (shown in 3D for intuition)",
    "Detector trained; baseline comparison done — TreeLearn / point-cloud comparison still in progress.",
)
notes(s, """
Module three, individual-tree segmentation, is implemented for our detector. I train a YOLOv11 model
on the three-channel raster to predict tree centers, using fixed two-meter boxes from the field X-Y
labels. Importantly, because the channels are physical features, I disable color augmentation — color
jitter would corrupt their meaning — while still allowing geometric augmentation. For the comparison,
I use the same plot split against a single-channel density CNN, against TreeLearn, and against a
point-cloud baseline. The density-CNN comparison is done; running TreeLearn on these plots is part of
the remaining work.
""")

s = module_slide(
    "Module 4 — DBH Extraction & Evaluation", "todo",
    [("4.1  Tree-level trunk crop",
      "Around each predicted tree, collect candidate trunk points near the breast-height band."),
     ("4.2  Circle / cylinder fitting",
      "Fit DBH near 1.3 m with multi-height bins + RANSAC / outlier removal; compare to field DBH.")],
    ASSETS / "breast_slice.png",
    "Breast-height slice from which the trunk circle / cylinder is fitted",
    "Not yet implemented — this is the core remaining contribution of the thesis.",
)
notes(s, """
Module four, DBH extraction and evaluation, is the main remaining work. For each predicted tree, I
crop candidate trunk points around the breast-height band, then fit a circle or cylinder near one
point three meters to estimate DBH, using multiple height bins with RANSAC and outlier removal to
handle noisy trunks. Finally I compare estimated DBH against the field measurements. This module is
not implemented yet — it is the core contribution I will build next.
""")

# =====================================================================
# PRELIMINARY WORK
# =====================================================================
s = slide()
title_block(s, "Preliminary Work — What Is Done")
bullets(s, Inches(0.6), Inches(1.8), Inches(6.4), Inches(4.5), [
    "Modules 1–3 implemented end-to-end over all 12 rubber plots.",
    "Multi-channel rasters generated; YOLOv11 detectors trained.",
    "Trained & compared 4 multi-channel runs vs. the single-channel density baseline (same split).",
    "Best multi-channel model: mAP50-95 ≈ 0.61 (mAP50 ≈ 0.99).",
    "Key finding: transfer from a density-pretrained model ≫ generic pretraining (0.61 vs 0.36).",
    "Next: DBH module (4) + TreeLearn / point-cloud comparison + efficiency measurement.",
], size=15, gap=10)
fig_with_caption(s, ASSETS / "results_table.png", Inches(7.2), Inches(1.95), Inches(5.6), Inches(3.9),
                 "Model comparison so far (ranked by mAP50-95)")
page_number(s)
notes(s, """
Here is what is already done. Modules one through three run end-to-end over all twelve plots. I have
generated the multi-channel rasters and trained YOLOv11 detectors, and I trained four multi-channel
configurations and compared them against the single-channel density baseline on the same split. The
best multi-channel model reaches about zero point six one mAP at 50-95, and about zero point nine nine
at mAP-50. The clearest finding so far is that initializing from a density-pretrained model strongly
beats generic pretraining — about zero point six one versus zero point three six — so transfer from the
single-channel task really helps. What remains is the DBH module, the TreeLearn and point-cloud
comparison, and the efficiency measurements.
""")

# =====================================================================
# EXPERIMENTAL DESIGN
# =====================================================================
s = slide()
title_block(s, "Experimental Design — How We Measure")
cols = [
    ("Segmentation accuracy", GREEN_M, [
        "Precision, Recall, F1",
        "Tree detection rate (TDR)",
        "mAP50, mAP50-95",
    ]),
    ("DBH accuracy", BLUE_LINE, [
        "MAE / RMSE vs. field DBH",
        "Bias across plots",
        "Effect of missed / merged trees",
    ]),
    ("Efficiency", RGBColor(0x8A,0x6D,0x1E), [
        "Runtime (preprocess + infer)",
        "Peak GPU / CPU memory",
        "vs. TreeLearn on same plots",
    ]),
]
cw = Inches(3.95); ch = Inches(3.3); x = Inches(0.6); y = Inches(2.0)
for head, col, rows in cols:
    cc = card(s, x, y, cw, ch, fill=WHITE, line=col)
    hb = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, cw, Inches(0.7))
    hb.fill.solid(); hb.fill.fore_color.rgb = col; hb.line.fill.background(); hb.shadow.inherit = False
    tf = hb.text_frame; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    para(tf, head, size=15, bold=True, color=WHITE, align=PP_ALIGN.CENTER, first=True, space_after=0)
    tbx, tf = textbox(s, x + Inches(0.25), y + Inches(0.95), cw - Inches(0.5), ch - Inches(1.1))
    for i, r in enumerate(rows):
        para(tf, "•  " + r, size=14, color=INK, first=(i == 0), space_after=10, line=1.05)
    x = x + cw + Inches(0.28)
tb, tf = textbox(s, Inches(0.6), Inches(5.55), Inches(12.1), Inches(1.0))
para(tf, "Fair comparison: identical plot-level split, image size, box size, epochs, and augmentation policy across all methods.",
     size=14, italic=True, color=GREEN_D, first=True, space_after=0)
page_number(s)
notes(s, """
I measure three things. First, segmentation accuracy — precision, recall, F1, tree detection rate,
and mAP at fifty and fifty-to-ninety-five. Second, DBH accuracy — mean absolute error and RMSE against
field DBH, any bias across plots, and how missed or merged trees propagate into DBH error. Third,
efficiency — runtime for preprocessing and inference, and peak memory, directly versus TreeLearn on
the same plots. The key to fairness is that every method uses the identical plot-level split, image
size, box size, epoch budget, and augmentation policy.
""")

# =====================================================================
# DATASET
# =====================================================================
s = slide()
title_block(s, "Dataset")
bullets(s, Inches(0.6), Inches(1.8), Inches(6.5), Inches(4.6), [
    "12 rubber-plantation plots, captured with handheld LiDAR + SLAM.",
    "Labels: field-measured tree X/Y positions and DBH (DBHaverage.csv per plot).",
    "Rasterized to one 320×320 top-view image per plot (0.125 m / pixel, ~40 m area).",
    "Split by plot (train/val/test) to prevent leakage.",
    "Characteristic: trees in regular rows → strong, exploitable spatial prior.",
    "Small-data regime → transfer learning and augmentation matter.",
], size=15, gap=10)
fig_with_caption(s, ASSETS / "pc_segmented.png", Inches(7.25), Inches(1.9), Inches(5.5), Inches(2.85),
                 "One plot, point cloud segmented to individual trees")
picture(s, ASSETS / "raster_multi_green.png", Inches(8.3), Inches(5.25), h=Inches(1.55))
picture(s, ASSETS / "raster_density.png", Inches(10.05), Inches(5.25), h=Inches(1.55))
caption(s, Inches(7.25), Inches(6.9), Inches(5.5), "Rasterized inputs derived per plot")
page_number(s)
notes(s, """
The dataset is twelve rubber-plantation plots captured with handheld LiDAR and SLAM. Labels are
field-measured tree X-Y positions and DBH, one CSV per plot. Each plot becomes a single three-hundred-
twenty by three-hundred-twenty top-view image at twelve-and-a-half centimeters per pixel, covering
about forty meters. I split by plot to prevent leakage. Two characteristics matter: the trees grow in
regular rows, which is a strong spatial prior the model can exploit; and with only twelve plots this
is a small-data regime, which is why transfer learning and augmentation are important. The figures
show one segmented plot and the rasterized inputs.
""")

# =====================================================================
# EXPECTED OUTCOME  (no "Contribution", no success metrics)
# =====================================================================
s = slide()
title_block(s, "Expected Outcome")
cards_data = [
    ("Multi-channel segmentation pipeline",
     "A validated workflow turning handheld-LiDAR clouds into per-tree detections using density, height, and breast-height evidence."),
    ("DBH-ready tree crops",
     "Trunk-point subset for each predicted tree, enabling DBH fitting from breast-height slices."),
    ("Accuracy–efficiency benchmark",
     "A controlled comparison of multi-channel CNN vs. density CNN, TreeLearn, and a point-cloud baseline on the same plots."),
    ("Segmentation→DBH error analysis",
     "Evidence of how missed, merged, and false detections affect downstream DBH estimates."),
]
positions = [(Inches(0.6), Inches(1.95)), (Inches(6.75), Inches(1.95)),
             (Inches(0.6), Inches(4.35)), (Inches(6.75), Inches(4.35))]
for (l, t), (head, body) in zip(positions, cards_data):
    cc = card(s, l, t, Inches(6.0), Inches(2.15), fill=CARD, line=GREEN_M)
    tf = cc.text_frame; tf.word_wrap = True; tf.margin_left = Pt(14); tf.margin_right = Pt(12); tf.margin_top = Pt(10)
    para(tf, head, size=16, bold=True, color=GREEN_D, first=True, space_after=5, line=1.0)
    para(tf, body, size=13.5, color=INK, space_after=0, line=1.1)
page_number(s)
notes(s, """
I expect four outcomes. One: a validated multi-channel segmentation pipeline that turns handheld-LiDAR
clouds into per-tree detections using density, height, and breast-height evidence. Two: DBH-ready tree
crops — the trunk points for each predicted tree, ready for fitting. Three: a controlled accuracy-and-
efficiency benchmark comparing the multi-channel CNN against the density CNN, TreeLearn, and a
point-cloud baseline on the same plots. And four: an analysis of how segmentation errors — missed,
merged, or false trees — propagate into DBH error.
""")

# =====================================================================
# MILESTONES  (Gantt-style table)
# =====================================================================
s = slide()
title_block(s, "Milestones")
months = ["Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
tasks = [
    ("Literature review & related work", [1, 1, 0, 0, 0, 0, 0]),
    ("Data preparation & feature rasterization (done)", [1, 0, 0, 0, 0, 0, 0]),
    ("Individual tree segmentation + baseline / TreeLearn", [1, 1, 1, 0, 0, 0, 0]),
    ("DBH extraction & evaluation", [0, 0, 1, 1, 1, 0, 0]),
    ("Experiments & accuracy–efficiency analysis", [0, 0, 0, 1, 1, 1, 0]),
    ("Thesis writing & publication", [0, 0, 0, 0, 1, 1, 1]),
    ("Proposal / final defense & exam", [0, 0, 0, 0, 0, 1, 1]),
]
rows = len(tasks) + 1
colc = len(months) + 1
left, top = Inches(0.6), Inches(1.85)
tot_w, tot_h = Inches(12.1), Inches(4.8)
gtbl = s.shapes.add_table(rows, colc, left, top, tot_w, tot_h).table
gtbl.first_row = True
gtbl.columns[0].width = Inches(5.5)
mw = (tot_w - Inches(5.5)) // len(months)
for j in range(len(months)):
    gtbl.columns[j + 1].width = mw
# header
hdr = ["Task"] + months
for j, htext in enumerate(hdr):
    c = gtbl.cell(0, j)
    c.fill.solid(); c.fill.fore_color.rgb = GREEN_D
    c.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = c.text_frame.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = htext; _set(r, 13, True, WHITE)
for i, (name, spans) in enumerate(tasks):
    rr = i + 1
    c = gtbl.cell(rr, 0)
    c.fill.solid(); c.fill.fore_color.rgb = WHITE if i % 2 == 0 else RGBColor(0xF1,0xF5,0xF2)
    c.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = c.text_frame.paragraphs[0]; p.alignment = PP_ALIGN.LEFT
    r = p.add_run(); r.text = name; _set(r, 12, False, INK)
    for j, on in enumerate(spans):
        cc = gtbl.cell(rr, j + 1)
        cc.fill.solid()
        cc.fill.fore_color.rgb = GREEN_M if on else (WHITE if i % 2 == 0 else RGBColor(0xF1,0xF5,0xF2))
        cc.text_frame.paragraphs[0].add_run().text = ""
tb, tf = textbox(s, Inches(0.6), Inches(6.85), Inches(12.1), Inches(0.4))
para(tf, "~4 months of work (literature review → publication), plus 1–2 months for presentation and examination.",
     size=13, italic=True, color=GRAY_T, first=True, space_after=0)
page_number(s)
notes(s, """
The plan runs about four months of work from the literature review through to publication, plus one
to two months for the presentation and examination. Data preparation and feature rasterization are
already finished. Segmentation and the baseline-and-TreeLearn comparison run through the summer; the
DBH module follows; then experiments and the accuracy-efficiency analysis; and finally writing,
publication, and the defense. The shaded cells show the planned span of each task.
""")

# =====================================================================
# THANK YOU / Q&A
# =====================================================================
if THEME == "chula":
    _page += 1
    s = prs.slides.add_slide(_layout("Section Header"))  # Chula pink background
    _strip_placeholders(s, keep=())
    tb, tf = textbox(s, Inches(1.5), Inches(2.7), Inches(10.3), Inches(2.0), anchor=MSO_ANCHOR.MIDDLE)
    para(tf, "Thank You", size=44, bold=True, color=WHITE, align=PP_ALIGN.CENTER, first=True, space_after=8)
    para(tf, "Questions & Answers", size=22, color=WHITE, align=PP_ALIGN.CENTER, space_after=0)
    page_number(s, dark_bg=True)
else:
    s = slide()
    band = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SW, Inches(0.28))
    band.fill.solid(); band.fill.fore_color.rgb = GREEN_M; band.line.fill.background(); band.shadow.inherit = False
    bb = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, SH - Inches(0.28), SW, Inches(0.28))
    bb.fill.solid(); bb.fill.fore_color.rgb = GREEN_M; bb.line.fill.background(); bb.shadow.inherit = False
    tb, tf = textbox(s, Inches(1.5), Inches(2.7), Inches(10.3), Inches(2.0), anchor=MSO_ANCHOR.MIDDLE)
    para(tf, "Thank You", size=44, bold=True, color=GREEN_D, align=PP_ALIGN.CENTER, first=True, space_after=8)
    para(tf, "Questions & Answers", size=22, color=GREEN_M, align=PP_ALIGN.CENTER, space_after=0)
    page_number(s)
notes(s, """
Thank you for your attention. I am happy to take questions.
""")

prs.save(str(OUT))
print(f"Saved: {OUT}")
print(f"Slides: {len(prs.slides.__iter__.__self__._sldIdLst)}")
