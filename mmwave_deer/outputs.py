"""Physical alert outputs for the DeerWatch unit (buzzer, RGB LED, CAN).

Runs on a Raspberry Pi using `gpiozero`. On any non-Pi machine (or if gpiozero is not
installed) it degrades to a no-op console driver so the rest of the stack still runs.

GPIO map (BCM) - see docs/INTEGRATION.md:
  buzzer  GPIO18 (PWM, via NPN driver)
  LED R   GPIO17
  LED G   GPIO27
  LED B   GPIO22
  MUTE    GPIO23 (input, pull-up)
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from mmwave_deer.types import ThreatAssessment

BUZZER_PIN = 18
LED_R_PIN = 17
LED_G_PIN = 27
LED_B_PIN = 22
MUTE_PIN = 23


@dataclass
class _State:
    muted: bool = False
    last_alert_t: float = 0.0


class AlertOutputs:
    """Drive buzzer + RGB LED from threat state, with alert cooldown."""

    def __init__(self, cooldown_s: float = 8.0, enable_gpio: bool = True):
        self.cooldown_s = cooldown_s
        self.state = _State()
        self._buzzer = None
        self._led = None
        self._button = None
        self._gpio = enable_gpio and self._init_gpio()

    def _init_gpio(self) -> bool:
        try:
            from gpiozero import RGBLED, Button, TonalBuzzer  # type: ignore
        except Exception:
            print("[outputs] gpiozero unavailable - console-only alert driver")
            return False
        try:
            self._buzzer = TonalBuzzer(BUZZER_PIN)
            self._led = RGBLED(LED_R_PIN, LED_G_PIN, LED_B_PIN)
            self._button = Button(MUTE_PIN, pull_up=True, bounce_time=0.05)
            self._button.when_pressed = self.toggle_mute
            return True
        except Exception as e:  # pragma: no cover - hardware specific
            print(f"[outputs] GPIO init failed ({e}) - console-only driver")
            return False

    def toggle_mute(self):
        self.state.muted = not self.state.muted
        print(f"[outputs] audio {'MUTED' if self.state.muted else 'ON'}")

    def set_status(self, status: str):
        """status: SCANNING (green), TRACKING (amber), ALERT (red)."""
        color = {
            "SCANNING": (0, 1, 0),
            "TRACKING": (1, 0.6, 0),
            "ALERT": (1, 0, 0),
        }.get(status, (0, 0, 1))
        if self._gpio and self._led is not None:
            self._led.color = color

    def alert(self, threat: ThreatAssessment, label: str = "Deer"):
        now = time.time()
        if now - self.state.last_alert_t < self.cooldown_s:
            self.set_status("ALERT")
            return
        self.state.last_alert_t = now
        self.set_status("ALERT")
        msg = f"{label} {threat.side.upper()} {int(round(threat.range_m))}m tier={threat.tier}"
        print(f"[ALERT] {msg}")
        if self.state.muted:
            return
        self._beep(threat.tier)

    def _beep(self, tier: str):
        pattern = {
            "immediate": [(880, 0.12), (0, 0.05), (880, 0.12), (0, 0.05), (880, 0.12)],
            "near": [(740, 0.15), (0, 0.08), (740, 0.15)],
            "medium": [(620, 0.2)],
        }.get(tier, [(500, 0.2)])
        if not (self._gpio and self._buzzer is not None):
            return
        for freq, dur in pattern:
            try:
                if freq <= 0:
                    self._buzzer.stop()
                else:
                    self._buzzer.play(freq)
                time.sleep(dur)
            finally:
                self._buzzer.stop()

    def close(self):
        for dev in (self._buzzer, self._led, self._button):
            try:
                if dev is not None:
                    dev.close()
            except Exception:
                pass


class CanBroadcaster:
    """Optional: broadcast a threat frame on the vehicle CAN bus via python-can."""

    def __init__(self, channel: str = "can0", bitrate: int = 500000, arb_id: int = 0x520):
        self.arb_id = arb_id
        self._bus = None
        try:
            import can  # type: ignore
            self._bus = can.interface.Bus(channel=channel, bustype="socketcan", bitrate=bitrate)
        except Exception as e:
            print(f"[can] disabled ({e})")

    def send(self, threat: ThreatAssessment):
        if self._bus is None:
            return
        import can  # type: ignore
        rng = min(int(round(threat.range_m)), 255)
        side = {"left": 1, "ahead": 2, "right": 3}.get(threat.side, 0)
        tier = {"immediate": 3, "near": 2, "medium": 1, "far": 0}.get(threat.tier, 0)
        data = bytes([0xDE, side, rng, tier, min(threat.count, 255), 0, 0, 0])
        try:
            self._bus.send(can.Message(arbitration_id=self.arb_id, data=data, is_extended_id=False))
        except Exception as e:  # pragma: no cover
            print(f"[can] send failed: {e}")

    def close(self):
        if self._bus is not None:
            try:
                self._bus.shutdown()
            except Exception:
                pass
