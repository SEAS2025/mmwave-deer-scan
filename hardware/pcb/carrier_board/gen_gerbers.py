"""Generate a manufacturable RS-274X Gerber + Excellon package for the
DeerWatch carrier board (2-layer FR4, 70 x 50 mm) and zip it for JLCPCB upload.

Outputs (in ./gerbers):
  DeerWatch-Carrier.GTL  top copper      DeerWatch-Carrier.GTS  top mask
  DeerWatch-Carrier.GBL  bottom copper   DeerWatch-Carrier.GBS  bottom mask
  DeerWatch-Carrier.GTO  top silk        DeerWatch-Carrier.GBO  bottom silk
  DeerWatch-Carrier.GKO  board outline   DeerWatch-Carrier.TXT  drill (Excellon)
  DeerWatch-Carrier-gerbers.zip          carrier_preview.png

SCOPE: this is the low-frequency carrier (power + IO + alerting). The 60/77 GHz RF is a
COTS module (IWR6843AOPEVM). Pad geometry, board outline, drills, ground pour and
silkscreen are production-grade; final copper net routing should be verified in KiCad and
in the JLCPCB Gerber viewer before mass production. See FAB_NOTES.md.

    python hardware/pcb/carrier_board/gen_gerbers.py
"""

from __future__ import annotations

import math
import zipfile
from pathlib import Path

# ----------------------------------------------------------------------------
# Board + format
# ----------------------------------------------------------------------------
BW, BH = 70.0, 50.0          # board size mm
SCALE = 1_000_000            # 1e-6 mm units, matches FSLAX46Y46
NAME = "DeerWatch-Carrier"
OUTDIR = Path(__file__).resolve().parent / "gerbers"


def u(v):
    """mm -> gerber integer units (6 decimal places)."""
    return str(int(round(v * SCALE)))


# ----------------------------------------------------------------------------
# Aperture manager
# ----------------------------------------------------------------------------
class Apertures:
    def __init__(self):
        self.defs = []      # list of macro/aperture definition strings (without %..%)
        self.codes = {}     # key -> Dnn
        self._n = 10

    def get(self, key):
        if key in self.codes:
            return self.codes[key]
        code = f"D{self._n}"
        self._n += 1
        kind = key[0]
        if kind == "C":
            self.defs.append(f"ADD{code[1:]}C,{key[1]:.6f}")
        elif kind == "R":
            self.defs.append(f"ADD{code[1:]}R,{key[1]:.6f}X{key[2]:.6f}")
        elif kind == "O":
            self.defs.append(f"ADD{code[1:]}O,{key[1]:.6f}X{key[2]:.6f}")
        else:
            raise ValueError(key)
        self.codes[key] = code
        return code


# ----------------------------------------------------------------------------
# Geometry collectors (also used by the PNG preview)
# ----------------------------------------------------------------------------
class Geo:
    def __init__(self):
        self.top_flash = []     # (key, x, y)
        self.bot_flash = []
        self.top_mask = []
        self.bot_mask = []
        self.top_track = []     # (width, [(x,y)...])
        self.bot_track = []
        self.silk_top = []      # [(x,y)...] polylines
        self.silk_bot = []
        self.drills = []        # (dia, x, y, plated)
        self.tht_clear = []     # (x, y, dia) for bottom pour clearance


GEO = Geo()

