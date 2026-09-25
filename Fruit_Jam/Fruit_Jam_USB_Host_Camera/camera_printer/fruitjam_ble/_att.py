# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`fruitjam_ble._att`
================================================================================

Attribute Protocol (ATT) server and client for `fruitjam_ble.bleio`.

The server answers requests against the local attribute table, a list indexed
by handle. Each entry has ``_kind``: 0 for a service declaration, 1 for a
characteristic (both its declaration and value handles) and 2 for a
descriptor.

* Author(s): Tim Cocks
"""

import struct
import time

from micropython import const

# pylint: disable=protected-access, import-outside-toplevel

MAX_MTU = const(247)

_CID_ATT = const(0x0004)
_REQUEST_TIMEOUT = const(10)

_ERROR_RSP = const(0x01)
_MTU_REQ = const(0x02)
_MTU_RSP = const(0x03)
_FIND_INFO_REQ = const(0x04)
_FIND_INFO_RSP = const(0x05)
_FIND_BY_TYPE_REQ = const(0x06)
_FIND_BY_TYPE_RSP = const(0x07)
_READ_BY_TYPE_REQ = const(0x08)
_READ_BY_TYPE_RSP = const(0x09)
_READ_REQ = const(0x0A)
_READ_RSP = const(0x0B)
_READ_BLOB_REQ = const(0x0C)
_READ_BLOB_RSP = const(0x0D)
_READ_BY_GROUP_REQ = const(0x10)
_READ_BY_GROUP_RSP = const(0x11)
_WRITE_REQ = const(0x12)
_WRITE_RSP = const(0x13)
_PREPARE_WRITE_REQ = const(0x16)
_PREPARE_WRITE_RSP = const(0x17)
_EXECUTE_WRITE_REQ = const(0x18)
_EXECUTE_WRITE_RSP = const(0x19)
_HANDLE_VALUE_NTF = const(0x1B)
_HANDLE_VALUE_IND = const(0x1D)
_HANDLE_VALUE_CFM = const(0x1E)
_WRITE_CMD = const(0x52)

_INVALID_HANDLE = const(0x01)
_READ_NOT_PERMITTED = const(0x02)
_WRITE_NOT_PERMITTED = const(0x03)
_INVALID_PDU = const(0x04)
_REQUEST_NOT_SUPPORTED = const(0x06)
_INVALID_OFFSET = const(0x07)
_ATTRIBUTE_NOT_FOUND = const(0x0A)
_INVALID_ATTRIBUTE_VALUE_LENGTH = const(0x0D)
_UNSUPPORTED_GROUP_TYPE = const(0x10)

# Characteristic property bits, as in the Bluetooth spec.
_PROP_READ = const(0x02)
_PROP_WRITE_NO_RESPONSE = const(0x04)
_PROP_WRITE = const(0x08)

_RESPONSES = (
    _ERROR_RSP,
    _MTU_RSP,
    _FIND_INFO_RSP,
    _FIND_BY_TYPE_RSP,
    _READ_BY_TYPE_RSP,
    _READ_RSP,
    _READ_BLOB_RSP,
    _READ_BY_GROUP_RSP,
    _WRITE_RSP,
    _PREPARE_WRITE_RSP,
    _EXECUTE_WRITE_RSP,
)

_PRIMARY_SERVICE = b"\x00\x28"
_SECONDARY_SERVICE = b"\x01\x28"
_CHARACTERISTIC = b"\x03\x28"

_BASE_UUID = b"\xfb\x34\x9b\x5f\x80\x00\x00\x80\x00\x10\x00\x00\x00\x00\x00\x00"


def full_uuid(packed):
    """Return the 16-byte form of a packed 2- or 16-byte UUID, for comparing
    UUIDs of different sizes."""
    if len(packed) == 16:
        return bytes(packed)
    full = bytearray(_BASE_UUID)
    full[12] = packed[0]
    full[13] = packed[1]
    return bytes(full)


def _error(request, handle, code):
    return struct.pack("<BBHB", _ERROR_RSP, request, handle, code)


def _send(conn, pdu):
    conn._adapter._send_l2cap(conn, _CID_ATT, pdu)


def _type_of(db, handle):
    obj = db[handle]
    if obj._kind == 0:
        return _SECONDARY_SERVICE if obj.secondary else _PRIMARY_SERVICE
    if obj._kind == 1 and handle == obj.decl_handle:
        return _CHARACTERISTIC
    return obj.uuid._packed()


def _value_of(conn, db, handle):
    """Return ``(error code, value)`` for reading ``handle``."""
    obj = db[handle]
    if obj._kind == 0:
        return 0, obj.uuid._packed()
    if obj._kind == 1:
        if handle == obj.decl_handle:
            return (
                0,
                bytes((obj.properties,))
                + struct.pack("<H", obj.handle)
                + obj.uuid._packed(),
            )
        if not obj.properties & _PROP_READ or not obj.read_perm:
            return _READ_NOT_PERMITTED, None
        return 0, obj._read(conn)
    if not obj.read_perm:
        return _READ_NOT_PERMITTED, None
    return 0, obj._read(conn)


def _check_write(obj, handle, value):
    if obj._kind == 0 or (obj._kind == 1 and handle == obj.decl_handle):
        return _WRITE_NOT_PERMITTED
    if obj._kind == 1 and not obj.properties & (_PROP_WRITE | _PROP_WRITE_NO_RESPONSE):
        return _WRITE_NOT_PERMITTED
    if not obj.write_perm:
        return _WRITE_NOT_PERMITTED
    if len(value) > obj.max_length or (
        obj.fixed_length and len(value) != obj.max_length
    ):
        return _INVALID_ATTRIBUTE_VALUE_LENGTH
    return 0


def _handle_range(db, pdu):
    """Return ``(start, last)`` for a request's handle range, or None if invalid."""
    start, end = struct.unpack_from("<HH", pdu, 1)
    if start == 0 or start > end:
        return None
    return start, min(end, len(db) - 1)


