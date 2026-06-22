# Integration Diagrams

Mermaid diagrams render on GitHub. Source-of-truth wiring for the prototype build.

---

## 1. System block diagram

```mermaid
flowchart LR
  subgraph VEH[Vehicle]
    BAT[12V battery / fuse box]
  end

  subgraph UNIT[DeerWatch unit - IP65 enclosure]
    direction TB
    subgraph PCB[Carrier PCB rev A]
      FUSE[3A fuse]
      RP[Reverse-polarity P-FET]
      TVS[TVS SMBJ16A]
      BUCK[Buck 5V/5A TPS5450]
      LDO[LDO 3V3]
      CAN[CAN xcvr SN65HVD230]
      BZD[Buzzer driver]
      LED[RGB status LED]
      BTN[MUTE button]
    end
    RADAR[IWR6843AOPEVM 60GHz]
    PI[Raspberry Pi 5]
    BUZ[Piezo buzzer]
  end

  BAT -->|12V tap| FUSE --> RP --> TVS --> BUCK
  BUCK -->|5V 5A| PI
  BUCK -->|5V| RADAR
  BUCK --> LDO --> CAN
  RADAR -->|USB CDC / UART JSON| PI
  PI -->|GPIO| BZD --> BUZ
  PI -->|GPIO PWM| LED
  BTN -->|GPIO in| PI
  PI <-->|SPI/UART| CAN
  CAN -->|CAN H/L| BAT
  PI -.->|HDMI / Wi-Fi| EXT[Display / phone / thermal unit]
```

---

## 2. Power tree

```mermaid
flowchart TD
  V12[12V in 9-16V] --> F[Fuse 3A]
  F --> Q1[P-FET reverse polarity]
  Q1 --> T[TVS clamp]
  T --> CIN[Bulk 100uF]
  CIN --> U1[TPS5450 buck]
  U1 --> R5[5V / 5A rail]
  R5 --> PI[Pi 5  ~5A peak]
  R5 --> RAD[Radar EVM ~0.5A]
  R5 --> U2[AMS1117-3.3]
  U2 --> R3[3V3 rail]
  R3 --> CANL[CAN xcvr logic]
  R3 --> LEDL[LED logic]
```

---

## 3. Raspberry Pi 5 GPIO assignment (BCM numbering)

| Signal | BCM | Pin | Direction | Notes |
|--------|-----|-----|-----------|-------|
| Buzzer | GPIO18 | 12 | out (PWM) | via MMBT2222A driver Q2 |
| LED R | GPIO17 | 11 | out | 330R -> RGB R |
| LED G | GPIO27 | 13 | out | 330R -> RGB G |
| LED B | GPIO22 | 15 | out | 330R -> RGB B |
| MUTE btn | GPIO23 | 16 | in (pull-up) | tactile SW1 to GND |
| CAN TX | GPIO (UART/SPI) | per HAT | out | SN65HVD230 or MCP2515 HAT |
| CAN RX | GPIO | per HAT | in | |
| 5V | - | 2,4 | power | from carrier buck |
| GND | - | 6,9,14,20,25,30,34,39 | gnd | |

```mermaid
flowchart LR
  PI[Pi 5 40-pin] -->|GPIO18 PWM| Q2[Q2 NPN] --> BZ[Buzzer]
  PI -->|GPIO17/27/22 +330R| RGB[RGB LED]
  SW[MUTE SW1] -->|GPIO23 pull-up| PI
  PI -->|5V/GND from header J3| PCB[Carrier]
```

---

## 4. Wiring / connector map

| Connector | On | Mates to | Pins |
|-----------|----|---------|------|
| J1 | Carrier | 12V fuse-tap harness | +12V, GND |
| J2 | Carrier | Vehicle CAN (optional) | CANH, CANL, GND |
| J3 | Carrier | Pi 5 40-pin header | 2x20 |
| J4 | Carrier | Radar EVM USB/UART | 5V, GND, RX, TX |
| BZ1 | Carrier | Piezo buzzer | +, - |
| USB | Pi | Radar EVM micro-USB | data |

---

## 5. Detect -> alert sequence

```mermaid
sequenceDiagram
  participant R as Radar EVM
  participant P as Pi (mmwave_deer)
  participant O as Outputs
  participant T as Thermal unit (opt)

  R->>P: point cloud frame (UART JSON, 10 Hz)
  P->>P: cluster() + detector.detect()
  alt deer-like cluster, confirm_frames reached
    P->>T: query confirmation (Wi-Fi, optional)
    T-->>P: thermal hit y/n
    P->>O: buzzer + voice "Deer LEFT 40m"
    P->>O: LED red
    P->>O: CAN threat frame (optional)
  else no/weak detection
    P->>O: LED green/amber
  end
```

---

## 6. Boot / runtime

```mermaid
flowchart TD
  A[Power on 12V] --> B[Pi boots Linux]
  B --> C[systemd: deerwatch.service]
  C --> D[send .cfg chirp profile to EVM]
  D --> E[open reader UART]
  E --> F[live_scanner loop 10Hz]
  F --> G{deer?}
  G -- yes --> H[outputs.alert + log]
  G -- no --> F
  H --> F
```
