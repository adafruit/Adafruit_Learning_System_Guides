# SPDX-FileCopyrightText: 2020 Kevin J. Walters for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# cpb-quick-draw v1.11
# CircuitPython (on CPBs) Quick Draw reaction game
# This is a two player game using two Circuit Playground Bluefruit boards
# to test the reaction time of the players in a "quick draw" with the
# synchronisation and draw times exchanged via Bluetooth Low Energy
# The switches must be set to DIFFERENT positions on the two CPBs

# Tested with Circuit Playground Bluefruit Alpha
# and CircuitPython and 5.0.0-beta.2

# Needs recent adafruit_ble and adafruit_circuitplayground.bluefruit libraries

# copy this file to CPB board as code.py

# MIT License

# Copyright (c) 2020 Kevin J. Walters

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import time
import gc
import struct
import random  # On a CPB this seeds from a hardware RNG in the CPU

# This is the new cp object which works on CPX and CPB
from adafruit_circuitplayground import cp

from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService

from adafruit_bluefruit_connect.packet import Packet

debug = 3

# Bluetooth scanning timeout
BLESCAN_TIMEOUT = 5

TURNS = 10
# Integer number of seconds
SHORTEST_DELAY = 1
LONGEST_DELAY = 5  # This was 10 in the original game

# Misdraw time (100ms)
IMPOSSIBLE_DUR = 0.1

# The duration of the short blue flashes (in seconds) during time delay
# measurement in ping_for_rtt() and the long one at the end
SYNC_FLASH_DUR = 0.1
SYNCED_LONGFLASH_DUR = 2

# The pause between displaying each pixel in the result summary
SUMMARY_DUR = 0.5

# The number of "pings" sent by ping_for_rtt()
NUM_PINGS = 8

# Special values used to indicate failed exchange of reaction times
# and no value
ERROR_DUR = -1.0
TIME_NONE = -2.0

# A timeout value for the protocol
protocol_timeout = 14.0

# These application specific packets could be placed in an another file
# and then import'ed
class TimePacket(Packet):
    """A packet for exchanging time information,
       duration (last rtt) and time.monotonic() and lastrtt."""

    _FMT_PARSE = '<xxffx'
    PACKET_LENGTH = struct.calcsize(_FMT_PARSE)
    # _FMT_CONSTRUCT doesn't include the trailing checksum byte.
    _FMT_CONSTRUCT = '<2sff'

    # Using lower case in attempt to avoid clashing with standard packets
    _TYPE_HEADER = b'!z'

    # number of args must match _FMT_PARSE
    # for Packet.parse_private() to work, hence the sendtime parameter
    def __init__(self, duration, sendtime):
        """Construct a TimePacket."""
        self._duration = duration
        self._sendtime = sendtime  # over-written later in to_bytes()

    def to_bytes(self):
        """Return the bytes needed to send this packet.
           Unusually this also sets the sendtime to the current time indicating
           when the data was serialised.
        """
        self._sendtime = time.monotonic()  # refresh _sendtime
        partial_packet = struct.pack(self._FMT_CONSTRUCT, self._TYPE_HEADER,
                                     self._duration, self._sendtime)
        return self.add_checksum(partial_packet)

    @property
    def duration(self):
        """The last rtt value or a negative number if n/a."""
        return self._duration

    @property
    def sendtime(self):
        """The time packet was sent (when to_bytes() was last called)."""
        return self._sendtime

TimePacket.register_packet_type()


class StartGame(Packet):  # pylint: disable=too-few-public-methods
    """A packet to indicate the receiver must start the game immediately."""

    _FMT_PARSE = '<xxx'
    PACKET_LENGTH = struct.calcsize(_FMT_PARSE)
    # _FMT_CONSTRUCT doesn't include the trailing checksum byte.
    _FMT_CONSTRUCT = '<2s'

    # Using lower case in attempt to avoid clashing with standard packets
    _TYPE_HEADER = b'!y'

    def to_bytes(self):
        """Return the bytes needed to send this packet.
        """
        partial_packet = struct.pack(self._FMT_CONSTRUCT, self._TYPE_HEADER)
        return self.add_checksum(partial_packet)


StartGame.register_packet_type()

# This board's role is determine by the switch, the two CPBs must have
# the switch in different positions
# left is the master / client / central device
# right is the slave / server / peripheral device
master_device = cp.switch  # True when switch is left (near ear symbol)

