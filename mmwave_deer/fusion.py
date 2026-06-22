"""Sensor fusion: confirm radar deer detections against the thermal unit.

The thermal project (agm-taipan-deer-scan) runs a web scanner that exposes
GET /api/status with a JSON body including `detections`, `deer_hits`, and `armed`.
This module queries that endpoint and gates radar alerts on thermal agreement, which
sharply cuts false positives from guardrails and vehicles.

Fusion policy (configurable):
  - radar_only : alert on radar alone (thermal optional, advisory)
  - confirm    : require recent thermal hit within `window_s` to escalate to ALERT
  - either     : alert if radar OR thermal fires
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ThermalState:
    last_hit_t: float = 0.0
    last_count: int = 0
    connected: bool = False


@dataclass
class ThermalConfirmer:
    url: str = "http://127.0.0.1:8080/api/status"
    window_s: float = 2.5
    timeout_s: float = 0.4
    _state: ThermalState = field(default_factory=ThermalState)

    def poll(self) -> ThermalState:
        try:
            import requests
            r = requests.get(self.url, timeout=self.timeout_s)
            data = r.json()
            self._state.connected = bool(data.get("connected", False))
            hits = int(data.get("deer_hits", data.get("detections", 0)) or 0)
            if hits > 0 or data.get("armed"):
                self._state.last_hit_t = time.time()
                self._state.last_count = hits
        except Exception:
            self._state.connected = False
        return self._state

    def thermal_recent(self) -> bool:
        return (time.time() - self._state.last_hit_t) <= self.window_s


class FusionGate:
    def __init__(self, policy: str = "radar_only", confirmer: Optional[ThermalConfirmer] = None):
        self.policy = policy
        self.confirmer = confirmer or ThermalConfirmer()

    def should_alert(self, radar_armed: bool) -> bool:
        if self.policy == "radar_only":
            return radar_armed
        self.confirmer.poll()
        thermal = self.confirmer.thermal_recent()
        if self.policy == "confirm":
            return radar_armed and thermal
        if self.policy == "either":
            return radar_armed or thermal
        return radar_armed