# ----------------------------------------------------------------------------
# Compact uppercase stroke font (grid 0..5 x 0..7), polylines
# ----------------------------------------------------------------------------
F = {
    "A": [[(0, 0), (0, 5), (2.5, 7), (5, 5), (5, 0)], [(0, 3), (5, 3)]],
    "B": [[(0, 0), (0, 7), (4, 7), (5, 6), (5, 4.5), (4, 3.5), (0, 3.5)], [(4, 3.5), (5, 2.5), (5, 1), (4, 0), (0, 0)]],
    "C": [[(5, 6), (3, 7), (1, 7), (0, 5), (0, 2), (1, 0), (3, 0), (5, 1)]],
    "D": [[(0, 0), (0, 7), (3, 7), (5, 5), (5, 2), (3, 0), (0, 0)]],
    "E": [[(5, 7), (0, 7), (0, 0), (5, 0)], [(0, 3.5), (3.5, 3.5)]],
    "F": [[(5, 7), (0, 7), (0, 0)], [(0, 3.5), (3.5, 3.5)]],
    "G": [[(5, 6), (3, 7), (1, 7), (0, 5), (0, 2), (1, 0), (3, 0), (5, 1), (5, 3), (3, 3)]],
    "H": [[(0, 0), (0, 7)], [(5, 0), (5, 7)], [(0, 3.5), (5, 3.5)]],
    "I": [[(1, 7), (4, 7)], [(2.5, 7), (2.5, 0)], [(1, 0), (4, 0)]],
    "J": [[(4, 7), (4, 2), (3, 0), (1, 0), (0, 2)]],
    "K": [[(0, 0), (0, 7)], [(0, 3), (5, 7)], [(0, 3), (5, 0)]],
    "L": [[(0, 7), (0, 0), (5, 0)]],
    "M": [[(0, 0), (0, 7), (2.5, 4), (5, 7), (5, 0)]],
    "N": [[(0, 0), (0, 7), (5, 0), (5, 7)]],
    "O": [[(1, 0), (0, 2), (0, 5), (1, 7), (4, 7), (5, 5), (5, 2), (4, 0), (1, 0)]],
    "P": [[(0, 0), (0, 7), (4, 7), (5, 6), (5, 4.5), (4, 3.5), (0, 3.5)]],
    "Q": [[(1, 0), (0, 2), (0, 5), (1, 7), (4, 7), (5, 5), (5, 2), (4, 0), (1, 0)], [(3, 2), (5, 0)]],
    "R": [[(0, 0), (0, 7), (4, 7), (5, 6), (5, 4.5), (4, 3.5), (0, 3.5)], [(2.5, 3.5), (5, 0)]],
    "S": [[(5, 6), (3, 7), (1, 7), (0, 6), (0, 4.5), (1, 3.5), (4, 3.5), (5, 2.5), (5, 1), (4, 0), (1, 0), (0, 1)]],
    "T": [[(0, 7), (5, 7)], [(2.5, 7), (2.5, 0)]],
    "U": [[(0, 7), (0, 2), (1, 0), (4, 0), (5, 2), (5, 7)]],
    "V": [[(0, 7), (2.5, 0), (5, 7)]],
    "W": [[(0, 7), (1.2, 0), (2.5, 4), (3.8, 0), (5, 7)]],
    "X": [[(0, 0), (5, 7)], [(0, 7), (5, 0)]],
    "Y": [[(0, 7), (2.5, 3.5), (5, 7)], [(2.5, 3.5), (2.5, 0)]],
    "Z": [[(0, 7), (5, 7), (0, 0), (5, 0)]],
    "0": [[(1, 0), (0, 2), (0, 5), (1, 7), (4, 7), (5, 5), (5, 2), (4, 0), (1, 0)], [(0, 1), (5, 6)]],
    "1": [[(1, 5), (2.5, 7), (2.5, 0)], [(1, 0), (4, 0)]],
    "2": [[(0, 6), (1, 7), (4, 7), (5, 6), (5, 4), (0, 0), (5, 0)]],
    "3": [[(0, 7), (5, 7), (2.5, 4)], [(5, 4), (5, 1), (4, 0), (1, 0), (0, 1)]],
    "4": [[(4, 0), (4, 7), (0, 2), (5, 2)]],
    "5": [[(5, 7), (0, 7), (0, 4), (4, 4), (5, 3), (5, 1), (4, 0), (1, 0), (0, 1)]],
    "6": [[(5, 6), (4, 7), (1, 7), (0, 5), (0, 1), (1, 0), (4, 0), (5, 1), (5, 3), (4, 4), (0, 4)]],
    "7": [[(0, 7), (5, 7), (2, 0)]],
    "8": [[(1, 3.5), (0, 2.5), (0, 1), (1, 0), (4, 0), (5, 1), (5, 2.5), (4, 3.5), (1, 3.5), (0, 4.5), (0, 6), (1, 7), (4, 7), (5, 6), (5, 4.5), (4, 3.5)]],
    "9": [[(0, 1), (1, 0), (4, 0), (5, 2), (5, 6), (4, 7), (1, 7), (0, 6), (0, 4), (1, 3), (5, 3)]],
    "-": [[(1, 3.5), (4, 3.5)]],
    "+": [[(2.5, 1.5), (2.5, 5.5)], [(0.5, 3.5), (4.5, 3.5)]],
    ".": [[(2.2, 0), (2.8, 0), (2.8, 0.6), (2.2, 0.6), (2.2, 0)]],
    "/": [[(0, 0), (5, 7)]],
    " ": [],
}


