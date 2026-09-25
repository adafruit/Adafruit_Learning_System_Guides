# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`fruitjam_ble.bleio`
================================================================================

A Python implementation of CircuitPython's ``_bleio`` API on top of an HCI
Bluetooth controller, so that ``adafruit_ble`` and the libraries built on it
work unchanged. The built-in HCI ``_bleio`` can't scan or connect as a
central; this one can.

Copied from the experimental USB host Bluetooth library, which reaches a USB
dongle instead of the Fruit Jam's ESP32-C6.

Importing `fruitjam_ble` registers this module as ``_bleio``.
That has to happen before ``adafruit_ble`` is imported, because the
``adafruit_ble`` modules bind ``_bleio`` when they are first imported.

Advertising, scanning, connections as peripheral or central, a GATT server and
a GATT client are implemented. Pairing, bonding and the security modes of
`Attribute` are not: every link is unencrypted.

Unlike the native module, nothing runs in the background. Events are handled
whenever this module is waiting or is asked for state, such as
`Adapter.connected` or `CharacteristicBuffer.in_waiting`, so poll one of those
regularly while connected.

* Author(s): Tim Cocks
"""

import struct
import time

from micropython import const

from . import _att

# pylint: disable=protected-access, too-many-lines, global-statement, too-many-locals, unused-argument

adapter = None
"""The first `Adapter` created, used by default by ``adafruit_ble.BLERadio``."""

_OP_DISCONNECT = const(0x0406)
_OP_SET_EVENT_MASK = const(0x0C01)
_OP_WRITE_LOCAL_NAME = const(0x0C13)
_OP_LE_SET_EVENT_MASK = const(0x2001)
_OP_LE_SET_ADV_PARAMS = const(0x2006)
_OP_LE_SET_ADV_DATA = const(0x2008)
_OP_LE_SET_SCAN_RESPONSE_DATA = const(0x2009)
_OP_LE_SET_ADV_ENABLE = const(0x200A)
_OP_LE_SET_SCAN_PARAMS = const(0x200B)
_OP_LE_SET_SCAN_ENABLE = const(0x200C)
_OP_LE_CREATE_CONNECTION = const(0x200D)
_OP_LE_CREATE_CONNECTION_CANCEL = const(0x200E)
_OP_LE_CONNECTION_UPDATE = const(0x2013)

_EVT_DISCONNECTION_COMPLETE = const(0x05)
_EVT_LE_META = const(0x3E)
_SUBEVT_CONNECTION_COMPLETE = const(0x01)
_SUBEVT_ADVERTISING_REPORT = const(0x02)
_SUBEVT_CONNECTION_UPDATE_COMPLETE = const(0x03)

_CID_SIGNALING = const(0x0005)
_CID_SMP = const(0x0006)

_ROLE_CENTRAL = const(0)


class BluetoothError(Exception):
    """Catchall exception for Bluetooth related errors."""


class RoleError(BluetoothError):
    """Raised when a resource is used as the mismatched role."""


class SecurityError(BluetoothError):
    """Raised when a security related error occurs."""


def set_adapter(new_adapter):
    """Set the adapter to use for BLE."""
    global adapter  # noqa: PLW0603
    adapter = new_adapter


class Attribute:
    """Security modes for attributes. They are accepted for compatibility, but
    only `NO_ACCESS` has an effect, since links are never encrypted."""

    NO_ACCESS = 0x00
    OPEN = 0x11
    ENCRYPT_NO_MITM = 0x21
    ENCRYPT_WITH_MITM = 0x31
    LESC_ENCRYPT_WITH_MITM = 0x41
    SIGNED_NO_MITM = 0x12
    SIGNED_WITH_MITM = 0x22


class UUID:
    """A 16-bit or 128-bit UUID.

    :param value: a 16-bit int, a 16-byte little-endian buffer or a string
        like ``'6e400001-b5a3-f393-e0a9-e50e24dcca9e'``
    """

    def __init__(self, value):
        if isinstance(value, UUID):
            self._uuid16 = value._uuid16
            self._base = value._base
            return
        if isinstance(value, int):
            if not 0 <= value <= 0xFFFF:
                raise ValueError("UUID integer value must be 0-0xffff")
            self._uuid16 = value
            self._base = None
            return
        if isinstance(value, str):
            digits = value.replace("-", "")
            if len(digits) != 32 or len(value) != 36:
                raise ValueError(
                    "UUID string not 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'"
                )
            packed = bytearray(16)
            for i in range(16):
                packed[15 - i] = int(digits[2 * i : 2 * i + 2], 16)
        else:
            packed = bytearray(value)
            if len(packed) != 16:
                raise ValueError("Byte buffer must be 16 bytes.")
        self._uuid16 = packed[12] | (packed[13] << 8)
        packed[12] = 0
        packed[13] = 0
        self._base = bytes(packed)

    @property
    def uuid16(self):
        """The 16-bit part of the UUID."""
        return self._uuid16

    @property
    def uuid128(self):
        """The 128-bit value, little-endian. Only for 128-bit UUIDs."""
        if self._base is None:
            raise AttributeError("not a 128-bit UUID")
        packed = bytearray(self._base)
        packed[12] = self._uuid16 & 0xFF
        packed[13] = self._uuid16 >> 8
        return bytes(packed)

    @property
    def size(self):
        """16 or 128."""
        return 16 if self._base is None else 128

    def pack_into(self, buffer, offset=0):
        """Pack the UUID into ``buffer`` at ``offset``, little-endian."""
        packed = self._packed()
        if offset + len(packed) > len(buffer):
            raise IndexError("Buffer too small")
        for i, b in enumerate(packed):
            buffer[offset + i] = b

    def _packed(self):
        if self._base is None:
            return struct.pack("<H", self._uuid16)
        return self.uuid128

    def _full(self):
        return _att.full_uuid(self._packed())

    def __eq__(self, other):
        return (
            isinstance(other, UUID)
            and self._uuid16 == other._uuid16
            and self._base == other._base
        )

    def __hash__(self):
        return hash(self._packed())

    def __repr__(self):
        if self._base is None:
            return "UUID(0x%04x)" % self._uuid16
        packed = self.uuid128
        h = "".join("%02x" % packed[i] for i in range(15, -1, -1))
        return "UUID('%s-%s-%s-%s-%s')" % (
            h[0:8],
            h[8:12],
            h[12:16],
            h[16:20],
            h[20:32],
        )


class Address:
    """A Bluetooth device address.

    :param address: 6 bytes, least significant byte first
    :param int address_type: one of the type constants below
    """

    PUBLIC = 0x0
    RANDOM_STATIC = 0x1
    RANDOM_PRIVATE_RESOLVABLE = 0x2
    RANDOM_PRIVATE_NON_RESOLVABLE = 0x3

    def __init__(self, address, address_type):
        if len(address) != 6:
            raise ValueError("Address must be 6 bytes long")
        if not 0 <= address_type <= 3:
            raise ValueError("Address type out of range")
        self._bytes = bytes(address)
        self._type = address_type

    @property
    def address_bytes(self):
        """The address, least significant byte first."""
        return self._bytes

    @property
    def type(self):
        """The address type."""
        return self._type

    def _hci_type(self):
        return 0 if self._type == Address.PUBLIC else 1

    @staticmethod
    def _from_hci(address_type, address):
        if address_type in (0, 2):
            return Address(address, Address.PUBLIC)
        top = address[5] >> 6
        if top == 0b11:
            return Address(address, Address.RANDOM_STATIC)
        if top == 0b01:
            return Address(address, Address.RANDOM_PRIVATE_RESOLVABLE)
        return Address(address, Address.RANDOM_PRIVATE_NON_RESOLVABLE)

    def __eq__(self, other):
        return (
            isinstance(other, Address)
            and self._bytes == other._bytes
            and self._type == other._type
        )

    def __hash__(self):
        return hash(self._bytes)

    def __repr__(self):
        return "<Address %s>" % ":".join(
            "%02x" % self._bytes[i] for i in range(5, -1, -1)
        )


# The local GATT database. The index into it is the attribute handle.
_db = [None]
_device_name = None
_generic_services_added = False


def _add_attribute(obj):
    _db.append(obj)
    return len(_db) - 1


def _check_last(service):
    if service.end_handle != len(_db) - 1:
        raise RuntimeError("Can only add to the most recently created Service")


def _ensure_generic_services():
    global _generic_services_added, _device_name  # noqa: PLW0603
    if _generic_services_added:
        return
    _generic_services_added = True
    gap = Service(UUID(0x1800))
    _device_name = Characteristic.add_to_service(
        gap,
        UUID(0x2A00),
        properties=Characteristic.READ,
        max_length=248,
        initial_value=b"CIRCUITPY",
    )
    Characteristic.add_to_service(
        gap,
        UUID(0x2A01),
        properties=Characteristic.READ,
        max_length=2,
        fixed_length=True,
        initial_value=b"\x00\x00",
    )
    gatt = Service(UUID(0x1801))
    Characteristic.add_to_service(
        gatt,
        UUID(0x2A05),
        properties=Characteristic.INDICATE,
        read_perm=Attribute.NO_ACCESS,
        write_perm=Attribute.NO_ACCESS,
        max_length=4,
        fixed_length=True,
        initial_value=b"\x01\x00\xff\xff",
    )


class Service:
    """A GATT service, local or discovered on a remote device.

    :param UUID uuid: the service UUID
    :param bool secondary: True for a secondary service
    """

    _kind = 0

    def __init__(self, uuid, *, secondary=False, _connection=None):
        self.uuid = uuid
        self.secondary = secondary
        self.connection = _connection
        self._characteristics = []
        self.handle = 0
        self.end_handle = 0
        if _connection is None:
            _ensure_generic_services()
            self.handle = _add_attribute(self)
            self.end_handle = self.handle

    @property
    def characteristics(self):
        """The service's characteristics, as a tuple."""
        return tuple(self._characteristics)

    @property
    def remote(self):
        """True if the service belongs to a remote device."""
        return self.connection is not None

    def deinit(self):
        """Does nothing. Local services stay in the GATT database."""

    def __repr__(self):
        return "<Service: %r>" % self.uuid


