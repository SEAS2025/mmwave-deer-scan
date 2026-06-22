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

## Documentation & design

| Doc | What |
|-----|------|
| [docs/SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md) | architecture, sensor/compute/power, requirements, risks |
| [docs/BOM.md](docs/BOM.md) / [docs/bom.csv](docs/bom.csv) | parts, links, cost roll-up (proto ~$400, prod target ~$140) |
| [docs/INTEGRATION.md](docs/INTEGRATION.md) | block diagram, power tree, GPIO map, wiring, sequence |
| [hardware/README.md](hardware/README.md) | enclosure drawing + carrier PCB |
| [hardware/enclosure/orthographic.svg](hardware/enclosure/orthographic.svg) | dimensioned 3-view drawing |
| [hardware/pcb/carrier_board/](hardware/pcb/carrier_board/) | Gerbers + `DeerWatch-Carrier-gerbers.zip` for JLCPCB |

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

## Tests

```powershell
pytest tests/
```

## Related

- Thermal deer scan: https://github.com/SEAS2025/agm-taipan-deer-scan