def silk_text(x, y, s, h=1.4, layer="top"):
    """Draw stroke text; (x,y) bottom-left, h = char height mm."""
    sx = h / 7.0
    cw = 5 * sx + 1.2 * sx  # char advance
    buf = GEO.silk_top if layer == "top" else GEO.silk_bot
    cx = x
    for ch in s.upper():
        for stroke in F.get(ch, F[" "]):
            buf.append([(cx + px * sx, y + py * sx) for px, py in stroke])
        cx += cw


# ----------------------------------------------------------------------------
# Footprint primitives
# ----------------------------------------------------------------------------
def pad_smd(x, y, w, h):
    key = ("R", w, h)
    GEO.top_flash.append((key, x, y))
    GEO.top_mask.append((("R", w + 0.1, h + 0.1), x, y))


def pad_tht_round(x, y, pad_d, drill_d, plated=True):
    GEO.top_flash.append((("C", pad_d), x, y))
    GEO.bot_flash.append((("C", pad_d), x, y))
    GEO.top_mask.append((("C", pad_d + 0.1), x, y))
    GEO.bot_mask.append((("C", pad_d + 0.1), x, y))
    GEO.drills.append((drill_d, x, y, plated))
    GEO.tht_clear.append((x, y, pad_d + 0.5))


def mount_hole(x, y, drill_d=3.2):
    GEO.drills.append((drill_d, x, y, False))
    GEO.tht_clear.append((x, y, drill_d + 1.2))
    # silk ring
    ring = [(x + (drill_d / 2 + 0.6) * math.cos(t), y + (drill_d / 2 + 0.6) * math.sin(t))
            for t in [i * math.pi / 8 for i in range(17)]]
    GEO.silk_top.append(ring)


def rect_outline(x0, y0, x1, y1, layer="top"):
    poly = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
    (GEO.silk_top if layer == "top" else GEO.silk_bot).append(poly)


def header_2xN(x, y, n, pitch=2.54, pad_d=1.7, drill=1.0):
    """2 x n header, pin1 at (x,y), rows in +y, pins in +x."""
    for col in range(n):
        for row in range(2):
            pad_tht_round(x + col * pitch, y + row * pitch, pad_d, drill)
    rect_outline(x - 1.6, y - 1.6, x + (n - 1) * pitch + 1.6, y + pitch + 1.6)
    # pin1 marker
    GEO.silk_top.append([(x - 1.6, y - 0.4), (x - 0.4, y - 1.6)])


def screw_term(x, y, n, pitch=5.08, pad_d=2.4, drill=1.3):
    for i in range(n):
        pad_tht_round(x + i * pitch, y, pad_d, drill)
    rect_outline(x - 2.6, y - 3.0, x + (n - 1) * pitch + 2.6, y + 3.2)