class Characteristic:
    """A GATT characteristic. Create local ones with `add_to_service`; remote
    ones come from `Connection.discover_remote_services`."""

    BROADCAST = 0x01
    READ = 0x02
    WRITE_NO_RESPONSE = 0x04
    WRITE = 0x08
    NOTIFY = 0x10
    INDICATE = 0x20

    _kind = 1

    def __init__(self):
        self.service = None
        self.uuid = None
        self.properties = 0
        self.read_perm = Attribute.OPEN
        self.write_perm = Attribute.OPEN
        self.max_length = 20
        self.fixed_length = False
        self.decl_handle = 0
        self.handle = 0
        self._value = b""
        self._descriptors = []
        self._cccd = None
        self._cccd_handle = 0
        self._observer = None

    @classmethod
    def add_to_service(
        cls,
        service,
        uuid,
        *,
        properties=0,
        read_perm=Attribute.OPEN,
        write_perm=Attribute.OPEN,
        max_length=20,
        fixed_length=False,
        initial_value=None,
        user_description=None,
    ):
        """Create a characteristic and add it to the most recently created local
        service. Arguments match the native ``_bleio``.

        :return: the new Characteristic
        """
        if service.remote:
            raise ValueError("Can't add to a remote Service")
        _check_last(service)
        if not 0 <= max_length <= 512:
            raise ValueError("max_length must be 0-512")
        if initial_value is None:
            initial_value = bytes(max_length if fixed_length else 0)
        elif len(initial_value) > max_length or (
            fixed_length and len(initial_value) != max_length
        ):
            raise ValueError("initial_value length is wrong")
        characteristic = cls()
        characteristic.service = service
        characteristic.uuid = uuid
        characteristic.properties = properties
        characteristic.read_perm = read_perm
        characteristic.write_perm = write_perm
        characteristic.max_length = max_length
        characteristic.fixed_length = fixed_length
        characteristic._value = bytes(initial_value)
        characteristic.decl_handle = _add_attribute(characteristic)
        characteristic.handle = _add_attribute(characteristic)
        service.end_handle = characteristic.handle
        if properties & (Characteristic.NOTIFY | Characteristic.INDICATE):
            cccd = Descriptor.add_to_characteristic(
                characteristic,
                UUID(0x2902),
                max_length=2,
                fixed_length=True,
                initial_value=b"\x00\x00",
            )
            cccd._is_cccd = True
            characteristic._cccd = cccd
            characteristic._cccd_handle = cccd.handle
        if user_description:
            description = user_description.encode()
            Descriptor.add_to_characteristic(
                characteristic,
                UUID(0x2901),
                read_perm=read_perm,
                write_perm=Attribute.NO_ACCESS,
                max_length=len(description),
                fixed_length=True,
                initial_value=description,
            )
        service._characteristics.append(characteristic)
        return characteristic

    @property
    def descriptors(self):
        """The characteristic's descriptors, as a tuple."""
        return tuple(self._descriptors)

    @property
    def value(self):
        """The value. Reading a remote characteristic asks the remote device;
        setting a local one notifies or indicates subscribed clients."""
        if self.service is not None and self.service.remote:
            return _att.read(self.service.connection, self.handle)
        return self._value

    @value.setter
    def value(self, value):
        if self.service is not None and self.service.remote:
            # Like the native nRF _bleio: write without response whenever the
            # characteristic allows it, since that needs one connection event
            # instead of a round trip.
            if not self.properties & (
                Characteristic.WRITE | Characteristic.WRITE_NO_RESPONSE
            ):
                raise BluetoothError("Characteristic not writable")
            with_response = not self.properties & Characteristic.WRITE_NO_RESPONSE
            _att.write(self.service.connection, self.handle, value, with_response)
            return
        value = bytes(value)
        if len(value) > self.max_length or (
            self.fixed_length and len(value) != self.max_length
        ):
            raise ValueError("Value length is wrong")
        self._value = value
        if self._cccd is not None and adapter is not None:
            adapter._send_to_subscribers(self, value)

    def set_cccd(self, *, notify=False, indicate=False):
        """Subscribe to notifications or indications from a remote characteristic."""
        if self.service is None or not self.service.remote:
            raise RoleError("Only remote Characteristics have a CCCD to set")
        if not self._cccd_handle:
            raise BluetoothError("Characteristic has no CCCD")
        value = struct.pack("<H", (1 if notify else 0) | (2 if indicate else 0))
        _att.write(self.service.connection, self._cccd_handle, value, True)

    def _read(self, conn):
        return self._value

    def _write(self, conn, value):
        self._value = value
        if self._observer is not None:
            self._observer._on_data(value)

    def deinit(self):
        """Does nothing. Local characteristics stay in the GATT database."""

    def __repr__(self):
        return "<Characteristic: %r>" % self.uuid


