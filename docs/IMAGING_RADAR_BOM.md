# Imaging-radar bill of materials (R&D track)

Hardware to go beyond the point cloud toward micro-Doppler signatures and ISAR /
3D imaging of a deer. See the `radar-3d-imaging-requirements` canvas for the
resolution rationale and `mmwave_deer/imaging/` for the processing skeleton.

The jump from "detection" to "imaging" is mostly about **(a) capturing raw ADC**
instead of the SDK point cloud, and **(b) a much larger virtual array** for
cross-range resolution. There are three cost tiers.

---

## Tier 0 — Raw-capture upgrade to the existing single chip (cheapest)

Unlocks micro-Doppler + single-chip ISAR with the radar you already plan to use.
12 virtual channels (coarse angle), but full raw ADC.

| Item | Part | Qty | Est. unit | Notes |
|------|------|-----|-----------|-------|
| Radar EVM | TI AWR1843BOOST (or IWR6843ISK) | 1 | $299 | already in the baseline BOM |
| Raw ADC capture | TI DCA1000EVM | 1 | $599 | LVDS raw-ADC capture over Ethernet |
| Capture host | laptop/mini-PC (Ethernet, 16 GB) | 1 | $700 | runs mmWave Studio + offline processing |
| Cabling / 5 V supply | misc | 1 | $60 | |
| **Tier 0 total** | | | **~$1,650** | micro-Doppler now; ISAR is single-aperture only |

Software: TI **mmWave Studio** (free) for capture + calibration; process with
`mmwave_deer/imaging/` or OpenRadar.

---

## Tier 1 — Cascaded MIMO imaging radar (the real "imaging" tier)

TI's 4-chip AWR2243 cascade: **12 TX × 16 RX → up to 192 virtual channels**
(~86 effective azimuth), ~1.4° azimuth resolution, 2-D (az + el) array. This is
the reference design **TIDEP-01012**.

| Item | Part | Qty | Est. unit | Notes |
|------|------|-----|-----------|-------|
| Cascade RF board | TI MMWCAS-RF-EVM (4× AWR2243) | 1 | $2,500 | the imaging array |
| Capture / processing board | TI MMWCAS-DSP-EVM (TDA2) | 1 | $1,800 | raw capture + first-stage DSP |
| GPU workstation | Ryzen/i7 + RTX 4070 Ti+ (32 GB RAM) | 1 | $2,200 | beamforming / super-res / ML |
| Bench PSU | 12 V / 5 A+ regulated | 1 | $120 | |
| Tripod + pan/tilt mount | aluminium | 1 | $150 | for SAR sweeps / aiming |
| Cabling, SD, misc | | 1 | $130 | |
| **Tier 1 total** | | | **~$6,900** | dense 4D cube; ISAR + super-resolution feasible |

Software: mmWave Studio (cascade capture + array calibration — **mandatory**,
phase coherence across the 4 chips), then GPU processing (CUDA FFT/beamforming,
PyTorch for any ML reconstruction).

---

## Tier 2 — Commercial 4D imaging radar (turnkey, highest resolution)

Automotive "4D imaging" radars output a dense range/azimuth/elevation/Doppler
cloud approaching a low-res image. Pricing is sales-channel / NDA and these are
integration-heavy.

| Vendor | Product | Virtual ch. | Azimuth res. | Notes |
|--------|---------|-------------|--------------|-------|
| Arbe | Phoenix | ~2304 | ~1° | highest channel count; dev kit via sales |
| Uhnder | digital-code radar | high | ~1° | CDMA MIMO, good interference immunity |
| Continental / ZF | ARS540 / premium 4D | — | ~1° | automotive tier-1 |

Budget: dev kits typically **$5k–$25k+** plus integration; engage vendor sales.

---

## Compute & data summary (all tiers)

| Need | Tier 0 | Tier 1 | Tier 2 |
|------|--------|--------|--------|
| Raw ADC capture | DCA1000 | MMWCAS-DSP / FPGA | vendor SDK |
| First-stage FFTs | CPU (offline) | FPGA + GPU | on-module |
| Angle super-res / ML | CPU/GPU offline | GPU (CUDA) | host GPU |
| Real-time imaging | no (offline) | hard (GPU) | yes |
| Training data | — | K-Radar / RADIal / Coloradar | same |

## Recommendation

- For **DeerWatch's actual goal** (early warning + species ID), Tier 0 plus the
  micro-Doppler + ML classifier in `mmwave_deer/imaging/` is enough — and far
  cheaper than imaging.
- Pursue **Tier 1** only as a research track if a true 3-D radar image of a deer
  is a hard requirement; expect significant calibration, compute, and offline
  reconstruction effort.

> Prices are rough public estimates (TI store / typical retail) for planning, not
> quotes. Confirm current pricing and lead times before purchasing.
