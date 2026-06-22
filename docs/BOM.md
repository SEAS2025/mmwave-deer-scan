# Bill of Materials & Cost

Prices are approximate, USD, mid-2026, single-unit unless noted. Links go to the
manufacturer or an authorized distributor. Verify live price/stock before ordering.

Machine-readable version: [`bom.csv`](bom.csv).

---

## A. System-level BOM (prototype, qty 1)

| # | Item | Mfr / Part | Qty | Unit $ | Ext $ | Link |
|---|------|------------|-----|--------|-------|------|
| 1 | mmWave radar EVM (60 GHz AoP) | TI IWR6843AOPEVM | 1 | 174 | 174 | https://www.ti.com/tool/IWR6843AOPEVM |
| 2 | Compute | Raspberry Pi 5 (4 GB) | 1 | 110 | 110 | https://www.raspberrypi.com/products/raspberry-pi-5/ |
| 3 | Active cooler | RPi Active Cooler | 1 | 5 | 5 | https://www.raspberrypi.com/products/active-cooler/ |
| 4 | microSD (64 GB A2) | SanDisk Extreme | 1 | 10 | 10 | https://www.sandisk.com/ |
| 5 | Carrier PCB + parts (this repo) | DeerWatch carrier rev A | 1 | 35 | 35 | `hardware/pcb/carrier_board/` |
| 6 | Enclosure IP65 PC | Hammond 1554F2GY (160x90x60) | 1 | 22 | 22 | https://www.hammfg.com/part/1554F2GY |
| 7 | Mount bracket | Generic L-bracket / RAM mount | 1 | 12 | 12 | https://www.rammount.com/ |
| 8 | 12 V fuse tap harness | Add-a-circuit + 3 A blade | 1 | 9 | 9 | https://www.amazon.com/s?k=add+a+circuit+fuse+tap |
| 9 | USB-A to micro-USB (radar data) | generic | 1 | 5 | 5 | https://www.amazon.com/ |
| 10 | Piezo buzzer 12 mm | CUI CEM-1203(42) | 1 | 2 | 2 | https://www.cui.com/product/audio/buzzers |
| 11 | GPS module (optional, geo-log) | u-blox NEO-M9N (SparkFun) | 1 | 40 | 40 | https://www.sparkfun.com/products/15712 |
| 12 | Bench PSU 27 W USB-C (dev only) | RPi 27W USB-C | 1 | 12 | 12 | https://www.raspberrypi.com/products/27w-power-supply/ |
|   | **Prototype subtotal** | | | | **~$436** | (without GPS/bench PSU: ~$384) |