# The default brightness is 1.0 - leaving at that as it
# improves performance by removing need for a second buffer in memory
# 10 is number of NeoPixels on CPX/CPB
numpixels = 10
halfnumpixels = numpixels // 2
pixels = cp.pixels

faint_red = (1, 0, 0)
red = (40, 0, 0)
green = (0, 30, 0)
blue = (0, 0, 10)
brightblue = (0, 0, 100)
yellow = (40, 20, 0)
white = (30, 30, 30)
black = (0, 0, 0)

win_colour = green
win_pixels = [win_colour] * halfnumpixels
opponent_misdraw_colour = faint_red
misdraw_colour = red
misdraw_pixels = [misdraw_colour] * halfnumpixels
draw_colour = yellow
draw_pixels = [draw_colour] * halfnumpixels
lose_colour = black

if master_device:
    # button A is on left (usb at top
    player_button = lambda: cp.button_a
    # player_button.switch_to_input(pull=digitalio.Pull.DOWN)

    player_px = (0, halfnumpixels)
    opponent_px = (halfnumpixels, numpixels)
else:
    # button B is on right
    player_button = lambda: cp.button_b
    # player_button.switch_to_input(pull=digitalio.Pull.DOWN)

    player_px = (halfnumpixels, numpixels)
    opponent_px = (0, halfnumpixels)


def d_print(level, *args, **kwargs):
    """A simple conditional print for debugging based on global debug level."""
    if not isinstance(level, int):
        print(level, *args, **kwargs)
    elif debug >= level:
        print(*args, **kwargs)


def read_packet(timeout=None):
    """Read a packet with an optional locally implemented timeout.
       This is a workaround due to the timeout not being configurable."""
    if timeout is None:
        return Packet.from_stream(uart)  # Current fixed timeout is 1s

    packet = None
    read_start_t = time.monotonic()
    while packet is None and time.monotonic() - read_start_t < timeout:
        packet = Packet.from_stream(uart)
    return packet


def connect():
    """Connect two boards using the first Nordic UARTService the client
       finds over Bluetooth Low Energy.
       No timeouts, will wait forever."""
    new_conn = None
    new_uart = None
    if master_device:
        # Master code
        while new_uart is None:
            d_print("Disconnected, scanning")
            for advertisement in ble.start_scan(ProvideServicesAdvertisement,
                                                timeout=BLESCAN_TIMEOUT):
                d_print(2, advertisement.address, advertisement.rssi, "dBm")
                if UARTService not in advertisement.services:
                    continue
                d_print(1, "Connecting to", advertisement.address)
                ble.connect(advertisement)
                break
            for conns in ble.connections:
                if UARTService in conns:
                    d_print("Found UARTService")
                    new_conn = conns
                    new_uart = conns[UARTService]
                    break
            ble.stop_scan()

    else:
        # Slave code
        new_uart = UARTService()
        advertisement = ProvideServicesAdvertisement(new_uart)
        d_print("Advertising")
        ble.start_advertising(advertisement)
        # Is there a conn object somewhere here??
        while not ble.connected:
            pass

    return (new_conn, new_uart)