def _mtu_req(conn, db, pdu):
    # pylint: disable=unused-argument
    # argument used to match interface
    if len(pdu) != 3:
        return _error(_MTU_REQ, 0, _INVALID_PDU)
    client_mtu = pdu[1] | (pdu[2] << 8)
    conn._mtu = max(23, min(client_mtu, MAX_MTU))
    return struct.pack("<BH", _MTU_RSP, MAX_MTU)


def _find_info_req(conn, db, pdu):
    if len(pdu) != 5:
        return _error(_FIND_INFO_REQ, 0, _INVALID_PDU)
    handles = _handle_range(db, pdu)
    if handles is None:
        return _error(_FIND_INFO_REQ, pdu[1] | (pdu[2] << 8), _INVALID_HANDLE)
    start, last = handles
    out = bytearray((_FIND_INFO_RSP, 0))
    for handle in range(start, last + 1):
        attribute_type = _type_of(db, handle)
        uuid_format = 1 if len(attribute_type) == 2 else 2
        if not out[1]:
            out[1] = uuid_format
        elif uuid_format != out[1]:
            break
        if len(out) + 2 + len(attribute_type) > conn._mtu:
            break
        out += struct.pack("<H", handle) + attribute_type
    if not out[1]:
        return _error(_FIND_INFO_REQ, start, _ATTRIBUTE_NOT_FOUND)
    return out


def _find_by_type_req(conn, db, pdu):
    if len(pdu) < 7:
        return _error(_FIND_BY_TYPE_REQ, 0, _INVALID_PDU)
    handles = _handle_range(db, pdu)
    if handles is None:
        return _error(_FIND_BY_TYPE_REQ, pdu[1] | (pdu[2] << 8), _INVALID_HANDLE)
    start, last = handles
    out = bytearray((_FIND_BY_TYPE_RSP,))
    if pdu[5:7] == _PRIMARY_SERVICE and len(pdu) in (9, 23):
        wanted = full_uuid(pdu[7:])
        for handle in range(start, last + 1):
            obj = db[handle]
            if obj._kind != 0 or obj.secondary or handle != obj.handle:
                continue
            if full_uuid(obj.uuid._packed()) != wanted:
                continue
            if len(out) + 4 > conn._mtu:
                break
            out += struct.pack("<HH", handle, obj.end_handle)
    if len(out) == 1:
        return _error(_FIND_BY_TYPE_REQ, start, _ATTRIBUTE_NOT_FOUND)
    return out


