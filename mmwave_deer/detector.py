from __future__ import annotations

import math

from mmwave_deer.processing.cluster import cluster_points
from mmwave_deer.profile import DEER_RADAR_PROFILE
from mmwave_deer.types import Cluster, Detection, DetectorState, RadarFrame


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


def _in_band(value: float, lo: float, hi: float) -> float:
    if value < lo or value > hi:
        return 0.0
    return 1.0




class MmWaveDeerDetector:
    """Heuristic deer classifier from clustered mmWave returns."""

    def __init__(
        self,
        profile: dict | None = None,
        cluster_eps_m: float = 0.75,
        cluster_min_points: int = 2,
        min_snr_db: float = 8.0,
    ):
        self.p = profile or DEER_RADAR_PROFILE
        self.cluster_eps_m = cluster_eps_m
        self.cluster_min_points = cluster_min_points
        self.min_snr_db = min_snr_db
        self.state = DetectorState()

    def _score_cluster(self, c: Cluster) -> float:
        p = self.p
        range_m = math.hypot(c.centroid_x, c.centroid_y)
        if range_m < p["min_range_m"] or range_m > p["max_range_m"]:
            return 0.0
        if abs(c.centroid_y) > p["max_lateral_m"]:
            return 0.0

        length = max(c.extent_x, 0.25)
        width = max(c.extent_y, 0.15)
        height = max(c.extent_z, 0.2)
        speed = abs(c.mean_velocity)

        size_score = (
            _in_band(length, p["min_length_m"], p["max_length_m"])
            + _in_band(width, p["min_width_m"], p["max_width_m"])
            + _in_band(height, p["min_height_m"], p["max_height_m"])
        ) / 3.0
        speed_score = _in_band(speed, p["min_speed_mps"], p["max_speed_mps"])
        snr_score = _clamp01(c.mean_snr / 20.0)
        density_score = _clamp01(c.point_count / 6.0)

        # Penalize very fast returns (likely vehicles)
        if speed > 6.5 and length > 2.0:
            size_score *= 0.35

        raw = 0.42 * size_score + 0.22 * speed_score + 0.18 * snr_score + 0.18 * density_score
        return raw * self.state.sensitivity

    def detect(self, frame: RadarFrame) -> list[Detection]:
        clusters = cluster_points(
            frame.points,
            eps_m=self.cluster_eps_m,
            min_points=self.cluster_min_points,
            min_snr_db=self.min_snr_db,
        )
        dets: list[Detection] = []
        threshold = self.p["score_threshold"] / max(self.state.sensitivity, 0.5)

        for c in clusters:
            score = self._score_cluster(c)
            if score < threshold:
                continue
            range_m = math.hypot(c.centroid_x, c.centroid_y)
            dets.append(
                Detection(
                    cluster=c,
                    score=score,
                    range_m=range_m,
                    lateral_m=c.centroid_y,
                )
            )

        dets.sort(key=lambda d: d.range_m)
        return dets
