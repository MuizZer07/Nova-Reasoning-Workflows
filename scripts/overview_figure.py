#!/usr/bin/env python3
"""Study overview figure (Fig. 1): figures/overview.png.

Every label is taken from the Methods section of the paper: (A) the four Nova workflows over
shared evidence (Table 2), (B) the six datasets (Table 1), (C) the three benchmark settings
(Table 3), (D) the Reasoning Requirement Levels and the evaluation. Edit the text here when
the Methods change. Usage: python scripts/overview_figure.py
"""
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("NOVA_OVERVIEW_OUT") or os.path.abspath(os.path.join(HERE, "..", "figures", "overview.png"))
# NOVA_RQS: comma-separated RQ labels to draw (e.g. "RQ1a,RQ1b"; empty = none), used for the slides that
# reveal the research questions one by one; unset = all of them (the paper figure)
_rqs = os.environ.get("NOVA_RQS")
SHOW_RQ = None if _rqs is None else {x.strip() for x in _rqs.split(",") if x.strip()}

INSTANT, THINKING, DEEP, AUTO = "#2a78d6", "#eb6834", "#eda100", "#1baf7a"
DEEP_INK = "#b07800"                       # darker amber for text on light backgrounds
INK, INK2, LINE = "#0b0b0b", "#3d3c39", "#c9c8c3"
PANEL, CARD, NOVA = "#f6f6f4", "#ffffff", "#5b4bb7"
DATA, LIT, MODEL, RULES = "#3987e5", "#8a5cc7", "#52514e", "#c0392b"
CAT = {"Tumor suppression": "#c0392b", "Infectious disease": "#7b4fb3", "Drug response": "#1f8a70"}
RRL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#184f95"]

DA = 1.36                                    # panel A reaches DA lower than panels B-D's original top (frontier box)
W, H = 16.0, 9.6 + DA
plt.rcParams.update({"font.family": "Arial", "text.color": INK})
fig = plt.figure(figsize=(W, H))
# two overlaid axes with the same scale: panels B-D are drawn in axB at their own coordinates and so sit
# DA lower than in axA (panel A); axB is added first, so panel A and the links between panels draw on top
axB = fig.add_axes([0, 0, 1, 1])
axB.set_xlim(0, W)
axB.set_ylim(0, H)
axB.axis("off")
axA = fig.add_axes([0, 0, 1, 1])
axA.set_xlim(0, W)
axA.set_ylim(-DA, 9.6)
axA.axis("off")
ax = axA                                     # the drawing helpers use the current `ax`


def tint(hex_color, a):
    """Mix a colour with white (a = share of the colour)."""
    c = [int(hex_color[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(255 - a * (255 - v)) for v in c)


def box(x, y, w, h, fc=CARD, ec=LINE, lw=1.0, r=0.08, ls="-", z=1):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=%g" % r,
                                fc=fc, ec=ec, lw=lw, ls=ls, zorder=z))


def text(x, y, s, size=12, color=INK, weight="normal", ha="center", va="center", style="normal", z=5, **kw):
    ax.text(x, y, s, fontsize=size, color=color, fontweight=weight, ha=ha, va=va, style=style, zorder=z,
            linespacing=1.15, **kw)


def arrow(x0, y0, x1, y1, color=INK2, lw=1.5, ls="-", head=11, z=4):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=head, color=color,
                                 lw=lw, ls=ls, zorder=z, shrinkA=0, shrinkB=0))


def badge(x, y, s, col, r=0.15, size=12):
    ax.add_patch(plt.Circle((x, y), r, color=col, zorder=6))
    text(x, y, s, size, "white", "bold", z=7)


def panel(x, y, w, h, letter, title):
    box(x, y, w, h, fc=PANEL, ec="none", r=0.14, z=0)
    badge(x + 0.3, y + h - 0.3, letter, INK, 0.2, 14)
    text(x + 0.62, y + h - 0.3, title, 16, weight="bold", ha="left")


def step(x, y, w, h, s, col, size=12, fill=None):
    box(x, y, w, h, fc=fill or tint(col, 0.08), ec=col, lw=1.1, r=0.05, z=2)
    text(x + w / 2, y + h / 2, s, size)


