"""Experimental high-resolution radar imaging pipeline (R&D track).

These modules are *stubs / reference skeletons* for going beyond the sparse
point cloud toward micro-Doppler signatures and ISAR imaging of a moving deer.
They operate on raw ADC data (the kind captured with a DCA1000 / cascade
capture board), not the SDK point cloud. Everything here runs on numpy against
synthetic data so the pipeline shape can be exercised before real hardware.

See docs/IMAGING_RADAR_BOM.md for the hardware needed to feed real data in, and
the "radar-3d-imaging-requirements" canvas for the resolution rationale.
"""

from mmwave_deer.imaging.radar_cube import (
    RadarParams,
    RadarCube,
    range_fft,
    doppler_fft,
    angle_fft,
    range_doppler_map,
)
from mmwave_deer.imaging.microdoppler import (
    stft,
    micro_doppler_spectrogram,
    gait_cadence_hz,
    bulk_velocity_mps,
)
from mmwave_deer.imaging.isar import (
    range_compression,
    align_range_profiles,
    dominant_scatterer_autofocus,
    form_isar_image,
    image_entropy,
)
from mmwave_deer.imaging.synth import simulate_walking_deer, simulate_deer_cube

__all__ = [
    "RadarParams",
    "RadarCube",
    "range_fft",
    "doppler_fft",
    "angle_fft",
    "range_doppler_map",
    "stft",
    "micro_doppler_spectrogram",
    "gait_cadence_hz",
    "bulk_velocity_mps",
    "range_compression",
    "align_range_profiles",
    "dominant_scatterer_autofocus",
    "form_isar_image",
    "image_entropy",
    "simulate_walking_deer",
    "simulate_deer_cube",
]
