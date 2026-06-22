# DeerWatch carrier - KiCad project

This folder holds the **KiCad** version of the carrier board, generated from the
same layout as the Python Gerber generator but as a real, editable `.kicad_pcb`
so it can be routed and design-rule-checked with KiCad's own engine.

## Files

| File | What it is |
|------|------------|
| `DeerWatch-Carrier.kicad_pcb` | Board: 70x50 mm, 34 footprints, 7 nets, edge cuts, GND pour |
| `DeerWatch-Carrier.kicad_pro` | Project (DRC severity overrides) |
| `../gen_kicad.py` | Generator that emits the `.kicad_pcb` |
| `kicad_gerbers/` | Gerbers + Excellon drill exported **by KiCad** (authoritative) |
| `DeerWatch-Carrier-KiCad-gerbers.zip` | JLCPCB-ready bundle of the above |
| `board_top.png` | KiCad 3D render (top) |
| `board_top.svg` | 2D plot (F.Cu / B.Cu / silk / edge / fab) |
| `drc.json` | Latest DRC report |

## How it was made / how to reproduce

```bash
# 1. (re)generate the board from the layout script
python hardware/pcb/carrier_board/gen_kicad.py

# 2. design-rule check (uses the .kicad_pro severities)
kicad-cli pcb drc  DeerWatch-Carrier.kicad_pcb

# 3. export manufacturing data
kicad-cli pcb export gerbers -o kicad_gerbers --no-protel-ext DeerWatch-Carrier.kicad_pcb
kicad-cli pcb export drill   -o kicad_gerbers --format excellon DeerWatch-Carrier.kicad_pcb

# 4. previews
kicad-cli pcb render --side top -o board_top.png DeerWatch-Carrier.kicad_pcb
```

Built and verified against **KiCad 10.0.3**.

## DRC status

```
Found 0 violations
Found 37 unconnected items
```

* **0 violations** - no clearance, shorting, track-crossing, edge-clearance,
  solder-mask-bridge or co-located-hole errors. Footprint-library cross-check
  notices (`lib_footprint_issues`) are set to *ignore* in the project because
  every footprint is a self-contained inline footprint (not pulled from a
  managed KiCad library), so there is nothing to cross-check against.
* **37 unconnected items** - this is the remaining **ratsnest**. What is already
  routed:
  * **GND** - fully connected through the poured `B.Cu` ground zone.
  * **+12V** - J1 -> C1 -> U1 (VIN) routed on `B.Cu`.
  * **+5V** - U1 (SW) -> L1 -> C2 routed on `B.Cu`.

  The ratsnest left for interactive routing is the signal + remaining power
  fan-out: CAN (CANH/CANL), the Raspberry-Pi GPIO pins, +3V3 (U2 -> U3 and Pi),
  the buzzer/LED/button IO, and the +5V taps to U2/J4/D2. These are short,
  low-speed nets - finish them in the KiCad PCB editor (route + "Edit > Fill all
  zones") and re-run DRC before fabricating.

## Why two Gerber paths exist

* `../gerbers*/` - produced directly by `gen_gerbers.py` (fast, dependency-free,
  also drives the AWR1843 variant). Good for a quick JLCPCB upload of the
  power/IO carrier.
* `kicad_gerbers/` - produced by **KiCad** from the DRC'd board. This is the
  authoritative set for the production 60 GHz carrier once interactive routing
  is finished.
