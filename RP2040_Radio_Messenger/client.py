# SPDX-FileCopyrightText: 2023 Eva Herrada for Adafruit Industries
# SPDX-FileCopyrightText: 2018 MikeTheWatchGuy
# SPDX-License-Identifier: LGPL-3.0-only

# Partially based on:
# https://github.com/PySimpleGUI/PySimpleGUI/blob/master/DemoPrograms/Demo_Chat_With_History.py

import time
import pathlib
import os

import PySimpleGUI as sg
import serial
from cryptography.fernet import Fernet

# Replace NUMBER with your phone number including country code
NUMBER = "REPLACE_ME"

try:
    with open("secret.key", "rb") as key_file:
        key = key_file.read()
except FileNotFoundError:
    with open("secret.key", "wb") as key_file:
        key_file.write(Fernet.generate_key())

    with open("secret.key", "rb") as key_file:
        key = key_file.read()

aes = Fernet(key)

port = int(input("port: /dev/ttyACM"))

s = int(input("signal?"))

ser = serial.Serial(f"/dev/ttyACM{port}", 115200, timeout=0.050)

last_time = time.monotonic()


def ChatBotWithHistory():  # pylint: disable=too-many-statements,too-many-branches,too-many-locals
    # -------  Make a new Window  ------- #
    # give our form a spiffy set of colors
    sg.theme("DarkPurple4")

    layout = [
        [sg.Text("Encrypted LoRa Messaging Client", size=(40, 1))],
        [sg.Output(size=(127, 30), key="history", font=("Helvetica 10"))],
        [sg.Button("CLEAR", button_color=(sg.YELLOWS[0], sg.BLUES[0]))],
        [
            sg.ML(size=(85, 5), enter_submits=True, key="query", do_not_clear=False),
            sg.Button(
                "SEND", button_color=(sg.YELLOWS[0], sg.BLUES[0]), bind_return_key=True
            ),
            sg.Button("EXIT", button_color=(sg.YELLOWS[0], sg.GREENS[0])),
        ],
    ]

    window = sg.Window(
        "Chat window with history",
        layout,
        default_element_size=(30, 2),
        font=("Helvetica", " 13"),
        default_button_element_size=(8, 2),
        return_keyboard_events=True,
    )

    # ---===--- Loop taking in user input and using it  --- #
    command_history = []
    history_offset = 0

    last_id = None
    while True:
        event, value = window.read(timeout=0.05)

        while ser.in_waiting:
            data_in = ser.readline()
            mess = data_in.decode()[:-1]
            try:
                if mess.startswith("Received"):
                    mess = mess.split(" ", 1)[1]
                    mess_id, text = mess.split("|", 1)
                    text = aes.decrypt(text.encode()).decode()
                    print(f"> {text}")
                    if s:
                        os.system(f'signal-cli send -m "{text}" {NUMBER}')
                elif "|" in mess:
                    mess_id, text = mess.split("|", 1)
                    last_id = int(mess_id)
                if "Delivered" in mess:
                    mess_id = int(mess.split(" ", 1)[1])
                    if mess_id == last_id:
                        print("Delivered")
                if "RSSI" in mess:
                    print(mess + "\n")
            except Exception as error:  # pylint: disable=broad-except
                print(error)

        if os.path.isfile("message"):
            print("entered")
            time.sleep(0.1)
            path = pathlib.Path("message")
            with path.open() as file:
                signal = file.readline().rstrip()
            print(f"< {signal}")
            ser.write(aes.encrypt(signal.encode()))
            ser.write(signal.encode())
            ser.write("\r".encode())
            command_history.append(signal)
            history_offset = len(command_history) - 1
            # manually clear input because keyboard events blocks clear
            window["query"].update("")
            os.system("rm message")

        if event:
            if event == "SEND":
                query = value["query"].rstrip()
                print(f"< {query}")
                ser.write(aes.encrypt(query.encode()))
                ser.write(query.encode())
                ser.write("\r".encode())
                command_history.append(query)
                history_offset = len(command_history) - 1
                # manually clear input because keyboard events blocks clear
                window["query"].update("")
                # EXECUTE YOUR COMMAND HERE

            elif event in (sg.WIN_CLOSED, "EXIT"):  # quit if exit event or X
                break

            elif "Up" in event and len(command_history) != 0:
                command = command_history[history_offset]
                # decrement is not zero
                history_offset -= 1 * (history_offset > 0)
                window["query"].update(command)

            elif "Down" in event and len(command_history) != 0:
                # increment up to end of list
                history_offset += 1 * (history_offset < len(command_history) - 1)
                command = command_history[history_offset]
                window["query"].update(command)

            elif event == "CLEAR":
                window["history"].update("")

            elif "Escape" in event:
                window["query"].update("")


ChatBotWithHistory()
