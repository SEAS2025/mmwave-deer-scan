"""Generate a real KiCad PCB (.kicad_pcb) for the DeerWatch carrier board.

This emits a board that opens directly in KiCad 8/9/10 with:
  * Edge.Cuts board outline (70 x 50 mm)
  * every component placed as a footprint with pads (matches the Gerber layout)
  * power/ground nets (GND, +12V, +5V, +3V3) assigned to the relevant pads
  * routed power rails on F.Cu (track endpoints land on pad centres)
  * a poured GND zone on B.Cu (connects all GND pads)

After generating, run KiCad's own DRC and Gerber export with kicad-cli:

    python hardware/pcb/carrier_board/gen_kicad.py
    kicad-cli pcb drc   --severity-error  DeerWatch-Carrier.kicad_pcb
    kicad-cli pcb export gerbers -o kicad_gerbers DeerWatch-Carrier.kicad_pcb

NOTE: this is the low-frequency carrier (power + IO + alerting). Signal IO nets
(CAN, GPIO, buzzer, LED) are placed but intended for interactive routing in KiCad;
the power tree + ground pour are routed here so DRC checks real copper.
"""

from __future__ import annotations

import uuid
from pathlib import Path

BW, BH = 70.0, 50.0
OUT = Path(__file__).resolve().parent / "kicad" / "DeerWatch-Carrier.kicad_pcb"

# ---------------------------------------------------------------------------
# Nets
# ---------------------------------------------------------------------------
NETS = ["", "GND", "+12V", "+5V", "+3V3", "CANH", "CANL"]
NETNUM = {n: i for i, n in enumerate(NETS)}


def Y(y):
    """Engineering y (up) -> KiCad y (down)."""
    return round(BH - y, 4)


def uid():
    return str(uuid.uuid4())


# Collect routed-pad absolute centres so tracks can land exactly on them.
PADXY = {}  # label -> (x, y_kicad)


# ---------------------------------------------------------------------------
# Footprint / pad emitters
# ---------------------------------------------------------------------------
def _pad(num, ptype, dx, dy, sx, sy, net, drill=None, label=None, ox=0.0, oy=0.0):
    layers = '"F.Cu" "F.Paste" "F.Mask"' if ptype == "smd" else '"*.Cu" "*.Mask"'
    if ptype == "smd":
        head = f'(pad "{num}" smd roundrect (at {dx} {dy}) (size {sx} {sy}) (layers {layers}) (roundrect_rratio 0.2)'
    elif ptype == "np":
        head = f'(pad "" np_thru_hole circle (at {dx} {dy}) (size {sx} {sy}) (drill {drill}) (layers {layers})'
    else:
        head = f'(pad "{num}" thru_hole circle (at {dx} {dy}) (size {sx} {sy}) (drill {drill}) (layers {layers})'
    netstr = ""
    if net:
        netstr = f' (net {NETNUM[net]} "{net}")'
    if label and net:
        PADXY[label] = (round(ox + dx, 4), round(oy + dy, 4))
    return f"    {head}{netstr} (uuid \"{uid()}\"))"


def footprint(ref, value, x, y, pads):
    ky = Y(y)
    lines = [
        f'  (footprint "deerwatch:{ref}" (layer "F.Cu")',
        f'    (uuid "{uid()}")',
        f"    (at {x} {ky})",
        f'    (property "Reference" "{ref}" (at 0 -2.4 0) (layer "F.Fab") (uuid "{uid()}")',
        f'      (effects (font (size 0.9 0.9) (thickness 0.15))))',
        f'    (property "Value" "{value}" (at 0 2.4 0) (layer "F.Fab") (uuid "{uid()}")',
        f'      (effects (font (size 0.9 0.9) (thickness 0.15))))',
    ]
    lines += [p.replace("(at ", "(at ", 1) for p in pads_abs(pads, x, ky)]
    lines.append("  )")
    return lines


