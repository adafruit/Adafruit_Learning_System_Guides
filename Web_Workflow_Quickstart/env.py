# SPDX-FileCopyrightText: 2022 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import os
import storage
import microcontroller

# Get all files in the format of .env.xxxxxxxxxx
def enumerate_env_files():
    found_files = []
    all_files = os.listdir("/")
    for current_file in all_files:
        if current_file[:4] == ".env" and len(current_file) > 4:
            found_files.append(current_file)
    return found_files


# Compare .env to enumerated env files
def get_current_env_file(enumerated_files):
    with open(".env") as env:
        env_lines = env.readlines()
        for env_file in enumerated_files:
            with open(env_file) as f:
                lines = f.readlines()
                if len(env_lines) != len(lines):
                    continue
                file_may_match = True
                for line_no, env_line in enumerate(env_lines):
                    if env_line != lines[line_no]:
                        file_may_match = False
                        break
                if not file_may_match:
                    continue
                return env_file
    return None


# Erase .env then write the contents of the new env file
def change_env_file(env_file):
    try:
        storage.remount("/", False)
        open(".env", "w").close()
        with open(".env", "w") as env, open(env_file) as f:
            for line in f.readlines():
                env.write(line)
        env.close()
        print("Done. Hard resetting board...")
        microcontroller.reset()
    except RuntimeError:
        print("You can't change the env file with this script while USB is mounted")


# Return a prettier name than the env file
def pretty_name(env_file):
    name = env_file[5:]
    name = name[0].upper() + name[1:]
    return f"{name} .env file"

env_files = enumerate_env_files()

if len(env_files) < 2:
    print("You need to have at least 2 env files to change")

result = get_current_env_file(env_files)
if result:
    env_files.remove(result)
print("WARNING: This will overwrite all of your current .env file settings.")
if len(env_files) == 1:
    answer = input(f"Change to {pretty_name(env_files[0])}? ")
    answer = answer.lower()
    if answer in ("y", "yes"):
        change_env_file(env_files[0])
else:
    valid_selection = False
    while not valid_selection:
        print("Select an option:")
        for index, file in enumerate(env_files):
            print(f"{index + 1}: {pretty_name(file)}")
        answer = input("Which option would you like? ")
        if answer.isdigit() and 0 < int(answer) <= len(env_files):
            valid_selection = True
            change_env_file(env_files[int(answer) - 1])
        print(f"{answer} was an invalid selection.\n")
