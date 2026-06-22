"""Send a TI mmWave .cfg chirp profile to the EVM control UART, line by line.

Usage:
  python deploy/send_cfg.py --port /dev/ttyACM0 --cfg firmware/iwr6843_deer.cfg
On Windows the control port is typically the lower-numbered COM of the two the EVM
enumerates (the higher one streams data).
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", required=True, help="EVM control UART (e.g. /dev/ttyACM0 or COM4)")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--cfg", type=Path, default=Path("firmware/iwr6843_deer.cfg"))
    args = ap.parse_args()

    import serial  # pyserial

    lines = [ln.strip() for ln in args.cfg.read_text().splitlines()
             if ln.strip() and not ln.strip().startswith("%")]

    with serial.Serial(args.port, args.baud, timeout=1) as ser:
        for ln in lines:
            ser.write((ln + "\n").encode())
            time.sleep(0.05)
            resp = ser.read(256).decode(errors="ignore").strip()
            print(f">> {ln}\n   {resp}")
    print(f"Sent {len(lines)} config lines to {args.port}")


if __name__ == "__main__":
    main()
