# SPDX-FileCopyrightText: 2025 John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
ESP-NOW MIDI Juggling Ball
communicates to Feather TFT connected to computer/synth via USB
"""

import time
import wifi
import espnow
import board
import neopixel
import analogio
import adafruit_lis3dh

# CONFIGURATION: Set this for each device
DEVICE_ID = "ball_A"  # Options: "ball_A", "ball_B", "ball_C"

# Sleep configuration -- light sleep, will wake on tap detection
SLEEP_AFTER = 30  # Seconds of inactivity before sleep turns off NeoPixels/radio

# Device list
DEVICES = ["ball_A", "ball_B", "ball_C"]

ALL_COLORS = [0xEE0010, 0x00FF00, 0x0010EE]  # indexed to DEVICES

# Current color state (starts with device's default)
current_color_index = DEVICES.index(DEVICE_ID)
CURRENT_COLOR = ALL_COLORS[current_color_index]

NUM_PIX = 2  # 2 for PCB version, however many you want for BFF
# Set up NeoPixel and I2C for accelerometer
pixel = neopixel.NeoPixel(board.A0, NUM_PIX)  # board.A0 for PCB, A3 for BFF
pixel.brightness = 1.0
pixel.fill(CURRENT_COLOR)

# Set up battery monitoring
voltage_pin = analogio.AnalogIn(board.A2)


def get_battery_voltage():
    """Read battery voltage from A2 pin"""
    # Take the raw voltage pin value, and convert it to voltage
    voltage = (voltage_pin.value / 65536) * 2 * 3.3
    return voltage


# Initialize I2C and LIS3DH accelerometer
try:
    # i2c = board.STEMMA_I2C()  # use this if connecting to STEMMA QT
    i2c = board.I2C()
    try:
        lis3dh = adafruit_lis3dh.LIS3DH_I2C(i2c, address=0x18)
        print("LIS3DH address: 0x18")
    except ValueError:
        lis3dh = adafruit_lis3dh.LIS3DH_I2C(i2c, address=0x19)
        print("LIS3DH address: 0x19")
    lis3dh.range = adafruit_lis3dh.RANGE_2_G
    lis3dh.set_tap(1, 90)
    has_accelerometer = True
    print("LIS3DH accelerometer initialized with tap detection")
except Exception as e:
    print(f"Accelerometer init failed: {e}")
    has_accelerometer = False


# Channel switching hack
wifi.radio.start_ap(" ", "", channel=6, max_connections=0)
wifi.radio.stop_ap()


def format_mac(mac_bytes):
    return ":".join(f"{b:02x}" for b in mac_bytes)


def get_my_mac():
    return format_mac(wifi.radio.mac_address)


def cycle_color():
    """Cycle to the next color in the list"""
    global current_color_index, CURRENT_COLOR  # pylint: disable=global-statement
    current_color_index = (current_color_index + 1) % len(ALL_COLORS)
    CURRENT_COLOR = ALL_COLORS[current_color_index]
    pixel.fill(CURRENT_COLOR)
    print(f"Color changed to: {CURRENT_COLOR:06X}")


def flash():
    """Quick flash for tap feedback"""
    pixel.fill((200, 200, 200))
    time.sleep(0.15)
    pixel.fill(CURRENT_COLOR)


def enter_sleep():
    """Enter low-power sleep mode"""
    global is_sleeping  # pylint: disable=global-statement
    # print("Entering sleep mode - turning off NeoPixels and radio")
    pixel.fill((0, 0, 0))  # Turn off all NeoPixels
    pixel.brightness = 0
    wifi.radio.stop_ap()  # Turn off radio
    is_sleeping = True


def wake_up():
    """Wake from sleep mode"""
    global is_sleeping, last_activity_time  # pylint: disable=global-statement
    # print("Waking up - restoring NeoPixels and radio")
    pixel.brightness = 1.0
    pixel.fill(CURRENT_COLOR)
    # Restart radio
    wifi.radio.start_ap(" ", "", channel=6, max_connections=0)
    wifi.radio.stop_ap()
    is_sleeping = False
    last_activity_time = time.monotonic()


def check_tap():
    """Check if accelerometer detects tap"""
    if not has_accelerometer:
        return False
    try:
        return lis3dh.tapped
    except Exception as e:
        print(f"Accelerometer read error: {e}")
        return False


def send_trigger_message(trigger_type="tap"):
    """Send trigger message with current device color"""
    current_time = time.monotonic()  # pylint: disable=redefined-outer-name
    message = f"TRIGGER|{DEVICE_ID}|{trigger_type}|{current_time:.1f}"  # pylint: disable=redefined-outer-name

    try:
        e.send(message, broadcast_peer)
        # print(f"TX: {message}")
        flash()
        return True
    except Exception as ex:
        print(f"Send error: {ex}")
        return False


def send_battery_report():
    """Send battery voltage report to bridge with current color"""
    voltage = get_battery_voltage()
    current_time = time.monotonic()  # pylint: disable=redefined-outer-name
    message = (  # pylint: disable=redefined-outer-name
        f"BATTERY|{DEVICE_ID}|{voltage:.2f}|{CURRENT_COLOR:06X}|{current_time:.1f}"
    )

    try:
        e.send(message, broadcast_peer)
        print(f"TX Battery: {message} ({voltage:.2f}V, color: {CURRENT_COLOR:06X})")
        return True
    except Exception as ex:
        print(f"Battery report send error: {ex}")
        return False


# Initialize ESP-NOW
e = espnow.ESPNow()
broadcast_peer = espnow.Peer(mac=b"\xff\xff\xff\xff\xff\xff", channel=6)
e.peers.append(broadcast_peer)

my_mac = get_my_mac()
print(f"{DEVICE_ID} ball starting - MAC: {my_mac}, Color: {CURRENT_COLOR:06X}")

# Clear accelerometer startup noise
print("Initializing accelerometer...")
time.sleep(0.5)
if has_accelerometer:
    print("Clearing startup tap artifacts...")
    for i in range(10):
        try:
            tap_state = lis3dh.tapped
            if tap_state:
                print(f"Cleared startup tap {i + 1}")
            time.sleep(0.1)
        except Exception:
            pass
    print("Accelerometer ready for tap detection")

# Timing variables
last_tap_time = 0
tap_debounce = 0.3
startup_time = time.monotonic()
startup_protection = 0.5

# Sleep/wake tracking
last_activity_time = time.monotonic()
is_sleeping = False

while True:
    current_time = time.monotonic()  #  pylint: disable=redefined-outer-name

    # Check for sleep timeout
    if not is_sleeping and (current_time - last_activity_time > SLEEP_AFTER):
        enter_sleep()

    # Check for tap (primary trigger and wake-up source)
    if has_accelerometer:
        # Only check for taps after startup protection period
        if current_time - startup_time > startup_protection:
            if check_tap():
                # If sleeping, wake up first
                if is_sleeping:
                    wake_up()

                # Check debounce for actual trigger
                if current_time - last_tap_time > tap_debounce:
                    send_trigger_message("tap")
                    last_tap_time = current_time
                    last_activity_time = current_time
        else:
            # During startup protection, clear any false tap detections
            if check_tap():
                print("Ignoring tap during startup protection period")

    # Check for incoming packets from bridge (only if not sleeping)
    if not is_sleeping and e:
        packet = e.read()
        sender_mac = format_mac(packet.mac)

        if sender_mac != my_mac:
            message = packet.msg.decode("utf-8")  # pylint:disable=redefined-outer-name
            last_activity_time = current_time  # Any message counts as activity

            # Handle color change commands from bridge
            if message.startswith("COLOR|"):
                parts = message.split("|")
                if len(parts) >= 3:
                    target_device = parts[1]
                    command = parts[2]

                    # Only respond if this message is for us
                    if target_device == DEVICE_ID and command == "next":
                        cycle_color()
                        # Send battery report when color changes
                        send_battery_report()

            # Handle trigger messages from other balls for visual feedback
            # elif message.startswith("TRIGGER|"):
            #     parts = message.split("|")
            #     if len(parts) >= 4:
            #         sender_device = parts[1]
            #         trigger_type = parts[2]
            #         print(f"Trigger from {sender_device} ({trigger_type})")
            #         # Brief red flash for other ball triggers
            #         flash()

    time.sleep(0.01)  # Fast polling for responsive tap detection
