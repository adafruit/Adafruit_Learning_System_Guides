# SPDX-FileCopyrightText: 2022 Tim C for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
GitHub Actions Status Tower Light
"""
import json
import time
import os
import serial
import requests

# Customisations for this program
# Update with the URL from any repo running Actions to get the status. Defaults to CircuitPython.
REPO_WORKFLOW_URL = "https://api.github.com/repos/kattni/circuitpython/actions/workflows/build.yml/runs"  # pylint: disable=line-too-long
# The rate at which the program will query GitHub for an updated status. You can increase or
# decrease the delay time to fit the duration and frequency of Actions runs on your repo.
# Defaults to 3 minutes.
POLL_DELAY = 60 * 3  # 3 minutes
# The length of time in seconds the LED remains on once the Actions run has completed.
# Defaults to 30 seconds.
COMPLETION_LIGHT_TIME = 30  # seconds
# The length of time in seconds the buzzer beeps once the actions run has completed.
# Set this to 0 to disable the buzzer. Defaults to 1 second.
COMPLETION_BUZZER_TIME = 1  # seconds
# Determines whether the code sends commands to the tower light. Set it to False to disable the
# tower light code and run this example without requiring the tower light. Defaults to True.
ENABLE_USB_LIGHT_MESSAGES = True

# Serial port. Update the serial port to match the port of the tower light on your computer.
# Windows will be a COM** port. If you are on Windows, comment out the Mac/Linux line, and
# uncomment the line immediately below.
# serial_port = "COM57"
# Mac/Linux will be a /dev/** path to the serial port. If you're having trouble finding it,
# check the contents of the /dev/ directory with the tower light unplugged and plugged in.
serial_port = "/dev/tty.usbserial-144430"

# USB Tower Light constants
RED_ON = 0x11
RED_OFF = 0x21
RED_BLINK = 0x41

YELLOW_ON = 0x12
YELLOW_OFF = 0x22
YELLOW_BLINK = 0x42

GREEN_ON = 0x14
GREEN_OFF = 0x24
GREEN_BLINK = 0x44

BUZZER_ON = 0x18
BUZZER_OFF = 0x28
BUZZER_BLINK = 0x48

# Baud rate for serial communication
baud_rate = 9600


def send_command(serialport, cmd):
    serialport.write(bytes([cmd]))


def reset_state():
    # Clean up any old state
    send_command(mSerial, BUZZER_OFF)
    send_command(mSerial, RED_OFF)
    send_command(mSerial, YELLOW_OFF)
    send_command(mSerial, GREEN_OFF)


def buzzer_on_completion():
    if COMPLETION_BUZZER_TIME > 0:
        send_command(mSerial, BUZZER_ON)
        time.sleep(COMPLETION_BUZZER_TIME)
        send_command(mSerial, BUZZER_OFF)


already_shown_ids = []

headers = {'Accept': "application/vnd.github.v3+json",
           'Authorization': f"token {os.getenv('GITHUB_API_TOKEN')}"}


mSerial = None
if ENABLE_USB_LIGHT_MESSAGES:
    print("Opening serial port.")
    mSerial = serial.Serial(serial_port, baud_rate)

print("Starting Github Actions Status Watcher.")
print("Press Ctrl-C to Exit")
try:
    while True:
        print("Fetching workflow run status.")
        response = requests.get(f"{REPO_WORKFLOW_URL}?per_page=1", headers=headers)
        response_json = response.json()
        with open("action_status_result.json", "w") as f:
            f.write(json.dumps(response_json))

        workflow_run_id = response_json['workflow_runs'][0]['id']
        if workflow_run_id not in already_shown_ids:
            status = response_json['workflow_runs'][0]['status']
            conclusion = response_json['workflow_runs'][0]['conclusion']
            print(f"Status - Conclusion: {status} - {conclusion}")

            if status == "queued":
                print("Actions run status: Queued.")
                if ENABLE_USB_LIGHT_MESSAGES:
                    print("Sending serial command 'YELLOW_BLINK'.")
                    send_command(mSerial, YELLOW_BLINK)

            if status == "in_progress":
                print("Actions run status: In progress.")
                if ENABLE_USB_LIGHT_MESSAGES:
                    print("Sending serial command 'YELLOW_ON'.")
                    send_command(mSerial, YELLOW_ON)

            if status == "completed":
                print(f"Adding {workflow_run_id} to shown workflow IDs.")
                already_shown_ids.append(workflow_run_id)

                if conclusion == "success":
                    print("Actions run status: Completed - successful.")
                    if ENABLE_USB_LIGHT_MESSAGES:
                        send_command(mSerial, YELLOW_OFF)
                        print("Sending serial command 'GREEN_ON'.")
                        send_command(mSerial, GREEN_ON)
                        buzzer_on_completion()
                    time.sleep(COMPLETION_LIGHT_TIME - COMPLETION_BUZZER_TIME)
                    if ENABLE_USB_LIGHT_MESSAGES:
                        print("Sending serial command 'GREEN_OFF'.")
                        send_command(mSerial, GREEN_OFF)

                if conclusion == "failure":
                    print("Actions run status: Completed - failed.")
                    if ENABLE_USB_LIGHT_MESSAGES:
                        send_command(mSerial, YELLOW_OFF)
                        print("Sending serial command 'RED_ON'.")
                        send_command(mSerial, RED_ON)
                        buzzer_on_completion()
                    time.sleep(COMPLETION_LIGHT_TIME - COMPLETION_BUZZER_TIME)
                    if ENABLE_USB_LIGHT_MESSAGES:
                        print("Sending serial command 'RED_OFF'.")
                        send_command(mSerial, RED_OFF)

                if conclusion == "cancelled":
                    print("Actions run status: Completed - cancelled.")
                    if ENABLE_USB_LIGHT_MESSAGES:
                        send_command(mSerial, YELLOW_OFF)
                        print("Sending serial command 'RED_BLINK'.")
                        send_command(mSerial, RED_BLINK)
                        buzzer_on_completion()
                    time.sleep(COMPLETION_LIGHT_TIME - COMPLETION_BUZZER_TIME)
                    if ENABLE_USB_LIGHT_MESSAGES:
                        print("Sending serial command 'RED_OFF'.")
                        send_command(mSerial, RED_OFF)

        else:
            print("Already followed the current run.")
        time.sleep(POLL_DELAY)

except KeyboardInterrupt:
    print("\nExiting Github Actions Status Watcher.")
    reset_state()
