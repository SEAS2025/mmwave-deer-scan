from __future__ import annotations

import abc
import time
from typing import Iterator

from mmwave_deer.types import RadarFrame


class RadarReader(abc.ABC):
    @abc.abstractmethod
    def frames(self) -> Iterator[RadarFrame]:
        raise NotImplementedError

    def close(self) -> None:
        pass


class FrameSource:
    """Wrap any reader with monotonic timestamps."""

    def __init__(self, reader: RadarReader):
        self.reader = reader

    def __iter__(self) -> Iterator[RadarFrame]:
        for frame in self.reader.frames():
            if frame.timestamp <= 0:
                frame.timestamp = time.time()
            yield frame

    def close(self) -> None:
        self.reader.close()
