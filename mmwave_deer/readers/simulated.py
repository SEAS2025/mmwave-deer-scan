from __future__ import annotations

import json
import random
import time
from typing import Iterator

from mmwave_deer.readers.base import RadarReader
from mmwave_deer.types import RadarFrame, RadarPoint


class SimulatedReader(RadarReader):
    """Synthetic roadside scene for development without radar hardware."""

    def __init__(self, fps: float = 10.0, seed: int = 42):
        self.fps = fps
        self.rng = random.Random(seed)
        self._frame = 0
        self._deer_x = 28.0
        self._deer_y = -1.4
        self._deer_vx = -0.35

    def frames(self) -> Iterator[RadarFrame]:
        interval = 1.0 / max(self.fps, 1.0)
        while True:
            self._frame += 1
            self._deer_x += self._deer_vx * interval
            if self._deer_x < 8.0:
                self._deer_vx = abs(self._deer_vx)
            elif self._deer_x > 45.0:
                self._deer_vx = -abs(self._deer_vx)

            yield RadarFrame(
                frame_number=self._frame,
                points=self._scene_points(),
                timestamp=time.time(),
            )
            time.sleep(interval)

    def _scene_points(self) -> list[RadarPoint]:
        pts: list[RadarPoint] = []
        for x, y in ((18.0, -3.5), (22.0, 3.2), (35.0, -4.0)):
            pts.append(RadarPoint(x=x, y=y, z=0.8, velocity=0.0, snr=9.0 + self.rng.uniform(-1, 1)))

        for dx, dy, dz in ((0.0, 0.0, 0.9), (0.35, 0.08, 1.05), (-0.25, -0.05, 0.75), (0.55, 0.0, 0.55)):
            pts.append(
                RadarPoint(
                    x=self._deer_x + dx + self.rng.uniform(-0.05, 0.05),
                    y=self._deer_y + dy + self.rng.uniform(-0.04, 0.04),
                    z=dz + self.rng.uniform(-0.03, 0.03),
                    velocity=self._deer_vx + self.rng.uniform(-0.08, 0.08),
                    snr=14.0 + self.rng.uniform(-2, 2),
                )
            )

        if self._frame % 90 == 0:
            for i in range(6):
                pts.append(RadarPoint(x=55.0 + i * 0.9, y=0.2, z=0.9, velocity=-12.0, snr=22.0))

        return pts