class Descriptor:
    """A GATT descriptor. Create local ones with `add_to_characteristic`."""

    _kind = 2

    def __init__(self):
        self.characteristic = None
        self.uuid = None
        self.read_perm = Attribute.OPEN
        self.write_perm = Attribute.OPEN
        self.max_length = 20
        self.fixed_length = False
        self.handle = 0
        self._value = b""
        self._is_cccd = False

    @classmethod
    def add_to_characteristic(
        cls,
        characteristic,
        uuid,
        *,
        read_perm=Attribute.OPEN,
        write_perm=Attribute.OPEN,
        max_length=20,
        fixed_length=False,
        initial_value=b"",
    ):
        """Create a descriptor and add it to a characteristic of the most recently
        created local service.

        :return: the new Descriptor
        """
        service = characteristic.service
        _check_last(service)
        if len(initial_value) > max_length or (
            fixed_length and len(initial_value) != max_length
        ):
            raise ValueError("initial_value length is wrong")
        descriptor = cls()
        descriptor.characteristic = characteristic
        descriptor.uuid = uuid
        descriptor.read_perm = read_perm
        descriptor.write_perm = write_perm
        descriptor.max_length = max_length
        descriptor.fixed_length = fixed_length
        descriptor._value = bytes(initial_value)
        descriptor.handle = _add_attribute(descriptor)
        service.end_handle = descriptor.handle
        characteristic._descriptors.append(descriptor)
        return descriptor

    def _remote_connection(self):
        service = self.characteristic.service
        return service.connection if service is not None else None

    @property
    def value(self):
        """The value. Reading a remote descriptor asks the remote device."""
        conn = self._remote_connection()
        if conn is not None:
            return _att.read(conn, self.handle)
        return self._value

    @value.setter
    def value(self, value):
        conn = self._remote_connection()
        if conn is not None:
            _att.write(conn, self.handle, value, True)
            return
        if len(value) > self.max_length or (
            self.fixed_length and len(value) != self.max_length
        ):
            raise ValueError("Value length is wrong")
        self._value = bytes(value)

    def _read(self, conn):
        if self._is_cccd:
            return struct.pack("<H", conn._cccd.get(self.handle, 0))
        return self._value

    def _write(self, conn, value):
        if self._is_cccd:
            conn._cccd[self.handle] = value[0] | (value[1] << 8)
        else:
            self._value = value

    def __repr__(self):
        return "<Descriptor: %r>" % self.uuid


