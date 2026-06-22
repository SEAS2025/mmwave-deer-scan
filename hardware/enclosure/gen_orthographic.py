"""Generate a dimensioned orthographic 3-view engineering drawing (SVG) of the
DeerWatch enclosure. Third-angle projection: FRONT, TOP (above front), RIGHT SIDE.

All dimensions in millimetres. Run:
    python hardware/enclosure/gen_orthographic.py
-> writes hardware/enclosure/orthographic.svg
"""

from __future__ import annotations

from pathlib import Path

# ---- Enclosure nominal dimensions (mm) -------------------------------------
W = 160.0   # width  (X)
H = 90.0    # height (Y)
D = 60.0    # depth  (Z)

# Front-face features
RADOME_W, RADOME_H = 80.0, 50.0          # RF-transparent window
RADOME_X = (W - RADOME_W) / 2.0          # centered X
RADOME_Y = 14.0                          # from top
LED_D = 6.0                              # status LED hole dia
BTN_D = 8.0                              # MUTE button dia
GLAND_D = 12.0                           # cable gland dia
MOUNT_HOLE_D = 4.5                       # M4 mount clearance
TILT_DEG = 5.0                           # boresight down-tilt

SCALE = 2.4                              # px per mm
M = 70.0                                 # margin px between/around views
DIM = "#1f6feb"                          # dimension color
OUT = "#111"                             # outline color
FEAT = "#444"                            # feature color


class SVG:
    def __init__(self):
        self.e = []
        self.minx = self.miny = 1e9
        self.maxx = self.maxy = -1e9

    def _bb(self, x, y):
        self.minx = min(self.minx, x); self.miny = min(self.miny, y)
        self.maxx = max(self.maxx, x); self.maxy = max(self.maxy, y)

    def line(self, x1, y1, x2, y2, stroke=OUT, w=1.4, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.e.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                      f'stroke="{stroke}" stroke-width="{w}"{d}/>')
        self._bb(x1, y1); self._bb(x2, y2)

    def rect(self, x, y, w, h, stroke=OUT, sw=1.6, fill="none", rx=0):
        self.e.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
                      f'rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
        self._bb(x, y); self._bb(x + w, y + h)

    def circle(self, cx, cy, r, stroke=FEAT, sw=1.3, fill="none"):
        self.e.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" '
                      f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
        self._bb(cx - r, cy - r); self._bb(cx + r, cy + r)

    def text(self, x, y, s, size=11, anchor="middle", fill="#111", weight="normal", rot=None):
        s = str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        tr = f' transform="rotate({rot} {x:.1f} {y:.1f})"' if rot is not None else ""
        self.e.append(f'<text x="{x:.1f}" y="{y:.1f}" font-family="Consolas,monospace" '
                      f'font-size="{size}" text-anchor="{anchor}" fill="{fill}" '
                      f'font-weight="{weight}"{tr}>{s}</text>')
        self._bb(x, y)

    def arrow(self, x, y, ang):
        import math
        a = math.radians(ang)
        for da in (150, -150):
            b = math.radians(ang + da)
            self.e.append(f'<line x1="{x:.1f}" y1="{y:.1f}" '
                          f'x2="{x+7*math.cos(b):.1f}" y2="{y+7*math.sin(b):.1f}" '
                          f'stroke="{DIM}" stroke-width="1.2"/>')

    def dim_h(self, x1, x2, y, label, off=0):
        yy = y + off
        self.line(x1, yy, x2, yy, stroke=DIM, w=1.0)
        self.arrow(x1, yy, 0); self.arrow(x2, yy, 180)
        # extension lines
        self.line(x1, y, x1, yy, stroke=DIM, w=0.6, dash="2,2")
        self.line(x2, y, x2, yy, stroke=DIM, w=0.6, dash="2,2")
        self.text((x1 + x2) / 2, yy - 4, label, size=10, fill=DIM)

    def dim_v(self, y1, y2, x, label, off=0):
        xx = x + off
        self.line(xx, y1, xx, y2, stroke=DIM, w=1.0)
        self.arrow(xx, y1, 90); self.arrow(xx, y2, 270)
        self.line(x, y1, xx, y1, stroke=DIM, w=0.6, dash="2,2")
        self.line(x, y2, xx, y2, stroke=DIM, w=0.6, dash="2,2")
        self.text(xx - 6, (y1 + y2) / 2, label, size=10, fill=DIM, anchor="middle", rot=-90)

    def render(self, title_lines):
        pad = 30
        w = self.maxx - self.minx + 2 * pad
        h = self.maxy - self.miny + 2 * pad
        ox, oy = pad - self.minx, pad - self.miny
        body = "\n".join(self.e)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h:.0f}" '
                f'viewBox="0 0 {w:.0f} {h:.0f}">\n'
                f'<rect x="0" y="0" width="{w:.0f}" height="{h:.0f}" fill="white"/>\n'
                f'<g transform="translate({ox:.1f},{oy:.1f})">\n{body}\n</g>\n</svg>\n')


def mm(v):
    return v * SCALE


