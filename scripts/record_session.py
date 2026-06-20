from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mmwave_deer.readers import FrameSource, load_config, make_reader


def main():
    ap = argparse.ArgumentParser(description="Record raw mmWave JSON frames for training")
    ap.add_argument("--config", type=Path, help="YAML config path")
    ap.add_argument("--out", type=Path, default=Path("recordings"))
    ap.add_argument("--seconds", type=float, default=60.0)
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()

    cfg = load_config(args.config)
    if args.demo:
        cfg.setdefault("reader", {})["type"] = "simulated"

    args.out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = args.out / f"session_{stamp}.jsonl"

    source = FrameSource(make_reader(cfg))
    deadline = time.time() + args.seconds
    count = 0

    print(f"Recording to {out_path} for {args.seconds:.0f}s ...")
    try:
        with out_path.open("w", encoding="utf-8") as f:
            for frame in source:
                if time.time() > deadline:
                    break
                row = {
                    "frame_number": frame.frame_number,
                    "timestamp": frame.timestamp,
                    "points": [
                        {"x": p.x, "y": p.y, "z": p.z, "velocity": p.velocity, "snr": p.snr}
                        for p in frame.points
                    ],
                }
                f.write(json.dumps(row) + "\n")
                count += 1
    except KeyboardInterrupt:
        pass
    finally:
        source.close()

    print(f"Saved {count} frames -> {out_path}")


if __name__ == "__main__":
    main()
