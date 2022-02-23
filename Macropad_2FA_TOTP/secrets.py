# SPDX-FileCopyrightText: 2021 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# This file is where you keep secret settings, passwords, and tokens!
# If you put them in the code you risk committing that info or sharing it

secrets = {
                  # tuples of name, sekret key, color
    'totp_keys' : [("Github", "JBSWY3DPEHPK3PXP", 0x8732A8),
                   ("Discord", "JBSWY3DPEHPK3PXQ", 0x32A89E),
                   ("Slack", "JBSWY5DZEHPK3PXR", 0xFC861E),
                   ("Basecamp", "JBSWY6DZEHPK3PXS", 0x55C24C),
                   ("Gmail", "JBSWY7DZEHPK3PXT", 0x3029FF),
                   None,
                   None, # must have 12 entires
                   None, # set None for unused keys
                   None,
                   ("Hello Kitty", "JBSWY7DZEHPK3PXU", 0xED164F),
                   None,
                   None,
                  ]
    }