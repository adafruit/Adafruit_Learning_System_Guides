# SPDX-FileCopyrightText: 2020 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
from datetime import datetime
import board
import adafruit_bme280
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

#--| User Config |-----------------------------------------------
SERVICE_ACCOUNT_FILE = 'YOUR_CREDENTIALS_FILE.json'
SPREADSHEET_ID = 'YOUR_SHEET_ID'
DATA_LOCATION = 'A1'
UPDATE_RATE = 60
#--| User Config |-----------------------------------------------

# Sensor setup
bme = adafruit_bme280.Adafruit_BME280_I2C(board.I2C())

# Google Sheets API setup
SCOPES = ['https://spreadsheets.google.com/feeds',
          'https://www.googleapis.com/auth/drive']
CREDS = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
SHEET = build('sheets', 'v4', credentials=CREDS).spreadsheets()

# Logging loop
print("Logging...")
while True:
    values = [[datetime.now().isoformat(), bme.pressure, bme.temperature, bme.humidity]]
    SHEET.values().append(spreadsheetId=SPREADSHEET_ID,
                          valueInputOption='RAW',
                          range=DATA_LOCATION,
                          body={'values' : values}).execute()
    time.sleep(UPDATE_RATE)