# =============================================================== A. Nova workflows
AX, AY, AW, AH = 0.15, 3.64, 15.7, 5.81
panel(AX, AY, AW, AH, "A", "The Same Model, Tools, and Evidence; Different Reasoning Structure")
MAIN_LW = 2.4                               # the three main boxes: query, Nova workflows, interpretation
SOFT = 0.45                                 # inner boxes: borders mixed with white, so the main boxes stand out

# left: shared resources (top) and the researcher's query (bottom, entering Nova-Auto)
LX, LW = 0.6, 2.72
box(LX, 5.95, LW, 2.91, fc=CARD, ec=LINE, lw=1.0)
text(LX + LW / 2, 8.6, "Shared by All Workflows", 13.5, INK2, "bold")
for title, body, col, top, bot in [
        ("Analysis Results", "iPathwayGuide: DEGs,\npathways, GO, regulators,\nmiRNAs, diseases", DATA, 8.36, 7.4),
        ("Literature Engine", "PubMed; lexical and\nsemantic search", LIT, 7.2, 6.62),
        ("Language Model", "GLM-5.2 (open weights)", MODEL, 6.45, 6.07)]:
    ax.add_patch(plt.Rectangle((LX + 0.14, bot), 0.07, top - bot, color=col, zorder=3))
    text(LX + 0.33, top - 0.1, title, 13, col, "bold", ha="left")
    text(LX + 0.33, top - 0.25, body, 11.5, INK2, ha="left", va="top")

box(LX, 4.3, LW, 1.42, fc=CARD, ec=INK, lw=MAIN_LW)        # feeds both Nova-Auto and the frontier model
text(LX + LW / 2, 5.2, "Researcher Query", 14.5, weight="bold")
text(LX + LW / 2, 4.86, "About one experiment", 12, INK2)

# the Nova bounding box
NX0, NX1, NY0, NY1 = 3.5, 12.97, 4.80, 8.86
box(NX0, NY0, NX1 - NX0, NY1 - NY0, fc=tint(NOVA, 0.05), ec=NOVA, lw=MAIN_LW + 0.4, r=0.12)
text(NX0 + 0.2, 8.69, "Nova Workflows", 14, NOVA, "bold", ha="left")

# direction of more structure (top)
gx0, gx1, gy = 5.38, 6.0, 8.69
for i in range(60):
    ax.add_patch(plt.Rectangle((gx0 + i * (gx1 - gx0) / 60, gy - 0.04), (gx1 - gx0) / 60 + 0.005, 0.08,
                               color=tint(INK2, 0.12 + 0.8 * i / 59), lw=0, zorder=2))
arrow(gx1 - 0.05, gy, gx1 + 0.08, gy, INK2, 1.0, head=14)
text(gx1 + 0.17, gy, "More Structure  →  More Cost", 12, INK2, "bold", ha="left")


def rq(xc, yc, label, line, w, h=0.3, to=()):
    """Research-question pill: where in the study each question is answered.
    `to`: (x_on_pill, x_target, y_target) edges from the pill to what it compares."""
    if SHOW_RQ is not None and label not in SHOW_RQ:
        return
    box(xc - w / 2, yc - h / 2, w, h, fc=tint(NOVA, 0.12), ec=NOVA, lw=1.2, r=0.1, z=8)
    text(xc, yc, label + "  " + line, 11.5, NOVA, "bold", z=9)
    for xp, xt, yt in to:
        yp = yc - h / 2 if yt < yc else yc + h / 2
        ax.plot([xp, xt], [yp, yt], color=NOVA, lw=1.1, zorder=7, solid_capstyle="round")
        ax.add_patch(plt.Circle((xt, yt), 0.035, color=NOVA, zorder=9))




def inner(x, y, w, h, s, col, size=12, fill=None, dashed=False, color=INK, style="normal"):
    """A step inside a workflow card: light border, so the cards and main boxes read first."""
    box(x, y, w, h, fc=fill or CARD, ec=tint(col, SOFT), lw=0.9, r=0.05, z=2, ls=(0, (3, 2)) if dashed else "-")
    text(x + w / 2, y + h / 2, s, size, color, style=style)


