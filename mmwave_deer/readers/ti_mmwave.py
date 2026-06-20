from __future__ import annotations

import json
import time
from typing import Iterator

from mmwave_deer.readers.base import RadarReader
from mmwave_deer.types import RadarFrame, RadarPoint


def parse_ti_frame(payload: dict) -> RadarFrame:
    """Parse TI mmWave Demo Visualizer / SDK UART JSON frame."""
    frame_number = int(payload.get("frameNumber", payload.get("frame", 0)))
    points: list[RadarPoint] = []

    if "detectedPoints" in payload:
        raw_pts = payload["detectedPoints"]
    elif "pointCloud" in payload:
        raw_pts = payload["pointCloud"]
    else:
        raw_pts = []

    for p in raw_pts:
        if isinstance(p, dict):
            points.append(
                RadarPoint(
                    x=float(p.get("x", p.get("range", 0.0))),
                    y=float(p.get("y", 0.0)),
                    z=float(p.get("z", 0.0)),
                    velocity=float(p.get("velocity", p.get("doppler", 0.0))),
                    snr=float(p.get("snr", p.get("SNR", 0.0))),
                )
            )
        elif isinstance(p, (list, tuple)) and len(p) >= 4:
            points.append(
                RadarPoint(
                    x=float(p[0]),
                    y=float(p[1]),
                    z=float(p[2]),
                    velocity=float(p[3]),
                    snr=float(p[4] if len(p) > 4 else 0.0),
                )
            )

    return RadarFrame(frame_number=frame_number, points=points, timestamp=time.time())


class TiMmWaveReader(RadarReader):
    """Read newline-delimited JSON frames from a TI mmWave EVM over serial."""

    def __init__(self, port: str, baud: int = 115200, timeout: float = 1.0):
        import serial

        self._ser = serial.Serial(port, baudrate=baud, timeout=timeout)

    def frames(self) -> Iterator[RadarFrame]:
        buf = ""
        while True:
            chunk = self._ser.read(4096)
            if not chunk:
                continue
            buf += chunk.decode("utf-8", errors="ignore")
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                line = line.strip()
                if not line or not line.startswith("{"):
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                yield parse_ti_frame(payload)

    def close(self) -> None:
        if self._ser and self._ser.is_open:
            self._ser.close()


class SerialJsonReader(TiMmWaveReader):
    """Generic JSON-lines radar feed (same parser as TI UART output)."""

    pass