def build():
    s = SVG()

    # ----- FRONT view (W x H), origin top-left at (fx, fy) -----
    fx, fy = 0.0, mm(D) + M
    s.text(fx + mm(W) / 2, fy - 8, "FRONT VIEW", size=13, weight="bold")
    s.rect(fx, fy, mm(W), mm(H), rx=4)
    # radome window
    rx = fx + mm(RADOME_X); ry = fy + mm(RADOME_Y)
    s.rect(rx, ry, mm(RADOME_W), mm(RADOME_H), stroke=FEAT, sw=1.3)
    s.text(rx + mm(RADOME_W) / 2, ry + mm(RADOME_H) / 2, "RF RADOME", size=10, fill=FEAT)
    s.text(rx + mm(RADOME_W) / 2, ry + mm(RADOME_H) / 2 + 12, "(no metal)", size=8, fill=FEAT)
    # LED + button along bottom
    led_cx = fx + mm(30); ctrl_y = fy + mm(H - 16)
    s.circle(led_cx, ctrl_y, mm(LED_D) / 2); s.text(led_cx, ctrl_y + 16, "LED", size=8, fill=FEAT)
    btn_cx = fx + mm(W - 30)
    s.circle(btn_cx, ctrl_y, mm(BTN_D) / 2); s.text(btn_cx, ctrl_y + 16, "MUTE", size=8, fill=FEAT)
    # dimensions
    s.dim_h(fx, fx + mm(W), fy + mm(H), f"{W:.0f}", off=34)
    s.dim_v(fy, fy + mm(H), fx, f"{H:.0f}", off=-30)
    s.dim_h(rx, rx + mm(RADOME_W), ry, f"{RADOME_W:.0f}", off=-22)
    s.dim_v(ry, ry + mm(RADOME_H), rx + mm(RADOME_W), f"{RADOME_H:.0f}", off=26)
    s.text(fx + mm(W) / 2, fy + mm(H) + 20, f"LED dia {LED_D:.0f}   MUTE dia {BTN_D:.0f}",
           size=8, fill=FEAT, anchor="middle")

    # ----- TOP view (W x D) placed above front (third-angle) -----
    tx, ty = 0.0, 0.0
    s.text(tx + mm(W) / 2, ty - 8, "TOP VIEW", size=13, weight="bold")
    s.rect(tx, ty, mm(W), mm(D), rx=4)
    # rear face glands (12V, CAN) on top edge near rear
    g1 = tx + mm(40); g2 = tx + mm(80); g3 = tx + mm(120)
    rear_y = ty + mm(D - 10)
    for gx, lab in ((g1, "12V"), (g2, "USB"), (g3, "CAN")):
        s.circle(gx, rear_y, mm(GLAND_D) / 2)
        s.text(gx, rear_y + 4, lab, size=7, fill=FEAT)
    # 4 mounting bosses (corners inset 12mm)
    for bx in (tx + mm(12), tx + mm(W - 12)):
        for by in (ty + mm(12), ty + mm(D - 12)):
            s.circle(bx, by, mm(MOUNT_HOLE_D) / 2, stroke=DIM)
    s.text(tx + mm(12), ty + mm(12) - 10, "4x M4", size=8, fill=DIM, anchor="middle")
    s.dim_v(ty, ty + mm(D), tx, f"{D:.0f}", off=-30)
    s.dim_h(tx + mm(12), tx + mm(W - 12), ty, f"{W-24:.0f} (mount)", off=-22)

    # ----- RIGHT SIDE view (D x H) placed right of front -----
    sx, sy = mm(W) + M, mm(D) + M
    s.text(sx + mm(D) / 2, sy - 8, "RIGHT SIDE VIEW", size=13, weight="bold")
    s.rect(sx, sy, mm(D), mm(H), rx=4)
    # radome on front edge (left side of this view = front of unit)
    s.line(sx, sy + mm(RADOME_Y), sx, sy + mm(RADOME_Y + RADOME_H), stroke=FEAT, w=3)
    s.text(sx + mm(D) / 2, sy + mm(H) / 2, "boresight", size=8, fill=FEAT)
    # down-tilt indicator arrow from front
    s.line(sx, sy + mm(H/2), sx - 36, sy + mm(H/2) + 36 * 0.0875, stroke=DIM, w=1.2)
    s.text(sx - 20, sy + mm(H/2) - 6, f"{TILT_DEG:.0f} deg", size=9, fill=DIM, anchor="end")
    s.text(sx - 20, sy + mm(H/2) + 8, "down-tilt", size=8, fill=DIM, anchor="end")
    s.dim_h(sx, sx + mm(D), sy + mm(H), f"{D:.0f}", off=34)
    s.dim_v(sy, sy + mm(H), sx + mm(D), f"{H:.0f}", off=26)

    # ----- title block -----
    bx = mm(W) + M
    by = 0.0
    bw, bh = mm(D) + 8, mm(D)
    s.rect(bx, by, bw, bh, sw=1.2)
    lines = [
        ("PROJECT", "DeerWatch mmWave"),
        ("PART", "Enclosure ENC-001 rev A"),
        ("MATERIAL", "Polycarbonate, IP65"),
        ("UNITS", "mm  (third-angle)"),
        ("ENVELOPE", f"{W:.0f} x {H:.0f} x {D:.0f}"),
        ("SCALE", "see dims (not to print)"),
        ("RADOME", f"{RADOME_W:.0f} x {RADOME_H:.0f}, wall <=2mm"),
        ("TILT", f"{TILT_DEG:.0f} deg down"),
    ]
    yy = by + 18
    s.text(bx + 8, yy, "DRAWING", size=11, anchor="start", weight="bold"); yy += 16
    for k, v in lines:
        s.text(bx + 8, yy, f"{k:9s} {v}", size=9, anchor="start", fill="#222")
        yy += 14

    return s.render([])


def main():
    out = Path(__file__).resolve().parent / "orthographic.svg"
    out.write_text(build(), encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
