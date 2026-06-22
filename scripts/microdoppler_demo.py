"""Demo: synthesize a walking deer, build its micro-Doppler signature and a
range-Doppler / ISAR view, print the extracted gait + bulk velocity, and
optionally save PNG heatmaps.

    python scripts/microdoppler_demo.py
    python scripts/microdoppler_demo.py --out samples --snr 15

This runs entirely on synthetic data (numpy). With real hardware you would feed
a captured raw ADC cube instead of the simulator.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mmwave_deer.imaging import (
    RadarParams,
    simulate_walking_deer,
    simulate_deer_cube,
    micro_doppler_spectrogram,
    gait_cadence_hz,
    bulk_velocity_mps,
    range_doppler_map,
    range_compression,
    align_range_profiles,
    dominant_scatterer_autofocus,
    form_isar_image,
    image_entropy,
)


def _save_heatmap(arr: np.ndarray, path: Path) -> bool:
    """Grayscale PNG heatmap via Pillow; returns False if Pillow is missing."""
    try:
        from PIL import Image
    except Exception:
        return False
    a = arr.astype(float)
    a = (a - a.min()) / (np.ptp(a) + 1e-12)
    img = (a * 255).astype(np.uint8)
    Image.fromarray(img).save(path)
    return True


def main() -> None:
    ap = argparse.ArgumentParser(description="micro-Doppler / ISAR synthetic demo")
    ap.add_argument("--out", default="samples", help="output dir for PNGs")
    ap.add_argument("--range", type=float, default=30.0)
    ap.add_argument("--velocity", type=float, default=2.5)
    ap.add_argument("--swing", type=float, default=1.6, help="leg-swing cadence (Hz)")
    ap.add_argument("--snr", type=float, default=20.0)
    ap.add_argument("--duration", type=float, default=1.5)
    args = ap.parse_args()

    params = RadarParams()

    # --- micro-Doppler -----------------------------------------------------
    slow, truth = simulate_walking_deer(
        params, range0_m=args.range, bulk_velocity_mps=args.velocity,
        leg_swing_hz=args.swing, snr_db=args.snr, duration_s=args.duration,
    )
    vel, time, mag_db = micro_doppler_spectrogram(
        slow, params.prf_hz, params.wavelength_m, nperseg=256, noverlap=192
    )
    cadence, conf = gait_cadence_hz(vel, time, mag_db)
    v_bulk = bulk_velocity_mps(vel, mag_db)

    print("=== micro-Doppler ===")
    print(f"  dwell             : {truth['duration_s']:.2f} s ({truth['n_samples']} chirps @ {params.prf_hz/1e3:.1f} kHz)")
    print(f"  bulk velocity     : {v_bulk:+.2f} m/s   (truth {truth['bulk_velocity_mps']:+.2f})")
    print(f"  gait cadence      : {cadence:.2f} Hz    (truth {truth['leg_swing_hz']:.2f}, conf {conf:.2f})")
    print(f"  spectrogram shape : {mag_db.shape} (velocity bins x time frames)")

    # --- range-Doppler + ISAR ---------------------------------------------
    cube, ctruth = simulate_deer_cube(
        params, range0_m=args.range, bulk_velocity_mps=args.velocity,
        leg_swing_hz=args.swing, snr_db=args.snr,
    )
    rd = range_doppler_map(cube)
    rbin = int(np.unravel_index(np.argmax(rd), rd.shape)[0])
    rng_axis = params.range_axis()
    print("\n=== range-Doppler / ISAR ===")
    print(f"  peak range bin    : {rbin} ~ {rng_axis[rbin]:.1f} m (truth {ctruth['range0_m']:.1f})")

    slice0 = cube.data[:, :, 0]               # one channel: (n_samples, n_chirps)
    profiles = range_compression(slice0)
    e0 = image_entropy(form_isar_image(profiles))
    focused = dominant_scatterer_autofocus(align_range_profiles(profiles))
    isar = form_isar_image(focused)
    print(f"  ISAR image shape  : {isar.shape} (range x cross-range)")
    print(f"  entropy           : {e0:.3f} -> {image_entropy(isar):.3f} (lower = better focus)")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    ok1 = _save_heatmap(mag_db, out / "microdoppler.png")
    n_half = rd.shape[0] // 2
    ok2 = _save_heatmap(20 * np.log10(rd[:n_half] + 1e-9), out / "range_doppler.png")
    ok3 = _save_heatmap(20 * np.log10(isar + 1e-9), out / "isar.png")
    if ok1 and ok2 and ok3:
        print(f"\nWrote PNGs to {out}/ (microdoppler, range_doppler, isar)")
    else:
        print("\n(Pillow not installed - skipped PNG output)")


if __name__ == "__main__":
    main()