def _read_by_type_req(conn, db, pdu):
    if len(pdu) not in (7, 21):
        return _error(_READ_BY_TYPE_REQ, 0, _INVALID_PDU)
    handles = _handle_range(db, pdu)
    if handles is None:
        return _error(_READ_BY_TYPE_REQ, pdu[1] | (pdu[2] << 8), _INVALID_HANDLE)
    start, last = handles
    wanted = full_uuid(pdu[5:])
    out = bytearray((_READ_BY_TYPE_RSP, 0))
    for handle in range(start, last + 1):
        if full_uuid(_type_of(db, handle)) != wanted:
            continue
        error, value = _value_of(conn, db, handle)
        if error:
            if not out[1]:
                return _error(_READ_BY_TYPE_REQ, handle, error)
            break
        value = value[: min(conn._mtu - 4, 253)]
        if not out[1]:
            out[1] = 2 + len(value)
        elif 2 + len(value) != out[1]:
            break
        if len(out) + out[1] > conn._mtu:
            break
        out += struct.pack("<H", handle) + value
    if not out[1]:
        return _error(_READ_BY_TYPE_REQ, start, _ATTRIBUTE_NOT_FOUND)
    return out


def _read_by_group_req(conn, db, pdu):
    if len(pdu) not in (7, 21):
        return _error(_READ_BY_GROUP_REQ, 0, _INVALID_PDU)
    handles = _handle_range(db, pdu)
    if handles is None:
        return _error(_READ_BY_GROUP_REQ, pdu[1] | (pdu[2] << 8), _INVALID_HANDLE)
    start, last = handles
    group = full_uuid(pdu[5:])
    if group == full_uuid(_PRIMARY_SERVICE):
        secondary = False
    elif group == full_uuid(_SECONDARY_SERVICE):
        secondary = True
    else:
        return _error(_READ_BY_GROUP_REQ, start, _UNSUPPORTED_GROUP_TYPE)
    out = bytearray((_READ_BY_GROUP_RSP, 0))
    for handle in range(start, last + 1):
        obj = db[handle]
        if obj._kind != 0 or handle != obj.handle or obj.secondary != secondary:
            continue
        value = obj.uuid._packed()
        if not out[1]:
            out[1] = 4 + len(value)
        elif 4 + len(value) != out[1]:
            break
        if len(out) + out[1] > conn._mtu:
            break
        out += struct.pack("<HH", handle, obj.end_handle) + value
    if not out[1]:
        return _error(_READ_BY_GROUP_REQ, start, _ATTRIBUTE_NOT_FOUND)
    return out


def _read_req(conn, db, pdu):
    if len(pdu) != 3:
        return _error(_READ_REQ, 0, _INVALID_PDU)
    handle = pdu[1] | (pdu[2] << 8)
    if handle == 0 or handle >= len(db):
        return _error(_READ_REQ, handle, _INVALID_HANDLE)
    error, value = _value_of(conn, db, handle)
    if error:
        return _error(_READ_REQ, handle, error)
    return bytes((_READ_RSP,)) + value[: conn._mtu - 1]


def _read_blob_req(conn, db, pdu):
    if len(pdu) != 5:
        return _error(_READ_BLOB_REQ, 0, _INVALID_PDU)
    handle, offset = struct.unpack_from("<HH", pdu, 1)
    if handle == 0 or handle >= len(db):
        return _error(_READ_BLOB_REQ, handle, _INVALID_HANDLE)
    error, value = _value_of(conn, db, handle)
    if error:
        return _error(_READ_BLOB_REQ, handle, error)
    if offset > len(value):
        return _error(_READ_BLOB_REQ, handle, _INVALID_OFFSET)
    return bytes((_READ_BLOB_RSP,)) + value[offset : offset + conn._mtu - 1]


