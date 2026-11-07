"""Datasheet conversions, independent of I2C/ROS for regression testing.

ICM-20649: TDK DS-000192 v1.1, tables 1/2 (FS_SEL=0).
ICM-20948: TDK DS-000189 v1.6, sections 3.2/3.3 (FS_SEL=0).
MS5837: TE 30BA/02BA second-order compensation and PROM CRC-4.
Reference: https://github.com/bluerobotics/ms5837-python
"""
import math
import struct

ICM20649_WHO_AM_I = 0xE1
ICM20948_WHO_AM_I = 0xEA

# LSB per g and LSB per deg/s at FS_SEL=0 with the DLPF enabled, which is what
# ImuSensorNode.initialize_sensor writes. The two parts share a register layout
# but not a full-scale range, so that same configuration yields +/-4g and
# +/-500 deg/s on the 20649 against +/-2g and +/-250 deg/s on the 20948 -
# a factor of two on both axes if the wrong table is used.
_ICM_SCALE = {
    ICM20649_WHO_AM_I: (8192.0, 65.5),
    ICM20948_WHO_AM_I: (16384.0, 131.0),
}

# LSB per degree C and the die temperature at which the raw count is zero.
# Both parts specify the same figures. TEMP_OUT_H/L sit at 0x39/0x3A, directly
# after GYRO_ZOUT_L, so one 14-byte burst from ACCEL_XOUT_H picks them up with
# no extra transaction - and the temperature is then guaranteed to belong to
# the same sample as the accel and gyro it arrived with.
_ICM_TEMP = {
    ICM20649_WHO_AM_I: (333.87, 21.0),
    ICM20948_WHO_AM_I: (333.87, 21.0),
}

ICM_BURST_WITHOUT_TEMPERATURE = 12
ICM_BURST_WITH_TEMPERATURE = 14


def decode_icm(block, who_am_i=ICM20649_WHO_AM_I):
    """Return (acceleration m/s^2, angular velocity rad/s) from an ICM burst.

    Accepts a 12-byte accel+gyro read or the 14-byte read that also carries
    TEMP_OUT. The trailing temperature bytes are ignored here; pass the same
    block to ``decode_icm_temperature`` for those.
    """
    if len(block) not in (ICM_BURST_WITHOUT_TEMPERATURE, ICM_BURST_WITH_TEMPERATURE):
        raise ValueError(
            'ICM burst must be one 12-byte (accel+gyro) or 14-byte '
            f'(accel+gyro+temperature) read; got {len(block)}')
    scale = _ICM_SCALE.get(who_am_i)
    if scale is None:
        raise ValueError(f'Unsupported IMU WHO_AM_I 0x{who_am_i:02x}')
    accel_lsb_per_g, gyro_lsb_per_dps = scale
    raw = struct.unpack('>6h', bytes(block[:ICM_BURST_WITHOUT_TEMPERATURE]))
    return ([v * 9.80665 / accel_lsb_per_g for v in raw[:3]],
            [math.radians(v / gyro_lsb_per_dps) for v in raw[3:]])


def decode_icm_temperature(block, who_am_i=ICM20649_WHO_AM_I):
    """Return the die temperature in Celsius from a 14-byte ICM burst.

    This is the sensor's own die, not the water: it reads well above ambient
    once the board has been powered for a while. It is worth publishing anyway,
    because gyro bias moves with it at roughly 0.05 deg/s per degree C - enough
    that a bias measured on a cool bench does not describe a warm vehicle.
    """
    if len(block) != ICM_BURST_WITH_TEMPERATURE:
        raise ValueError(
            'Temperature needs the 14-byte burst that includes TEMP_OUT; '
            f'got {len(block)}')
    calibration = _ICM_TEMP.get(who_am_i)
    if calibration is None:
        raise ValueError(f'Unsupported IMU WHO_AM_I 0x{who_am_i:02x}')
    lsb_per_degc, offset_degc = calibration
    raw = struct.unpack('>h', bytes(block[ICM_BURST_WITHOUT_TEMPERATURE:]))[0]
    return raw / lsb_per_degc + offset_degc


