# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`fruitjam_ble.uart_hci`
================================================================================

Bluetooth HCI transport over a UART (the "H4" transport of the Bluetooth Core
specification): every packet starts with a one byte type, 0x01 for a command,
0x02 for ACL data and 0x04 for an event. This is how an AirLift co-processor
running NINA firmware talks in Bluetooth mode.

It has the same methods as the USB host Bluetooth library's ``USBHCI``, which is
all `fruitjam_ble.bleio` needs from a transport.

* Author(s): Tim Cocks
"""

import time

from micropython import const

# pylint: disable=too-many-branches

_H4_COMMAND = const(0x01)
_H4_ACL = const(0x02)
_H4_EVENT = const(0x04)

_EVT_COMMAND_COMPLETE = const(0x0E)
_EVT_COMMAND_STATUS = const(0x0F)
_EVT_NUM_COMPLETED_PACKETS = const(0x13)

OP_RESET = const(0x0C03)
OP_READ_LOCAL_VERSION = const(0x1001)
OP_READ_BUFFER_SIZE = const(0x1005)
OP_READ_BD_ADDR = const(0x1009)
OP_LE_READ_BUFFER_SIZE = const(0x2002)


class HCIError(Exception):
    """A controller answered an HCI command with a nonzero status.

    :param int opcode: the command that failed
    :param int status: the HCI status code
    """

    def __init__(self, opcode, status):
        super().__init__(f"HCI command 0x{opcode:04x} failed, status 0x{status:02x}")
        self.opcode = opcode
        self.status = status


class HCITimeoutError(Exception):
    """The controller did not answer an HCI command, or did not let us send."""


class UARTHCI:
    """
    Bluetooth HCI transport over a UART.

    The controller is reset during construction.

    :param busio.UART uart: the UART, made with ``timeout=0`` and a receive
        buffer big enough to hold what arrives between polls (4096 bytes is
        plenty)
    :param digitalio.DigitalInOut rts: optional output held low to tell the
        controller it may send
    :param digitalio.DigitalInOut cts: optional input the controller holds high
        while it can't take more data
    :param float timeout: how long to wait for a command's response, in seconds
    """

    def __init__(self, uart, *, rts=None, cts=None, timeout=1.0):
        self.uart = uart
        self._rts = rts
        self._cts = cts
        self.timeout = timeout
        if rts is not None:
            rts.value = False
        self._rx = bytearray()
        self._events = []
        self._acl = []
        self._command = bytearray(4 + 255)
        self.acl_packet_size = 27
        self.acl_packets_free = 1
        self._acl_out = bytearray(5 + 251)

        # Throw away anything left over, such as the controller's boot messages.
        while uart.in_waiting:
            uart.read()
        self.send_command(OP_RESET)

    def _write(self, data):
        cts = self._cts
        if cts is not None and cts.value:
            deadline = time.monotonic() + self.timeout
            while cts.value:
                if time.monotonic() > deadline:
                    raise HCITimeoutError("controller is busy")
        self.uart.write(data)

    def _pump(self):
        """Move whatever the UART has received into the event and ACL queues."""
        uart = self.uart
        waiting = uart.in_waiting
        if not waiting:
            return
        self._rx.extend(uart.read(waiting))
        rx = self._rx
        start = 0
        end = len(rx)
        while start < end:
            kind = rx[start]
            if kind == _H4_EVENT:
                if end - start < 3:
                    break
                total = 3 + rx[start + 2]
                if end - start < total:
                    break
                event = bytes(rx[start + 1 : start + total])
                if event[0] == _EVT_NUM_COMPLETED_PACKETS:
                    # Credits come back here no matter who is waiting, so ACL
                    # writes never stall.
                    for i in range(event[2]):
                        self.acl_packets_free += event[5 + 4 * i] | (
                            event[6 + 4 * i] << 8
                        )
                else:
                    self._events.append(event)
            elif kind == _H4_ACL:
                if end - start < 5:
                    break
                total = 5 + (rx[start + 3] | (rx[start + 4] << 8))
                if end - start < total:
                    break
                self._acl.append(bytes(rx[start + 1 : start + total]))
            else:
                # Not the start of a packet: lost sync. Skip a byte and look again.
                total = 1
            start += total
        if start:
            self._rx = rx[start:]

    def _wait(self, queue, timeout_ms):
        self._pump()
        if not queue and timeout_ms > 0:
            deadline = time.monotonic_ns() + timeout_ms * 1_000_000
            while not queue and time.monotonic_ns() < deadline:
                self._pump()
        if queue:
            return queue.pop(0)
        return None

    def send_command(self, opcode, params=b""):
        """Send an HCI command and wait for its Command Complete or Command Status
        event. Unrelated events that arrive in the meantime are kept for
        `read_event`.

        :param int opcode: the 16-bit opcode (OGF << 10 | OCF)
        :param params: the command's parameters
        :return: the return parameters that follow the status byte
        :rtype: bytes
        :raises HCIError: if the controller answers with a nonzero status
        :raises HCITimeoutError: if the controller does not answer
        """
        command = self._command
        command[0] = _H4_COMMAND
        command[1] = opcode & 0xFF
        command[2] = opcode >> 8
        command[3] = len(params)
        command[4 : 4 + len(params)] = params
        self._write(memoryview(command)[: 4 + len(params)])
        events = self._events
        checked = len(events)
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            self._pump()
            while checked < len(events):
                event = events[checked]
                code = event[0]
                if (
                    code == _EVT_COMMAND_COMPLETE
                    and event[3] | (event[4] << 8) == opcode
                ):
                    events.pop(checked)
                    if len(event) > 5 and event[5]:
                        raise HCIError(opcode, event[5])
                    return event[6:]
                if code == _EVT_COMMAND_STATUS and event[4] | (event[5] << 8) == opcode:
                    events.pop(checked)
                    if event[2]:
                        raise HCIError(opcode, event[2])
                    return b""
                checked += 1
        raise HCITimeoutError(f"no answer to HCI command 0x{opcode:04x}")

    def read_event(self, timeout_ms=1):
        """Return the next HCI event as ``event code, parameter length,
        parameters...``, or None if none arrived within ``timeout_ms``
        milliseconds."""
        return self._wait(self._events, timeout_ms)

    def read_acl(self, timeout_ms=1):
        """Return the next ACL data packet, header included, or None if none
        arrived within ``timeout_ms`` milliseconds."""
        return self._wait(self._acl, timeout_ms)

    def read_buffer_size(self):
        """Ask the controller how big and how many ACL packets it takes, for
        `write_acl`'s flow control."""
        try:
            response = self.send_command(OP_LE_READ_BUFFER_SIZE)
            size = response[0] | (response[1] << 8)
            count = response[2]
        except HCIError:
            size = count = 0
        if not size or not count:
            # 0 means LE shares the BR/EDR buffers.
            response = self.send_command(OP_READ_BUFFER_SIZE)
            size = response[0] | (response[1] << 8)
            count = response[3] | (response[4] << 8)
        self.acl_packet_size = min(size, len(self._acl_out) - 5)
        self.acl_packets_free = count

    def write_acl(self, handle, data, *, packet_boundary=0x0):
        """Send ACL data to a connection, split into controller-sized packets.

        :param int handle: the connection handle
        :param data: an L2CAP frame, header included
        :param int packet_boundary: the PB flag of the first packet. The default,
            "first non-automatically-flushable", is the only start flag a host may
            use on an LE link; the ESP32-C6's controller drops LE data sent with
            the "first automatically flushable" flag (``0x2``).
        """
        out = self._acl_out
        out[0] = _H4_ACL
        offset = 0
        while offset < len(data) or offset == 0:
            chunk = min(self.acl_packet_size, len(data) - offset)
            if self.acl_packets_free <= 0:
                deadline = time.monotonic() + self.timeout
                while self.acl_packets_free <= 0:
                    self._pump()
                    if time.monotonic() > deadline:
                        raise HCITimeoutError("controller did not free an ACL buffer")
            flags = packet_boundary if offset == 0 else 0x1
            out[1] = handle & 0xFF
            out[2] = ((handle >> 8) & 0x0F) | (flags << 4)
            out[3] = chunk & 0xFF
            out[4] = chunk >> 8
            out[5 : 5 + chunk] = data[offset : offset + chunk]
            self._write(memoryview(out)[: 5 + chunk])
            self.acl_packets_free -= 1
            offset += chunk
            if not chunk:
                break

    def read_local_version(self):
        """Return ``(hci_version, hci_revision, lmp_version, manufacturer,
        lmp_subversion)`` from the controller."""
        r = self.send_command(OP_READ_LOCAL_VERSION)
        return (
            r[0],
            r[1] | (r[2] << 8),
            r[3],
            r[4] | (r[5] << 8),
            r[6] | (r[7] << 8),
        )

    def read_bd_addr(self):
        """Return the controller's public address, least significant byte first."""
        return self.send_command(OP_READ_BD_ADDR)[:6]

    def __repr__(self):
        return "Bluetooth HCI over " + repr(self.uart)
