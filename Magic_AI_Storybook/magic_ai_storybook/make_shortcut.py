#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2023 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT
# Desktop Icon from <a href="https://www.flaticon.com/free-icons/book"
# title="book icons">Book icons created by Freepik - Flaticon</a>

import os


def create_folders(file_path):
    path = os.path.dirname(file_path)
    if not os.path.exists(path):
        os.makedirs(path)


def write_file(path, contents):
    create_folders(path)
    with open(path, "w") as f:
        f.write(contents)

    print(f"Shortcut created at {path}")


def main():
    APP_TITLE = "Magic Storybook"
    RUN_IN_TERMINAL = True
    APP_PATH = "~/Magic_AI_Storybook/story.py"
    APP_ICON = "~/Magic_AI_Storybook/images/magic_book_icon.png"
    FILENAME = "storybook.desktop"
    ENV_PATH = "~/story"
    AUTO_START = True

    if os.geteuid() == 0:
        username = os.environ["SUDO_USER"]
    else:
        username = os.getlogin()
    user_homedir = os.path.expanduser(f"~{username}")

    print("Username is ", username)
    print("User home directory is ", user_homedir)

    APP_PATH = APP_PATH.replace("~", user_homedir)
    APP_ICON = APP_ICON.replace("~", user_homedir)
    PYTHON_PATH = "python"
    if ENV_PATH is not None:
        ENV_PATH = ENV_PATH.replace("~", user_homedir)
        PYTHON_PATH = ENV_PATH + "/bin/" + PYTHON_PATH

    shortcut_template = f"""[Desktop Entry]
Comment=Run {APP_TITLE}
Terminal={"true" if RUN_IN_TERMINAL else "false"}
Name={APP_TITLE}
Exec=sudo -E env PATH=$PATH {PYTHON_PATH} {APP_PATH}
Type=Application
Icon={APP_ICON}
"""

    write_file(f"{user_homedir}/Desktop/{FILENAME}", shortcut_template)
    if AUTO_START:
        write_file(f"{user_homedir}/.config/autostart/{FILENAME}", shortcut_template)


if __name__ == "__main__":
    main()