def _write_req(conn, db, pdu):
    respond = pdu[0] == _WRITE_REQ
    if len(pdu) < 3:
        return _error(pdu[0], 0, _INVALID_PDU) if respond else None
    handle = pdu[1] | (pdu[2] << 8)
    if handle == 0 or handle >= len(db):
        return _error(pdu[0], handle, _INVALID_HANDLE) if respond else None
    value = bytes(pdu[3:])
    obj = db[handle]
    error = _check_write(obj, handle, value)
    if error:
        return _error(pdu[0], handle, error) if respond else None
    obj._write(conn, value)
    return bytes((_WRITE_RSP,)) if respond else None


def _prepare_write_req(conn, db, pdu):
    if len(pdu) < 5:
        return _error(_PREPARE_WRITE_REQ, 0, _INVALID_PDU)
    handle, offset = struct.unpack_from("<HH", pdu, 1)
    if handle == 0 or handle >= len(db):
        return _error(_PREPARE_WRITE_REQ, handle, _INVALID_HANDLE)
    error = _check_write(db[handle], handle, b"")
    if error and error != _INVALID_ATTRIBUTE_VALUE_LENGTH:
        return _error(_PREPARE_WRITE_REQ, handle, error)
    conn._prepared.append((handle, offset, bytes(pdu[5:])))
    return bytes((_PREPARE_WRITE_RSP,)) + bytes(pdu[1:])


def _execute_write_req(conn, db, pdu):
    prepared = conn._prepared
    conn._prepared = []
    if len(pdu) == 2 and pdu[1]:
        values = {}
        for handle, offset, part in prepared:
            value = values.setdefault(handle, bytearray())
            if offset != len(value):
                return _error(_EXECUTE_WRITE_REQ, handle, _INVALID_OFFSET)
            value += part
        for handle, value in values.items():
            error = _check_write(db[handle], handle, value)
            if error:
                return _error(_EXECUTE_WRITE_REQ, handle, error)
        for handle, value in values.items():
            db[handle]._write(conn, bytes(value))
    return bytes((_EXECUTE_WRITE_RSP,))


_SERVER = {
    _MTU_REQ: _mtu_req,
    _FIND_INFO_REQ: _find_info_req,
    _FIND_BY_TYPE_REQ: _find_by_type_req,
    _READ_BY_TYPE_REQ: _read_by_type_req,
    _READ_REQ: _read_req,
    _READ_BLOB_REQ: _read_blob_req,
    _READ_BY_GROUP_REQ: _read_by_group_req,
    _WRITE_REQ: _write_req,
    _WRITE_CMD: _write_req,
    _PREPARE_WRITE_REQ: _prepare_write_req,
    _EXECUTE_WRITE_REQ: _execute_write_req,
}


def process(conn, db, pdu):
    """Handle one ATT PDU that arrived on ``conn``."""
    if not pdu:
        return
    opcode = pdu[0]
    if opcode in _RESPONSES:
        conn._response = bytes(pdu)
        return
    if opcode in (_HANDLE_VALUE_NTF, _HANDLE_VALUE_IND):
        if len(pdu) >= 3:
            conn._on_notification(pdu[1] | (pdu[2] << 8), bytes(pdu[3:]))
        if opcode == _HANDLE_VALUE_IND:
            _send(conn, bytes((_HANDLE_VALUE_CFM,)))
        return
    if opcode == _HANDLE_VALUE_CFM:
        conn._confirmed = True
        return
    handler = _SERVER.get(opcode)
    if handler is None:
        if not opcode & 0x40:
            _send(conn, _error(opcode, 0, _REQUEST_NOT_SUPPORTED))
        return
    response = handler(conn, db, pdu)
    if response is not None:
        _send(conn, response)


def notify(conn, handle, value):
    """Send a Handle Value Notification, truncated to fit the connection's MTU."""
    _send(conn, struct.pack("<BH", _HANDLE_VALUE_NTF, handle) + value[: conn._mtu - 3])


def indicate(conn, handle, value):
    """Send a Handle Value Indication and wait for the client to confirm it."""
    conn._confirmed = False
    _send(conn, struct.pack("<BH", _HANDLE_VALUE_IND, handle) + value[: conn._mtu - 3])
    deadline = time.monotonic() + _REQUEST_TIMEOUT
    while not conn._confirmed and conn._connected and time.monotonic() < deadline:
        conn._adapter._poll()