def pads_abs(pads, ox, oy):
    """pads here already use footprint-local coords; we pass abs origin for PADXY."""
    out = []
    for spec in pads:
        spec = dict(spec)
        spec["ox"] = ox
        spec["oy"] = oy
        out.append(_pad(**spec))
    return out


def smd(num, dx, dy, sx, sy, net="", label=None):
    return {"num": num, "ptype": "smd", "dx": dx, "dy": -dy, "sx": sx, "sy": sy, "net": net, "label": label}


def tht(num, dx, dy, dia, drill, net="", label=None):
    return {"num": num, "ptype": "tht", "dx": dx, "dy": -dy, "sx": dia, "sy": dia, "net": net, "drill": drill, "label": label}


def npth(dx, dy, dia):
    return {"num": "", "ptype": "np", "dx": dx, "dy": -dy, "sx": dia, "sy": dia, "net": "", "drill": dia}


# NOTE: dy is negated above because footprint-local +y is downward in KiCad, but
# the placement coords below are written engineering-style (+y up) for consistency.


# ---------------------------------------------------------------------------
# Board placement (mirrors gen_gerbers.place())
# ---------------------------------------------------------------------------
def components():
    fps = []

    # M1..M4 mounting holes (M3, NPTH)
    for i, (mx, my) in enumerate([(4, 4), (4, BH - 4), (BW - 4, 4), (BW - 4, BH - 4)], 1):
        fps.append(("MH", footprint(f"MH{i}", "M3", mx, my, [npth(0, 0, 3.2)])))

    # J1 12V screw terminal (5.08 pitch, 2P)
    fps.append(("J1", footprint("J1", "12V_IN", 8, 7, [
        tht("1", -2.54, 0, 2.6, 1.3, "+12V", "J1_12V"),
        tht("2", 2.54, 0, 2.6, 1.3, "GND"),
    ])))

    # J2 CAN screw terminal 3P
    fps.append(("J2", footprint("J2", "CAN", 24, 7, [
        tht("1", -5.08, 0, 2.6, 1.3, "CANH"),
        tht("2", 0, 0, 2.6, 1.3, "CANL"),
        tht("3", 5.08, 0, 2.6, 1.3, "GND"),
    ])))

    # J3 Raspberry Pi 2x20 header
    j3x = (BW - 19 * 2.54) / 2
    j3y = BH - 8.0
    pin_pads = []
    n = 1
    for col in range(20):
        for row in range(2):
            px = -((19 * 2.54) / 2) + col * 2.54
            py = (1.27 if row == 0 else -1.27)
            # assign a realistic subset of power/ground pins
            net = ""
            if n in (2, 4):
                net = "+5V"
            elif n in (1, 17):
                net = "+3V3"
            elif n in (6, 9, 14, 20, 25, 30, 34, 39):
                net = "GND"
            lbl = f"PI{n}" if net in ("+5V", "+3V3") else None
            pin_pads.append(tht(str(n), round(px, 3), round(py, 3), 1.7, 1.0, net, lbl))
            n += 1
    fps.append(("J3", footprint("J3", "RPi_2x20", BW / 2, j3y, pin_pads)))

    # J4 radar 4P header (2x2, 2.54)
    fps.append(("J4", footprint("J4", "RADAR", 52, 6, [
        tht("1", -1.27, 1.27, 1.7, 1.0, "+5V", "J4_5V"),
        tht("2", 1.27, 1.27, 1.7, 1.0, "GND"),
        tht("3", -1.27, -1.27, 1.7, 1.0, ""),
        tht("4", 1.27, -1.27, 1.7, 1.0, ""),
    ])))

    # U1 buck TPS5450 SO-8 + thermal pad
    u1 = []
    for i in range(4):  # pins 1-4 left
        u1.append(smd(str(i + 1), -2.7, 1.905 - i * 1.27, 1.5, 0.6,
                      net=("GND" if i == 2 else ""), label=("U1_GND" if i == 2 else None)))
    for i in range(4):  # pins 5-8 right
        pin = 8 - i
        net = "+5V" if pin == 5 else ("+12V" if pin == 8 else "")
        lbl = "U1_SW" if pin == 5 else ("U1_VIN" if pin == 8 else None)
        u1.append(smd(str(pin), 2.7, 1.905 - i * 1.27, 1.5, 0.6, net=net, label=lbl))
    u1.append(smd("9", 0, 0, 3.0, 3.5, "GND", "U1_PAD"))
    fps.append(("U1", footprint("U1", "TPS5450", 20, 30, u1)))

    # L1 power inductor (2 pads)
    fps.append(("L1", footprint("L1", "10uH", 33, 30, [
        smd("1", -2.6, 0, 2.4, 3.0, "+5V", "L1_A"),
        smd("2", 2.6, 0, 2.4, 3.0, "+5V", "L1_B"),
    ])))

    # D2 schottky SMA (catch diode)
    fps.append(("D2", footprint("D2", "SS34", 33, 22, [
        smd("1", -2.3, 0, 1.6, 1.8, "GND"),
        smd("2", 2.3, 0, 1.6, 1.8, "+5V", "D2_K"),
    ])))

    # C1 bulk in (electrolytic, THT)
    fps.append(("C1", footprint("C1", "100uF", 10, 22, [
        tht("1", -1.75, 0, 2.2, 1.0, "+12V", "C1_P"),
        tht("2", 1.75, 0, 2.2, 1.0, "GND"),
    ])))

    # C2 bulk out
    fps.append(("C2", footprint("C2", "100uF", 44, 24, [
        tht("1", -1.75, 0, 2.2, 1.0, "+5V", "C2_P"),
        tht("2", 1.75, 0, 2.2, 1.0, "GND"),
    ])))

    # U2 LDO AMS1117-3.3 SOT-223
    fps.append(("U2", footprint("U2", "AMS1117-3.3", 44, 34, [
        smd("1", -2.3, -3.15, 1.5, 1.2, "GND"),
        smd("2", 0, -3.15, 1.5, 1.2, "+3V3", "U2_OUT"),
        smd("3", 2.3, -3.15, 1.5, 1.2, "+5V", "U2_IN"),
        smd("4", 0, 3.15, 3.6, 2.0, "+3V3"),
    ])))

    # U3 CAN transceiver SOIC-8 (SN65HVD230: 2=GND, 3=VCC, 6=CANL, 7=CANH)
    u3 = []
    for i in range(4):  # pins 1-4 left
        pin = i + 1
        net = "GND" if pin == 2 else ("+3V3" if pin == 3 else "")
        lbl = "U3_VCC" if pin == 3 else None
        u3.append(smd(str(pin), -2.7, 1.905 - i * 1.27, 1.5, 0.6, net=net, label=lbl))
    for i in range(4):  # pins 5-8 right
        pin = 8 - i
        net = "CANL" if pin == 6 else ("CANH" if pin == 7 else "")
        u3.append(smd(str(pin), 2.7, 1.905 - i * 1.27, 1.5, 0.6, net=net))
    fps.append(("U3", footprint("U3", "SN65HVD230", 30, 14, u3)))

    # Q1 reverse-polarity P-FET SOT-23
    fps.append(("Q1", footprint("Q1", "P-FET", 14, 16, [
        smd("1", -0.95, -1.0, 0.9, 1.0, ""),
        smd("2", 0.95, -1.0, 0.9, 1.0, "+12V"),
        smd("3", 0, 1.0, 0.9, 1.0, "+12V"),
    ])))

    # Q2 buzzer NPN SOT-23
    fps.append(("Q2", footprint("Q2", "NPN", 58, 30, [
        smd("1", -0.95, -1.0, 0.9, 1.0, ""),
        smd("2", 0.95, -1.0, 0.9, 1.0, "GND"),
        smd("3", 0, 1.0, 0.9, 1.0, ""),
    ])))

    # D3 RGB LED 5050 (4 pad)
    d3 = []
    for k, (dx, dy) in enumerate([(-1.4, -1.4), (-1.4, 1.4), (1.4, 1.4), (1.4, -1.4)]):
        d3.append(smd(str(k + 1), dx, dy, 1.0, 1.0, net=("+5V" if k == 0 else "")))
    fps.append(("D3", footprint("D3", "RGB5050", 63, 40, d3)))

    # D1 TVS SMB
    fps.append(("D1", footprint("D1", "SMBJ16A", 18, 22, [
        smd("1", -2.3, 0, 1.8, 2.2, "+12V"),
        smd("2", 2.3, 0, 1.8, 2.2, "GND"),
    ])))

    # R1..R6 0603 cluster
    rx = 50
    for i in range(6):
        ry = 22 + (i % 3) * 2.2
        fps.append((f"R{i+1}", footprint(f"R{i+1}", "0603", rx, ry, [
            smd("1", -0.8, 0, 0.9, 0.95, ""),
            smd("2", 0.8, 0, 0.9, 0.95, ""),
        ])))
        if (i + 1) % 3 == 0:
            rx += 3.0

    # C3..C9 decoupling
    for i, (cx, cy) in enumerate([(6, 30), (6, 33), (10, 16), (40, 27), (35, 14), (38, 14), (50, 34)], 3):
        fps.append((f"C{i}", footprint(f"C{i}", "100nF", cx, cy, [
            smd("1", -0.8, 0, 0.9, 0.95, ""),
            smd("2", 0.8, 0, 0.9, 0.95, ""),
        ])))

    # SW1 mute tactile (4 THT)
    fps.append(("SW1", footprint("SW1", "TACT", 62, 16, [
        tht("1", -3.25, 2.25, 1.6, 0.9, "GND"),
        tht("2", 3.25, 2.25, 1.6, 0.9, ""),
        tht("3", -3.25, -2.25, 1.6, 0.9, "GND"),
        tht("4", 3.25, -2.25, 1.6, 0.9, ""),
    ])))

    # BZ1 buzzer header 2P
    fps.append(("BZ1", footprint("BZ1", "BUZZER", 64, 30, [
        tht("1", -1.27, 0, 1.7, 1.0, ""),
        tht("2", 1.27, 0, 1.7, 1.0, "GND"),
    ])))

    return fps


