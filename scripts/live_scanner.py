from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mmwave_deer.alert import assess_threats, format_callout
from mmwave_deer.detector import MmWaveDeerDetector
from mmwave_deer.profile import DEER_RADAR_PROFILE
from mmwave_deer.readers import FrameSource, load_config, make_reader


def print_frame_summary(frame_number: int, point_count: int, detections, status: str, fps: float):
    det_str = ", ".join(f"{d.range_m:.1f}m score={d.score:.2f}" for d in detections[:3]) or "none"
    print(
        f"[{time.strftime('%H:%M:%S')}] frame={frame_number:5d}  pts={point_count:3d}  "
        f"fps={fps:4.1f}  {status:12s}  hits: {det_str}"
    )


def main():
    ap = argparse.ArgumentParser(description="mmWave roadside deer scanner")
    ap.add_argument("--config", type=Path, help="YAML config path")
    ap.add_argument("--reader", choices=("simulated", "ti_mmwave", "serial_json"), help="Override reader type")
    ap.add_argument("--port", help="Serial port (e.g. COM3)")
    ap.add_argument("--sensitivity", type=float, default=1.0)
    ap.add_argument("--confirm-frames", type=int, default=DEER_RADAR_PROFILE["confirm_frames"])
    ap.add_argument("--demo", action="store_true", help="Force simulated reader")
    ap.add_argument("--outputs", action="store_true", help="Drive Pi GPIO buzzer/LED (hardware)")
    ap.add_argument("--can", action="store_true", help="Broadcast threats on vehicle CAN")
    ap.add_argument("--fusion", choices=("radar_only", "confirm", "either"), default="radar_only",
                    help="Thermal fusion policy (queries thermal unit /api/status)")
    ap.add_argument("--thermal-url", default="http://127.0.0.1:8080/api/status",
                    help="Thermal unit status endpoint for fusion")
    args = ap.parse_args()

    cfg = load_config(args.config)
    if args.demo:
        cfg.setdefault("reader", {})["type"] = "simulated"
    if args.reader:
        cfg.setdefault("reader", {})["type"] = args.reader
    if args.port:
        cfg.setdefault("reader", {})["port"] = args.port

    reader_cfg = cfg.get("reader", {})
    det_cfg = cfg.get("detector", {})
    road_cfg = cfg.get("road", {})

    detector = MmWaveDeerDetector(
        cluster_eps_m=float(det_cfg.get("cluster_eps_m", 0.75)),
        cluster_min_points=int(det_cfg.get("cluster_min_points", 2)),
        min_snr_db=float(det_cfg.get("min_snr_db", 8.0)),
    )
    detector.state.sensitivity = args.sensitivity

    source = FrameSource(make_reader(cfg))
    confirm_streak = 0
    fps_t = time.time()
    fps_n = 0
    fps = 0.0

    outputs = None
    can_bcast = None
    gate = None
    if args.outputs or args.can:
        from mmwave_deer.outputs import AlertOutputs, CanBroadcaster
        if args.outputs:
            outputs = AlertOutputs(cooldown_s=float(cfg.get("alert", {}).get("cooldown_s", 8.0)))
        if args.can:
            can_bcast = CanBroadcaster()
    if args.fusion != "radar_only":
        from mmwave_deer.fusion import FusionGate, ThermalConfirmer
        gate = FusionGate(policy=args.fusion, confirmer=ThermalConfirmer(url=args.thermal_url))

    print("=" * 60)
    print("mmWave Deer Scanner")
    print("=" * 60)
    print(f"Reader: {reader_cfg.get('type', 'simulated')}  fusion: {args.fusion}"
          f"  outputs: {bool(outputs)}  can: {bool(can_bcast)}")
    print("Ctrl+C to stop\n")

    try:
        for frame in source:
            fps_n += 1
            if time.time() - fps_t >= 1.0:
                fps = fps_n / (time.time() - fps_t)
                fps_n = 0
                fps_t = time.time()

            detections = detector.detect(frame)
            if detections:
                confirm_streak += 1
            else:
                confirm_streak = max(0, confirm_streak - 1)

            radar_armed = confirm_streak >= args.confirm_frames
            armed = gate.should_alert(radar_armed) if gate is not None else radar_armed
            status = "DEER ALERT" if armed else ("TRACKING" if detections else "SCANNING")
            print_frame_summary(frame.frame_number, len(frame.points), detections, status, fps)

            if outputs is not None:
                outputs.set_status("ALERT" if armed else ("TRACKING" if detections else "SCANNING"))

            if armed:
                threat = assess_threats(
                    detections,
                    left_bound=float(road_cfg.get("left_bound_m", -2.0)),
                    right_bound=float(road_cfg.get("right_bound_m", 2.0)),
                )
                if threat:
                    print(f"  >>> {format_callout(threat)}  tier={threat.tier}")
                    if outputs is not None:
                        outputs.alert(threat)
                    if can_bcast is not None:
                        can_bcast.send(threat)
                    confirm_streak = 0
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        source.close()
        if outputs is not None:
            outputs.close()
        if can_bcast is not None:
            can_bcast.close()


if __name__ == "__main__":
    main()
