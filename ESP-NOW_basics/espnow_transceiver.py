# SPDX-FileCopyrightText: John Park for Adafruit 2025
# SPDX-License-Identifier: MIT
"""
ESP-NOW transciever demo for ESP32-S2/S3 TFT Feather boards with display
"""
import time
import wifi
import espnow
import board
import digitalio
import displayio
import terminalio
from adafruit_display_text import label
from adafruit_display_shapes.rect import Rect


# Setup the display (using built-in display like your example)
display = board.DISPLAY
group = displayio.Group()

# Create background rectangles like your example
background_rect = Rect(0, 0, display.width, display.height, fill=000000)
group.append(background_rect)

# Set up a button on pin D0/BOOT
button = digitalio.DigitalInOut(board.BUTTON)
button.direction = digitalio.Direction.INPUT
button.pull = digitalio.Pull.UP

# CONFIGURATION: Set this for each device
DEVICE_ID = "board_A"  # Options: "board_A", "board_B", "board_C", "board_D"

# Channel switching hack
wifi.radio.start_ap(" ", "", channel=6, max_connections=0)
wifi.radio.stop_ap()

def format_mac(mac_bytes):
    return ':'.join(f'{b:02x}' for b in mac_bytes)

def get_my_mac():
    return format_mac(wifi.radio.mac_address)

# Initialize ESP-NOW
e = espnow.ESPNow()
peer = espnow.Peer(mac=b'\xff\xff\xff\xff\xff\xff', channel=6)
e.peers.append(peer)

my_mac = get_my_mac()
print(f"{DEVICE_ID} board starting - MAC: {my_mac}")

# Colors
TOMATO = 0xFF6347
WHITE = 0xFFFFFF
GREEN = 0x00FF00
BLUE = 0x0080FF
RED = 0xFF0000

# Sender colors mapping
SENDER_COLORS = {
    "board_A": 0x32FF32,  # Lime green
    "board_B": 0x00FFFF,  # Cyan
    "board_C": 0xC8A2C8,  # Lilac
    "board_D": 0xFFFFFF   # White
}

def get_sender_color(rx_message):
    """Extract sender ID from message and return corresponding color"""
    for board_id in SENDER_COLORS:
        if rx_message.startswith(board_id):
            return SENDER_COLORS[board_id]
    return WHITE  # Default to white if sender not recognized

# Create text labels using anchor positioning like your example
title_label = label.Label(terminalio.FONT, text=f"ESP-NOW {DEVICE_ID}", color=TOMATO,
                         scale=2, anchor_point=(0, 0), anchored_position=(5, 5))
group.append(title_label)

status_label = label.Label(terminalio.FONT, text="press D0 to send", color=TOMATO,
                          scale=2, anchor_point=(0, 0), anchored_position=(5, 35))
group.append(status_label)

sent_label = label.Label(terminalio.FONT, text="TX'd: --", color=TOMATO,
                        scale=2, anchor_point=(0, 0), anchored_position=(5, 65))
group.append(sent_label)

# Create a second label for the colored counter part
sent_counter_label = label.Label(terminalio.FONT, text="",color=SENDER_COLORS.get(DEVICE_ID, WHITE),
                               scale=2, anchor_point=(0, 0), anchored_position=(80, 65))
group.append(sent_counter_label)

received_label = label.Label(terminalio.FONT, text="RX'd: --", color=TOMATO,
                            scale=2, anchor_point=(0, 0), anchored_position=(5, 95))
group.append(received_label)

# Create a second label for the colored message part
received_message_label = label.Label(terminalio.FONT, text="", color=WHITE,
                                   scale=2, anchor_point=(0, 0), anchored_position=(80, 95))
group.append(received_message_label)

# Show the display
display.root_group = group

# Button debouncing
last_button_time = 0
button_debounce = 0.2  # 200ms debounce
message_count = 0

while True:
    current_time = time.monotonic()

    # Check for button press (button is active low due to pull-up)
    if not button.value and (current_time - last_button_time > button_debounce):
        message_count += 1
        message = f"{DEVICE_ID} {message_count}"

        try:
            e.send(message, peer)
            print(f"Sent: {message}")

            # Update display
            status_label.text = "...>"
            status_label.color = TOMATO
            sent_label.text = "TX'd: "  # Keep this tomato colored
            sent_counter_label.text = str(message_count)  # Color with sender color
            sent_counter_label.color = SENDER_COLORS.get(DEVICE_ID, WHITE)
        #pylint: disable=broad-exception-caught
        except Exception as ex:
            print(f"Send failed: {ex}")
            status_label.text = "xxx"
            status_label.color = RED

        last_button_time = current_time

    # Reset status after a moment
    if current_time - last_button_time > 0.2:
        status_label.text = "press D0 to send"
        status_label.color = TOMATO

    # Check for incoming packets
    if e:
        packet = e.read()
        if packet:
            sender_mac = format_mac(packet.mac)

            if sender_mac != my_mac:
                message = packet.msg.decode('utf-8')
                print(f"received: {message}")

                # Update display with sender color
                status_label.text = "<..."
                status_label.color = TOMATO
                sender_color = get_sender_color(message)
                received_label.text = "RX'd: "  # Keep this tomato colored
                received_message_label.text = message[-12:]  # Color just the message
                received_message_label.color = sender_color

    time.sleep(0.05)  # Light polling