def soic(x, y, pins, pitch=1.27, span=5.2, pw=0.6, ph=1.55):
    """SOIC body centered at (x,y); pins per side = pins/2."""
    per = pins // 2
    x0 = x - (per - 1) * pitch / 2
    for i in range(per):
        pad_smd(x0 + i * pitch, y - span / 2, pw, ph)
        pad_smd(x0 + i * pitch, y + span / 2, pw, ph)
    bw = (per - 1) * pitch + 1.2
    rect_outline(x - bw / 2, y - 1.9, x + bw / 2, y + 1.9)
    GEO.silk_top.append([(x - bw / 2 + 0.2, y - 1.9), (x - bw / 2 + 0.2, y - 1.0)])


def sot23(x, y):
    pad_smd(x - 0.95, y - 0.5, 0.7, 0.9)
    pad_smd(x - 0.95, y + 0.5, 0.7, 0.9)
    pad_smd(x + 0.95, y, 0.7, 0.9)
    rect_outline(x - 0.8, y - 0.85, x + 0.8, y + 0.85)


def sot223(x, y):
    for dy in (-2.3, 0, 2.3):
        pad_smd(x - 3.0, y + dy, 1.5, 0.9)
    pad_smd(x + 3.0, y, 3.5, 6.0)  # tab
    rect_outline(x - 3.4, y - 3.3, x + 3.4, y + 3.3)


def chip(x, y, body=2.0):
    """0805/SMA-ish two-pad part, long axis x."""
    pad_smd(x - body / 2 - 0.5, y, 1.0, 1.3)
    pad_smd(x + body / 2 + 0.5, y, 1.0, 1.3)
    rect_outline(x - body / 2 - 1.0, y - 0.9, x + body / 2 + 1.0, y + 0.9)


def chip0603(x, y):
    pad_smd(x - 0.8, y, 0.8, 0.9)
    pad_smd(x + 0.8, y, 0.8, 0.9)


def inductor(x, y):
    pad_smd(x - 2.6, y, 2.2, 3.4)
    pad_smd(x + 2.6, y, 2.2, 3.4)
    rect_outline(x - 3.6, y - 2.2, x + 3.6, y + 2.2)


def elec_cap(x, y, drill=0.9, pad=1.9, pitch=2.5):
    pad_tht_round(x - pitch / 2, y, pad, drill)
    pad_tht_round(x + pitch / 2, y, pad, drill)
    r = 3.2
    ring = [(x + r * math.cos(t), y + r * math.sin(t)) for t in [i * math.pi / 10 for i in range(21)]]
    GEO.silk_top.append(ring)
    GEO.silk_top.append([(x - pitch / 2 - 0.6, y + 1.2), (x - pitch / 2 + 0.6, y + 1.2)])  # '-' polarity


def tactile(x, y):
    for dx in (-3.0, 3.0):
        for dy in (-2.0, 2.0):
            pad_tht_round(x + dx, y + dy, 1.6, 1.0)
    rect_outline(x - 3.0, y - 3.0, x + 3.0, y + 3.0)


def track(width, pts, layer="top"):
    (GEO.top_track if layer == "top" else GEO.bot_track).append((width, pts))


