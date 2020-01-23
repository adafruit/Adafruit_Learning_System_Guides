# This file is where you keep secret settings, passwords, and tokens!
# If you put them in the code you risk committing that info or sharing it

secrets = {
    'ssid' : 'yourwifissid',
    'password' : 'yourwifipassword',
    'timezone' : "America/New_York", # http://worldtimeapi.org/timezones
    # https://github.com/pyotp/pyotp example
    'totp_keys' : [("Discord ", "JBSWY3DPEHPK3PXP"),
                   ("Gmail", "JBSWY3DPEHPK3PZP"),
                   ("GitHub", "JBSWY5DZEHPK3PXP"),
                   ("Adafruit", "JBSWY6DZEHPK3PXP"),
                   ("Outlook", "JBSWY7DZEHPK3PXP")]
    }
