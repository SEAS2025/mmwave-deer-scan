# DeerWatch Carrier - Fabrication Notes (JLCPCB)

2-layer power + IO + alerting carrier for the DeerWatch mmWave unit. The 60/77 GHz RF is a
COTS module (IWR6843AOPEVM) - it is **not** on this board.

## Files (in `gerbers/`)

| File | Layer |
|------|-------|
| `DeerWatch-Carrier.GTL` | Top copper |
| `DeerWatch-Carrier.GBL` | Bottom copper (ground pour) |
| `DeerWatch-Carrier.GTS` | Top solder mask |
| `DeerWatch-Carrier.GBS` | Bottom solder mask |
| `DeerWatch-Carrier.GTO` | Top silkscreen |
| `DeerWatch-Carrier.GBO` | Bottom silkscreen |
| `DeerWatch-Carrier.GKO` | Board outline |
| `DeerWatch-Carrier.TXT` | Drill (Excellon 2, metric) |

Upload `DeerWatch-Carrier-gerbers.zip` directly to https://jlcpcb.com.
Format: RS-274X, units mm, coordinate format 4.6, absolute.

## Recommended JLCPCB order settings

| Option | Value |
|--------|-------|
| Layers | 2 |
| Dimensions | 70 x 50 mm |
| Thickness | 1.6 mm |
| Material | FR-4 |
| Surface finish | HASL (lead-free) or ENIG |
| Copper weight | 1 oz (35 um); 2 oz if >3 A continuous on 5 V rail |
| Min track/space | 0.15 mm (design uses >= 0.4 mm) |
| Min hole | 0.3 mm (design uses >= 1.0 mm) |
| Solder mask | green (any) |
| Silkscreen | white |

## Regenerate

```
python hardware/pcb/carrier_board/gen_gerbers.py
```

Produces all layers, the zip, and `carrier_preview.png`. Validated to parse cleanly with
`gerbonara` (RS-274X + Excellon).

## IMPORTANT before mass production

This package is **production-grade for mechanical, pads, drills, pour, mask, and
silkscreen**, and is correct to fabricate as a bare board. Net-level copper routing is
represented for the main power nets; before a production run you should:

1. Import the netlist into KiCad, complete + DRC the routing, and re-export.
2. Verify in the JLCPCB Gerber **online viewer** (preview every layer).
3. Confirm footprints against the exact LCSC parts in `docs/BOM.md`.
4. For >3 A continuous, widen the 5 V/GND copper or use 2 oz copper.
5. Add fiducials + panelization if using SMT assembly service.

## Assembly

- THT: J1/J2 screw terminals, J3 Pi 2x20 socket, J4 radar header, C1/C2 electrolytics,
  SW1, BZ1.
- SMD (top): U1 buck, U2 LDO, U3 CAN, Q1/Q2, D1/D2, L1, D3 RGB, R/C passives.
- Mounting: 4x M3 corner holes (3.2 mm), 4 mm inset.
