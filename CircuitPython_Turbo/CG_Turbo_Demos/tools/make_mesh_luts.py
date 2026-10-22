#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 John Park with Claude Opus 5.5 for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Lighting tables for the 3D model demo: CG_Turbo_Demos_Code/mesh_luts.bin.

    python3 tools/make_mesh_luts.py

For each model (MODELS, in order), four 64 x 64 little-endian u16 tables,
back to back: rgb565 for Lambert (diffuse only), Phong (specular from the
reflected light, (R.V)^n) and Blinn (specular from the half vector, (N.H)^n),
with the same light, material and exponent, so Phong and Blinn differ only
in the specular model; then Phong for a textured surface, as m | h << 8: the
texel scaled by m / 32 (diffuse), plus h * 0x0841 (white, h / 31 of full:
the highlight), m small enough that no channel overflows (turbo_source/mesh.py). The
light is white; each model has its own color. Each is indexed by a
view-space normal: [iy * 64 + ix], nx = (2 ix + 1 - 64) / 63, ny likewise
(y up), facing the camera. The light is directional and the view nearly
orthographic, so a pixel's lighting depends only on its normal: these tables
are the per-pixel lighting.
"""

import pathlib

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent

# each model's diffuse color (RGB, 0-1), in meshview's model order
MODELS = (
    ("teapot", np.array([0.80, 0.68, 0.57])),  # glazed clay, a little cooler
    ("bunny", np.array([0.74, 0.74, 0.76])),  # light gray
)
AMBIENT = 0.12
LIGHT = np.array([-0.45, 0.55, -0.70])  # toward the light: upper left, the camera's side
SPECULAR = 0.75
SHININESS = 24
MODES = ("lambert", "phong", "blinn", "texture")


def rgb565(c):
    c = np.clip(np.asarray(c) * 255 + 0.5, 0, 255).astype(np.uint32)
    return ((c[..., 0] >> 3) << 11) | ((c[..., 1] >> 2) << 5) | (c[..., 2] >> 3)


def textured(diffuse, specular):
    """m | h << 8: out = texel * m / 32 + white * h / 31, per channel at most
    full (red: floor(31 m / 32) + h <= 31; green and blue follow)."""
    h = np.round(31 * np.clip(specular, 0, 1)).astype(np.uint32)
    room = (32 * (31 - h)) // 31
    m = np.minimum(np.round(32 * diffuse * (1 - h / 31)).astype(np.uint32), room)
    return m | (h << 8)


def table(mode, color_of_surface):
    i = (np.arange(64) * 2 + 1 - 64) / 63  # meshview's NORMAL_SCALE
    nx, ny = np.meshgrid(i, i)
    nz = -np.sqrt(np.clip(1 - nx * nx - ny * ny, 0, 1))  # toward the camera, which looks along +z
    n = np.stack([nx, ny, nz], axis=-1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    light = LIGHT / np.linalg.norm(LIGHT)
    view = np.array([0.0, 0.0, -1.0])  # from the surface to the camera
    diffuse = np.clip(n @ light, 0, 1)
    color = color_of_surface * (AMBIENT + (1 - AMBIENT) * diffuse[..., None])
    if mode == "texture":
        reflected = 2 * (n @ light)[..., None] * n - light
        return textured(AMBIENT + (1 - AMBIENT) * diffuse, SPECULAR * np.clip(reflected @ view, 0, 1) ** SHININESS)
    if mode == "phong":
        reflected = 2 * (n @ light)[..., None] * n - light
        color = color + SPECULAR * (np.clip(reflected @ view, 0, 1) ** SHININESS)[..., None]
    elif mode == "blinn":
        half = (light + view) / np.linalg.norm(light + view)
        color = color + SPECULAR * (np.clip(n @ half, 0, 1) ** SHININESS)[..., None]
    return rgb565(color)


def main():
    out = ROOT / "CG_Turbo_Demos_Code" / "mesh_luts.bin"
    data = b"".join(table(mode, color).astype("<u2").tobytes() for _, color in MODELS for mode in MODES)
    out.write_bytes(data)
    print("wrote", out.relative_to(ROOT), len(data), "bytes:", ", ".join(name for name, _ in MODELS), "x", ", ".join(MODES))


if __name__ == "__main__":
    main()
