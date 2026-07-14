# SPDX-FileCopyrightText: 2026 Pedro Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT
'''
Low-precision moon position + phase for CircuitPython.
Based on Paul Schlyter's "Computing planetary positions" (accuracy ~0.3 deg,
plenty for a 0.52-deg moon disc + camera framing).
'''
import math

D2R = math.pi / 180.0
R2D = 180.0 / math.pi


def _rev(x):
    return x % 360.0


def _days_since_j2000(y, mo, d, h, mi, s):
    # valid 1900-2100, UTC in, fractional day out
    a = 367 * y - 7 * (y + (mo + 9) // 12) // 4 + 275 * mo // 9 + d - 730530
    return a + (h + mi / 60.0 + s / 3600.0) / 24.0


def _sun_lon(d):
    w = _rev(282.9404 + 4.70935e-5 * d)
    e = 0.016709 - 1.151e-9 * d
    M = _rev(356.0470 + 0.9856002585 * d)
    E = M + e * R2D * math.sin(M * D2R) * (1 + e * math.cos(M * D2R))
    xv = math.cos(E * D2R) - e
    yv = math.sqrt(1 - e * e) * math.sin(E * D2R)
    v = math.atan2(yv, xv) * R2D
    return _rev(v + w), _rev(M + w)  # true lon, mean lon-ish for LST


def moon_altaz_phase(utc, lat, lon):
    """utc = time.struct_time (UTC). Returns (alt_deg, az_deg, illum 0..1, waxing bool)."""
    d = _days_since_j2000(utc.tm_year, utc.tm_mon, utc.tm_mday,
                          utc.tm_hour, utc.tm_min, utc.tm_sec)
    # --- moon orbital elements ---
    N = _rev(125.1228 - 0.0529538083 * d)
    i = 5.1454
    w = _rev(318.0634 + 0.1643573223 * d)
    a = 60.2666  # earth radii
    e = 0.054900
    M = _rev(115.3654 + 13.0649929509 * d)

    # Kepler
    E = M + e * R2D * math.sin(M * D2R) * (1 + e * math.cos(M * D2R))
    for _ in range(4):
        E = E - (E - e * R2D * math.sin(E * D2R) - M) / (1 - e * math.cos(E * D2R))
    xv = a * (math.cos(E * D2R) - e)
    yv = a * math.sqrt(1 - e * e) * math.sin(E * D2R)
    v = math.atan2(yv, xv) * R2D
    r = math.sqrt(xv * xv + yv * yv)

    # ecliptic coords
    xh = r * (math.cos(N * D2R) * math.cos((v + w) * D2R)
              - math.sin(N * D2R) * math.sin((v + w) * D2R) * math.cos(i * D2R))
    yh = r * (math.sin(N * D2R) * math.cos((v + w) * D2R)
              + math.cos(N * D2R) * math.sin((v + w) * D2R) * math.cos(i * D2R))
    zh = r * math.sin((v + w) * D2R) * math.sin(i * D2R)
    lonm = _rev(math.atan2(yh, xh) * R2D)
    latm = math.atan2(zh, math.sqrt(xh * xh + yh * yh)) * R2D

    # major perturbations
    slon, _ = _sun_lon(d)
    Ms = _rev(356.0470 + 0.9856002585 * d)
    Lm = _rev(N + w + M)
    Dm = _rev(Lm - slon)          # elongation
    F = _rev(Lm - N)
    lonm += (-1.274 * math.sin((M - 2 * Dm) * D2R)
             + 0.658 * math.sin(2 * Dm * D2R)
             - 0.186 * math.sin(Ms * D2R)
             - 0.059 * math.sin((2 * M - 2 * Dm) * D2R)
             - 0.057 * math.sin((M - 2 * Dm + Ms) * D2R)
             + 0.053 * math.sin((M + 2 * Dm) * D2R))
    latm += (-0.173 * math.sin((F - 2 * Dm) * D2R)
             - 0.055 * math.sin((M - F - 2 * Dm) * D2R)
             - 0.046 * math.sin((M + F - 2 * Dm) * D2R)
             + 0.033 * math.sin((F + 2 * Dm) * D2R))

    # ecliptic -> equatorial
    ecl = (23.4393 - 3.563e-7 * d) * D2R
    xg = math.cos(lonm * D2R) * math.cos(latm * D2R)
    yg = math.sin(lonm * D2R) * math.cos(latm * D2R)
    zg = math.sin(latm * D2R)
    xe = xg
    ye = yg * math.cos(ecl) - zg * math.sin(ecl)
    ze = yg * math.sin(ecl) + zg * math.cos(ecl)
    ra = _rev(math.atan2(ye, xe) * R2D)
    dec = math.atan2(ze, math.sqrt(xe * xe + ye * ye)) * R2D

    # local sidereal time — the 280.46° constant is referenced to J2000.0
    # (2000 Jan 1 12:00 UT) but d counts from Schlyter's epoch (2000 Jan 0.0),
    # 1.5 days earlier; without the -1.5 the moon lands ~181° off in hour angle
    gmst = _rev(280.46061837 + 360.98564736629 * (d - 1.5))
    lst = _rev(gmst + lon)
    ha = _rev(lst - ra)
    if ha > 180:
        ha -= 360

    sin_alt = (math.sin(dec * D2R) * math.sin(lat * D2R)
               + math.cos(dec * D2R) * math.cos(lat * D2R) * math.cos(ha * D2R))
    alt = math.asin(sin_alt) * R2D
    az = math.atan2(math.sin(ha * D2R),
                    math.cos(ha * D2R) * math.sin(lat * D2R)
                    - math.tan(dec * D2R) * math.cos(lat * D2R)) * R2D
    az = _rev(az + 180)  # from north, clockwise

    # topocentric parallax correction (moon is close!)
    alt -= 0.95 * math.cos(alt * D2R)

    # phase from elongation
    elong = math.acos(math.cos((slon - lonm) * D2R) * math.cos(latm * D2R)) * R2D
    illum = (1 - math.cos(elong * D2R)) / 2.0
    waxing = _rev(lonm - slon) < 180
    return alt, az, illum, waxing


def phase_name(illum, waxing):
    if illum < 0.03:
        return "NEW MOON"
    if illum > 0.97:
        return "FULL MOON"
    if illum < 0.35:
        return "WAXING CRESCENT" if waxing else "WANING CRESCENT"
    if illum < 0.65:
        return "FIRST QUARTER" if waxing else "LAST QUARTER"
    return "WAXING GIBBOUS" if waxing else "WANING GIBBOUS"