# workflows 1-3: cards with padding between and inside them
PAD, CG = 0.12, 0.16                         # inner padding of a card, gap between cards
CX = NX0 + 0.18
TOTW = NX1 - 0.18 - CX - 2 * CG
CWS = [TOTW * f / 3.0 for f in (0.93, 0.95, 1.12)]   # Deep Thinking gets the widest card
CY, CH, HB = 5.98, 2.14, 0.62                # card bottom, height, header band
XS = [CX, CX + CWS[0] + CG, CX + CWS[0] + CWS[1] + 2 * CG]
# strategy wording as in the Introduction
cols = [("1", "Nova-Instant", "Direct grounded retrieval", INSTANT, XS[0]),
        ("2", "Nova-Thinking", "Fixed multi-stage reasoning", THINKING, XS[1]),
        ("3", "Nova-Deep Thinking", "Dynamic decomposition across\nspecialized sub-agents", DEEP, XS[2])]
for k, (num, name, tag, col, x) in enumerate(cols):
    CW = CWS[k]
    ink = col if col != DEEP else DEEP_INK
    box(x, CY, CW, CH, fc=CARD, ec=tint(col, 0.7), lw=1.3)
    box(x + 0.02, CY + CH - HB, CW - 0.04, HB - 0.02, fc=tint(col, 0.16), ec="none", r=0.07)
    badge(x + 0.32, CY + CH - HB / 2, num, ink)
    text(x + 0.3 + CW / 2, CY + CH - 0.19, name, 14, ink, "bold")
    text(x + 0.3 + CW / 2, CY + CH - 0.45, tag, 12, INK2)
BTOP, BBOT = CY + CH - HB - PAD, CY + PAD    # body area of each card
RQY = CY + CH + 0.25                          # row of RQ pills above the cards, with edges to both cards
# RQ1, the main question about structure, closes the header row: is more structure worth its cost?
RQ1W = 3.75
rq(NX1 - 0.14 - RQ1W / 2, gy, "RQ1", "Does more structure help, at what cost?", RQ1W)
# its three parts: 1a, 1b above the cards, 1c below Auto
for xg, lab, line, w in ((XS[1] - CG / 2, "RQ1a", "Single vs. multi-pass?", 2.55),
                         (XS[2] - CG / 2, "RQ1b", "Fixed vs. dynamic?", 2.2)):
    rq(xg, RQY, lab, line, w, to=((xg - 0.85, xg - 0.85, CY + CH), (xg + 0.85, xg + 0.85, CY + CH)))
if SHOW_RQ is None or "RQ1a" in SHOW_RQ:
    text(XS[1] - CG / 2 - 1.4, RQY, "Research Questions\n(RQs):", 11, NOVA, "bold", ha="right")

# 1 Instant: a single round of parallel tool calls -> direct answer
x, CW = XS[0], CWS[0]
IW = CW - 2 * PAD
inner(x + PAD, BTOP - 0.5, IW, 0.5, "Single round of\nparallel tool calls", INSTANT)
arrow(x + CW / 2, BTOP - 0.52, x + CW / 2, BBOT + 0.48, tint(INSTANT, 0.8), 1.2, head=9)
inner(x + PAD, BBOT, IW, 0.46, "Direct answer,\nno self-review", INSTANT, fill=tint(INSTANT, 0.12))

# 2 Thinking: fixed plan -> planned lookups -> evidence log -> calibrated synthesis
x, CW = XS[1], CWS[1]
IW = CW - 2 * PAD
rg = 0.2
rw = (IW - 2 * rg) / 3
for i, st in enumerate(["Evidence\nplan", "Planned\nlookups", "Evidence\nlog"]):
    rx = x + PAD + i * (rw + rg)
    inner(rx, BTOP - 0.42, rw, 0.42, st, THINKING, 11)
    if i:
        arrow(rx - rg + 0.03, BTOP - 0.21, rx - 0.03, BTOP - 0.21, tint(THINKING, 0.8), 1.2, head=8)
text(x + CW / 2, (BTOP - 0.42 + BBOT + 0.46) / 2, "Counter-evidence planned for", 11.5, INK2, style="italic")
inner(x + PAD, BBOT, IW, 0.46, "Calibrated synthesis\nin reasoning mode", THINKING, fill=tint(THINKING, 0.12))

