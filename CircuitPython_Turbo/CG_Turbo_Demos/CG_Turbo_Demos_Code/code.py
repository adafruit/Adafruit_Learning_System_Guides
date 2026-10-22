# SPDX-FileCopyrightText: 2026 John Park with Claude Opus 5.5 for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Boot into the demo menu (menu.py).

To run one demo directly while developing, set DEMO to its module instead:
voxel_demo, cornell_demo, metaballs_demo or meshes_demo. Keep this
file tiny: demos allocate their SRAM framebuffers first thing, and anything
imported before them uses up SRAM.
"""

DEMO = "menu"

__import__(DEMO)
