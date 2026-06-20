from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from mmwave_deer.readers.base import FrameSource, RadarReader
from mmwave_deer.readers.simulated import SimulatedReader
from mmwave_deer.readers.ti_mmwave import SerialJsonReader, TiMmWaveReader

__all__ = [
    "FrameSource",
    "RadarReader",
    "SimulatedReader",
    "SerialJsonReader",
    "TiMmWaveReader",
    "load_config",
    "make_reader",
]


def load_config(path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or Path(__file__).resolve().parents[2] / "config" / "default.yaml"
    if not cfg_path.exists():
        return {}
    return yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}


def make_reader(cfg: dict[str, Any]) -> RadarReader:
    reader_cfg = cfg.get("reader", {})
    kind = str(reader_cfg.get("type", "simulated")).lower()
    if kind == "simulated":
        return SimulatedReader(fps=float(reader_cfg.get("fps", 10.0)))
    port = str(reader_cfg.get("port", "COM3"))
    baud = int(reader_cfg.get("baud", 115200))
    if kind in ("ti_mmwave", "serial_json"):
        return TiMmWaveReader(port=port, baud=baud)
    raise ValueError(f"Unknown reader type: {kind}")
