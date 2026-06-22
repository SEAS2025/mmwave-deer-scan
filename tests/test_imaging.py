import numpy as np

from mmwave_deer.imaging import (
    RadarParams,
    simulate_walking_deer,
    simulate_deer_cube,
    micro_doppler_spectrogram,
    gait_cadence_hz,
    bulk_velocity_mps,
    range_fft,
    doppler_fft,
    angle_fft,
    range_doppler_map,
    range_compression,
    align_range_profiles,
    dominant_scatterer_autofocus,
    form_isar_image,
    image_entropy,
)


def test_microdoppler_recovers_gait_and_velocity():
    params = RadarParams()
    slow, truth = simulate_walking_deer(
        params, bulk_velocity_mps=2.5, leg_swing_hz=1.6, duration_s=2.0, snr_db=25.0
    )
    vel, time, mag_db = micro_doppler_spectrogram(
        slow, params.prf_hz, params.wavelength_m, nperseg=256, noverlap=192
    )
    assert mag_db.shape[0] == 256
    assert mag_db.shape[1] == len(time)

    v_bulk = bulk_velocity_mps(vel, mag_db)
    assert abs(v_bulk - 2.5) < 1.5  # torso centroid near truth

    cadence, conf = gait_cadence_hz(vel, time, mag_db)
    assert 0.5 < cadence < 6.0  # gait periodicity detected (allow harmonics)
    assert conf > 0.0


def test_cube_range_doppler_angle_shapes_and_peak():
    params = RadarParams(n_samples=128, n_chirps=64)
    cube, truth = simulate_deer_cube(params, range0_m=30.0, azimuth_deg=10.0, snr_db=30.0)
    assert cube.shape == (128, 64, params.n_virtual)

    rc = range_fft(cube)
    assert rc.shape == (128, 64, params.n_virtual)
    rd = doppler_fft(rc)
    assert rd.shape == (128, 64, params.n_virtual)
    ang = angle_fft(rd, n_angle_bins=32)
    assert ang.shape == (128, 64, 32)

    rdmap = range_doppler_map(cube)
    rbin = int(np.unravel_index(np.argmax(rdmap), rdmap.shape)[0])
    rng_axis = params.range_axis()
    assert abs(rng_axis[rbin] - 30.0) < 5.0  # peak near true range


def test_isar_pipeline_runs_and_autofocus_is_finite():
    params = RadarParams(n_samples=128, n_chirps=64)
    cube, _ = simulate_deer_cube(params, range0_m=25.0, snr_db=30.0)
    profiles = range_compression(cube.data[:, :, 0])
    assert profiles.shape == (128, 64)

    aligned = align_range_profiles(profiles)
    focused = dominant_scatterer_autofocus(aligned)
    img = form_isar_image(focused)
    assert img.shape == (128, 64)
    assert np.isfinite(image_entropy(img))
