"""Adapter for the OpenRadar (PreSenseRadar) DSP stack.

OpenRadar (https://github.com/presenseradar/openradar) processes raw ADC data from a
TI DCA1000 capture card into range/Doppler/point clouds. This adapter wraps either:

  1. a user-supplied callable that yields detected points as an (N, 5) array of
     [x, y, z, velocity, snr], or
  2. raw ADC frames + a minimal range/Doppler/CFAR pipeline using `mmwave.dsp`.

It is intentionally import-light: the heavy `mmwave` package is only imported when the
raw-ADC path is actually used, so the simulated/UART paths never need it.
"""

from __future__ import annotations

import time
from typing import Callable, Iterable, Iterator, Optional

import numpy as np

from mmwave_deer.readers.base import RadarReader
from mmwave_deer.types import RadarFrame, RadarPoint


def points_array_to_frame(arr: np.ndarray, frame_number: int) -> RadarFrame:
    """Convert an (N,5) [x,y,z,vel,snr] array into a RadarFrame."""
    pts = []
    if arr is not None and len(arr):
        arr = np.asarray(arr, dtype=float).reshape(-1, arr.shape[-1])
        for row in arr:
            x, y, z = row[0], row[1], row[2]
            vel = row[3] if len(row) > 3 else 0.0
            snr = row[4] if len(row) > 4 else 0.0
            pts.append(RadarPoint(x=float(x), y=float(y), z=float(z),
                                  velocity=float(vel), snr=float(snr)))
    return RadarFrame(frame_number=frame_number, points=pts, timestamp=time.time())


class PointCloudReader(RadarReader):
    """Wrap any iterable/callable of point arrays into the RadarReader interface.

    Example:
        reader = PointCloudReader(my_openradar_generator)   # yields (N,5) arrays
    """

    def __init__(self, source: Callable[[], Iterable[np.ndarray]] | Iterable[np.ndarray]):
        self._source = source

    def frames(self) -> Iterator[RadarFrame]:
        iterable = self._source() if callable(self._source) else self._source
        for i, arr in enumerate(iterable, start=1):
            yield points_array_to_frame(arr, i)


class DcaOpenRadarReader(RadarReader):
    """Raw-ADC path: DCA1000 capture -> OpenRadar DSP -> point cloud.

    Requires `openradar` (the `mmwave` package) and a DCA1000 capture card. The default
    pipeline is a minimal range-FFT + Doppler-FFT + CFAR; tune for your antenna geometry.
    """

    def __init__(self, num_chirps: int = 128, num_rx: int = 4, num_samples: int = 256,
                 range_res_m: float = 0.047, doppler_res_mps: float = 0.13,
                 cfar_guard: int = 2, cfar_train: int = 8, cfar_scale: float = 1.2):
        self.num_chirps = num_chirps
        self.num_rx = num_rx
        self.num_samples = num_samples
        self.range_res_m = range_res_m
        self.doppler_res_mps = doppler_res_mps
        self.cfar_guard = cfar_guard
        self.cfar_train = cfar_train
        self.cfar_scale = cfar_scale
        self._dca = None
        self._dsp = None

    def _ensure_openradar(self):
        if self._dsp is not None:
            return
        try:
            import mmwave as mm  # type: ignore
            from mmwave.dataloader import DCA1000  # type: ignore
        except ImportError as e:
            raise ImportError(
                "OpenRadar not installed. `pip install openradar` (the `mmwave` package) "
                "and connect a DCA1000 capture card, or use PointCloudReader with your own "
                "point generator."
            ) from e
        self._dsp = mm.dsp
        self._dca = DCA1000()

    def _adc_to_points(self, adc: np.ndarray) -> np.ndarray:
        """Minimal range/Doppler/CFAR -> [x,y,z,vel,snr] points."""
        dsp = self._dsp
        radar_cube = dsp.range_processing(adc)
        det_matrix, _ = dsp.doppler_processing(radar_cube, num_tx_antennas=3)
        power = np.abs(det_matrix)

        thresh, _ = dsp.ca_cfar(
            power, guard_len=self.cfar_guard, noise_len=self.cfar_train,
            mode="wrap", scale=self.cfar_scale,
        ) if hasattr(dsp, "ca_cfar") else (power.mean() * self.cfar_scale, None)

        peaks = np.argwhere(power > thresh)
        pts = []
        n_doppler = power.shape[1] if power.ndim > 1 else 1
        for rb, db in peaks:
            rng = rb * self.range_res_m
            vel = (db - n_doppler / 2) * self.doppler_res_mps
            snr = float(power[rb, db] / max(np.median(power), 1e-6))
            # Single-sensor: assume boresight (y=range, x=0) until AoA is added.
            pts.append([0.0, rng, 0.9, vel, snr])
        return np.array(pts, dtype=float) if pts else np.empty((0, 5))

    def frames(self) -> Iterator[RadarFrame]:
        self._ensure_openradar()
        i = 0
        while True:
            i += 1
            adc = self._dca.read()
            adc = self._dsp.reshape_frame(adc) if hasattr(self._dsp, "reshape_frame") else adc
            yield points_array_to_frame(self._adc_to_points(adc), i)

    def close(self) -> None:
        if self._dca is not None and hasattr(self._dca, "close"):
            self._dca.close()
