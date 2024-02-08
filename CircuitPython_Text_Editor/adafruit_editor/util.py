# SPDX-FileCopyrightText: 2023 Jeff Epler for Adafruit Industries
#
# SPDX-License-Identifier: MIT
def readonly():
    try:
        import storage  # pylint: disable=import-outside-toplevel
    except ImportError:
        return False

    return storage.getmount("/").readonly
