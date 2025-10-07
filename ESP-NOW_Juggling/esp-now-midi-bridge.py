# SPDX-FileCopyrightText: 2025 John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
ESP-NOW MIDI Bridge
Bridge ESP-NOW messages to USB MIDI
Runs on ESP32-S3 Feather TFT connected to computer/synth via USB
"""

import time
import wifi
import espnow
import usb_midi
import adafruit_midi
from adafruit_midi.note_on import NoteOn
from adafruit_midi.note_off import NoteOff
import board
import neopixel
import displayio
import terminalio
from adafruit_display_text import label
from adafruit_display_shapes.circle import Circle
import keypad

# Set up NeoPixel for visual feedback
pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)
pixel.brightness = 1

# Set up buttons for color control
# D0 has opposite pull direction from D1 and D2
button_d0 = keypad.Keys(
    (board.D0,), value_when_pressed=False, pull=True
)  # Opposite pull
buttons_d1_d2 = keypad.Keys(
    (board.D1, board.D2), value_when_pressed=True, pull=True
)  # Normal pull

# MIDI note mappings - centralized on the bridge
MIDI_MAPPINGS = {
    "ball_A": {
        "notes": [42, 43, 45, 47],  # Sequence of notes to cycle through
        "color": (238, 0, 16),  # Pink (for bridge LED/display)
    },
    "ball_B": {
        "notes": [50, 50, 50, 50, 50, 62],  # Single note
        "color": (0, 255, 0),  # Green (for bridge LED/display)
    },
    "ball_C": {
        "notes": [47, 45, 40],  # Sequence
        "color": (0, 16, 238),  # Blue (for bridge LED/display)
    },
}

# Track current position in each device's note sequence
note_positions = {device: 0 for device in MIDI_MAPPINGS.keys()}  # pylint:disable=consider-iterating-dictionary

# Track connection status for display (last seen time)
connection_status = {}
CONNECTION_TIMEOUT = 5.0

# Track current ball colors (start with defaults, update when COLOR command sent)
ball_colors = {
    "ball_A": 0xEE0010,  # Pink
    "ball_B": 0x00FF00,  # Green
    "ball_C": 0x0010EE,  # Blue
}

# All available colors for cycling
ALL_COLORS = [0xEE0010, 0x00FF00, 0x0010EE]

# Track battery voltages
ball_voltages = {"ball_A": "-.-V", "ball_B": "-.-V", "ball_C": "-.-V"}

# Channel switching hack for ESP-NOW
wifi.radio.start_ap(" ", "", channel=6, max_connections=0)
wifi.radio.stop_ap()

# Initialize MIDI
print("Available MIDI ports:", len(usb_midi.ports))
for i, port in enumerate(usb_midi.ports):
    print(f"Port {i}: {port}")

midi_out_port = None
for port in usb_midi.ports:
    if hasattr(port, "write"):
        midi_out_port = port
        break

if midi_out_port:
    midi = adafruit_midi.MIDI(midi_out=midi_out_port, out_channel=0)
    print(f"MIDI initialized with port: {midi_out_port}")
else:
    print("No MIDI output port found!")
    midi = None


def format_mac(mac_bytes):
    """Convert MAC address bytes to standard colon-separated format"""
    return ":".join(f"{b:02x}" for b in mac_bytes)


def blink_color(color, count=1):
    """Blink the NeoPixel with specified color and count"""
    for _ in range(count):
        pixel[0] = color
        time.sleep(0.02)
        pixel[0] = (0, 0, 0)


def parse_trigger_message(message_str):
    """Parse trigger message and return device info"""
    if not message_str.startswith("TRIGGER|"):
        return None, None, None

    try:
        parts = message_str.split("|")
        if len(parts) >= 4:
            device_id = parts[1]  # pylint:disable=redefined-outer-name
            trigger_type = parts[2]  # pylint:disable=redefined-outer-name
            timestamp = parts[3]  # pylint:disable=redefined-outer-name
            return device_id, trigger_type, timestamp
    except Exception:  # pylint:disable=broad-except
        pass

    return None, None, None


def parse_battery_message(message_str):
    """Parse battery voltage message with color"""
    if not message_str.startswith("BATTERY|"):
        return None, None, None

    try:
        parts = message_str.split("|")
        if len(parts) >= 4:
            device_id = parts[1]  # pylint:disable=redefined-outer-name
            voltage = parts[2]  # pylint:disable=redefined-outer-name
            color_hex = int(parts[3], 16)  # pylint:disable=redefined-outer-name
            return device_id, voltage, color_hex
    except Exception:  # pylint:disable=broad-except
        pass

    return None, None, None


def send_midi_note(device_id, velocity=100, duration=0.05):  # pylint:disable=redefined-outer-name
    """Send a MIDI note based on device mapping, cycling through sequence"""
    if not midi or device_id not in MIDI_MAPPINGS:
        print(f"MIDI not available or unknown device: {device_id}")
        return

    mapping = MIDI_MAPPINGS[device_id]  # pylint:disable=redefined-outer-name
    notes_sequence = mapping["notes"]

    # Get current note from sequence
    current_position = note_positions[device_id]
    note = notes_sequence[current_position]

    # Move to next position in sequence (with wrap-around)
    note_positions[device_id] = (current_position + 1) % len(notes_sequence)

    try:
        midi.send(NoteOn(note, velocity))
        time.sleep(duration)
        midi.send(NoteOff(note, 0))
    except Exception as err:  # pylint:disable=broad-except
        print(f"MIDI error: {err}")


def send_color_command(device_id):  # pylint:disable=redefined-outer-name
    """Send color cycle command to a specific ball"""
    try:
        message = f"COLOR|{device_id}|next"  # pylint:disable=redefined-outer-name
        e.send(message, broadcast_peer)
        print(f"Sent color command: {message}")

        # Update tracked ball color
        current_color_index = ALL_COLORS.index(ball_colors[device_id])
        next_color_index = (current_color_index + 1) % len(ALL_COLORS)
        ball_colors[device_id] = ALL_COLORS[next_color_index]
        print(f"{device_id} color now: {ball_colors[device_id]:06X}")

        return True
    except Exception as ex:  # pylint:disable=broad-except
        print(f"Color send error: {ex}")
        return False


def handle_button_presses():
    """Check for button presses and send color commands"""
    # Handle D0 button (ball_A) - opposite pull direction
    d0_event = button_d0.events.get()
    if d0_event and d0_event.pressed:
        send_color_command("ball_A")
        print("ball_A color cycle")

    # Handle D1 and D2 buttons (ball_B and ball_C)
    d1_d2_event = buttons_d1_d2.events.get()
    if d1_d2_event and d1_d2_event.pressed:
        if d1_d2_event.key_number == 0:  # D1 pressed (ball_B)
            send_color_command("ball_B")
            print("ball_B color cycle")
        elif d1_d2_event.key_number == 1:  # D2 pressed (ball_C)
            send_color_command("ball_C")
            print("ball_C color cycle")


# Initialize TFT display
display = board.DISPLAY
group = displayio.Group()

# Colors
BGCOLOR = 0x000000
TEXT_COLOR = 0xFFFFFF
DISCONNECTED_COLOR = 0x404040


def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple"""
    r = (hex_color >> 16) & 0xFF
    g = (hex_color >> 8) & 0xFF
    b = hex_color & 0xFF
    return (r, g, b)


