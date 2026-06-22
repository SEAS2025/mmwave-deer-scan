# DeerWatch 77 GHz variant - AWR1843BOOST

The baseline DeerWatch build uses the 60 GHz **IWR6843AOPEVM** (wide field of
view, antenna-on-package, lowest cost). This document describes the **77 GHz
AWR1843BOOST** variant for highway-speed / long-range roadside deployment.

## 1. When to choose which

| | IWR6843AOPEVM (60 GHz) | AWR1843BOOST (77 GHz) |
|---|---|---|
| Band | 60-64 GHz | 76-81 GHz |
| Practical deer range | ~50 m | ~105-150 m |
| Field of view | ~120 x 120 deg (AoP) | ~100 x 40 deg (etched array) |
| Antenna | on-package | PCB array |
| Best for | rural / low-speed roads, wide coverage | highways, long warning distance |
| EVM cost | ~$174 | ~$299 |

Use 60 GHz where coverage angle matters (curvy, low-speed roads). Use 77 GHz
where **warning distance** matters: at 100 km/h a vehicle covers ~28 m/s, so the
extra ~55-100 m of range buys 2-3 s more reaction time.

## 2. Range math (firmware/awr1843_deer.cfg)

The 77 GHz profile trades range resolution for reach:

```
profileCfg 0 77 7 6 60 0 0 7 1 256 5000 0 0 30
            |        |     |        |   |
            startFreq=77 GHz        |   sampleRate=5000 ksps
                     freqSlope=7 MHz/us
                                ADC samples=256
```

* Max range  `Rmax = Fs * c / (2 * slope) = 5e6 * 3e8 / (2 * 7e12) ~= 107 m`
* Range res  `dR   = c / (2 * B_adc)`, `B_adc = slope * (N / Fs) ~= 358 MHz` -> `dR ~= 0.42 m`
* Wavelength `lambda = c / 78.5e9 ~= 3.8 mm` (vs 5.0 mm at 60 GHz) -> finer Doppler

Compared with the 60 GHz profile (`~0.05 m` res, `~50 m` range) the 77 GHz
profile is coarser per-bin but reaches roughly twice as far - the right trade
for a fast road where you want the earliest possible callout. Tune in the TI
mmWave Demo Visualizer before field use.

## 3. Software

No code changes are required - the AWR1843 streams the same detected-point JSON
over its data UART as the IWR6843, so the existing `ti` reader works. Use the
variant config, which relaxes the cluster epsilon for the coarser bins and
widens the road bounds:

```bash
# flash the 77 GHz chirp profile to the EVM CLI UART
python deploy/send_cfg.py --port COM5 --cfg firmware/awr1843_deer.cfg --baud 115200

# run the scanner against the data UART (921600) with the 77 GHz config
python scripts/live_scanner.py --config config/awr1843.yaml
```

`mmwave_deer/profile.py` already allows targets out to `max_range_m = 120`, so
the long-range returns are scored normally.

## 4. Carrier PCB delta

The AWR1843BOOST is a BoosterPack-form-factor board (vs the AoP module), so the
carrier exposes a BoosterPack-style power/IO header instead of the 4-pin radar
header. Everything else (buck, LDO, CAN, alert IO, Pi 2x20) is unchanged.

Generate the variant Gerbers:

```bash
python hardware/pcb/carrier_board/gen_gerbers.py --variant awr1843
# -> hardware/pcb/carrier_board/gerbers_awr1843/
#    hardware/pcb/carrier_board/DeerWatch-CarrierHD-gerbers.zip
#    hardware/pcb/carrier_board/carrier_preview_awr1843.png
```

| | 60 GHz carrier | 77 GHz carrier (HD) |
|---|---|---|
| Board | `DeerWatch-Carrier` 70x50 | `DeerWatch-CarrierHD` 70x50 |
| Radar connector | 4-pin power/UART header (J4) | 1x10 BoosterPack power/IO header (J4) |
| Silk title | `DEERWATCH CARRIER REV A` | `DEERWATCH CARRIER-HD 77GHZ` |

Data still flows over USB (XDS110) to the Pi; the header carries 5V power and
the BoosterPack IO subset. Mount the EVM on external standoffs.

## 5. BOM delta (vs baseline)

| Item | Baseline | 77 GHz variant | Delta |
|------|----------|----------------|-------|
| Radar EVM | IWR6843AOPEVM ~$174 | AWR1843BOOST ~$299 | **+$125** |
| Radome | thin ABS / PC, RF-transparent | same (verify low loss at 77 GHz) | ~$0 |
| Carrier PCB | `DeerWatch-Carrier` | `DeerWatch-CarrierHD` | ~$0 (same 2-layer) |
| Everything else | - | unchanged | $0 |

Net build-cost increase is the EVM price difference (~$125). Confirm the radome
material has acceptable insertion loss at 77-81 GHz (thin polycarbonate/ABS is
usually fine; avoid filled or thick plastics).
