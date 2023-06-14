# SPDX-FileCopyrightText: 2023 Eva Herrada for Adafruit Industries
# SPDX-License-Identifier: MIT

from subprocess import check_output
import os

while True:
    SIGNAL = check_output('signal-cli receive', shell=True).decode("utf-8")
    if "Body" in SIGNAL:
        signal_msg = SIGNAL.split("Body")[1].split("\n")[0][2:]
        print(signal_msg)
        os.system("touch message")
        with open("message", "w") as F: # pylint: disable=unspecified-encoding
            F.write(signal_msg)
