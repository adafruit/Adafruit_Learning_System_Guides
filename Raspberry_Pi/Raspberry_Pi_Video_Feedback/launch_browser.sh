#!/bin/bash
# SPDX-FileCopyrightText: 2026 Tim Cocks, written for Adafruit Industries
#
# SPDX-License-Identifier: MIT
export DISPLAY=:0
systemd-cat -t glitch_cam_browser chromium --kiosk --disable-infobars --start-maximized http://localhost:5000/ &
