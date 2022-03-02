# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""Example of infinite loop. Final print statement is never reached."""
print("Loop starting!")
while True:
    print("Loop running!")
print("Loop finished!")
