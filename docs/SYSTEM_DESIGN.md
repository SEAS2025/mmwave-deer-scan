# DeerWatch mmWave - System Design

Roadside / vehicle-mounted **mmWave radar deer early-warning system**. Companion to the
thermal project [agm-taipan-deer-scan](https://github.com/SEAS2025/agm-taipan-deer-scan):
radar gives all-weather, day/night range + velocity; thermal confirms and classifies.

> **Scope note on the custom PCB / Gerbers.** We deliberately do **not** hand-route the
> 60/77 GHz RF front end. At prototype stage the RF is a certified COTS module
> (TI IWR6843AOPEVM / AWR1843BOOST). The custom board in this repo is the **carrier /
> power-and-IO board** that the radar module + Raspberry Pi plug into. This is the correct
> engineering decision: RF antenna-on-package is pre-validated by TI, and we own the
> low-frequency power, protection, alerting, and vehicle-interface domain. The Gerbers
> produced here are for that 2-layer carrier board.

---

## 1. Requirements

| #  | Requirement | Target |
|----|-------------|--------|
| R1 | Detect deer-class target (RCS ~1-10 m^2, 0.4-1.5 m tall) | >= 50 m (60 GHz), >= 120 m (77 GHz) |
| R2 | Lateral coverage (single sensor) | >= +/-50 deg azimuth |
| R3 | Range resolution | <= 0.1 m |
| R4 | Velocity (closing/crossing) | +/- 25 m/s, <= 0.3 m/s resolution |
| R5 | Decision latency (detect -> alert) | <= 250 ms |
| R6 | All-weather, day/night | rain/fog/dark tolerant |
| R7 | Vehicle power | 9-16 V automotive, load-dump tolerant |
| R8 | Operating temperature | -20 ... +60 C |
| R9 | Ingress protection | IP65 enclosure |
| R10| Alert outputs | audible + visual + (optional) vehicle bus |
| R11| False-positive rejection | discriminate deer vs vehicle/guardrail |

---

## 2. Architecture

```
                       +------------------------------------------+
   12V vehicle  -------+          DeerWatch unit (IP65)            |
   (fused tap)         |                                          |
                       |  +-----------+   USB (CDC/UART JSON)      |
                       |  | Carrier   |  +-------------------+     |
                       |  | PCB       |  | Radar module      |     |
                       |  | -TVS/fuse |  | IWR6843AOPEVM     |--+  |
                       |  | -rev-pol  |  | (60 GHz AoP)      |  |  |
                       |  | -5V/5A    |  +-------------------+  |  |
                       |  |  buck     |                         |  |
                       |  | -3V3 LDO  |  +-------------------+   |  |
                       |  | -buzzer   |  | Raspberry Pi 5    |<--+  |
                       |  | -RGB LED  |<-| (compute)         |      |
                       |  | -MUTE btn |GPIO mmwave_deer stack|      |
                       |  | -CAN xcvr |  +---------+---------+      |
                       |  +----+------+            | HDMI / Wi-Fi   |
                       +-------|-------------------|----------------+
                               |                   |
                        CAN to vehicle     Display / phone / thermal unit
```

### 2.1 Signal / data flow

```
RF chirps --> IWR6843 RF+DSP --> detected point cloud (x,y,z,vel,snr)
   UART/USB JSON --> Pi: reader --> cluster --> detector --> threat assess
                                                      |
              +----------------------------+----------+-----------+
              v                            v                      v
        alert outputs                 session log          thermal fusion
   (buzzer/voice/LED/CAN)           (.jsonl record)     (confirm w/ Taipan)
```

The host pipeline already exists in `mmwave_deer/`:
`readers -> processing/cluster -> detector -> alert`. This design adds the **hardware**
that carries it and the **fusion / output** layers.

---

## 3. Sensor selection

| Option | Band | Deer range* | FoV | Cost | Use |
|--------|------|-------------|-----|------|-----|
| **IWR6843AOPEVM** | 60-64 GHz | ~50 m | 120 x 120 deg | ~$174 | **Prototype baseline** - wide FoV, AoP, USB |
| IWR6843ISK | 60-64 GHz | ~80 m | narrower, higher gain | ~$199 | longer range, narrower beam |
| **AWR1843BOOST** | 76-81 GHz | ~120-150 m | ~100 deg | $299 | **Highway-speed variant** |

\* Approximate detection range for a deer-class RCS at typical roadside SNR; tune chirp
config for range vs. update rate.

**Decision:** Prototype on **IWR6843AOPEVM** (wide FoV, lowest cost, AoP eliminates RF
routing). Provide a config + carrier variant for **AWR1843BOOST** when highway range is
required - see [VARIANT_AWR1843.md](VARIANT_AWR1843.md) (firmware `awr1843_deer.cfg`,
config `config/awr1843.yaml`, carrier `gen_gerbers.py --variant awr1843`, ~+$125 BOM).

### 3.1 Radar chirp configuration (starting point, IWR6843)

| Param | Value | Note |
|-------|-------|------|
| Start freq | 60.25 GHz | band start |
| Bandwidth | 3.2 GHz | range res ~ c/(2*BW) ~ 4.7 cm |
| Frame rate | 10 Hz | meets R5 latency budget |
| Max unambiguous range | ~60 m | range-FFT / ADC sampling |
| Max velocity | +/-25 m/s | chirp repetition |
| TX/RX | 3 TX / 4 RX | azimuth + elevation |

Config is shipped as a `.cfg` profile sent to the EVM at boot (see `firmware/`).

---

## 4. Compute

**Raspberry Pi 5 (4 GB)** baseline; 8 GB for on-device ML (RadarNeXt / OpenRadar models).

| Why Pi 5 | |
|----------|---|
| USB 3.0 | radar data + optional thermal capture |
| 40-pin GPIO | buzzer, LED, MUTE, CAN HAT/transceiver |
| Wi-Fi/BLE | phone/display, OTA, fusion link to thermal unit |
| Linux | reuse `mmwave_deer` Python stack as-is |
| Production lifetime | guaranteed to >= Jan 2036 |

Alt for heavier ML: **NVIDIA Jetson Orin Nano** (drop-in compute swap, higher cost).

---

## 5. Power

Automotive 9-16 V (load-dump to 40 V transient) -> regulated 5 V/5 A for Pi + radar,
3.3 V for aux logic.

```
12V tap -> [Fuse 3A] -> [Reverse-polarity P-FET] -> [TVS SMBJ16A] -> [Bulk 100uF]
        -> Buck 5V/5A (TPS5450 / module) -> Pi 5V rail (5A) + radar 5V
        -> 3V3 LDO (from 5V) -> CAN xcvr, LED logic
```

Protection budget:
- **Fuse**: 3 A blade tap on the vehicle side.
- **Reverse polarity**: P-channel MOSFET (low-loss vs. diode).
- **Load dump / transient**: TVS diode (SMBJ16A) clamps to safe rail.
- **Inrush**: bulk capacitance + soft-start of buck.

The Pi 5 wants 5 V/5 A (PD); the carrier delivers it directly so no USB-C brick is needed
in-vehicle.

---

## 6. Alerting & I/O

| Output | Hardware | Behavior |
|--------|----------|----------|
| Audible | Piezo buzzer (GPIO via MOSFET) + Pi audio (voice) | EGPWS-style "Deer - LEFT 40 m"; tier escalation |
| Visual | RGB status LED | green=scan, amber=track, red=alert |
| Mute | Tactile button (GPIO) | toggle audio |
| Vehicle bus | CAN transceiver (SN65HVD230) | broadcast threat frame (optional) |
| Display | HDMI / phone over Wi-Fi | live point cloud + threats |
| Fusion | Wi-Fi/serial to thermal unit | confirm deer with Taipan thermal |

Voice callouts reuse the proven EGPWS style from the thermal project.

---

## 7. Detection / software stack

Already implemented (`mmwave_deer/`), extended by this design:

1. **reader** - `TiMmWaveReader` (UART JSON) / `SimulatedReader` / new `OpenRadarReader`.
2. **cluster** - density clustering of sparse returns.
3. **detector** - `MmWaveDeerDetector` heuristic (size/speed/SNR/lateral gating).
4. **alert** - tiered threat assessment + side-of-road callouts.
5. **fusion** *(new)* - gate radar detections against thermal confirmations.
6. **outputs** *(new)* - drive buzzer/LED/CAN from `gpiozero` on the Pi.

Upgrade path: swap the heuristic for an ML model (OpenRadar / RadarNeXt) trained on
recorded `.jsonl` sessions + RadarScenes (has an animal class).

---

## 8. Enclosure & mounting

- **IP65 polycarbonate** enclosure, ~160 x 100 x 60 mm.
- **Radome window**: thin (<= 2 mm) PC/ABS section in front of the AoP antenna - RF
  transparent at 60/77 GHz; no metal/labels in the beam.
- **Mount**: bull-bar / grille bracket or dash mount; radar boresight aligned to road,
  slight down-tilt to cut overhead clutter.
- See `hardware/enclosure/orthographic.svg` for the dimensioned 3-view drawing.

---

## 9. Bill of materials & cost

See [`docs/BOM.md`](BOM.md) and [`docs/bom.csv`](bom.csv). Summary:

| Build | Approx. cost / unit |
|-------|---------------------|
| **Prototype** (EVM + Pi + carrier PCB, qty 1) | ~**$400** |
| **Small batch** (qty 25, EVM-based) | ~**$330** |
| **Production** (qty 1000, chip-down radar) | ~**$140** (target) |

---

## 10. Risks & mitigations

| Risk | Mitigation |
|------|------------|
| Vehicle/guardrail false positives | velocity + size gating; ML classifier; thermal fusion |
| Rain/spray clutter | CFAR thresholds; track persistence (`confirm_frames`) |
| RF blocked by enclosure | RF-transparent radome window, no metal in beam |
| Load dump damages electronics | TVS + fuse + reverse-polarity FET |
| Pi thermal throttling | active cooler; 0-60 C automotive derating |
| 60 GHz range insufficient at highway speed | AWR1843 77 GHz variant |

---

## 11. Build / test phases

1. **Bench** - EVM + Pi on `default.yaml`, `--demo` then live UART; validate clustering.
2. **Carrier PCB bring-up** - power rails, protection, GPIO outputs (this repo's Gerbers).
3. **Field record** - `record_session.py`, label deer vs vehicle, build dataset.
4. **Model** - train classifier; A/B vs heuristic.
5. **Fusion** - integrate thermal confirmation.
6. **DV/PV** - temperature, vibration, EMC, IP65, vehicle EMC.
7. **Production** - chip-down radar + integrated board (post-prototype).
