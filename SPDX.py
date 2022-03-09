# SPDX-FileCopyrightText: 2022 Eva Herrada for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import os
import subprocess
import sys

print("Starting SPDX Check")

# add user bin to path!
BUILD_DIR = ""
# add user bin to path!
try:
    # If we're on actions
    BUILD_DIR = os.environ["GITHUB_WORKSPACE"]
except KeyError:
    try:
        # If we're on travis
        BUILD_DIR = os.environ["TRAVIS_BUILD_DIR"]
    except KeyError:
        # If we're running on local machine
        BUILD_DIR = os.path.abspath(".")

print(f"Running in {BUILD_DIR}\n")
files = []
missing_file = []

fail = False


def compare(file_, line_, correct):
    old = line_[:-1]
    try:
        right = line_.split(":")[1][:-1]
    except IndexError:
        print(f'{file_.split("_Guides/")[1]} may have an SPDX format issue:')
        print("The following line:")
        print(old)
        print("May be missing a colon.\nIt should look like this:")
        print(correct, "\n")
        return True

    new = f"{correct}{right.strip()}"
    cmd = f'CMD="diff <(echo \\"{old}\\") <(echo \\"{new}\\")"; /bin/bash -c "$CMD"'
    output = subprocess.getoutput(cmd).split("\n")

    if output:
        print(f'{file_.split("_Guides/")[1]} may have an SPDX format issue:')
        print("Change this:")
        print(output[1][2:])
        print("To this:")
        print(output[3][2:], "\n")
        return True

    return False


for r, d, f in os.walk(BUILD_DIR):
    for file in f:
        if file.split(".")[-1] in ("py", "cpp", "ino", "h"):
            files.append(os.path.join(r, file))

for file in files:
    with open(file, "r") as F:
        lines = []
        for line in F.readlines():
            if line[0] != "#" and line[:2] != "//":
                break
            lines.append(line)
        status = {"copyright": False, "license": False, "licensefile": False}
        for line in lines:
            if "SPDX-FileCopyrightText" in line:
                status["copyright"] = True
                if (
                    "# SPDX-FileCopyrightText: " not in line
                    and "// SPDX-FileCopyrightText: " not in line
                ):
                    if file.endswith(".py"):
                        if compare(file, line, "# SPDX-FileCopyrightText: "):
                            fail = True
                    else:
                        if compare(file, line, "// SPDX-FileCopyrightText: "):
                            fail = True

            if "SPDX-License-Identifier" in line:
                failed = False
                if (
                    "# SPDX-License-Identifier: " not in line
                    and "// SPDX-License-Identifier: " not in line
                ):
                    if file.endswith(".py"):
                        if compare(file, line, "# SPDX-License-Identifier: "):
                            fail = True
                            failed = True
                    else:
                        if compare(file, line, "// SPDX-License-Identifier: "):
                            fail = True
                            failed = True
                if not failed:
                    license_name = line.split("SPDX-License-Identifier: ")[1][:-1]
                    status["license"] = True
                    if os.path.isfile(BUILD_DIR + f"/LICENSES/{license_name}.txt"):
                        status["licensefile"] = True
                    elif license_name not in missing_file:
                        missing_file.append(f"LICENSES/{license_name}.txt")

        if not all(status.values()):
            fail = True
            print(f"{file} is missing SPDX\n")
            continue
        if not status["copyright"]:
            fail = True
            print(f"{file}: SPDX-FileCopyrightText line is missing")
        if not status["license"]:
            fail = True
            print(f"{file}: SPDX-License-Identifier line is missing")
        if not status["licensefile"] and status["license"]:
            fail = True
            print(f"{file}: {license_name}.txt is missing from LICENSES/")
        if (
            not status["copyright"]
            or not status["license"]
            or not status["licensefile"]
        ):
            print("\n")

if fail:
    if missing_file:
        print("Missing files:", missing_file)
    sys.exit(-1)
sys.exit(0)