def ping_for_rtt():  # pylint: disable=too-many-branches,too-many-statements
    """Calculate the send time for Bluetooth Low Energy based from
       a series of round-trip time measurements and assuming that
       half of that is the send time.
       This code must be run at approximately the same time
       on each device as the timeout per packet is one second."""
    # The rtt is sent to server but for first packet client
    # sent there's no value to send, -1.0 is specal first packet value
    rtt = TIME_NONE
    rtts = []
    offsets = []

    if master_device:
        # Master code
        while True:
            gc.collect()  # an opportune moment
            request = TimePacket(rtt, TIME_NONE)
            d_print(2, "TimePacket TX")
            uart.write(request.to_bytes())
            response = Packet.from_stream(uart)
            t2 = time.monotonic()
            if isinstance(response, TimePacket):
                d_print(2, "TimePacket RX", response.sendtime)
                rtt = t2 - request.sendtime
                rtts.append(rtt)
                time_remote_cpb = response.sendtime + rtt / 2.0
                offset = time_remote_cpb - t2
                offsets.append(offset)
                d_print(3,
                        "RTT plus a bit={:f},".format(rtt),
                        "remote_time={:f},".format(time_remote_cpb),
                        "offset={:f}".format(offset))
            if len(rtts) >= NUM_PINGS:
                break

            pixels.fill(blue)
            time.sleep(SYNC_FLASH_DUR)
            pixels.fill(black)
            # This second sleep is very important to ensure that the
            # server is already awaiting the next packet before client
            # sends it to avoid server instantly reading buffered packets
            time.sleep(SYNC_FLASH_DUR)

    else:
        responses = 0
        while True:
            gc.collect()  # an opportune moment
            packet = Packet.from_stream(uart)
            if isinstance(packet, TimePacket):
                d_print(2, "TimePacket RX", packet.sendtime)
                # Send response
                uart.write(TimePacket(TIME_NONE, TIME_NONE).to_bytes())
                responses += 1
                rtts.append(packet.duration)
                pixels.fill(blue)
                time.sleep(SYNC_FLASH_DUR)
                pixels.fill(black)
            elif packet is None:
                # This could be a timeout or an indication of a disconnect
                d_print(2, "None from from_stream()")
            else:
                print("Unexpected packet type", packet)
            if responses >= NUM_PINGS:
                break

    # indicate a good rtt calculate, skip first one
    # as it's not present on slave
    if debug >= 3:
        print("RTTs:", rtts)
    if master_device:
        rtt_start = 1
        rtt_end = len(rtts) - 1
    else:
        rtt_start = 2
        rtt_end = len(rtts)

    # Use quickest ones and hope any outlier times don't reoccur!
    quicker_rtts = sorted(rtts[rtt_start:rtt_end])[0:(NUM_PINGS // 2) + 1]
    mean_rtt = sum(quicker_rtts) / len(quicker_rtts)
    # Assuming symmetry between send and receive times
    # this may not be perfectly true, parsing is one factor here
    send_time = mean_rtt / 2.0

    d_print(2, "send_time=", send_time)

    # Indicate sync with a longer 2 second blue flash
    pixels.fill(brightblue)
    time.sleep(SYNCED_LONGFLASH_DUR)
    pixels.fill(black)
    return send_time


def random_pause():
    """This is the pause before the players draw.
       It only runs on the master (BLE client) as it should be followed
       by a synchronising barrier."""
    if master_device:
        time.sleep(random.randint(SHORTEST_DELAY, LONGEST_DELAY))


def barrier(packet_send_time):
    """Master send a Start message and then waits for a reply.
       Slave waits for Start message, then sends reply, then pauses
       for packet_send_time so both master and slave return from
       barrier() at the same time."""

    if master_device:
        uart.write(StartGame().to_bytes())
        d_print(2, "StartGame TX")
        packet = read_packet(timeout=protocol_timeout)
        if isinstance(packet, StartGame):
            d_print(2, "StartGame RX")
        else:
            print("Unexpected packet type", packet)

    else:
        packet = read_packet(timeout=protocol_timeout)
        if isinstance(packet, StartGame):
            d_print(2, "StartGame RX")
            uart.write(StartGame().to_bytes())
            d_print(2, "StartGame TX")
        else:
            print("Unexpected packet type", packet)

        print("Sleeping to sync up", packet_send_time)
        time.sleep(packet_send_time)


def sync_test():
    """For testing synchronisation. Warning - this is flashes a lot!"""
    for _ in range(40):
        pixels.fill(white)
        time.sleep(0.1)
        pixels.fill(black)
        time.sleep(0.1)


def get_opponent_reactiontime(player_reaction):
    """Send reaction time data to the other player and receive theirs.
       Reusing the TimePacket() for this."""
    opponent_reaction = ERROR_DUR
    if master_device:
        uart.write(TimePacket(player_reaction,
                              TIME_NONE).to_bytes())
        print("TimePacket TX")
        packet = read_packet(timeout=protocol_timeout)
        if isinstance(packet, TimePacket):
            d_print(2, "TimePacket RX")
            opponent_reaction = packet.duration
        else:
            d_print(2, "Unexpected packet type", packet)

    else:
        packet = read_packet(timeout=protocol_timeout)
        if isinstance(packet, TimePacket):
            d_print(2, "TimePacket RX")
            opponent_reaction = packet.duration
            uart.write(TimePacket(player_reaction,
                                  TIME_NONE).to_bytes())
            d_print(2, "TimePacket TX")
        else:
            print("Unexpected packet type", packet)
    return opponent_reaction


def show_winner(player_reaction, opponent_reaction):
    """Show the winner on the appropriate set of NeoPixels.
       Returns win, misdraw, draw, colour) - 3 booleans and a result colour."""
    l_win = False
    l_misdraw = False
    l_draw = False
    l_colour = lose_colour

    if player_reaction < IMPOSSIBLE_DUR or opponent_reaction < IMPOSSIBLE_DUR:
        if opponent_reaction != ERROR_DUR and opponent_reaction < IMPOSSIBLE_DUR:
            pixels[opponent_px[0]:opponent_px[1]] = misdraw_pixels
            l_colour = opponent_misdraw_colour

        # This must come after previous if to get the most appropriate colour
        if player_reaction != ERROR_DUR and player_reaction < IMPOSSIBLE_DUR:
            l_misdraw = True
            pixels[player_px[0]:player_px[1]] = misdraw_pixels
            l_colour = misdraw_colour  # overwrite any opponent_misdraw_colour

    else:
        if player_reaction < opponent_reaction:
            l_win = True
            pixels[player_px[0]:player_px[1]] = win_pixels
            l_colour = win_colour
        elif opponent_reaction < player_reaction:
            pixels[opponent_px[0]:opponent_px[1]] = win_pixels
        else:
            # Equality! Very unlikely to reach here
            l_draw = False
            pixels[player_px[0]:player_px[1]] = draw_pixels
            pixels[opponent_px[0]:opponent_px[1]] = draw_pixels
            l_colour = draw_colour

    return (l_win, l_misdraw, l_draw, l_colour)


def show_summary(result_colours):
    """Show the results on the NeoPixels."""
    # trim anything beyond 10
    for idx, p_colour in enumerate(result_colours[0:numpixels]):
        pixels[idx] = p_colour
        time.sleep(SUMMARY_DUR)

# CPB auto-seeds from hardware random number generation on the nRF52840 chip
# Note: original code for CPX uses A4-A7 analog inputs,
#       CPB cannot use A7 for analog in

wins = 0
misdraws = 0
losses = 0
draws = 0

# default timeout is 1.0 and on latest library with UARTService this
# cannot be changed
ble = BLERadio()

# Connect the two boards over Bluetooth Low Energy
# Switch on left for master / client, switch on right for slave / server
d_print("connect()")
(conn, uart) = connect()

# Calculate round-trip time (rtt) delay between the two CPB boards
# flashing blue to indicate the packets and longer 2s flash when done
ble_send_time = None
d_print("ping_for_rtt()")
ble_send_time = ping_for_rtt()

my_results = []

# play the game for a number of TURNS then show results
for _ in range(TURNS):
    # This is an attempt to force a reconnection but may not take into
    # account all disconnection scenarios
    if uart is None:
        (conn, uart) = connect()

    # This is a good time to garbage collect
    gc.collect()

    # Random pause to stop players preempting the draw
    random_pause()

    try:
        # Synchronise the two boards by exchanging a Start message
        d_print("barrier()")
        barrier(ble_send_time)

        if debug >= 4:
            sync_test()

        # Show white on all NeoPixels to indicate draw now
        # This will execute at the same time on both boards
        pixels.fill(white)

        # Wait for and time how long it takes for player to press button
        start_t = time.monotonic()
        while not player_button():
            pass
        finish_t = time.monotonic()

        # Turn-off NeoPixels
        pixels.fill(black)

        # Play the shooting sound
        # 16k mono 8bit normalised version of
        # https://freesound.org/people/Diboz/sounds/213925/
        cp.play_file("PistolRicochet.wav")

        # The CPBs are no longer synchronised due to reaction time varying
        # per player
        # Exchange draw times
        player_reaction_dur = finish_t - start_t
        opponent_reaction_dur = get_opponent_reactiontime(player_reaction_dur)

        # Show green for winner and red for any misdraws
        (win, misdraw, draw, colour) = show_winner(player_reaction_dur,
                                                   opponent_reaction_dur)
        my_results.append(colour)
        if misdraw:
            misdraw += 1
        elif draw:
            draws += 1
        elif win:
            wins += 1
        else:
            losses += 1

        # Output reaction times to serial console in Mu friendly format
        print("({:d}, {:d}, {:f}, {:f})".format(wins, misdraws,
                                                player_reaction_dur,
                                                opponent_reaction_dur))

        # Keep NeoPixel result colour for 5 seconds then turn-off and repeat
        time.sleep(5)
    except Exception as err:  # pylint: disable=broad-except
        print("Caught exception", err)
        if conn is not None:
            conn.disconnect()
            conn = None
        uart = None

    pixels.fill(black)

# show results summary on NeoPixels
show_summary(my_results)

# infinite pause to stop the code completing which would turn off NeoPixels
while True:
    pass