def _request(conn, pdu):
    conn._response = None
    _send(conn, pdu)
    deadline = time.monotonic() + _REQUEST_TIMEOUT
    while conn._response is None:
        if not conn._connected:
            raise ConnectionError(
                "Connection has been disconnected and can no longer be used."
            )
        if time.monotonic() > deadline:
            from .bleio import BluetoothError

            raise BluetoothError("ATT request timed out")
        conn._adapter._poll()
    return conn._response


def _raise_error(response):
    from .bleio import BluetoothError  # noqa: PLC0415 circular at import time

    raise BluetoothError(
        "ATT error 0x%02x on handle 0x%04x"
        % (response[4], response[2] | (response[3] << 8))
    )


def exchange_mtu(conn, mtu=MAX_MTU):
    """As a client, agree on the MTU with the server."""
    response = _request(conn, struct.pack("<BH", _MTU_REQ, mtu))
    if response[0] == _MTU_RSP:
        conn._mtu = max(23, min(mtu, response[1] | (response[2] << 8)))


def discover_services(conn):
    """Return ``(start handle, end handle, packed uuid)`` for each primary service."""
    found = []
    start = 1
    while start <= 0xFFFF:
        response = _request(
            conn, struct.pack("<BHHH", _READ_BY_GROUP_REQ, start, 0xFFFF, 0x2800)
        )
        if response[0] != _READ_BY_GROUP_RSP:
            break
        item_len = response[1]
        last = start
        for i in range(2, len(response) - item_len + 1, item_len):
            service_start, end = struct.unpack_from("<HH", response, i)
            found.append((service_start, end, response[i + 4 : i + item_len]))
            last = end
        if last >= 0xFFFF or last < start:
            break
        start = last + 1
    return found


def discover_characteristics(conn, start, end):
    """Return ``(declaration handle, properties, value handle, packed uuid)`` for each
    characteristic between ``start`` and ``end``."""
    found = []
    while start <= end:
        response = _request(
            conn, struct.pack("<BHHH", _READ_BY_TYPE_REQ, start, end, 0x2803)
        )
        if response[0] != _READ_BY_TYPE_RSP:
            break
        item_len = response[1]
        last = start
        for i in range(2, len(response) - item_len + 1, item_len):
            declaration, properties, value_handle = struct.unpack_from(
                "<HBH", response, i
            )
            found.append(
                (declaration, properties, value_handle, response[i + 5 : i + item_len])
            )
            last = declaration
        if last < start:
            break
        start = last + 1
    return found


def discover_descriptors(conn, start, end):
    """Return ``(handle, packed uuid)`` for each attribute between ``start`` and ``end``."""
    found = []
    while start <= end:
        response = _request(conn, struct.pack("<BHH", _FIND_INFO_REQ, start, end))
        if response[0] != _FIND_INFO_RSP:
            break
        item_len = 4 if response[1] == 1 else 18
        last = start
        for i in range(2, len(response) - item_len + 1, item_len):
            last = response[i] | (response[i + 1] << 8)
            found.append((last, response[i + 2 : i + item_len]))
        if last < start:
            break
        start = last + 1
    return found


def read(conn, handle):
    """Read a remote attribute, using Read Blob requests for long values."""
    response = _request(conn, struct.pack("<BH", _READ_REQ, handle))
    if response[0] != _READ_RSP:
        _raise_error(response)
    value = bytearray(response[1:])
    while len(response) == conn._mtu:
        response = _request(
            conn, struct.pack("<BHH", _READ_BLOB_REQ, handle, len(value))
        )
        if response[0] != _READ_BLOB_RSP:
            break
        value += response[1:]
    return bytes(value)


def write(conn, handle, value, with_response):
    """Write a remote attribute."""
    if len(value) > conn._mtu - 3:
        raise ValueError("Value longer than MTU")
    if with_response:
        response = _request(conn, struct.pack("<BH", _WRITE_REQ, handle) + bytes(value))
        if response[0] != _WRITE_RSP:
            _raise_error(response)
    else:
        _send(conn, struct.pack("<BH", _WRITE_CMD, handle) + bytes(value))