# 3 Deep Thinking: complexity-adaptive plan -> scoped sub-agents (parallel; dependent steps wait) -> synthesis
x, CW = XS[2], CWS[2]
IW = CW - 2 * PAD
inner(x + PAD, BTOP - 0.28, IW, 0.28, "Plan sized to the query's complexity", DEEP, 11.5)
sg = 0.1
sw_ = (IW - 2 * sg) / 3
sy, sh = BTOP - 0.7, 0.34
for i in range(3):
    rx = x + PAD + i * (sw_ + sg)
    arrow(x + CW / 2 + (i - 1) * 0.25, BTOP - 0.29, rx + sw_ / 2, sy + sh + 0.01, tint(DEEP_INK, 0.8), 1.0, head=7)
    inner(rx, sy, sw_, sh, "Sub-agent", DEEP, 11.5, fill=tint(DEEP, 0.1))
text(x + CW / 2, sy - 0.145, "scoped sub-agents run in parallel with\ntask-specific tools; dependent steps wait", 10,
     INK2, style="italic")
inner(x + PAD, BBOT, IW, 0.27, "Reconcile, then calibrated synthesis", DEEP, 11.5, fill=tint(DEEP, 0.14))

# 4 Auto (bottom): classifies, routes to one of 1-3, assesses sufficiency, and re-routes when needed
AY0 = NY0 + 0.42                              # room below Auto for its RQ label
AH0 = CY - 0.16 - AY0
box(CX, AY0, NX1 - 0.18 - CX, AH0, fc=tint(AUTO, 0.1), ec=tint(AUTO, 0.7), lw=1.3)
badge(CX + 0.27, AY0 + AH0 - 0.2, "4", AUTO, r=0.14)
text(CX + 0.5, AY0 + AH0 - 0.19, "Nova-Auto", 14, AUTO, "bold", ha="left")
text(CX + 0.13, AY0 + 0.15, "Adaptive routing and assessment", 11, INK2, ha="left")
rq(CX + 2.35, NY0 + 0.21, "RQ1c", "Does delegation match the best workflow?", 4.1,
   to=((CX + 0.35, CX + 0.35, AY0),))                     # edge to Auto's bottom-left corner
asw = [1.1, 1.1, 1.7, 1.9]
ax0 = NX1 - 0.18 - PAD - sum(asw) - 0.18 * 3
for i, s in enumerate(["Classify the\nrequest", "Route to\none workflow",
                       "Assess\nsufficiency", "Enrich and re-route\nwhen needed"]):
    xi = ax0 + sum(asw[:i]) + 0.18 * i
    inner(xi, AY0 + 0.09, asw[i], AH0 - 0.18, s, AUTO, 11.5)
    if i:
        arrow(xi - 0.16, AY0 + AH0 / 2, xi - 0.02, AY0 + AH0 / 2, tint(AUTO, 0.8), 1.2, head=8)
for k, (_, _, _, col, x) in enumerate(cols):         # delegation to one of workflows 1-3
    CW = CWS[k]
    arrow(x + CW / 2, AY0 + AH0 + 0.01, x + CW / 2, CY - 0.01, AUTO, 1.4, ls=(0, (3, 2)), head=9)

# inputs into Nova
arrow(LX + LW, 5.53, NX0 - 0.01, 5.53, INK, 1.8)                           # query -> Nova-Auto
arrow(LX + LW, 7.4, NX0 - 0.01, 7.4, DATA, 1.6)                            # tool calls

# the frontier model used directly (RQ2): same query and iPathwayGuide results, same kind of answer
FY0, FY1 = 3.72, 4.62
box(NX0, FY0, NX1 - NX0, FY1 - FY0, fc=CARD, ec=INK2, lw=MAIN_LW)
text(NX0 + 0.2, FY1 - 0.19, "Frontier Model, Used Directly", 14, INK2, "bold", ha="left")
RQ2W = 4.6
rq(NX0 + 3.55 + RQ2W / 2, FY1 - 0.19, "RQ2", "Reasoning structure vs. a frontier model?", RQ2W, h=0.24,
   to=((NX0 + 3.55 + RQ2W / 2, NX0 + 3.55 + RQ2W / 2, NY0),))   # edge up to the Nova workflows
fsw = [1.95, 2.35, 2.15, 2.19]                 # fills the box: 9.47 - 2 * 0.16 - 3 * 0.17
fx = NX0 + 0.16
for i, st in enumerate(["Query + iPathwayGuide\nresult files", "GPT-6 analyzes the files\nwith its own tools",
                        "Reasoning effort: Instant,\nMedium, or High", "Same items, answer format,\nand session order"]):
    if i:
        arrow(fx - 0.15, FY0 + 0.29, fx - 0.02, FY0 + 0.29, tint(INK2, 0.7), 1.2, head=8)
    inner(fx, FY0 + 0.08, fsw[i], 0.42, st, INK2, 11)
    fx += fsw[i] + 0.17
