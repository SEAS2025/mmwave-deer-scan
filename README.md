# mmWave Deer Scan

Roadside **mmWave radar** deer detection for ambulance / fleet safety — companion to [agm-taipan-deer-scan](https://github.com/SEAS2025/agm-taipan-deer-scan) (thermal).

Detect deer from FMCW point clouds using size, speed, and SNR heuristics. Designed for **TI mmWave** UART JSON output and a **simulated** feed for development without hardware.

## Features

- Point-cloud clustering on sparse mmWave returns
- Deer-shaped target scoring (length, height, lateral position, speed)
- EGPWS-style threat callouts (left / ahead / right + range tier)
- TI mmWave serial reader (JSON lines) + OpenRadar raw-ADC adapter
- Thermal fusion (confirm with agm-taipan-deer-scan) and Pi GPIO/CAN alert outputs
- Session recorder for labeled training data
- Simulated roadside scene for offline development
- **Full hardware design**: system architecture, BOM, integration diagrams,
  dimensioned enclosure drawing, and a JLCPCB-ready carrier-board Gerber package
- **Imaging R&D track**: micro-Doppler + ISAR processing skeleton on raw ADC
  (`mmwave_deer/imaging/`), with a synthetic walking-deer demo

## Documentation & design

| Doc | What |
|-----|------|
| [docs/SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md) | architecture, sensor/compute/power, requirements, risks |
| [docs/BOM.md](docs/BOM.md) / [docs/bom.csv](docs/bom.csv) | parts, links, cost roll-up (proto ~$400, prod target ~$140) |
| [docs/INTEGRATION.md](docs/INTEGRATION.md) | block diagram, power tree, GPIO map, wiring, sequence |
| [hardware/README.md](hardware/README.md) | enclosure drawing + carrier PCB |
| [hardware/enclosure/orthographic.svg](hardware/enclosure/orthographic.svg) | dimensioned 3-view drawing |
| [hardware/pcb/carrier_board/](hardware/pcb/carrier_board/) | Gerbers + `DeerWatch-Carrier-gerbers.zip` for JLCPCB |
| [hardware/pcb/carrier_board/kicad/](hardware/pcb/carrier_board/kicad/) | KiCad 10 project, DRC-clean, KiCad-exported Gerbers + 3D render |
| [docs/VARIANT_AWR1843.md](docs/VARIANT_AWR1843.md) | 77 GHz AWR1843BOOST variant - range math, config, carrier + BOM delta |
| [docs/IMAGING_RADAR_BOM.md](docs/IMAGING_RADAR_BOM.md) | imaging-radar tiers (raw capture / AWR2243 cascade / 4D) - parts + compute |

## Quick start

```powershell
cd mmwave-deer-scan
pip install -r requirements.txt
python scripts/live_scanner.py --demo
```

Or double-click `launch_scanner.bat`.

## Hardware

Primary target: **Texas Instruments mmWave EVM** (IWR6843 / AWR1843) with point-cloud UART JSON output.

1. Connect USB-UART (typically COM3 on Windows)
2. Edit `config/default.yaml` — set `reader.type: ti_mmwave` and `reader.port`
3. Run: `python scripts/live_scanner.py --reader ti_mmwave --port COM3`

On the Raspberry Pi with the carrier board (buzzer/LED + thermal fusion):

```bash
python scripts/live_scanner.py --reader ti_mmwave --port /dev/ttyACM0 --outputs --fusion confirm
```

## Record sessions

```powershell
python scripts/record_session.py --reader ti_mmwave --port COM3 --seconds 120
```

## Imaging (experimental)

Micro-Doppler signature + ISAR image formation from raw ADC. Runs on synthetic
data; feed a captured cube (DCA1000 / cascade) for real targets. See
[docs/IMAGING_RADAR_BOM.md](docs/IMAGING_RADAR_BOM.md).

```powershell
python scripts/microdoppler_demo.py --out samples
```

## Tests

```powershell
pytest tests/
```

## Related

- Thermal deer scan: https://github.com/SEAS2025/agm-taipan-deer-scan