# Create display elements in A, B, C order - TWO LINES PER BALL
ball_info = []
device_hex_colors = {
    "ball_A": 0xEE0010,  # Pink
    "ball_B": 0x00FF00,  # Green
    "ball_C": 0x0010EE,  # Blue
}

# Display balls in A, B, C order with two lines each
ordered_devices = ["ball_A", "ball_B", "ball_C"]
for i, device_id in enumerate(ordered_devices):
    if device_id in MIDI_MAPPINGS:
        mapping = MIDI_MAPPINGS[device_id]
        y_pos_line1 = 10 + (i * 50)  # First line
        y_pos_line2 = y_pos_line1 + 20  # Second line (20 pixels below)

        # Connection dot - use device hex color (fixed color for display)
        dot_color = device_hex_colors[device_id]
        dot = Circle(10, y_pos_line1 + 3, 4, fill=dot_color, outline=DISCONNECTED_COLOR)
        group.append(dot)

        # Line 1: Ball name and voltage in ball's current color
        ball_name = device_id.replace("ball_", "Ball ")
        voltage_text = ball_voltages[device_id]
        line1_text = f"{ball_name}  {voltage_text}"

        line1_label = label.Label(
            terminalio.FONT,
            text=line1_text,
            color=hex_to_rgb(ball_colors[device_id]),  # Use ball's current color
            scale=2,  # Bigger font
            x=25,
            y=y_pos_line1,
        )
        group.append(line1_label)

        # Line 2: MIDI notes
        notes_list = ", ".join(str(n) for n in mapping["notes"])
        line2_text = f"notes: {notes_list}"

        line2_label = label.Label(
            terminalio.FONT,
            text=line2_text,
            color=TEXT_COLOR,
            scale=1,  # Smaller font for notes line
            x=25,
            y=y_pos_line2,
        )
        group.append(line2_label)

        ball_info.append(
            {
                "device_id": device_id,
                "dot": dot,
                "line1_label": line1_label,
                "line2_label": line2_label,
                "connected_color": dot_color,
                "disconnected_color": DISCONNECTED_COLOR,
            }
        )

