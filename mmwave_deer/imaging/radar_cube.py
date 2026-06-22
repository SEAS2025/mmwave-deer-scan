"""Raw ADC radar-cube handling and the standard range / Doppler / angle FFTs.

A radar "cube" is the raw mixer output organised as

    [fast-time samples, slow-time chirps, virtual channels]

The classical FMCW imaging chain is three FFTs along those three axes:

    range FFT  (fast-time)  -> beat frequency -> range
    Doppler FFT (slow-time) -> phase change per chirp -> radial velocity
    angle FFT  (channels)   -> phase across the virtual array -> bearing

This module is intentionally dependency-light (numpy only) so it can run on
synthetic data; swap in a real captured cube from a DCA1000 / cascade board.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

C_LIGHT = 299_792_458.0


@dataclass
class RadarParams:
    """FMCW chirp + array parameters needed to label FFT axes physically."""

    f0_hz: float = 77e9          # start frequency
    slope_hz_per_s: float = 7e12  # chirp slope (Hz/s) ~ 7 MHz/us
    fs_hz: float = 5e6           # ADC sample rate
    n_samples: int = 256         # fast-time samples per chirp
    n_chirps: int = 128          # slow-time chirps per frame
    chirp_period_s: float = 70e-6  # slow-time sampling period (Tc)
    n_tx: int = 3
    n_rx: int = 4

    @property
    def wavelength_m(self) -> float:
        return C_LIGHT / self.f0_hz

    @property
    def n_virtual(self) -> int:
        return self.n_tx * self.n_rx

    @property
    def adc_bandwidth_hz(self) -> float:
        """Bandwidth actually spanned during ADC sampling (sets range res)."""
        return self.slope_hz_per_s * self.n_samples / self.fs_hz

    @property
    def range_resolution_m(self) -> float:
        return C_LIGHT / (2.0 * self.adc_bandwidth_hz)

    @property
    def max_range_m(self) -> float:
        return (self.fs_hz / 2.0) * C_LIGHT / (2.0 * self.slope_hz_per_s)

    @property
    def prf_hz(self) -> float:
        return 1.0 / self.chirp_period_s

    def range_axis(self) -> np.ndarray:
        """Range (m) for each fast-time FFT bin (first half)."""
        n = self.n_samples
        beat = np.arange(n) * self.fs_hz / n          # beat frequency per bin
        return beat * C_LIGHT / (2.0 * self.slope_hz_per_s)

    def velocity_axis(self) -> np.ndarray:
        """Radial velocity (m/s) for each (fftshifted) Doppler bin."""
        n = self.n_chirps
        k = np.arange(n) - n // 2
        f_d = k * self.prf_hz / n
        return f_d * self.wavelength_m / 2.0


@dataclass
class RadarCube:
    """Raw complex ADC cube: shape (n_samples, n_chirps, n_virtual)."""

    data: np.ndarray
    params: RadarParams

    def __post_init__(self) -> None:
        if self.data.ndim != 3:
            raise ValueError(f"cube must be 3-D (samples, chirps, channels), got {self.data.shape}")

    @property
    def shape(self) -> tuple[int, int, int]:
        return self.data.shape  # type: ignore[return-value]


def _window(n: int) -> np.ndarray:
    return np.hanning(n)


def range_fft(cube: RadarCube) -> np.ndarray:
    """Fast-time FFT -> complex array (n_range, n_chirps, n_channels)."""
    w = _window(cube.data.shape[0])[:, None, None]
    return np.fft.fft(cube.data * w, axis=0)


def doppler_fft(range_cube: np.ndarray) -> np.ndarray:
    """Slow-time FFT (fftshifted) -> (n_range, n_doppler, n_channels)."""
    w = _window(range_cube.shape[1])[None, :, None]
    return np.fft.fftshift(np.fft.fft(range_cube * w, axis=1), axes=1)


def angle_fft(rd_cube: np.ndarray, n_angle_bins: int | None = None) -> np.ndarray:
    """Channel FFT (fftshifted) -> (n_range, n_doppler, n_angle) magnitude-ready."""
    n = n_angle_bins or rd_cube.shape[2]
    return np.fft.fftshift(np.fft.fft(rd_cube, n=n, axis=2), axes=2)


def range_doppler_map(cube: RadarCube) -> np.ndarray:
    """Non-coherently integrate channels into a range-Doppler magnitude map."""
    rd = doppler_fft(range_fft(cube))
    n_half = rd.shape[0] // 2
    mag = np.abs(rd[:n_half]).sum(axis=2)
    return mag