def _poll():
    if adapter is not None:
        adapter._poll()


class CharacteristicBuffer:
    """Accumulates writes to a local characteristic, or notifications from a
    remote one, in a ring buffer.

    :param Characteristic characteristic: the characteristic to monitor
    :param float timeout: seconds to wait for the first byte and between bytes
    :param int buffer_size: size of the ring buffer
    """

    def __init__(self, characteristic, *, timeout=1.0, buffer_size=64):
        self.characteristic = characteristic
        self._timeout = timeout
        self._buffer = bytearray(buffer_size)
        self._start = 0
        self._count = 0
        characteristic._observer = self

    def _on_data(self, data):
        size = len(self._buffer)
        for b in data:
            if self._count == size:
                break
            self._buffer[(self._start + self._count) % size] = b
            self._count += 1

    def _wait(self, nbytes):
        deadline = time.monotonic() + self._timeout
        while self._count < nbytes:
            count = self._count
            _poll()
            if self._count != count:
                deadline = time.monotonic() + self._timeout
            elif time.monotonic() > deadline:
                break

    def _take(self, nbytes):
        n = min(nbytes, self._count)
        out = bytearray(n)
        size = len(self._buffer)
        for i in range(n):
            out[i] = self._buffer[(self._start + i) % size]
        self._start = (self._start + n) % size
        self._count -= n
        return out

    def read(self, nbytes=None):
        """Read up to ``nbytes`` bytes, or everything that arrives before the
        timeout if ``nbytes`` is None.

        :return: the data read, or None if nothing arrived
        :rtype: bytes or None
        """
        self._wait(len(self._buffer) if nbytes is None else nbytes)
        if not self._count:
            return None
        return bytes(self._take(self._count if nbytes is None else nbytes))

    def readinto(self, buf, nbytes=None):
        """Read into ``buf``, at most ``nbytes`` bytes if given.

        :return: the number of bytes read, or None if nothing arrived
        :rtype: int or None
        """
        nbytes = len(buf) if nbytes is None else min(nbytes, len(buf))
        self._wait(nbytes)
        if not self._count:
            return None
        data = self._take(nbytes)
        buf[: len(data)] = data
        return len(data)

    def readline(self):
        """Read up to and including a newline, or until the timeout.

        :return: the line read
        :rtype: bytes
        """
        line = bytearray()
        while True:
            self._wait(1)
            if not self._count:
                break
            b = self._take(1)
            line += b
            if b[0] == 0x0A:
                break
        return bytes(line)

    @property
    def in_waiting(self):
        """The number of bytes waiting to be read."""
        _poll()
        return self._count

    def reset_input_buffer(self):
        """Discard any bytes waiting to be read."""
        self._start = 0
        self._count = 0

    def deinit(self):
        """Stop monitoring the characteristic."""
        if self.characteristic._observer is self:
            self.characteristic._observer = None


