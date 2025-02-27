<!--
SPDX-FileCopyrightText: 2023 Jeff Epler for Adafruit Industries

SPDX-License-Identifier: MIT
-->

This is a port of runcpm to the raspberry pi pico.

It is based on:
 * [RunCPM](https://github.com/MockbaTheBorg/RunCPM/)
 * [RunCPM_RPi_Pico](https://github.com/guidol70/RunCPM_RPi_Pico)

It works on a Raspberry Pi Pico (or Pico W). It uses the internal flash
for storage, and can be mounted as USB storage.

If your Pico is placed on the Pico DV carrier board, you also get a 100x30
character screen to enjoy your CP/M output on!

First, build for your device. You must
 * Use the Philhower Pico Core
 * In the Tools menu, select
   * A flash size option that includes at least 512kB for filesystem
   * USB Stack: Adafruit TinyUSB

After it boots the first time, you need to
 * Format the flash device on your host computer
 * Create the folder "<DEVICE>/A/0"
 * Put something useful in that folder, such as [Zork](http://www.retroarchive.org/cpm/games/zork123_80.zip)
   * Files must respect the "8.3" naming convention (8 letters filename + 3 letters extension) and be all uppercase
 * Safely eject the drive, then reset the emulator.
 * Now at the "A0>" prompt you can run "ZORK1".
