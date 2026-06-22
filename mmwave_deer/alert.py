from __future__ import annotations

from mmwave_deer.profile import TIER_BOUNDS
from mmwave_deer.types import Detection, ThreatAssessment


def range_tier(meters: float) -> str:
    for name, bound in TIER_BOUNDS:
        if meters <= bound:
            return name
    return "far"


def side_of_road(lateral_m: float, left_bound: float = -2.0, right_bound: float = 2.0) -> str:
    if lateral_m < left_bound:
        return "left"
    if lateral_m > right_bound:
        return "right"
    return "ahead"


def format_callout(threat: ThreatAssessment, label: str = "Deer") -> str:
    side = threat.side.upper()
    m = int(round(threat.range_m))
    if threat.count > 1:
        return f"{label} - {threat.count} detected, nearest {side} {m}m"
    return f"{label} - {side} {m}m"


def assess_threats(
    detections: list[Detection],
    left_bound: float = -2.0,
    right_bound: float = 2.0,
) -> ThreatAssessment | None:
    if not detections:
        return None

    nearest = min(detections, key=lambda d: d.range_m)
    side = side_of_road(nearest.lateral_m, left_bound, right_bound)
    tier = range_tier(nearest.range_m)
    return ThreatAssessment(
        detection=nearest,
        side=side,
        range_m=nearest.range_m,
        tier=tier,
        count=len(detections),
    )
