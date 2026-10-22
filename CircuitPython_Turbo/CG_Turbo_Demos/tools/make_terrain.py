#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 John Park with Claude Opus 5.5 for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Generate a tileable VoxelSpace terrain: height plus baked-lit color.

    python3 tools/make_terrain.py --size 512 --seed 7

Writes:
  CG_Turbo_Demos_Code/terrain16.bin  little-endian u16 texels, height << 8 | palette index:
                        the full map (--size squared), then mip levels at half
                        and quarter size, each wrapping and row-major
  CG_Turbo_Demos_Code/palette.bin    256 little-endian rgb565 colors
  CG_Turbo_Demos_Code/shade.bin      the lighting alone (sun and ambient occlusion, no
                        material colors), one byte per texel, same levels
  docs/terrain.png, terrain_height.png  previews of the full map
Heights are 0-255 map units.
"""

import argparse
import pathlib

import numpy as np
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
SEA = 0.30  # sea level, as a fraction of the height range


def spectral_noise(rng, n, beta):
    """Tileable fractal noise: white noise with amplitudes shaped to 1/f**beta."""
    f = np.fft.fftfreq(n)
    radius = np.sqrt(f[:, None] ** 2 + f[None, :] ** 2)
    radius[0, 0] = 1.0
    spectrum = np.fft.fft2(rng.standard_normal((n, n))) / radius ** beta
    spectrum[0, 0] = 0
    field = np.real(np.fft.ifft2(spectrum))
    return (field - field.min()) / (field.max() - field.min())


def blur(a, passes=2):
    """Cheap wrapping box blur."""
    for _ in range(passes):
        a = (a + np.roll(a, 1, 0) + np.roll(a, -1, 0) + np.roll(a, 1, 1) + np.roll(a, -1, 1)) / 5
    return a


def lerp_colors(t, stops):
    """Piecewise-linear color ramp; stops are (position, (r, g, b))."""
    positions = np.array([p for p, _ in stops])
    colors = np.array([c for _, c in stops], dtype=float)
    return np.stack([np.interp(t, positions, colors[:, k]) for k in range(3)], axis=-1)


def make(n, seed, speckle=0.0, smooth=2, color_blur=2):
    rng = np.random.default_rng(seed)
    base = spectral_noise(rng, n, 2.1)
    ridges = 1 - np.abs(spectral_noise(rng, n, 1.8) * 2 - 1)
    height = base * 0.75 + ridges ** 2 * base * 0.45
    height = (height - height.min()) / (height.max() - height.min())
    height = height ** 1.35  # wider valleys, sharper peaks
    if smooth:
        height = blur(height, smooth)
    land = np.maximum(height, SEA)

    # lighting from the slope of the land surface (water is flat)
    relief = 255 * 0.9
    gy, gx = np.gradient(land * relief)
    normal = np.stack([-gx, -gy, np.ones_like(gx)], axis=-1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    sun = np.array([-0.55, -0.45, 0.70])
    sun /= np.linalg.norm(sun)
    diffuse = np.clip(normal @ sun, 0, 1)
    # cavities darker than ridges, for some ambient-occlusion depth
    occlusion = np.clip(1 + (land - blur(land, 6)) * 6, 0.6, 1.15)
    slope = 1 - normal[..., 2]

    t = (height - SEA) / (1 - SEA)
    colors = lerp_colors(
        t,
        [
            (0.00, (194, 178, 128)),  # sand
            (0.05, (110, 150, 60)),  # grass
            (0.35, (60, 110, 45)),  # forest
            (0.60, (120, 105, 85)),  # rock
            (0.80, (150, 145, 140)),
            (0.88, (240, 240, 245)),  # snow
            (1.00, (255, 255, 255)),
        ],
    )
    rock = np.array([115, 100, 85], dtype=float)
    steep = np.clip((slope - 0.45) * 5, 0, 1)[..., None]
    colors = colors * (1 - steep) + rock * steep
    if speckle:
        colors *= (1 - speckle / 2 + speckle * rng.random((n, n)))[..., None]  # texture speckle
    shade = (0.35 + 0.75 * diffuse) * occlusion
    colors *= shade[..., None]

    water = height < SEA
    depth = np.clip((SEA - height) / 0.12, 0, 1)[..., None]
    water_color = lerp_colors(depth[..., 0], [(0, (60, 140, 160)), (1, (15, 45, 95))])
    colors = np.where(water[..., None], water_color, colors)

    if color_blur:
        # fine slope and texture detail aliases badly under point sampling
        colors = np.stack([blur(colors[..., k], color_blur) for k in range(3)], axis=-1)
        shade = blur(shade, color_blur)
    colors = np.clip(colors, 0, 255).astype(np.uint8)
    heights = np.clip(land * relief, 0, 255).astype(np.uint32)
    return heights, colors, np.clip(shade * (255 / 1.3), 0, 255)


MIP_LEVELS = 3


def halve(a):
    """2x2 box average (the map wraps, and sizes are powers of two)."""
    a = a.astype(float)
    return (a[0::2, 0::2] + a[1::2, 0::2] + a[0::2, 1::2] + a[1::2, 1::2]) / 4


def rgb565(colors):
    c = colors.astype(np.uint32)
    return ((c[..., 0] >> 3) << 11) | ((c[..., 1] >> 2) << 5) | (c[..., 2] >> 3)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--size", type=int, default=512)
    parser.add_argument("--seed", type=int, default=7)
    # fine detail aliases (flickers) under VoxelSpace's point sampling: see
    # tools/voxel_flicker.py and NOTES.md
    parser.add_argument("--speckle", type=float, default=0.0, help="per-texel color noise")
    parser.add_argument("--smooth", type=int, default=2, help="height blur passes")
    parser.add_argument("--color-blur", type=int, default=2, help="color blur passes")
    parser.add_argument("--out", type=pathlib.Path, default=ROOT / "CG_Turbo_Demos_Code")
    parser.add_argument("--previews", type=pathlib.Path, default=ROOT / "docs")
    options = parser.parse_args()
    if options.size & (options.size - 1):
        parser.error("--size must be a power of two")
    heights, colors, shade = make(options.size, options.seed, options.speckle, options.smooth, options.color_blur)
    options.out.mkdir(exist_ok=True)
    quantized = Image.fromarray(colors).quantize(256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    palette = np.array(quantized.getpalette()[: 256 * 3], dtype=np.uint8).reshape(-1, 3)
    levels = []
    shades = []
    level_heights = heights.astype(float)
    level_colors = colors.astype(float)
    level_shade = shade
    for level in range(MIP_LEVELS):
        if level:
            level_heights = halve(level_heights)
            level_colors = halve(level_colors)
            level_shade = halve(level_shade)
        image = Image.fromarray(np.clip(level_colors + 0.5, 0, 255).astype(np.uint8))
        index = np.array(image.quantize(palette=quantized, dither=Image.Dither.NONE), dtype=np.uint16)
        texels = (np.clip(level_heights + 0.5, 0, 255).astype(np.uint16) << 8) | index
        levels.append(texels.astype("<u2").tobytes())
        shades.append(np.clip(level_shade + 0.5, 0, 255).astype(np.uint8).tobytes())
        if level == 0:
            Image.fromarray(palette[index]).save(options.previews / "terrain.png")
    data = b"".join(levels)
    (options.out / "terrain16.bin").write_bytes(data)
    (options.out / "palette.bin").write_bytes(rgb565(palette).astype("<u2").tobytes())
    (options.out / "shade.bin").write_bytes(b"".join(shades))
    Image.fromarray(heights.astype(np.uint8)).save(options.previews / "terrain_height.png")
    print("wrote", options.out / "terrain16.bin", len(data), "bytes,", MIP_LEVELS, "levels; heights", heights.min(), "-", heights.max())

if __name__ == "__main__":
    main()
