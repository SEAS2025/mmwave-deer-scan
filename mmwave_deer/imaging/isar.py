"""ISAR (Inverse Synthetic Aperture Radar) image formation - skeleton.

ISAR forms a 2-D image (range x cross-range) of a target by exploiting the
target's own change in aspect angle over a coherent dwell. Cross-range
resolution is

    dcr = lambda / (2 * delta_theta)

so only ~2 deg of aspect change buys ~5 cm at 77 GHz. The pipeline:

    1. range-compress each pulse           (range_compression)
    2. translational motion compensation    (align_range_profiles)
    3. phase autofocus                       (dominant_scatterer_autofocus)
    4. cross-range FFT over pulses           (form_isar_image)

Autofocus here is the dominant-scatterer algorithm (simple + robust for a
single bright scatterer). For real data, swap in PGA / minimum-entropy
autofocus. Everything is numpy-only and runs on synthetic data.
"""

from __future__ import annotations

import numpy as np

C_LIGHT = 299_792_458.0


def range_compression(adc: np.ndarray, window: bool = True) -> np.ndarray:
    """Fast-time FFT of (n_samples, n_pulses) -> range profiles (n_range, n_pulses)."""
    if adc.ndim != 2:
        raise ValueError("expected (n_samples, n_pulses)")
    if window:
        adc = adc * np.hanning(adc.shape[0])[:, None]
    return np.fft.fft(adc, axis=0)


def align_range_profiles(profiles: np.ndarray, ref_index: int = 0) -> np.ndarray:
    """Translational motion comp: integer-shift each pulse to align |profile|.

    Uses cross-correlation of the range-profile magnitude against a reference
    pulse and circularly shifts to remove bulk range walk.
    """
    n_range, n_pulses = profiles.shape
    ref = np.abs(profiles[:, ref_index])
    aligned = np.empty_like(profiles)
    for p in range(n_pulses):
        mag = np.abs(profiles[:, p])
        xc = np.fft.ifft(np.fft.fft(mag) * np.conj(np.fft.fft(ref))).real
        shift = int(np.argmax(xc))
        if shift > n_range // 2:
            shift -= n_range
        aligned[:, p] = np.roll(profiles[:, p], -shift)
    return aligned


def dominant_scatterer_autofocus(profiles: np.ndarray) -> np.ndarray:
    """Remove pulse-to-pulse phase using the brightest (dominant) range bin."""
    power = (np.abs(profiles) ** 2).sum(axis=1)
    bright = int(np.argmax(power))
    phase = np.angle(profiles[bright, :])
    correction = np.exp(-1j * phase)[None, :]
    return profiles * correction


def form_isar_image(profiles: np.ndarray) -> np.ndarray:
    """Cross-range FFT over the pulse axis -> ISAR magnitude image (range x cross-range)."""
    w = np.hanning(profiles.shape[1])[None, :]
    img = np.fft.fftshift(np.fft.fft(profiles * w, axis=1), axes=1)
    return np.abs(img)


def cross_range_axis(n_pulses: int, prf_hz: float, wavelength_m: float, omega_rad_s: float) -> np.ndarray:
    """Cross-range (m) per Doppler bin given target rotation rate omega.

    cross_range = (lambda / 2) * f_doppler / omega
    """
    k = np.arange(n_pulses) - n_pulses // 2
    f_d = k * prf_hz / n_pulses
    if omega_rad_s == 0:
        return np.full(n_pulses, np.nan)
    return (wavelength_m / 2.0) * f_d / omega_rad_s


def image_entropy(image: np.ndarray) -> float:
    """Image entropy - lower means better focused (autofocus quality metric)."""
    p = np.abs(image) ** 2
    total = p.sum()
    if total <= 0:
        return float("inf")
    p = p / total
    nz = p[p > 0]
    return float(-np.sum(nz * np.log(nz)))
