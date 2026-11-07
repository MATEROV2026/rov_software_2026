"""Regression tests for the datasheet conversions and calibration maths.

These cover the failures that have actually happened on this project, not a
general sweep: a burst length mismatch that silenced the IMU for every sample,
and the two-parts-one-register-map scale confusion.

Run with:  python3 -m pytest ros/src/materov/test/ -q
"""
import math
import struct
import sys
from pathlib import Path

import pytest

# Importable without a built workspace, so this runs on a laptop too.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from materov.sensor_math import (  # noqa: E402
    ICM20649_WHO_AM_I, ICM20948_WHO_AM_I, apply_accel_calibration,
    apply_gyro_bias, decode_icm, decode_icm20649, decode_icm_temperature)

G = 9.80665


def burst(ax=0, ay=0, az=0, gx=0, gy=0, gz=0, temp=None):
    """Build an ICM burst the way the device lays it out, big-endian."""
    values = [ax, ay, az, gx, gy, gz]
    if temp is None:
        return list(struct.pack('>6h', *values))
    return list(struct.pack('>7h', *values, temp))


class TestBurstLength:
    """The node reads 14 bytes; decode_icm used to insist on exactly 12.

    That mismatch raised ValueError on every sample. I2CSensorNode catches
    ValueError, so nothing crashed - it logged "Sensor unavailable; retry in
    5s" forever and published nothing.
    """

    def test_accepts_twelve_and_fourteen(self):
        twelve = burst(ax=16384, gz=131)
        fourteen = burst(ax=16384, gz=131, temp=2000)
        assert decode_icm(twelve, ICM20948_WHO_AM_I) == \
            decode_icm(fourteen, ICM20948_WHO_AM_I)

    def test_trailing_bytes_do_not_disturb_accel_or_gyro(self):
        base = decode_icm(burst(ax=1000, gy=-250), ICM20948_WHO_AM_I)
        for temp in (-32768, 0, 32767):
            assert decode_icm(burst(ax=1000, gy=-250, temp=temp),
                              ICM20948_WHO_AM_I) == base

    @pytest.mark.parametrize('length', [0, 6, 11, 13, 15, 24])
    def test_rejects_other_lengths(self, length):
        with pytest.raises(ValueError, match='12-byte|14-byte'):
            decode_icm([0] * length, ICM20948_WHO_AM_I)


class TestScaleFactors:
    """Same register map, half the full scale - a silent factor of two."""

    def test_parts_differ_by_exactly_two(self):
        block = burst(ax=8192, ay=-4096, az=16384, gx=131, gy=-65, gz=262)
        accel_48, gyro_48 = decode_icm(block, ICM20948_WHO_AM_I)
        accel_49, gyro_49 = decode_icm(block, ICM20649_WHO_AM_I)
        for a, b in zip(accel_49, accel_48):
            assert a == pytest.approx(2.0 * b)
        for a, b in zip(gyro_49, gyro_48):
            assert a == pytest.approx(2.0 * b, rel=1e-3)

    def test_one_g_reads_one_g(self):
        accel, _ = decode_icm(burst(az=16384), ICM20948_WHO_AM_I)
        assert accel[2] == pytest.approx(G)

    def test_legacy_wrapper_still_means_20649(self):
        block = burst(ax=1234, gz=-567)
        assert decode_icm20649(block) == decode_icm(block, ICM20649_WHO_AM_I)

    def test_unknown_part_rejected(self):
        with pytest.raises(ValueError, match='WHO_AM_I'):
            decode_icm(burst(), 0x12)


class TestTemperature:
    def test_zero_count_is_the_reference_temperature(self):
        assert decode_icm_temperature(burst(temp=0), ICM20948_WHO_AM_I) == \
            pytest.approx(21.0)

    def test_scale_is_one_over_sensitivity(self):
        # +333.87 LSB is one degree above the 21 C reference.
        assert decode_icm_temperature(burst(temp=334), ICM20948_WHO_AM_I) == \
            pytest.approx(22.0, abs=0.01)

    def test_negative_counts_read_below_reference(self):
        assert decode_icm_temperature(burst(temp=-3339), ICM20948_WHO_AM_I) < 11.5

    def test_needs_the_fourteen_byte_burst(self):
        with pytest.raises(ValueError, match='14-byte'):
            decode_icm_temperature(burst(ax=1), ICM20948_WHO_AM_I)


class TestAccelCalibration:
    def test_round_trips_a_corrupted_reading(self):
        bias = [-0.598206, -0.549172, -0.039227]
        scale = [1.008, 1.005, 1.004]
        for truth in ([0.0, 0.0, -G], [G * 0.5, -G * 0.3, -G * 0.81], [0.0, G, 0.0]):
            measured = [s * t + b for t, b, s in zip(truth, bias, scale)]
            recovered = apply_accel_calibration(measured, bias, scale)
            for got, want in zip(recovered, truth):
                assert got == pytest.approx(want, abs=1e-12)

    def test_identity_is_a_no_op(self):
        reading = [1.5, -2.5, 9.0]
        assert apply_accel_calibration(reading, [0.0] * 3, [1.0] * 3) == reading

    def test_zero_scale_rejected(self):
        with pytest.raises(ValueError, match='scale factor'):
            apply_accel_calibration([1, 2, 3], [0, 0, 0], [1, 0, 1])

    @pytest.mark.parametrize('bad', [[1, 2], [1, 2, 3, 4]])
    def test_wrong_length_rejected(self, bad):
        with pytest.raises(ValueError, match='three axes'):
            apply_accel_calibration(bad, [0, 0, 0], [1, 1, 1])


class TestGyroBias:
    def test_subtracts_per_axis(self):
        corrected = apply_gyro_bias([0.5, -0.25, 0.0241],
                                    [0.0035, -0.0012, 0.0241])
        assert corrected[0] == pytest.approx(0.4965)
        assert corrected[1] == pytest.approx(-0.2488)
        assert corrected[2] == pytest.approx(0.0)

    def test_a_bias_left_in_becomes_heading_drift(self):
        """One deg/s of residual is 60 degrees of false yaw per minute.

        Nothing underwater corrects heading, so this error integrates without
        bound. It is the reason gyro_bias is worth measuring carefully.
        """
        residual = apply_gyro_bias([0.0, 0.0, math.radians(1.0)], [0.0, 0.0, 0.0])
        drift_deg_per_minute = math.degrees(residual[2]) * 60
        assert drift_deg_per_minute == pytest.approx(60.0)

    def test_wrong_length_rejected(self):
        with pytest.raises(ValueError, match='three axes'):
            apply_gyro_bias([1, 2, 3], [0, 0])