class PacketBuffer:
    """Keeps whole packets written to a local characteristic, or notified by a
    remote one, and sends packets the other way.

    :param Characteristic characteristic: the characteristic to monitor
    :param int buffer_size: how many packets to keep
    :param int max_packet_size: largest packet, defaults to the characteristic's max_length
    """

    def __init__(self, characteristic, *, buffer_size, max_packet_size=None):
        self.characteristic = characteristic
        self._limit = buffer_size
        self._packets = []
        self._max_packet_size = max_packet_size or characteristic.max_length
        characteristic._observer = self

    def _on_data(self, data):
        if len(self._packets) < self._limit:
            self._packets.append(bytes(data))

    def readinto(self, buf):
        """Read the next packet into ``buf``.

        :return: the packet's length, or 0 if there was none
        :rtype: int
        """
        _poll()
        if not self._packets:
            return 0
        packet = self._packets.pop(0)
        if len(packet) > len(buf):
            raise ValueError("Buffer too short by %d bytes" % (len(packet) - len(buf)))
        buf[: len(packet)] = packet
        return len(packet)

    def write(self, data, *, header=None):
        """Send a packet, notifying clients of a local characteristic or writing
        a remote one.

        :return: the number of bytes written
        :rtype: int
        """
        packet = bytes(header) + bytes(data) if header else bytes(data)
        characteristic = self.characteristic
        if characteristic.service is not None and characteristic.service.remote:
            with_response = (
                not characteristic.properties & Characteristic.WRITE_NO_RESPONSE
            )
            _att.write(
                characteristic.service.connection,
                characteristic.handle,
                packet,
                with_response,
            )
        else:
            characteristic._value = packet
            if adapter is not None:
                adapter._send_to_subscribers(characteristic, packet)
        return len(packet)

    @property
    def incoming_packet_length(self):
        """Largest packet that can be received."""
        return self._max_packet_size

    @property
    def outgoing_packet_length(self):
        """Largest packet that can be sent."""
        return self._max_packet_size

    def deinit(self):
        """Stop monitoring the characteristic."""
        if self.characteristic._observer is self:
            self.characteristic._observer = None


def _data_matches(data, prefixes, any_match):
    if not prefixes:
        return True
    if not data:
        return False
    i = 0
    while i < len(prefixes):
        prefix_len = prefixes[i]
        i += 1
        prefix = bytes(prefixes[i : i + prefix_len])
        matched = False
        j = 0
        while j < len(data):
            structure_len = data[j]
            j += 1
            if structure_len == 0:
                break
            if (
                structure_len >= prefix_len
                and bytes(data[j : j + prefix_len]) == prefix
            ):
                if any_match:
                    return True
                matched = True
                break
            j += structure_len
        if not matched and not any_match:
            return False
        i += prefix_len
    return not any_match


class ScanEntry:
    """One advertisement or scan response received while scanning."""

    def __init__(self, address, advertisement_bytes, rssi, connectable, scan_response):
        self.address = address
        self.advertisement_bytes = advertisement_bytes
        self.rssi = rssi
        self.connectable = connectable
        self.scan_response = scan_response

    def matches(self, prefixes, *, match_all=True):
        """True if the advertisement has fields starting with ``prefixes``, a
        run of length-prefixed byte strings."""
        return _data_matches(self.advertisement_bytes, prefixes, not match_all)


class ScanResults:
    """Iterates over `ScanEntry` objects until the scan stops."""

    def __init__(self, owner, prefixes, minimum_rssi, buffer_size, timeout):
        self._adapter = owner
        self._prefixes = bytes(prefixes)
        self._minimum_rssi = minimum_rssi
        self._buffer_size = buffer_size
        self._buffered = 0
        self._entries = []
        self._done = False
        self._deadline = time.monotonic() + timeout if timeout else None

    def _add(self, entry):
        if entry.rssi < self._minimum_rssi:
            return
        if not _data_matches(entry.advertisement_bytes, self._prefixes, True):
            return
        if self._buffered + len(entry.advertisement_bytes) > self._buffer_size:
            return
        self._buffered += len(entry.advertisement_bytes)
        self._entries.append(entry)

    def __iter__(self):
        return self

    def __next__(self):
        while not self._entries:
            if self._done:
                raise StopIteration
            self._adapter._poll()
        entry = self._entries.pop(0)
        self._buffered -= len(entry.advertisement_bytes)
        return entry