arrow(LX + LW, 4.46, NX0 - 0.01, 4.46, INK, 1.8)                           # query -> frontier model
text((LX + LW + NX0) / 2, 7.95, "Tool calls", 11, DATA, "bold", rotation=90)

# output
OX, OW = 13.25, 2.4
arrow(NX1, 6.87, OX - 0.01, 6.87, INK, 2.0)
arrow(NX1, (FY0 + FY1) / 2, OX - 0.01, (FY0 + FY1) / 2, INK, 2.0)   # frontier model -> same output
box(OX, FY0, OW, NY1 - FY0, fc=CARD, ec=INK, lw=MAIN_LW)
text(OX + OW / 2, 8.68, "Evidence-Grounded\nInterpretation", 15, weight="bold", va="top")
yy = 8.0
for s in ["Closed-form questions:\ndirect answer, then\nevidence for the choice",
          "Open questions: every\nclaim traced to a tool\ncall or the literature",
          "Conversation turns: keep\nearlier facts; revise only\nwhen evidence requires",
          "Hypothesis steps: evidence\nrelation and updated\nhypothesis state",
          "Final decision: retain,\nqualify, revise, reject,\nor insufficient"]:
    ax.add_patch(plt.Circle((OX + 0.15, yy - 0.1), 0.05, color=INK2, zorder=3))
    text(OX + 0.27, yy, s, 12, INK2, ha="left", va="top")
    yy -= 0.205 * (s.count("\n") + 1) + 0.28

rq(OX + OW / 2, NY1 + 0.32, "RQ3", "Do gains persist from\nquestions to decisions?", 2.7, h=0.46,
   to=((OX + OW / 2, OX + OW / 2, NY1),))                 # edge to the interpretation box

# =============================================================== B. datasets
ax = axB
BX, BY, BW, BH = 0.15, 0.15, 5.4, 4.45
panel(BX, BY, BW, BH, "B", "Six Public Transcriptomic Datasets")
text(BX + 0.25, 3.92, "Each with its iPathwayGuide analysis results", 12, INK2, ha="left")
rows = [("GSE47363", "Tumor suppression", "U2OS osteosarcoma cells,\nmiR-542-3p (activates p53)", "20,526", "1,166"),
        ("GSE147507", "Infectious disease", "Host response to\nSARS-CoV-2 infection", "9,400", "812"),
        ("GSE150316", "Infectious disease", "COVID-19 autopsy lung", "15,112", "229"),
        ("GSE26487", "Drug response", "Dexamethasone-treated\nkeratinocytes", "8,577", "62"),
        ("GSE74000", "Drug response", "Acetaminophen-exposed\nhepatic systems", "19,826", "557"),
        ("GSE58434", "Drug response", "Vitamin D-treated\nairway smooth muscle", "13,476", "699")]
cx = [0.5, 1.78, 4.5, 5.3]
ty = 3.55
box(0.28, ty - 0.18, 5.12, 0.36, fc=tint(INK2, 0.12), ec="none", r=0.05)
for x, h, ha in zip(cx, ["GEO Series", "Experiment", "Genes", "DEGs"], ["left", "left", "right", "right"]):
    text(x, ty, h, 11.5, INK2, "bold", ha=ha)
rh = 0.47
for i, (geo, cat, exp, genes, deg) in enumerate(rows):
    y = ty - 0.49 - i * rh
    if i % 2 == 0:
        box(0.28, y - rh / 2 + 0.02, 5.12, rh - 0.04, fc=CARD, ec="none", r=0.04)
    ax.add_patch(plt.Circle((0.39, y), 0.06, color=CAT[cat], zorder=3))
    text(cx[0] + 0.03, y, geo, 12, weight="bold", ha="left")
    text(cx[1], y, exp, 11, ha="left")
    text(cx[2], y, genes, 12, ha="right")
    text(cx[3], y, deg, 12, ha="right")
