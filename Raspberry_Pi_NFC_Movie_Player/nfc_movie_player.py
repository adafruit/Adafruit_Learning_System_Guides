# SPDX-FileCopyrightText: Copyright (c) 2024 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import subprocess
import csv
from datetime import datetime
import os
import tkinter as tk
from PIL import Image, ImageTk
import board
import busio
from digitalio import DigitalInOut
from adafruit_pn532.spi import PN532_SPI

# ---- Update these file paths for your raspberry pi! ----
username = "YOUR-USERNAME"
image_path = f"/home/{username}/Pictures/blinka.png"
movie_path = f"/media/{username}/YOUR-M.2-DRIVE-NAME"
csv_file = "movies.csv"
# ----

if not os.path.isfile(csv_file):
    with open(csv_file, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['uid', 'movie'])

root = tk.Tk()
root.attributes("-fullscreen", True)
root.configure(background="black")
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
root.geometry(f"{screen_width}x{screen_height}+0+0")

def toggle_fullscreen():
    root.attributes("-fullscreen", not root.attributes("-fullscreen"))

def exit_fullscreen():
    root.destroy()

root.bind("<F11>", toggle_fullscreen)
root.bind("<Escape>", exit_fullscreen)

image = Image.open(image_path)
photo = ImageTk.PhotoImage(image)

image_label = tk.Label(root, image=photo, bg="black")
image_label.place(x=0, y=0)

info_label = tk.Label(root, text = "00:00: AM", font=("Helvetica", 68), fg="white", bg="black")
info_label.place(x=1870, y = 1030, anchor="se")

x_pos, y_pos = 100, 100
x_speed, y_speed = 1, 1

spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
cs_pin = DigitalInOut(board.D24)
pn532 = PN532_SPI(spi, cs_pin, debug=False)

ic, ver, rev, support = pn532.firmware_version
print("Found PN532 with firmware version: {0}.{1}".format(ver, rev))

# Configure PN532 to communicate with MiFare cards
pn532.SAM_configuration()

print("Waiting for RFID/NFC card...")

now_playing = False
# pylint: disable=global-statement
def move():
    global x_pos, y_pos, x_speed, y_speed
    x_pos += x_speed
    y_pos += y_speed
    if x_pos + photo.width() >= root.winfo_screenwidth() or x_pos <= 0:
        x_speed = -x_speed
    if y_pos + photo.height() >= root.winfo_screenheight() or y_pos <= 0:
        y_speed = -y_speed
    image_label.place(x=x_pos, y=y_pos)
    root.after(30, move)

def get_movie(uid):
    with open(f"/home/{username}/{csv_file}", "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row["uid"] == uid:
                return row["movie"]
        return None

def read_card():
    global now_playing
    uid = pn532.read_passive_target(timeout=0.05)
    # Try again if no card is available.
    if uid is not None:
        print("Found card with UID:", [hex(i) for i in uid])
        title = str([hex(i) for i in uid])
        movie_name = get_movie(title)
        if movie_path:
            video = f"{movie_path}/{movie_name}.mp4"
            subprocess.run(["sudo", "-u", username, "vlc", "--fullscreen", video], check=False)
            now_playing = True
    else:
        current_time = datetime.now().strftime("%I:%M %p")
        info_label.config(text=f"{current_time}")
    root.after(2000, read_card)

def vlc_check():
    global now_playing
    try:
        result = subprocess.check_output(["pgrep", "-x", "vlc"])
        if result:
            return True
        else:
            return False
    except subprocess.CalledProcessError:
        now_playing = False
        return False
    root.after(5000, vlc_check)

if not now_playing:
    move()
    read_card()
if now_playing:
    vlc_check()

root.mainloop()
