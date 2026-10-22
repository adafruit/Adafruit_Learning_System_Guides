# SPDX-FileCopyrightText: 2026 John Park with Claude Opus 5.5 for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Cornell box path tracer: drives turbo_source/cornell_asm.py row by row.

Each pass adds one sample to every pixel of a SIZE x SIZE image centered on
the screen; the image refines pass by pass.
"""

import cornell_asm
import cornell_scene as scene
import display
import mem


class Cornell:
    def __init__(self, screen, scratch=None):
        """screen: a display.Display (back=False); scratch: SRAM for the
        parameter block, which the kernel reads all the time."""
        words = scene.WORDS
        if scratch is not None and len(scratch) >= 4 * words:
            self.block = memoryview(scratch)[: 4 * words].cast("I")
        else:
            self.block = memoryview(bytearray(4 * words)).cast("I")
        for i, word in enumerate(scene.BLOCK):
            self.block[i] = word
        self.block_address = mem.address(self.block)
        if self.block_address < mem.SRAM:
            print(
                "warning: Cornell block is in PSRAM (0x%08x): tracing will be slow"
                % self.block_address
            )
        self.accum = bytearray(scene.SIZE * scene.SIZE * 12)  # 3 floats per pixel
        self.accum_address = mem.address(self.accum)
        left = (display.WIDTH - scene.SIZE) // 2
        top = (display.HEIGHT - scene.SIZE) // 2
        self.out_address = mem.address(screen.screen) + (top * display.WIDTH + left) * 2
        self.passes = 0
        self.white_walls = False
        self.boxes = False

    def set_boxes(self, boxes):
        """The classic two boxes, or the two spheres; starts over."""
        self.block[scene.MODE] = 1 if boxes else 0
        self.boxes = boxes
        self.reset()

    def set_white_walls(self, white):
        """White side walls, or the classic red and green; starts over."""
        words = scene.WHITE_WALLS if white else scene.COLORED_WALLS
        for slot, word in zip(scene.WALL_SLOTS, words):
            self.block[slot] = word
        self.white_walls = white
        self.reset()

    def reset(self):
        mem.zero(self.accum, len(self.accum) // 4)
        self.passes = 0

    def trace_row(self, row):
        block = self.block
        block[scene.ACCUM] = self.accum_address + row * scene.SIZE * 12
        block[scene.OUT] = self.out_address + row * display.WIDTH * 2
        block[scene.INDEX] = row * scene.SIZE
        block[scene.ROW] = row
        cornell_asm.trace_row(self.block_address)

    def begin_pass(self):
        self.block[scene.PASS] = self.passes
        self.block[scene.SAMPLES] = self.passes + 1

    def end_pass(self):
        self.passes += 1