ly, lx = 0.32, 0.36
for cat, col in CAT.items():
    ax.add_patch(plt.Circle((lx + 0.07, ly), 0.065, color=col, zorder=3))
    text(lx + 0.2, ly, cat, 11, INK2, ha="left")
    lx += 0.38 + 0.087 * len(cat)

# =============================================================== C. benchmark settings
CX0, CW0 = 6.0, 4.95
panel(CX0, BY, CW0, BH, "C", "Benchmark: 1,000 Items")
text(CX0 + 0.25, 3.92, "Built from the publication, analysis results, and literature", 11.5, INK2, ha="left")


def node(x, y, col, r=0.11, fill=None):
    ax.add_patch(plt.Circle((x, y), r, fc=fill or col, ec=col, lw=1.2, zorder=4))


settings = [
    ("1", "Independent Questions", "400", INSTANT,
     "5 formats: multiple-choice, true/false,\nshort answer, evidence integration,\nmechanistic interpretation"),
    ("2", "Multi-Turn Conversations", "300 turns", THINKING,
     "30 conversations of 8–12 dependent\nturns; 103 challenge turns; 24\nconversations require a revision"),
    ("3", "Hypothesis Evaluation", "300 steps", DEEP_INK,
     "30 hypotheses of 8–12 evidence steps:\nrelation and state at each step; final\nretain/qualify/revise/reject/insufficient"),
]
for i, (num, title, n, col, body) in enumerate(settings):
    y0 = 2.6 - i * 1.17
    box(CX0 + 0.15, y0, CW0 - 0.3, 1.1, fc=CARD, ec=tint(col, 0.6), lw=1.2)
    badge(CX0 + 0.42, y0 + 0.84, num, col)
    text(CX0 + 0.66, y0 + 0.84, title, 13, weight="bold", ha="left")
    text(CX0 + CW0 - 0.27, y0 + 0.84, n, 13, col, "bold", ha="right")
    text(CX0 + 1.05, y0 + 0.68, body, 11.5, INK2, ha="left", va="top")
    gx, gy0 = CX0 + 0.47, y0 + 0.32
    if num == "1":                                   # independent questions
        for k in range(3):
            node(gx - 0.12 + k * 0.22, gy0, col, 0.065)
    elif num == "2":                                 # a chain whose turns depend on earlier turns
        xs = [gx - 0.2 + k * 0.2 for k in range(4)]
        for a, b in zip(xs, xs[1:]):
            ax.plot([a, b], [gy0, gy0], color=col, lw=1.0, zorder=3)
        ax.add_patch(FancyArrowPatch((xs[0], gy0 + 0.06), (xs[3], gy0 + 0.06), arrowstyle="-", color=col,
                                     lw=0.9, connectionstyle="arc3,rad=-0.6", zorder=3))
        for k, xx in enumerate(xs):
            node(xx, gy0, col, 0.06, fill=CARD if k != 2 else col)
    else:                                            # evidence steps toward a decision
        xs = [gx - 0.22 + k * 0.17 for k in range(3)]
        for a, b in zip(xs, xs[1:] + [xs[-1] + 0.25]):
            ax.plot([a, b], [gy0, gy0], color=col, lw=1.0, zorder=3)
        for xx in xs:
            node(xx, gy0, col, 0.055)
        dx = xs[-1] + 0.27
        ax.add_patch(plt.Polygon([(dx - 0.09, gy0), (dx, gy0 + 0.09), (dx + 0.09, gy0), (dx, gy0 - 0.09)],
                                 fc=col, ec=col, zorder=4))

# =============================================================== D. evaluation
DX0, DW0 = 11.35, 4.5
panel(DX0, BY, DW0, BH, "D", "Item Annotation and Evaluation")
text(DX0 + 0.25, 3.92, "A priori Reasoning Requirement Levels", 11.5, INK2, "bold", ha="left")
text(DX0 + DW0 - 0.15, 3.92, "Items", 11.5, INK2, "bold", ha="right")
levels = [("L0", "Retrieval", 47), ("L1", "Interpretation", 127), ("L2", "Cross-layer integration", 295),
          ("L3", "Mechanistic synthesis", 303), ("L4", "Critical mech. reasoning", 228)]