def decode_icm20649(block):
    """Retained so existing callers and regression tests keep working."""
    return decode_icm(block, ICM20649_WHO_AM_I)


def apply_accel_calibration(acceleration, bias, scale):
    """Return acceleration with per-axis offset and gain error removed.

    The sensor model is ``measured = scale * true + bias``, solved from six
    static positions: with an axis pointing up it reads +1g, pointing down
    -1g, so ``bias = (up + down) / 2`` and ``scale = (up - down) / 2``.
    Inverting gives ``(measured - bias) / scale``.

    Bias is in the same units as ``acceleration`` (m/s^2 here, so a 10 mg
    offset is 0.098); scale is dimensionless and near 1.0.
    """
    if len(acceleration) != 3 or len(bias) != 3 or len(scale) != 3:
        raise ValueError('Accelerometer calibration needs three axes')
    if any(s == 0.0 for s in scale):
        raise ValueError('Accelerometer scale factor cannot be zero')
    return [(a - b) / s for a, b, s in zip(acceleration, bias, scale)]


def apply_gyro_bias(angular_velocity, bias):
    """Return angular velocity with the stationary offset removed.

    Bias is the mean reading while the vehicle is still, in rad/s. It matters
    more than it looks: heading is the integral of this signal and nothing
    underwater corrects it, so 0.02 rad/s of residual is 69 degrees of false
    yaw per minute.
    """
    if len(angular_velocity) != 3 or len(bias) != 3:
        raise ValueError('Gyroscope bias needs three axes')
    return [w - b for w, b in zip(angular_velocity, bias)]


def prom_crc4(words):
    if len(words) != 7:
        raise ValueError('Expected seven PROM words')
    data = list(words) + [0]
    data[0] &= 0x0FFF
    remainder = 0
    for index in range(16):
        word = data[index // 2]
        remainder ^= (word & 255) if index % 2 else (word >> 8)
        for _ in range(8):
            remainder = ((remainder << 1) ^ (0x3000 if remainder & 0x8000 else 0)) & 0xFFFF
    return (remainder >> 12) & 15


def validate_prom(words):
    if len(words) != 7 or any(not 0 <= v <= 65535 for v in words):
        raise ValueError('Invalid PROM length or word')
    if not all(v not in (0, 65535) for v in words[1:]):
        raise ValueError('Empty/unprogrammed sensor calibration')
    if prom_crc4(words) != words[0] >> 12:
        raise ValueError('Pressure calibration CRC mismatch')


def compensate_ms5837(c, pressure_adc, temperature_adc, model='30BA'):
    """Return pressure in mbar and temperature in Celsius."""
    if model not in ('30BA', '02BA'):
        raise ValueError('pressure_model must be 30BA or 02BA')
    if len(c) != 7 or not (0 < pressure_adc < 0xFFFFFF and 0 < temperature_adc < 0xFFFFFF):
        raise ValueError('Invalid calibration/ADC conversion')
    dt = temperature_adc - c[5] * 256
    temp = 2000 + dt * c[6] / 2**23
    delta = temp - 2000
    ti = off_i = sens_i = 0.0
    if model == '02BA':
        sensitivity = c[1] * 2**16 + c[3] * dt / 2**7
        offset = c[2] * 2**17 + c[4] * dt / 2**6
        if temp < 2000:
            ti = 11 * dt**2 / 2**35
            off_i = 31 * delta**2 / 8
            sens_i = 63 * delta**2 / 32
        divisor = 32768 * 100
    else:
        sensitivity = c[1] * 2**15 + c[3] * dt / 2**8
        offset = c[2] * 2**16 + c[4] * dt / 2**7
        if temp < 2000:
            ti = 3 * dt**2 / 2**33
            off_i = 3 * delta**2 / 2
            sens_i = 5 * delta**2 / 8
            if temp < -1500:
                off_i += 7 * (temp + 1500)**2
                sens_i += 4 * (temp + 1500)**2
        else:
            ti = 2 * dt**2 / 2**37
            off_i = delta**2 / 16
        divisor = 8192 * 10
    pressure = (pressure_adc * (sensitivity - sens_i) / 2**21 - (offset - off_i)) / divisor
    return pressure, (temp - ti) / 100
