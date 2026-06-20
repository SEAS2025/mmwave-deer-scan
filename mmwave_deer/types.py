from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class RadarPoint:
    x: float  # forward range (m)
    y: float  # lateral (m), + = right
    z: float  # height (m)
    velocity: float  # m/s, + = receding
    snr: float = 0.0


@dataclass
class RadarFrame:
    frame_number: int
    points: list[RadarPoint] = field(default_factory=list)
    timestamp: float = 0.0


@dataclass
class Cluster:
    points: list[RadarPoint]
    centroid_x: float
    centroid_y: float
    centroid_z: float
    extent_x: float
    extent_y: float
    extent_z: float
    mean_velocity: float
    mean_snr: float
    point_count: int


@dataclass
class Detection:
    cluster: Cluster
    score: float
    label: str = "deer"
    range_m: float = 0.0
    lateral_m: float = 0.0
    side: str = "ahead"


@dataclass
class DetectorState:
    sensitivity: float = 1.0
    track_history: dict[int, int] = field(default_factory=dict)
    next_track_id: int = 0


@dataclass
class ThreatAssessment:
    detection: Detection
    side: str
    range_m: float
    tier: str
    count: int = 1