for i, (lv, name, n) in enumerate(levels):
    y = 3.62 - i * 0.27
    ax.add_patch(plt.Rectangle((DX0 + 0.25, y - 0.11), 0.36, 0.22, color=RRL[i], zorder=2))
    text(DX0 + 0.43, y, lv, 10.5, "white" if i >= 3 else INK, "bold")
    text(DX0 + 0.7, y, name, 11.5, ha="left")
    bl = 1.25 * n / 309
    ax.add_patch(plt.Rectangle((DX0 + 2.75, y - 0.09), bl, 0.18, color=RRL[i], zorder=2))
    text(DX0 + 2.8 + bl, y, str(n), 11, INK2, ha="left")

# how answers are evaluated: a two-column table (aspect, measure) in three groups: graded against the reference
# annotations, graded without them (SonicChat), and system checks that are measured rather than graded
text(DX0 + 0.25, 2.27, "Measures  (graders: Claude Opus 5.5; GPT-6)", 11.5, INK2, "bold", ha="left")
groups = [("Graded against the reference", DATA,
           [("Credit", "Match to reference: 1, 0.5, or 0"),
            ("Quality", "Correctness, completeness, reasoning"),
            ("Conversations", "Fact preservation, revision"),
            ("Hypotheses", "Relation, state, decision, calibration"),
            ("Suite score", "Mean over the three settings")]),
          ("Graded without the reference (SonicChat)", LIT,
           [("Judge", "SonicChat score (0–10), no reference"),
            ("Grounding", "Unsupported claims (%)")]),
          ("System checks (measured, not graded)", MODEL,
           [("Cost", "Tokens, tool calls, response time")])]
TX0, TX1, TW1, RH, GH = DX0 + 0.2, DX0 + DW0 - 0.15, 1.2, 0.175, 0.155
ty = 2.12
for gname, gcol, rows in groups:
    text(TX0 + 0.04, ty - GH / 2, gname, 10, gcol, "bold", ha="left", style="italic")
    ty -= GH
    y0 = ty
    for k, (lab, body) in enumerate(rows):
        fill = CARD if k % 2 == 0 else tint(INK2, 0.05)
        ax.add_patch(plt.Rectangle((TX0, ty - RH), TX1 - TX0, RH, fc=fill, ec="none", zorder=1))
        text(TX0 + 0.07, ty - RH / 2, lab, 11, INK, "bold", ha="left")
        text(TX0 + TW1 + 0.05, ty - RH / 2, body, 11, INK2, ha="left")
        ty -= RH
    ax.add_patch(plt.Rectangle((TX0 - 0.05, ty), 0.035, y0 - ty, fc=gcol, ec="none", zorder=2))
    ax.plot([TX0 + TW1 - 0.02] * 2, [y0, ty], color=LINE, lw=0.8, zorder=2)

# =============================================================== flow between panels
# B -> C: benchmark items are built from the datasets; C -> D: answers to them are evaluated
arrow(BX + BW + 0.02, 2.1, CX0 - 0.02, 2.1, INK2, 2.2, head=14, z=7)
arrow(CX0 + CW0 + 0.02, 2.1, DX0 - 0.02, 2.1, INK2, 2.2, head=14, z=7)

ax = axA                                     # links into panel A, in panel A's coordinates
# B -> A: the datasets' iPathwayGuide results, queried by Nova's tools and read directly by the frontier model
ex, top, fy = 0.36, 7.95, 3.97
ax.plot([ex, ex], [BY + BH - 0.02 - DA, top], color=DATA, lw=2.0, zorder=7, solid_capstyle="round")
arrow(ex, top, LX + 0.12, top, DATA, 2.0, head=13, z=7)
arrow(ex, fy, NX0 - 0.01, fy, DATA, 2.0, head=13, z=7)
text((LX + LW) / 2 + 0.3, fy + 0.14, "Result files", 11.5, DATA, "bold")
text(ex, 6.3, "iPathwayGuide results", 11.5, DATA, "bold", rotation=90, z=8,
     bbox=dict(fc=PANEL, ec="none", pad=1.5))
# RQ4: robustness of the interpretation's scores to the grader, reruns, model, and wording (panel D)
rq(13.4, (AY + BY + BH - DA) / 2, "RQ4", "Robust to grader, reruns, model, and wording?", 4.6, h=0.3,
   to=((OX + OW / 2, OX + OW / 2, FY0), (OX + OW / 2, OX + OW / 2, BY + BH - DA)))

fig.savefig(OUT, dpi=300, facecolor="white")
print("wrote", OUT)
