"""Micro-Doppler analysis - the cheap, achievable path to "see" a deer.

A walking deer is not a point: the torso has a bulk radial velocity while the
legs swing back and forth, sweeping a Doppler spread that repeats at the gait
cadence. A Short-Time Fourier Transform of the slow-time signal in one range
bin produces a micro-Doppler spectrogram whose structure classifies the target
and (via ISAR) can be turned into an image.

Implemented numpy-only (no scipy dependency). Feed complex slow-time samples
(one per chirp) from a single range bin of a captured/real cube.
"""

from __future__ import annotations

import numpy as np

C_LIGHT = 299_792_458.0


def stft(
    x: np.ndarray,
    nperseg: int = 64,
    noverlap: int = 48,
    window: str = "hann",
) -> tuple[np.ndarray, np.ndarray]:
    """Complex STFT for complex input, returning (frame_starts, Z).

    Z has shape (nperseg, n_frames) and is fftshifted so row 0 is the most
    negative Doppler. Both positive and negative velocities are kept (the input
    is complex, so the spectrum is two-sided).
    """
    x = np.asarray(x)
    if x.ndim != 1:
        raise ValueError("stft expects a 1-D slow-time signal")
    hop = nperseg - noverlap
    if hop <= 0:
        raise ValueError("noverlap must be < nperseg")
    win = np.hanning(nperseg) if window == "hann" else np.ones(nperseg)
    starts = np.arange(0, len(x) - nperseg + 1, hop)
    if len(starts) == 0:
        raise ValueError("signal shorter than one STFT window")
    cols = []
    for s in starts:
        seg = x[s : s + nperseg] * win
        cols.append(np.fft.fftshift(np.fft.fft(seg)))
    return starts, np.array(cols).T


def micro_doppler_spectrogram(
    slow_time: np.ndarray,
    prf_hz: float,
    wavelength_m: float,
    nperseg: int = 64,
    noverlap: int = 48,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (velocity_axis_mps, time_axis_s, magnitude_db).

    velocity_axis_mps : (nperseg,) radial velocity per Doppler bin
    time_axis_s       : (n_frames,) center time of each STFT window
    magnitude_db      : (nperseg, n_frames) power in dB
    """
    starts, Z = stft(slow_time, nperseg, noverlap)
    mag = np.abs(Z)
    mag_db = 20.0 * np.log10(mag + 1e-12)

    k = np.arange(nperseg) - nperseg // 2
    f_d = k * prf_hz / nperseg
    velocity = f_d * wavelength_m / 2.0

    hop = nperseg - noverlap
    time = (starts + nperseg / 2.0) / prf_hz
    return velocity, time, mag_db


def bulk_velocity_mps(velocity_axis: np.ndarray, magnitude_db: np.ndarray) -> float:
    """Power-weighted velocity centroid over the whole dwell ~ torso velocity."""
    power = 10.0 ** (magnitude_db / 10.0)
    profile = power.sum(axis=1)
    profile = profile / (profile.sum() + 1e-12)
    return float(np.sum(velocity_axis * profile))


def _doppler_bandwidth(velocity_axis: np.ndarray, magnitude_db: np.ndarray) -> np.ndarray:
    """Power-weighted velocity spread per time frame (the leg-swing envelope)."""
    power = 10.0 ** (magnitude_db / 10.0)
    w = power / (power.sum(axis=0, keepdims=True) + 1e-12)
    mean = np.sum(velocity_axis[:, None] * w, axis=0)
    var = np.sum(((velocity_axis[:, None] - mean) ** 2) * w, axis=0)
    return np.sqrt(var)


def gait_cadence_hz(
    velocity_axis: np.ndarray,
    time_axis: np.ndarray,
    magnitude_db: np.ndarray,
) -> tuple[float, float]:
    """Estimate leg-swing cadence (Hz) from the periodicity of the Doppler spread.

    Returns (cadence_hz, normalized_peak) where normalized_peak in [0,1] is a
    crude confidence from the autocorrelation peak height.

    NOTE: the Doppler-spread envelope peaks twice per stride (leg speed maximises
    mid-swing in each direction), so the returned cadence is often ~2x the true
    stride frequency. Treat it as a relative gait metric, not an absolute count.
    """
    if len(time_axis) < 4:
        return 0.0, 0.0
    env = _doppler_bandwidth(velocity_axis, magnitude_db)
    env = env - env.mean()
    ac = np.correlate(env, env, mode="full")[len(env) - 1 :]
    if ac[0] <= 0:
        return 0.0, 0.0
    ac_n = ac / ac[0]

    dt = float(np.mean(np.diff(time_axis)))
    # ignore lag 0; find first dominant peak
    peak_lag = 0
    peak_val = 0.0
    for lag in range(1, len(ac_n) - 1):
        if ac_n[lag] > ac_n[lag - 1] and ac_n[lag] >= ac_n[lag + 1] and ac_n[lag] > peak_val:
            peak_val = ac_n[lag]
            peak_lag = lag
    if peak_lag == 0:
        return 0.0, 0.0
    cadence = 1.0 / (peak_lag * dt)
    return float(cadence), float(peak_val)