class Connection:
    """A connection to a remote device, made by `Adapter.connect` or by a
    central connecting to our advertisement."""

    def __init__(self, owner, handle, peer, role, interval):
        self._adapter = owner
        self._handle = handle
        self._peer = peer
        self._role = role
        self._interval = interval
        self._connected = True
        self._mtu = 23
        self._cccd = {}
        self._rx = None
        self._rx_len = 0
        self._response = None
        self._confirmed = False
        self._prepared = []
        self._remote_attributes = {}

    @property
    def connected(self):
        """True while connected."""
        self._adapter._poll()
        return self._connected

    @property
    def paired(self):
        """Always False, since pairing is not implemented."""
        return False

    @property
    def connection_interval(self):
        """The time between connection events, in milliseconds."""
        return self._interval * 1.25

    @connection_interval.setter
    def connection_interval(self, value):
        units = max(6, min(3200, round(value / 1.25)))
        params = struct.pack("<HHHHHHH", self._handle, units, units, 0, 400, 0, 0)
        self._adapter._hci.send_command(_OP_LE_CONNECTION_UPDATE, params)

    @property
    def max_packet_length(self):
        """The largest ATT value that fits in one packet."""
        return self._mtu - 3

    def disconnect(self):
        """Disconnect from the remote device."""
        if not self._connected:
            return
        self._adapter._hci.send_command(
            _OP_DISCONNECT, struct.pack("<HB", self._handle, 0x13)
        )
        deadline = time.monotonic() + 2
        while self._connected and time.monotonic() < deadline:
            self._adapter._poll()

    def pair(self, *, bond=True):
        """Not implemented."""
        raise NotImplementedError("Pairing is not supported")

    def discover_remote_services(self, service_uuids_whitelist=None):
        """Discover the remote device's services, their characteristics and
        their descriptors.

        :param service_uuids_whitelist: only return services with these UUIDs
        :return: the services found
        :rtype: tuple(Service)
        """
        wanted = None
        if service_uuids_whitelist is not None:
            wanted = [uuid._full() for uuid in service_uuids_whitelist]
        services = []
        for start, end, service_uuid in _att.discover_services(self):
            uuid = _uuid_from_packed(service_uuid)
            if wanted is not None and uuid._full() not in wanted:
                continue
            service = Service(uuid, _connection=self)
            service.handle = start
            service.end_handle = end
            found = _att.discover_characteristics(self, start, end)
            for i, (declaration, properties, value_handle, uuid_bytes) in enumerate(
                found
            ):
                characteristic = Characteristic()
                characteristic.service = service
                characteristic.uuid = _uuid_from_packed(uuid_bytes)
                characteristic.properties = properties
                characteristic.max_length = 512
                characteristic.decl_handle = declaration
                characteristic.handle = value_handle
                last = found[i + 1][0] - 1 if i + 1 < len(found) else end
                if value_handle < last:
                    for handle, descriptor_uuid in _att.discover_descriptors(
                        self, value_handle + 1, last
                    ):
                        descriptor = Descriptor()
                        descriptor.characteristic = characteristic
                        descriptor.uuid = _uuid_from_packed(descriptor_uuid)
                        descriptor.handle = handle
                        characteristic._descriptors.append(descriptor)
                        if descriptor_uuid == b"\x02\x29":
                            characteristic._cccd_handle = handle
                service._characteristics.append(characteristic)
                self._remote_attributes[value_handle] = characteristic
            services.append(service)
        return tuple(services)

    def _on_notification(self, handle, value):
        characteristic = self._remote_attributes.get(handle)
        if characteristic is not None:
            characteristic._value = value
            if characteristic._observer is not None:
                characteristic._observer._on_data(value)

    def __repr__(self):
        return "<Connection %r>" % self._peer


def _uuid_from_packed(packed):
    if len(packed) == 2:
        return UUID(packed[0] | (packed[1] << 8))
    return UUID(packed)