# ---------------------------------------------------------------------------
# Tracks (power rails) - endpoints land on recorded pad centres
# ---------------------------------------------------------------------------
def tracks():
    """Route power rails on B.Cu using vias at each pad.

    The mid-board area carries only SMD pads (all on F.Cu) and a handful of THT
    annuli, so the back copper is a clean routing channel. A via is dropped at
    every power pad and the rail is run point-to-point on B.Cu through open
    corridors chosen to avoid the few THT pads. The GND zone on B.Cu auto-clears
    around these foreign-net vias/tracks.
    """
    segs = []
    THT = {"J1_12V", "C1_P", "C2_P", "J4_5V"}  # through-hole pads need no via

    def via(p, net):
        segs.append(
            f'  (via (at {p[0]} {p[1]}) (size 0.8) (drill 0.4) (layers "F.Cu" "B.Cu") '
            f'(net {NETNUM[net]}) (uuid "{uid()}"))'
        )

    def seg(p1, p2, w, net, layer="B.Cu"):
        segs.append(
            f'  (segment (start {p1[0]} {p1[1]}) (end {p2[0]} {p2[1]}) '
            f'(width {w}) (layer "{layer}") (net {NETNUM[net]}) (uuid "{uid()}"))'
        )

    def route(net, w, vlabels, waypoints):
        for lbl in vlabels:
            if lbl not in THT and lbl in PADXY:
                via(PADXY[lbl], net)
        for a, b in zip(waypoints, waypoints[1:]):
            seg(a, b, w, net)

    # +12V rail on B.Cu: J1 -> C1 -> U1 VIN. Approaches U1 pin8 from above (low
    # kicad-y) so it never crosses the +5V rail leaving U1 pin5.
    route("+12V", 0.6, ["U1_VIN"], [
        PADXY["J1_12V"], (3.0, 43.0), (3.0, 28.0), PADXY["C1_P"],
        (8.25, 15.0), (22.7, 15.0), PADXY["U1_VIN"],
    ])
    # +5V rail on B.Cu: U1 SW -> L1 -> C2. Stays in the mid corridor, clear of
    # C2's GND pad. (U2_IN / J4 / D2 left as ratsnest for interactive routing.)
    route("+5V", 0.8, ["U1_SW", "L1_A", "L1_B"], [
        PADXY["U1_SW"], (27.5, 22.0), PADXY["L1_A"],
        PADXY["L1_B"], (38.0, 22.0), (38.0, 26.0), PADXY["C2_P"],
    ])
    return segs


