import json
from pathlib import Path

import pytest

from mmwave_deer.detector import MmWaveDeerDetector
from mmwave_deer.types import RadarFrame, RadarPoint


FIXTURE = Path(__file__).parent / "fixtures" / "deer_cluster.json"


def test_detects_deer_cluster():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    points = [RadarPoint(**p) for p in data["points"]]
    frame = RadarFrame(frame_number=1, points=points)
    det = MmWaveDeerDetector()
    hits = det.detect(frame)
    assert hits, "expected at least one deer detection"
    assert hits[0].range_m > 5.0