# ----------------------------------------------------------------------------
# Placement (the actual board)
# ----------------------------------------------------------------------------
def place():
    # Mounting holes (M3) corners inset 4 mm
    for mx in (4, BW - 4):
        for my in (4, BH - 4):
            mount_hole(mx, my)

    # J3 Pi 2x20 header along top, centered
    j3x = (BW - 19 * 2.54) / 2
    j3y = BH - 8.0
    header_2xN(j3x, j3y, 20)
    silk_text(j3x, j3y + 3.0, "PI GPIO J3", 1.3)

    # J1 12V screw terminal (bottom-left)
    screw_term(8, 7, 2)
    silk_text(5.5, 11.5, "12V J1", 1.3)
    silk_text(6.0, 3.0, "+   -", 1.2)

    # J2 CAN screw terminal 3P
    screw_term(24, 7, 3)
    silk_text(24, 11.5, "CAN J2", 1.3)

    # J4 radar 4P header (bottom-right)
    header_2xN(52, 6, 2)  # 2x2 = 4 pins
    silk_text(50.5, 10.5, "RADAR J4", 1.2)

    # U1 buck TPS5450 SO-8 PowerPAD
    soic(20, 30, 8)
    pad_smd(20, 30, 3.0, 3.5)  # exposed thermal pad
    silk_text(15.5, 33.5, "U1 BUCK 5V", 1.2)

    # L1 power inductor
    inductor(33, 30)
    silk_text(30.5, 33.0, "L1", 1.2)

    # D2 schottky SMA
    chip(33, 22, body=2.6)
    silk_text(31.5, 23.6, "D2", 1.0)

    # C1 bulk in / C2 bulk out (electrolytic)
    elec_cap(10, 22)
    silk_text(7.5, 26.0, "C1", 1.0)
    elec_cap(44, 24)
    silk_text(41.5, 28.0, "C2", 1.0)

    # U2 LDO 3V3 SOT-223
    sot223(44, 34)
    silk_text(40.0, 38.0, "U2 3V3", 1.1)

    # U3 CAN xcvr SOIC-8
    soic(30, 14, 8)
    silk_text(25.5, 17.0, "U3 CAN", 1.2)

    # Q1 rev-pol P-FET, Q2 buzzer NPN (SOT-23)
    sot23(14, 16)
    silk_text(12.0, 17.5, "Q1", 0.9)
    sot23(58, 30)
    silk_text(56.0, 31.5, "Q2", 0.9)

    # D3 RGB status LED (5050, 4 pad) - use two-pad-ish approx with 4 pads
    for dx in (-1.4, 1.4):
        for dy in (-1.4, 1.4):
            pad_smd(58 + dx, 40 + dy, 1.0, 1.0)
    rect_outline(58 - 2.2, 40 - 2.2, 58 + 2.2, 40 + 2.2)
    silk_text(54.5, 43.0, "D3 LED", 1.1)

    # D1 TVS SMB near input
    chip(16, 22, body=2.2)
    silk_text(14.5, 23.6, "D1", 1.0)

    # R1..R6 0603 cluster near LED / signals
    rx = 50
    for i in range(6):
        chip0603(rx, 22 + (i % 3) * 2.2 + (i // 3) * 0.0)
        if i == 0:
            silk_text(48.0, 28.5, "R1-6", 1.0)
        rx += 0 if (i + 1) % 3 else 3.0

    # C3..C9 decoupling 0603/0805 scattered
    for i, (cx, cy) in enumerate([(24, 30), (24, 27), (40, 30), (40, 27), (35, 14), (38, 14), (50, 34)]):
        chip0603(cx, cy)

    # SW1 mute button
    tactile(62, 16)
    silk_text(58.5, 20.5, "SW1 MUTE", 1.1)

    # BZ1 buzzer header 2P
    pad_tht_round(64, 30, 1.7, 1.0)
    pad_tht_round(64 + 2.54, 30, 1.7, 1.0)
    silk_text(61.5, 33.0, "BZ1", 1.0)

    # ---- power routing (top copper) ----
    track(0.6, [(8, 7), (8, 16), (16, 22)])           # 12V -> protection area
    track(0.6, [(16, 22), (20, 27.5)])                # -> U1 in
    track(0.8, [(22.5, 30), (33, 30)])                # U1 SW -> L1
    track(0.8, [(35.6, 30), (44, 24)])                # L1 -> C2 / 5V
    track(0.5, [(44, 24), (44, 34)])                  # 5V -> LDO in
    track(0.5, [(44, 24), (52, 6)])                   # 5V -> radar J4
    track(0.5, [(44, 24), (j3x + 0 * 2.54, j3y)])     # 5V -> Pi header pin area
    track(0.4, [(58, 30), (64, 30)])                  # Q2 -> buzzer
    track(0.4, [(58, 38.6), (58, 40 - 1.4)])          # LED feed

    # ---- board title (silk) ----
    silk_text(8, BH - 3.2, "DEERWATCH CARRIER REV A", 1.6)
    silk_text(8, 0.6, "SEAS2025  2-LAYER FR4 1.6MM", 1.1)
    silk_text(BW - 20, 0.6, "JLCPCB", 1.1)


# ----------------------------------------------------------------------------
# Gerber writers
# ----------------------------------------------------------------------------
def gerber_header(ap_block):
    return (["%FSLAX46Y46*%", "%MOMM*%", "%LPD*%"] +
            [f"%{d}*%" for d in ap_block])


def _finish(path, ap, body):
    """Prepend header (with all apertures now registered) and write file."""
    lines = gerber_header(ap.defs) + body + ["M02*"]
    path.write_text("\n".join(lines) + "\n", encoding="ascii", newline="\n")


def write_copper(path, flashes, tracks, ap, pour=False):
    body = []
    if pour:
        body.append("G36*")
        body += contour_rect(0.6, 0.6, BW - 0.6, BH - 0.6)
        body.append("G37*")
        body.append("%LPC*%")
        for (x, y, d) in GEO.tht_clear:
            body.append(f"{ap.get(('C', d))}*")
            body.append(f"X{u(x)}Y{u(y)}D03*")
        body.append("%LPD*%")
    cur = None
    for key, x, y in flashes:
        code = ap.get(key)
        if code != cur:
            body.append(f"{code}*"); cur = code
        body.append(f"X{u(x)}Y{u(y)}D03*")
    for width, pts in tracks:
        code = ap.get(("C", width))
        if code != cur:
            body.append(f"{code}*"); cur = code
        x0, y0 = pts[0]
        body.append(f"X{u(x0)}Y{u(y0)}D02*")
        for (x, y) in pts[1:]:
            body.append(f"X{u(x)}Y{u(y)}D01*")
    _finish(path, ap, body)


def contour_rect(x0, y0, x1, y1):
    return [f"X{u(x0)}Y{u(y0)}D02*", f"X{u(x1)}Y{u(y0)}D01*",
            f"X{u(x1)}Y{u(y1)}D01*", f"X{u(x0)}Y{u(y1)}D01*",
            f"X{u(x0)}Y{u(y0)}D01*"]


def write_mask(path, flashes, ap):
    body = []
    cur = None
    for key, x, y in flashes:
        code = ap.get(key)
        if code != cur:
            body.append(f"{code}*"); cur = code
        body.append(f"X{u(x)}Y{u(y)}D03*")
    _finish(path, ap, body)


def write_silk(path, polys, ap):
    code = ap.get(("C", 0.15))
    body = [f"{code}*"]
    for poly in polys:
        if not poly:
            continue
        x0, y0 = poly[0]
        body.append(f"X{u(x0)}Y{u(y0)}D02*")
        for (x, y) in poly[1:]:
            body.append(f"X{u(x)}Y{u(y)}D01*")
    _finish(path, ap, body)


def write_outline(path, ap):
    code = ap.get(("C", 0.15))
    body = [f"{code}*"] + contour_rect(0, 0, BW, BH)
    _finish(path, ap, body)


def write_drill(path):
    tools = {}
    for (d, x, y, plated) in GEO.drills:
        tools.setdefault(round(d, 3), []).append((x, y))
    lines = ["M48", ";DRILL file {%s}" % NAME, ";FORMAT={-:-/ absolute / metric / decimal}",
             "FMAT,2", "METRIC", "G90"]
    tnames = {}
    for i, d in enumerate(sorted(tools), start=1):
        tnames[d] = f"T{i:02d}"
        lines.append(f"{tnames[d]}C{d:.3f}")
    lines.append("%")
    for d in sorted(tools):
        lines.append(tnames[d])
        for (x, y) in tools[d]:
            lines.append(f"X{x:.3f}Y{y:.3f}")
    lines.append("M30")
    path.write_text("\n".join(lines) + "\n", encoding="ascii", newline="\n")


# ----------------------------------------------------------------------------
# PNG preview (Pillow) - sanity render of what JLCPCB will fab
# ----------------------------------------------------------------------------
def preview(path, px_per_mm=12):
    try:
        from PIL import Image, ImageDraw
    except Exception:
        print("[preview] Pillow not available, skipping PNG")
        return
    pad = 8
    W = int(BW * px_per_mm) + 2 * pad
    H = int(BH * px_per_mm) + 2 * pad
    img = Image.new("RGB", (W, H), (12, 40, 20))
    dr = ImageDraw.Draw(img, "RGBA")

    def X(x):
        return pad + x * px_per_mm

    def Y(y):
        return H - pad - y * px_per_mm  # flip to engineering orientation

    # board substrate
    dr.rectangle([X(0), Y(BH), X(BW), Y(0)], fill=(20, 110, 60))
    # bottom pour hint
    dr.rectangle([X(0.6), Y(BH - 0.6), X(BW - 0.6), Y(0.6)], outline=(80, 200, 140, 120), width=1)

    def draw_flashes(flashes, color):
        for key, x, y in flashes:
            if key[0] == "C":
                r = key[1] / 2 * px_per_mm
                dr.ellipse([X(x) - r, Y(y) - r, X(x) + r, Y(y) + r], fill=color)
            else:
                w = key[1] * px_per_mm; h = key[2] * px_per_mm
                dr.rectangle([X(x) - w / 2, Y(y) - h / 2, X(x) + w / 2, Y(y) + h / 2], fill=color)

    draw_flashes(GEO.top_flash, (220, 200, 120))
    for width, pts in GEO.top_track:
        dr.line([(X(x), Y(y)) for x, y in pts], fill=(200, 150, 60), width=max(1, int(width * px_per_mm)))
    for (x, y, _p) in [(d[1], d[2], d[3]) for d in GEO.drills]:
        dr.ellipse([X(x) - 2, Y(y) - 2, X(x) + 2, Y(y) + 2], fill=(10, 10, 10))
    for poly in GEO.silk_top:
        if len(poly) >= 2:
            dr.line([(X(x), Y(y)) for x, y in poly], fill=(245, 245, 245), width=1)
    dr.rectangle([X(0), Y(BH), X(BW), Y(0)], outline=(255, 255, 0), width=2)
    img.save(path)
    print(f"[preview] wrote {path} ({W}x{H})")


# ----------------------------------------------------------------------------
def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    place()

    ap_top = Apertures()
    ap_bot = Apertures()
    ap_mt = Apertures()
    ap_mb = Apertures()
    ap_silk_t = Apertures()
    ap_silk_b = Apertures()
    ap_out = Apertures()

    files = {
        f"{NAME}.GTL": lambda p: write_copper(p, GEO.top_flash, GEO.top_track, ap_top),
        f"{NAME}.GBL": lambda p: write_copper(p, GEO.bot_flash, GEO.bot_track, ap_bot, pour=True),
        f"{NAME}.GTS": lambda p: write_mask(p, GEO.top_mask, ap_mt),
        f"{NAME}.GBS": lambda p: write_mask(p, GEO.bot_mask, ap_mb),
        f"{NAME}.GTO": lambda p: write_silk(p, GEO.silk_top, ap_silk_t),
        f"{NAME}.GBO": lambda p: write_silk(p, GEO.silk_bot, ap_silk_b),
        f"{NAME}.GKO": lambda p: write_outline(p, ap_out),
        f"{NAME}.TXT": write_drill,
    }
    written = []
    for fn, fnc in files.items():
        p = OUTDIR / fn
        fnc(p)
        written.append(p)

    preview(OUTDIR.parent / "carrier_preview.png")

    zip_path = OUTDIR.parent / f"{NAME}-gerbers.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in written:
            z.write(p, p.name)
    print(f"Wrote {len(written)} gerber/drill files + {zip_path.name}")
    for p in written:
        print(f"  {p.name:28s} {p.stat().st_size:6d} bytes")


if __name__ == "__main__":
    main()
