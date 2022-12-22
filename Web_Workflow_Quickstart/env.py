# SPDX-FileCopyrightText: 2022 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import os
import storage
import microcontroller

SETTINGS_FOLDER = "/"

# Get all files in the format of xxxxxxxxxx.toml except settings.toml
def enumerate_toml_files():
    found_files = []
    all_files = os.listdir(SETTINGS_FOLDER)
    for current_file in all_files:
        if current_file[:2] != "._" and current_file[-5:] == ".toml" and current_file != "settings.toml":
            found_files.append(SETTINGS_FOLDER + current_file)
    return found_files


# Compare settings.toml to enumerated toml files
def get_current_toml_file(enumerated_files):
    with open("settings.toml") as settings:
        settings_lines = settings.readlines()
        for toml_file in enumerated_files:
            with open(toml_file) as f:
                lines = f.readlines()
                if len(settings_lines) != len(lines):
                    continue
                file_may_match = True
                for line_no, settings_line in enumerate(settings_lines):
                    if settings_line != lines[line_no]:
                        file_may_match = False
                        break
                if not file_may_match:
                    continue
                return toml_file
    return None


# Erase settings.toml then write the contents of the new settings.toml file
def change_toml_file(toml_file):
    try:
        storage.remount("/", False)
        open("settings.toml", "w").close()
        with open("settings.toml", "w") as settings, open(toml_file) as f:
            for line in f.readlines():
                settings.write(line)
        settings.close()
        print("Done. Hard resetting board...")
        microcontroller.reset()
    except RuntimeError:
        print("You can't change the env file with this script while USB is mounted")


# Return a prettier name than the env file
def pretty_name(toml_file):
    name = toml_file.rsplit("/", 1)[1]
    name = name[:-5]
    name = name[0].upper() + name[1:]
    return f"{name} toml file"

toml_files = enumerate_toml_files()

if len(toml_files) < 2:
    print("You need to have at least 2 .toml files to change")

result = get_current_toml_file(toml_files)
if result:
    toml_files.remove(result)
print("WARNING: This will overwrite all of your current settings.toml file settings.")
if len(toml_files) == 1:
    answer = input(f"Change to {pretty_name(toml_files[0])}? ")
    answer = answer.lower()
    if answer in ("y", "yes"):
        change_toml_file(toml_files[0])
else:
    valid_selection = False
    while not valid_selection:
        print("Select an option:")
        for index, file in enumerate(toml_files):
            print(f"{index + 1}: {pretty_name(file)}")
        answer = input("Which option would you like? ")
        if answer.isdigit() and 0 < int(answer) <= len(toml_files):
            valid_selection = True
            change_toml_file(toml_files[int(answer) - 1])
        print(f"{answer} was an invalid selection.\n")