class Adapter:
    """A Bluetooth LE radio reached through an HCI transport. The Adapter
    created most recently is the module's `adapter`, which `CharacteristicBuffer`
    and `PacketBuffer` poll, so re-running code that makes a new Adapter (at the
    REPL, say) leaves no stale one behind.

    :param hci: an HCI transport such as `fruitjam_ble.uart_hci.UARTHCI`, set
        up and ready for commands
    :param str name: the device name, which defaults to ``CIRCUITPY`` plus the
        last two bytes of the address
    """

    def __init__(self, hci, *, name=None):
        global adapter  # noqa: PLW0603
        self._hci = hci
        hci.send_command(_OP_SET_EVENT_MASK, b"\xff\xff\xff\xff\xff\xff\xff\x3f")
        # LE connection complete, advertising report, connection update complete,
        # read remote features complete and data length change.
        hci.send_command(_OP_LE_SET_EVENT_MASK, b"\x4f\x00\x00\x00\x00\x00\x00\x00")
        hci.read_buffer_size()
        self._address = Address(hci.read_bd_addr(), Address.PUBLIC)
        self._connections = []
        self._advertising = False
        self._advertising_deadline = None
        self._scan = None
        self._connect_result = None
        self._db = _db
        _ensure_generic_services()
        self._name = None
        address = self._address.address_bytes
        self.name = name if name else "CIRCUITPY%02x%02x" % (address[1], address[0])
        adapter = self

    @property
    def enabled(self):
        """Always True. The controller is on while the Adapter exists."""
        return True

    @enabled.setter
    def enabled(self, value):
        if not value:
            self.stop_advertising()
            self.stop_scan()
            for conn in self.connections:
                conn.disconnect()

    @property
    def address(self):
        """The controller's public address."""
        return self._address

    @property
    def name(self):
        """The device name, also served by the GAP Device Name characteristic."""
        return self._name

    @name.setter
    def name(self, value):
        self._name = value
        encoded = value.encode()[:248]
        _device_name._value = encoded
        try:
            self._hci.send_command(
                _OP_WRITE_LOCAL_NAME, encoded + bytes(248 - len(encoded))
            )
        except Exception:  # noqa: BLE001 LE-only controllers may not take a local name.
            pass

    def start_advertising(
        self,
        data,
        *,
        scan_response=None,
        connectable=True,
        anonymous=False,
        timeout=0,
        interval=0.1,
        tx_power=0,
        directed_to=None,
    ):
        """Start advertising. Only legacy advertising (up to 31 bytes of data and
        of scan response) is supported, and ``anonymous``, ``tx_power`` and
        ``directed_to`` are ignored.

        :param data: advertising data
        :param scan_response: scan response data, or None
        :param bool connectable: whether centrals may connect
        :param int timeout: seconds to advertise for, 0 for no limit
        :param float interval: seconds between advertisements
        """
        if len(data) > 31 or (scan_response is not None and len(scan_response) > 31):
            raise ValueError(
                "Extended advertising is not supported; data must be <= 31 bytes"
            )
        if self._advertising:
            self.stop_advertising()
        units = max(0x20, min(0x4000, round(interval / 0.000625)))
        if connectable:
            advertising_type = 0x00  # ADV_IND
        elif scan_response:
            advertising_type = 0x02  # ADV_SCAN_IND
        else:
            advertising_type = 0x03  # ADV_NONCONN_IND
        hci = self._hci
        hci.send_command(
            _OP_LE_SET_ADV_PARAMS,
            struct.pack(
                "<HHBBB6sBB", units, units, advertising_type, 0, 0, bytes(6), 0x07, 0
            ),
        )
        hci.send_command(
            _OP_LE_SET_ADV_DATA,
            bytes((len(data),)) + bytes(data) + bytes(31 - len(data)),
        )
        scan_response = scan_response or b""
        hci.send_command(
            _OP_LE_SET_SCAN_RESPONSE_DATA,
            bytes((len(scan_response),))
            + bytes(scan_response)
            + bytes(31 - len(scan_response)),
        )
        hci.send_command(_OP_LE_SET_ADV_ENABLE, b"\x01")
        self._advertising = True
        self._advertising_deadline = time.monotonic() + timeout if timeout else None

    def stop_advertising(self):
        """Stop advertising."""
        if not self._advertising:
            return
        self._advertising = False
        try:
            self._hci.send_command(_OP_LE_SET_ADV_ENABLE, b"\x00")
        except Exception:  # noqa: BLE001 Already stopped by a connection.
            pass

    @property
    def advertising(self):
        """True while advertising."""
        self._poll()
        return self._advertising

    def start_scan(
        self,
        prefixes=b"",
        *,
        buffer_size=512,
        extended=False,
        timeout=None,
        interval=0.1,
        window=0.1,
        minimum_rssi=-80,
        active=True,
    ):
        """Start scanning, and return an iterable of `ScanEntry` that ends when
        the scan stops. Only legacy advertisements are received.

        :param prefixes: only return entries with fields starting with one of
            these length-prefixed byte strings
        :param int buffer_size: advertisement bytes to hold before dropping entries
        :param float timeout: seconds to scan, or None to scan until `stop_scan`
        :param float interval: seconds between the starts of scan windows
        :param float window: seconds of each scan window
        :param int minimum_rssi: ignore weaker entries
        :param bool active: request scan responses
        """
        if self._scan is not None:
            raise BluetoothError("Scan already in progress")
        interval_units = max(4, min(0x4000, round(interval / 0.000625)))
        window_units = max(4, min(interval_units, round(window / 0.000625)))
        hci = self._hci
        hci.send_command(
            _OP_LE_SET_SCAN_PARAMS,
            struct.pack(
                "<BHHBB", 1 if active else 0, interval_units, window_units, 0, 0
            ),
        )
        self._scan = ScanResults(self, prefixes, minimum_rssi, buffer_size, timeout)
        hci.send_command(_OP_LE_SET_SCAN_ENABLE, b"\x01\x00")
        return self._scan

    def stop_scan(self):
        """Stop scanning. Entries already received can still be iterated over."""
        if self._scan is None:
            return
        self._scan._done = True
        self._scan = None
        try:
            self._hci.send_command(_OP_LE_SET_SCAN_ENABLE, b"\x00\x00")
        except Exception:  # noqa: BLE001
            pass

    @property
    def connected(self):
        """True if there are any connections."""
        self._poll()
        return bool(self._connections)

    @property
    def connections(self):
        """The current connections, as a tuple."""
        self._poll()
        return tuple(self._connections)

    def connect(self, address, *, timeout):
        """Connect to a peripheral.

        :param Address address: the peripheral's address
        :param float timeout: seconds to try for
        :return: the new connection
        :rtype: Connection
        """
        self.stop_scan()
        params = struct.pack(
            "<HHBB6sBHHHHHH",
            0x0060,
            0x0030,
            0,
            address._hci_type(),
            address.address_bytes,
            0,
            0x0018,
            0x0028,
            0,
            400,
            0,
            0,
        )
        self._connect_result = None
        self._hci.send_command(_OP_LE_CREATE_CONNECTION, params)
        deadline = time.monotonic() + timeout
        while self._connect_result is None and time.monotonic() < deadline:
            self._poll()
        if self._connect_result is None:
            try:
                self._hci.send_command(_OP_LE_CREATE_CONNECTION_CANCEL)
            except Exception:  # noqa: BLE001
                pass
            deadline = time.monotonic() + 1
            while self._connect_result is None and time.monotonic() < deadline:
                self._poll()
        result = self._connect_result
        self._connect_result = None
        if not isinstance(result, Connection):
            raise BluetoothError(
                "Failed to connect: %s"
                % ("timeout" if result in (None, 0x02) else hex(result))
            )
        try:
            _att.exchange_mtu(result)
        except (BluetoothError, ConnectionError):
            pass
        return result

    def erase_bonding(self):
        """Does nothing, since bonding is not implemented."""

    def _find_connection(self, handle):
        for conn in self._connections:
            if conn._handle == handle:
                return conn
        return None

    def _send_l2cap(self, conn, cid, payload):
        frame = bytearray(4 + len(payload))
        struct.pack_into("<HH", frame, 0, len(payload), cid)
        frame[4:] = payload
        self._hci.write_acl(conn._handle, frame)

    def _send_to_subscribers(self, characteristic, value):
        handle = characteristic._cccd_handle
        for conn in self._connections:
            bits = conn._cccd.get(handle, 0)
            if bits & 1 and characteristic.properties & Characteristic.NOTIFY:
                _att.notify(conn, characteristic.handle, value)
            elif bits & 2 and characteristic.properties & Characteristic.INDICATE:
                _att.indicate(conn, characteristic.handle, value)

    def _poll(self):
        hci = self._hci
        for _ in range(8):
            event = hci.read_event(1)
            if event is None:
                break
            self._handle_event(event)
        for _ in range(8):
            packet = hci.read_acl(1)
            if packet is None:
                break
            self._handle_acl(packet)
        if (
            self._advertising_deadline is not None
            and time.monotonic() > self._advertising_deadline
        ):
            self._advertising_deadline = None
            self.stop_advertising()
        scan = self._scan
        if (
            scan is not None
            and scan._deadline is not None
            and time.monotonic() > scan._deadline
        ):
            self.stop_scan()

    def _handle_event(self, event):
        code = event[0]
        if code == _EVT_DISCONNECTION_COMPLETE:
            conn = self._find_connection(event[3] | (event[4] << 8))
            if conn is not None and not event[2]:
                conn._connected = False
                self._connections.remove(conn)
        elif code == _EVT_LE_META:
            subevent = event[2]
            if subevent == _SUBEVT_ADVERTISING_REPORT:
                self._handle_advertising_report(event)
            elif subevent == _SUBEVT_CONNECTION_COMPLETE:
                self._handle_connection_complete(event)
            elif subevent == _SUBEVT_CONNECTION_UPDATE_COMPLETE:
                conn = self._find_connection(event[4] | (event[5] << 8))
                if conn is not None and not event[3]:
                    conn._interval = event[6] | (event[7] << 8)

    def _handle_connection_complete(self, event):
        status = event[3]
        role = event[6]
        if status:
            if role == _ROLE_CENTRAL or self._connect_result is None:
                self._connect_result = status
            return
        handle = event[4] | (event[5] << 8)
        peer = Address._from_hci(event[7], bytes(event[8:14]))
        conn = Connection(self, handle, peer, role, event[14] | (event[15] << 8))
        self._connections.append(conn)
        if role == _ROLE_CENTRAL:
            self._connect_result = conn
        else:
            # A connection ends connectable advertising.
            self._advertising = False
            self._advertising_deadline = None

    def _handle_advertising_report(self, event):
        scan = self._scan
        if scan is None:
            return
        i = 4
        for _ in range(event[3]):
            event_type = event[i]
            address = Address._from_hci(event[i + 1], bytes(event[i + 2 : i + 8]))
            data_len = event[i + 8]
            data = bytes(event[i + 9 : i + 9 + data_len])
            rssi = event[i + 9 + data_len]
            if rssi > 127:
                rssi -= 256
            i += 10 + data_len
            scan._add(
                ScanEntry(address, data, rssi, event_type in (0, 1), event_type == 4)
            )

    def _handle_acl(self, packet):
        conn = self._find_connection((packet[0] | (packet[1] << 8)) & 0x0FFF)
        if conn is None:
            return
        data = packet[4:]
        if (packet[1] >> 4) & 0x3 != 0x1:  # Start of an L2CAP frame.
            if len(data) < 4:
                return
            conn._rx_len = 4 + (data[0] | (data[1] << 8))
            conn._rx = bytearray(data)
        elif conn._rx is not None:
            conn._rx += data
        else:
            return
        if len(conn._rx) < conn._rx_len:
            return
        frame = conn._rx
        conn._rx = None
        cid = frame[2] | (frame[3] << 8)
        payload = memoryview(frame)[4 : conn._rx_len]
        if cid == 0x0004:
            _att.process(conn, self._db, payload)
        elif cid == _CID_SIGNALING:
            self._handle_signaling(conn, payload)
        elif cid == _CID_SMP and payload and payload[0] in (0x01, 0x0B):
            # Pairing Request or Security Request: answer Pairing Failed, Pairing Not Supported.
            self._send_l2cap(conn, _CID_SMP, b"\x05\x05")

    def _handle_signaling(self, conn, payload):
        if len(payload) < 4:
            return
        code, identifier = payload[0], payload[1]
        if code == 0x12 and len(payload) >= 12 and conn._role == _ROLE_CENTRAL:
            # Connection Parameter Update Request from a peripheral: accept it.
            interval_min, interval_max, latency, supervision = struct.unpack_from(
                "<HHHH", payload, 4
            )
            self._send_l2cap(
                conn, _CID_SIGNALING, struct.pack("<BBHH", 0x13, identifier, 2, 0)
            )
            self._hci.send_command(
                _OP_LE_CONNECTION_UPDATE,
                struct.pack(
                    "<HHHHHHH",
                    conn._handle,
                    interval_min,
                    interval_max,
                    latency,
                    supervision,
                    0,
                    0,
                ),
            )
        elif code in (0x02, 0x04, 0x06, 0x0A, 0x12, 0x14, 0x17):
            # Requests we don't handle get a Command Reject, reason "not understood".
            self._send_l2cap(
                conn, _CID_SIGNALING, struct.pack("<BBHH", 0x01, identifier, 2, 0)
            )
