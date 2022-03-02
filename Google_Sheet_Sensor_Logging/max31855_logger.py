# SPDX-FileCopyrightText: 2020 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
from datetime import datetime
import board
import digitalio
import adafruit_max31855
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

#--| User Config |-----------------------------------------------
SERVICE_ACCOUNT_FILE = 'YOUR_CREDENTIALS_FILE.json'
SPREADSHEET_ID = 'YOUR_SHEET_ID'
DATA_LOCATION = 'A1'
UPDATE_RATE = 60
#--| User Config |-----------------------------------------------

# Sensor setup
cs = digitalio.DigitalInOut(board.C0)
max31855 = adafruit_max31855.MAX31855(board.SPI(), cs)

# Google Sheets API setup
SCOPES = ['https://spreadsheets.google.com/feeds',
          'https://www.googleapis.com/auth/drive']
CREDS = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
SHEET = build('sheets', 'v4', credentials=CREDS).spreadsheets()

# Logging loop
print("Logging...")
while True:
    values = [[datetime.now().isoformat(), max31855.temperature]]
    SHEET.values().append(spreadsheetId=SPREADSHEET_ID,
                          valueInputOption='RAW',
                          range=DATA_LOCATION,
                          body={'values' : values}).execute()
    time.sleep(UPDATE_RATE)