display.root_group = group


def update_connection_display():
    """Update connection status dots and text colors"""
    current_time = time.monotonic()  # pylint:disable=redefined-outer-name
    for ball in ball_info:
        device_id = ball["device_id"]  # pylint:disable=redefined-outer-name

        # Update connection dot
        if device_id in connection_status:
            time_since_last = current_time - connection_status[device_id]
            if time_since_last < CONNECTION_TIMEOUT:
                ball["dot"].fill = ball["connected_color"]
            else:
                ball["dot"].fill = ball["disconnected_color"]
        else:
            ball["dot"].fill = ball["disconnected_color"]

        # Update line 1 text (ball name and voltage) with current ball color
        ball_name = device_id.replace("ball_", "Ball ")  # pylint:disable=redefined-outer-name
        voltage_text = ball_voltages[device_id]  # pylint:disable=redefined-outer-name
        ball["line1_label"].text = f"{ball_name}  {voltage_text}"
        ball["line1_label"].color = hex_to_rgb(ball_colors[device_id])


# Initialize ESP-NOW
e = espnow.ESPNow()
broadcast_peer = espnow.Peer(mac=b"\xff\xff\xff\xff\xff\xff", channel=6)
e.peers.append(broadcast_peer)

print("ESP-NOW to MIDI Bridge starting...")
print("MIDI mappings loaded:")
for device, mapping in MIDI_MAPPINGS.items():
    notes = mapping["notes"]
    if len(notes) == 1:
        print(f"  {device}: Note {notes[0]} (single)")
    else:
        print(f"  {device}: Notes {notes} (sequence)")
print("Button controls: D0=ball_A, D1=ball_B, D2=ball_C (color cycling)")
print("Listening for ball trigger messages...")

# Update display once at startup
update_connection_display()
last_display_update = time.monotonic()
last_message_time = {}

while True:
    if e:  # Packet available
        packet = e.read()
        sender_mac = format_mac(packet.mac)
        message = packet.msg.decode("utf-8")

        print(f"ESP-NOW RX from {sender_mac}: {message}")

        # Parse battery messages
        battery_device_id, voltage, color_hex = parse_battery_message(message)
        if battery_device_id:
            ball_voltages[battery_device_id] = f"{voltage}V"
            # Update ball color from battery report
            if color_hex is not None:
                ball_colors[battery_device_id] = color_hex
                print(
                    f"Updated {battery_device_id} voltage: {voltage}V, color: {color_hex:06X}"
                )
            else:
                print(f"Updated {battery_device_id} voltage: {voltage}V")
            # Trigger display update
            update_connection_display()

        # Parse the trigger message
        device_id, trigger_type, timestamp = parse_trigger_message(message)

        if device_id and device_id in MIDI_MAPPINGS:
            current_time = time.monotonic()

            # Update connection status
            connection_status[device_id] = current_time

            # Simple debouncing
            if (
                device_id not in last_message_time
                or current_time - last_message_time[device_id] > 0.3
            ):
                print(f"Converting {device_id} trigger to MIDI")

                # Send MIDI note immediately
                if trigger_type == "tap":
                    send_midi_note(device_id)
                else:
                    send_midi_note(device_id)

                # Use bridge's fixed color for LED feedback
                bridge_color = MIDI_MAPPINGS[device_id]["color"]
                blink_color(bridge_color, count=1)

                last_message_time[device_id] = current_time

    # Handle button presses for color control
    handle_button_presses()

    # Update display occasionally
    current_time = time.monotonic()
    if current_time - last_display_update > 2.0:
        update_connection_display()
        last_display_update = current_time

    time.sleep(0.01)