> 77 GHz long-range variant: swap item 1 for **AWR1843BOOST** ($299,
> https://www.ti.com/tool/AWR1843BOOST). Prototype subtotal becomes ~$561.

---

## B. Carrier PCB component BOM (DeerWatch carrier rev A)

These populate the custom 2-layer board whose Gerbers are in
`hardware/pcb/carrier_board/gerbers/`. JLCPCB part numbers (LCSC) given where useful for
assembly service.

| Ref | Value / Part | Pkg | Qty | Unit $ | Ext $ | LCSC / Link |
|-----|--------------|-----|-----|--------|-------|-------------|
| PCB | 2-layer FR4 1.6 mm, HASL, 70x50 mm | - | 1 | 2.00 | 2.00 | JLCPCB upload |
| U1 | TPS5450DDA buck 5 V/5 A | SO-8 PowerPAD | 1 | 3.80 | 3.80 | https://www.ti.com/product/TPS5450 |
| U2 | AMS1117-3.3 LDO | SOT-223 | 1 | 0.20 | 0.20 | LCSC C6186 |
| U3 | SN65HVD230 CAN xcvr | SOIC-8 | 1 | 1.40 | 1.40 | https://www.ti.com/product/SN65HVD230 |
| Q1 | P-MOSFET reverse-polarity (e.g. SI2301) | SOT-23 | 1 | 0.10 | 0.10 | LCSC C10487 |
| Q2 | NPN buzzer driver (MMBT2222A) | SOT-23 | 1 | 0.05 | 0.05 | LCSC C8326 |
| D1 | TVS SMBJ16A | SMB | 1 | 0.25 | 0.25 | LCSC C77471 |
| D2 | Schottky SS34 (buck) | SMA | 1 | 0.08 | 0.08 | LCSC C8678 |
| L1 | 33 uH 5 A power inductor | SMD | 1 | 0.45 | 0.45 | LCSC C408412 |
| D3 | RGB status LED (common cathode) | 5050 | 1 | 0.12 | 0.12 | LCSC C2890 |
| C1 | 100 uF 50 V electrolytic (bulk in) | radial | 1 | 0.20 | 0.20 | LCSC C3015 |
| C2 | 100 uF 16 V (out bulk) | radial | 1 | 0.15 | 0.15 | LCSC C2686 |
| C3-6 | 10 uF 25 V X5R | 0805 | 4 | 0.03 | 0.12 | LCSC C15850 |
| C7-9 | 100 nF 50 V X7R | 0603 | 3 | 0.01 | 0.03 | LCSC C14663 |
| R1-3 | LED resistors 330 ohm | 0603 | 3 | 0.01 | 0.03 | LCSC C23138 |
| R4-6 | misc 10k / 1k / 120 (CAN term) | 0603 | 3 | 0.01 | 0.03 | LCSC C25804 |
| J1 | Screw terminal 2P 5.08 mm (12 V in) | THT | 1 | 0.30 | 0.30 | LCSC C8269 |
| J2 | Screw terminal 3P (CAN H/L/GND) | THT | 1 | 0.40 | 0.40 | LCSC C8270 |
| J3 | 2x20 socket header (Pi GPIO) | THT 2.54 | 1 | 0.55 | 0.55 | LCSC C2337 |
| J4 | USB-A or 4P header (radar) | THT | 1 | 0.30 | 0.30 | LCSC C319152 |
| SW1 | Tactile button (MUTE) | THT 6 mm | 1 | 0.05 | 0.05 | LCSC C318884 |
| BZ1 | Buzzer header 2P | THT | 1 | 0.05 | 0.05 | LCSC C7501 |
|     | **Carrier components subtotal** | | | | **~$11.4** | + PCB fab/assembly |

**Carrier board cost realized:**
- Prototype (qty 5 PCBs from JLCPCB, hand-assembled): ~$2 fab + ~$15 parts/board + ship -> budget **$35/board** (item A5).
- Qty 100 with JLCPCB SMT assembly: ~$8-12/board all-in.

---

## C. Cost roll-up

| Build | Radar | Compute | Carrier+misc | Enclosure/mount | Total/unit |
|-------|-------|---------|--------------|-----------------|-----------|
| Prototype qty 1 (60 GHz) | 174 | 125 | ~50 | ~45 | **~$394-436** |
| Small batch qty 25 (60 GHz) | ~165 | ~115 | ~25 | ~30 | **~$335** |
| Production qty 1000 (chip-down 60 GHz) | ~45* | ~55** | ~15 | ~25 | **~$140 target** |

\* Production replaces the EVM with a chip-down IWR6843AOP design (the radar IC is
~$15-25 at volume; the rest is the antenna-on-package layout + assembly).
\** Production may use a Compute Module 5 or an i.MX8 SoM instead of a full Pi.

> Production figures are **planning targets**, contingent on a chip-down RF redesign that
> is explicitly out of scope for the prototype carrier Gerbers in this repo.

---

## D. Where to buy (authorized)

- TI EVMs: https://www.ti.com/ (or Mouser/DigiKey)
- Raspberry Pi: https://www.raspberrypi.com/resellers/ , stock: https://rpilocator.com
- Passives/connectors/ICs: https://www.lcsc.com (JLCPCB assembly), https://www.digikey.com , https://www.mouser.com
- PCB fab/assembly: https://jlcpcb.com
- Enclosures: https://www.hammfg.com
