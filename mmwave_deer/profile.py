"""Expected radar signature for cervidae at roadside."""

DEER_RADAR_PROFILE = {
    "name": "Cervidae (deer)",
    "min_length_m": 0.7,
    "max_length_m": 2.8,
    "min_height_m": 0.45,
    "max_height_m": 1.45,
    "min_width_m": 0.25,
    "max_width_m": 1.2,
    "min_range_m": 3.0,
    "max_range_m": 120.0,
    "max_lateral_m": 12.0,
    "min_speed_mps": 0.05,
    "max_speed_mps": 9.0,
    "score_threshold": 0.52,
    "confirm_frames": 3,
}

TIER_BOUNDS = (("immediate", 25), ("near", 50), ("medium", 100))
