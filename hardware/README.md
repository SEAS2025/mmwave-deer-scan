# DeerWatch mmWave - Hardware

Hardware design for the roadside / vehicle deer early-warning unit. Full rationale in
[`../docs/SYSTEM_DESIGN.md`](../docs/SYSTEM_DESIGN.md).

## Contents

```
hardware/
  enclosure/
    gen_orthographic.py     # generates the dimensioned 3-view drawing
    orthographic.svg        # FRONT / TOP / RIGHT-SIDE with measurements (mm)
    orthographic_preview.png
    svg_to_png.py           # pure-Pillow SVG rasterizer (no cairo needed)
  pcb/
    carrier_board/
      gen_gerbers.py        # generates the full RS-274X + Excellon package
      gerbers/              # the 8 fab files
      DeerWatch-Carrier-gerbers.zip   # <- upload this to JLCPCB
      carrier_preview.png   # rendered board preview
      FAB_NOTES.md          # JLCPCB order settings + caveats
```

## Engineering drawing

Third-angle orthographic, all dims in mm. Enclosure envelope 160 x 90 x 60 mm,
RF radome window 80 x 50 mm, 5 deg boresight down-tilt.

```
python hardware/enclosure/gen_orthographic.py            # -> orthographic.svg
python hardware/enclosure/svg_to_png.py                  # -> orthographic_preview.png
```

Open `orthographic.svg` in any browser, Inkscape, or import to CAD.

## Carrier PCB

2-layer FR4, 70 x 50 mm. Power (12 V -> 5 V/5 A buck + 3V3 LDO), protection (fuse +
reverse-polarity FET + TVS), alert outputs (buzzer driver, RGB LED, MUTE), optional CAN,
and the Raspberry Pi 2x20 + radar headers.

```
python hardware/pcb/carrier_board/gen_gerbers.py
```

Validated to parse cleanly with `gerbonara`. See
[`pcb/carrier_board/FAB_NOTES.md`](pcb/carrier_board/FAB_NOTES.md) for JLCPCB upload.

> The 60/77 GHz RF front end is a certified COTS module (TI IWR6843AOPEVM), not a custom
> RF board. The carrier handles everything below RF.

## Bill of materials

See [`../docs/BOM.md`](../docs/BOM.md) (+ [`../docs/bom.csv`](../docs/bom.csv)) for the full
parts list, links, and cost roll-up (prototype ~$400, production target ~$140).
