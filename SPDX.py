import os

# add user bin to path!
BUILD_DIR = ''
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
        pass

files = []
missing_file = []

fail = False

for r, d, f in os.walk(BUILD_DIR):
    for file in f:
        if file.split('.')[-1] in ("py", "cpp", "ino", "h"):
            files.append(os.path.join(r, file))

for file in files:
    with open(file, "r") as F:
        lines = []
        for line in F.readlines():
            if line[0] != "#" and line[:2] != "//":
                break
            lines.append(line)
        status = {"copyright": False,
                  "license": False,
                  "licensefile": False}
        for line in lines:
            if "SPDX-FileCopyrightText:" in line:
                status["copyright"] = True
            if "SPDX-License-Identifier:" in line:
                license_name = line.split("SPDX-License-Identifier: ")[1][:-1]
                status["license"] = True
                if os.path.isfile(BUILD_DIR+f"/LICENSES/{license_name}.txt"):
                    status["licensefile"] = True
                elif license_name not in missing_file:
                    missing_file.append(f"LICENSES/{license_name}.txt")

        if not all(status.values()):
            fail = True
            print(f"{file} is missing SPDX")
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

if fail:
    if missing_file:
        print("Missing files:", missing_file)
    exit(-1)
exit(0)
