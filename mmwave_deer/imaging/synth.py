"""Synthetic walking-deer radar signal generator.

Models a deer as a bright torso scatterer (bulk radial velocity) plus a set of
leg scatterers whose range is modulated sinusoidally at the gait cadence -
producing the characteristic micro-Doppler spread. Used to exercise the imaging
pipeline and tests without hardware.

Signal model (coherent FMCW):
    phase = 2*pi * (2*slope*R/c) * t_fast        (beat / range term)
          + 4*pi * R / lambda                    (Doppler / slow-time term)
"""

from __future__ import annotations

import numpy as np

from mmwave_deer.imaging.radar_cube import RadarParams, RadarCube, C_LIGHT


def _scatterers(
    range0_m: float,
    bulk_velocity_mps: float,
    n_legs: int,
    leg_swing_hz: float,
    leg_amplitude_mps: float,
    t: np.ndarray,
    rng: np.random.Generator,
):
    """Yield (amplitude, R(t)) for the torso + each leg scatterer."""
    # torso: bright, smooth bulk motion
    yield 1.0, range0_m + bulk_velocity_mps * t
    # legs: sinusoidal velocity modulation -> integrate to range modulation
    for k in range(n_legs):
        phase = 2 * np.pi * k / n_legs + rng.uniform(-0.3, 0.3)
        amp_v = leg_amplitude_mps * (0.6 + 0.4 * rng.random())
        # R(t) = bulk + (amp_v / omega) * (1 - cos(omega t + phase)) approx swing
        omega = 2 * np.pi * leg_swing_hz
        r = range0_m + bulk_velocity_mps * t + (amp_v / omega) * np.sin(omega * t + phase)
        yield 0.4, r


def simulate_walking_deer(
    params: RadarParams | None = None,
    range0_m: float = 30.0,
    bulk_velocity_mps: float = 2.5,
    n_legs: int = 4,
    leg_swing_hz: float = 1.6,
    leg_amplitude_mps: float = 3.0,
    snr_db: float = 20.0,
    duration_s: float = 1.5,
    seed: int = 0,
) -> tuple[np.ndarray, dict]:
    """Return (slow_time_signal, truth) for one range bin.

    The gait cadence (~1-2 Hz) is far slower than one frame (~9 ms), so the
    slow-time record spans `duration_s` of continuous chirps (PRF from params),
    not a single frame's `n_chirps`.

    slow_time_signal : complex (N,) where N = duration_s * PRF.
    truth            : dict of the ground-truth parameters.
    """
    params = params or RadarParams()
    rng = np.random.default_rng(seed)
    n = max(8, int(duration_s * params.prf_hz))
    t = np.arange(n) * params.chirp_period_s
    lam = params.wavelength_m

    s = np.zeros(n, dtype=complex)
    for amp, r in _scatterers(range0_m, bulk_velocity_mps, n_legs, leg_swing_hz, leg_amplitude_mps, t, rng):
        # +4*pi*R/lambda convention: receding target (R increasing) -> +velocity
        s += amp * np.exp(1j * 4 * np.pi * r / lam)

    sig_power = np.mean(np.abs(s) ** 2)
    noise_power = sig_power / (10 ** (snr_db / 10.0))
    noise = np.sqrt(noise_power / 2) * (rng.standard_normal(s.shape) + 1j * rng.standard_normal(s.shape))
    s = s + noise

    truth = {
        "range0_m": range0_m,
        "bulk_velocity_mps": bulk_velocity_mps,
        "leg_swing_hz": leg_swing_hz,
        "n_legs": n_legs,
        "snr_db": snr_db,
        "n_samples": n,
        "duration_s": duration_s,
    }
    return s, truth


def simulate_deer_cube(
    params: RadarParams | None = None,
    range0_m: float = 30.0,
    bulk_velocity_mps: float = 2.5,
    azimuth_deg: float = 10.0,
    n_legs: int = 4,
    leg_swing_hz: float = 1.6,
    leg_amplitude_mps: float = 3.0,
    snr_db: float = 20.0,
    seed: int = 0,
) -> tuple[RadarCube, dict]:
    """Return a full (n_samples, n_chirps, n_virtual) cube + truth for a deer."""
    params = params or RadarParams()
    rng = np.random.default_rng(seed)
    t = np.arange(params.n_chirps) * params.chirp_period_s
    t_fast = np.arange(params.n_samples) / params.fs_hz
    lam = params.wavelength_m
    az = np.deg2rad(azimuth_deg)

    n_s, n_c, n_v = params.n_samples, params.n_chirps, params.n_virtual
    cube = np.zeros((n_s, n_c, n_v), dtype=complex)

    # per-channel azimuth steering phase (uniform linear virtual array, d=lambda/2)
    ch = np.arange(n_v)
    steer = np.exp(1j * np.pi * np.sin(az) * ch)  # (n_v,)

    for amp, r in _scatterers(range0_m, bulk_velocity_mps, n_legs, leg_swing_hz, leg_amplitude_mps, t, rng):
        for m in range(n_c):
            beat = 2 * np.pi * (2 * params.slope_hz_per_s * r[m] / C_LIGHT) * t_fast
            dopp = 4 * np.pi * r[m] / lam
            cube[:, m, :] += amp * (np.exp(1j * (beat + dopp))[:, None] * steer[None, :])

    sig_power = np.mean(np.abs(cube) ** 2)
    noise_power = sig_power / (10 ** (snr_db / 10.0))
    noise = np.sqrt(noise_power / 2) * (
        rng.standard_normal(cube.shape) + 1j * rng.standard_normal(cube.shape)
    )
    truth = {
        "range0_m": range0_m,
        "bulk_velocity_mps": bulk_velocity_mps,
        "azimuth_deg": azimuth_deg,
        "leg_swing_hz": leg_swing_hz,
    }
    return RadarCube(data=cube + noise, params=params), truth