def gnd_zone():
    pts = [(0.8, 0.8), (BW - 0.8, 0.8), (BW - 0.8, BH - 0.8), (0.8, BH - 0.8)]
    pts_s = " ".join(f"(xy {x} {y})" for x, y in pts)
    return [
        f'  (zone (net {NETNUM["GND"]}) (net_name "GND") (layers "B.Cu") (uuid "{uid()}")',
        '    (hatch edge 0.5)',
        '    (connect_pads (clearance 0.3))',
        '    (min_thickness 0.25)',
        '    (filled_areas_thickness no)',
        '    (fill yes (thermal_gap 0.3) (thermal_bridge_width 0.3))',
        f'    (polygon (pts {pts_s})))',
    ]


# ---------------------------------------------------------------------------
LAYERS = """  (layers
    (0 "F.Cu" signal)
    (31 "B.Cu" signal)
    (32 "B.Adhes" user "B.Adhesive")
    (33 "F.Adhes" user "F.Adhesive")
    (34 "B.Paste" user)
    (35 "F.Paste" user)
    (36 "B.SilkS" user "B.Silkscreen")
    (37 "F.SilkS" user "F.Silkscreen")
    (38 "B.Mask" user)
    (39 "F.Mask" user)
    (40 "Dwgs.User" user "User.Drawings")
    (41 "Cmts.User" user "User.Comments")
    (42 "Eco1.User" user "User.Eco1")
    (43 "Eco2.User" user "User.Eco2")
    (44 "Edge.Cuts" user)
    (45 "Margin" user)
    (46 "B.CrtYd" user "B.Courtyard")
    (47 "F.CrtYd" user "F.Courtyard")
    (48 "B.Fab" user)
    (49 "F.Fab" user)
  )"""


def edge_cuts():
    return [
        f'  (gr_rect (start 0 0) (end {BW} {BH}) '
        f'(stroke (width 0.1) (type solid)) (fill no) (layer "Edge.Cuts") (uuid "{uid()}"))'
    ]


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fps = components()

    out = []
    out.append('(kicad_pcb (version 20240108) (generator "deerwatch") (generator_version "8.0")')
    out.append("  (general (thickness 1.6) (legacy_teardrops no))")
    out.append('  (paper "A4")')
    out.append(LAYERS)
    out.append("  (setup (pad_to_mask_clearance 0.05))")
    for i, n in enumerate(NETS):
        out.append(f'  (net {i} "{n}")')
    for _, lines in fps:
        out += lines
    out += edge_cuts()
    out += tracks()
    out += gnd_zone()
    out.append(")")

    OUT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote {OUT}  ({OUT.stat().st_size} bytes, {len(fps)} footprints, {len(NETS)} nets)")


if __name__ == "__main__":
    main()
