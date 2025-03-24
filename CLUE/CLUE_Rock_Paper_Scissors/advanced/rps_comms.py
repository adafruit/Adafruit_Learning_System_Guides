# SPDX-FileCopyrightText: 2020 Kevin J Walters for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# MIT License

# Copyright (c) 2020 Kevin J. Walters

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import time
import random

import _bleio  # just for _bleio.BluetoothError

from adafruit_ble.advertising import Advertisement
import adafruit_ble.advertising.standard  # for encode_data and decode_data


NS_IN_S = 1000 * 1000 * 1000

# The default target time to broadcast in seconds for broadcastAndReceive
DEF_SEND_TIME_S = 4

# 20ms is the minimum delay between advertising packets
# in Bluetooth Low Energy
# extra 10us deals with API floating point rounding issues
MIN_AD_INTERVAL = 0.02001

debug = 3


def d_print(level, *args, **kwargs):
    """A simple conditional print for debugging based on global debug level."""
    if not isinstance(level, int):
        print(level, *args, **kwargs)
    elif debug >= level:
        print(*args, **kwargs)


def addrToText(mac_addr, big_endian=False, sep=""):
    """Convert a mac_addr in bytes to text."""
    # Note use of reversed() - macs are returned in an unusual LSB order
    # pylint: disable=superfluous-parens
    return sep.join(["{:02x}".format(b)
                     for b in (mac_addr if big_endian else reversed(mac_addr))])


def maxAck(acklist):
    """Return the highest ack number from a contiguous run.
       Returns 0 for an empty list."""

    if len(acklist) == 0:
        return 0
    elif len(acklist) == 1:
        return acklist[0]

    ordered_acklist = sorted(acklist)
    max_ack_sofar = ordered_acklist[0]
    for ack in ordered_acklist[1:]:
        if ack - max_ack_sofar > 1:
            break
        max_ack_sofar = ack
    return max_ack_sofar


def startScan(radio, send_ad, send_advertising,
              sequence_number, receive_n,
              ss_rx_ad_classes, rx_ad_classes,
              scan_time, ad_interval,
              buffer_size, minimum_rssi,
              match_locally, scan_response_request,
              enable_ack, awaiting_allrx, awaiting_allacks,
              ad_cb, name_cb, endscan_cb,
              received_ads_by_addr, blenames_by_addr,
              send_ad_rxs, acks):
    # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    """Send an Advertisement send_ad and then wait for up to scan_time to
       receive receive_n Advertisement packets from other devices.
       If receive_n is 0 then wait for the remaining scan_time.
       The callbacks can only be called when packets are received
       so endscan_db has limited functionality.
       This is called repeatedly by broadcastAndReceive.
       """
    complete = False

    if send_advertising:
        try:
            radio.start_advertising(send_ad, interval=ad_interval)
        except _bleio.BluetoothError:
            pass  # catch and ignore "Already advertising."

    # Timeout value is in seconds
    # RSSI -100 is probably practical minimum, -128 would be 8bit signed min
    # window and interval are 0.1 by default - same value means
    # continuous scanning although actual BLE implementations do have a
    # brief gaps in scanning
    # The 1800 byte buffer_size is a quirky workaround for
    # MemoryError: memory allocation failed, allocating 1784 bytes
    # from CP's symbol table growing as the program executes
    cls_send_ad = type(send_ad)
    matching_ads = 0
    for adv_ss in radio.start_scan(*ss_rx_ad_classes,
                                   minimum_rssi=minimum_rssi,
                                   buffer_size=buffer_size,  # default is 512, was 1536
                                   active=scan_response_request,
                                   timeout=scan_time):
        addr_text = addrToText(adv_ss.address.address_bytes)

        # Add name of the device to dict limiting
        # this to devices of interest by checking received_ads_by_addr
        # plus pass data to any callback function
        if (addr_text not in blenames_by_addr
                and addr_text in received_ads_by_addr):
            name = adv_ss.complete_name  # None indicates no value
            if name:  # This test ignores any empty strings too
                blenames_by_addr[addr_text] = name
                if name_cb is not None:
                    name_cb(name, addr_text, adv_ss.address, adv_ss)

        # If using application Advertisement type matching then
        # check the Advertisement's prefix and continue for loop if it
        # does not match
        adv = None
        d_print(5, "RXed RTA", match_locally, addr_text, repr(adv_ss))
        if match_locally:
            adv_ss_as_bytes = adafruit_ble.advertising.standard.encode_data(adv_ss.data_dict)
            for cls in rx_ad_classes:
                prefix = cls.prefix
                # This DOES NOT IMPLEMENT PROPER MATCHING
                # proper matching would involve parsing prefix and then matching each
                # resulting prefix against each dict entry from decode_data()
                # starting at 1 skips over the message length value
                if adv_ss_as_bytes[1:len(prefix)] == prefix[1:]:
                    adv = cls()
                    # Only populating fields in use
                    adv.data_dict = adafruit_ble.advertising.standard.decode_data(adv_ss_as_bytes)
                    adv.address = adv_ss.address
                    d_print(4, "RXed mm RTA", addr_text, adv)
                    break

        else:
            if any(isinstance(adv_ss, cls) for cls in rx_ad_classes):
                adv = adv_ss

        # Continue loop after an endscan callback if ad is not of interest
        if adv is None:  # this means adv was not in rx_ad_classes
            if endscan_cb is not None and endscan_cb(addr_text, adv_ss.address, adv_ss):
                complete = True
                break
            continue

        # Must be a match if this is reached
        matching_ads += 1
        if ad_cb is not None:
            ad_cb(addr_text, adv.address, adv)

        # Look for an ack and record it in acks if not already there
        if hasattr(adv, "ack") and isinstance(adv.ack, int):
            d_print(4, "Found ack")
            if addr_text not in acks:
                acks[addr_text] = [adv.ack]
            elif adv.ack not in acks[addr_text]:
                acks[addr_text].append(adv.ack)

        if addr_text in received_ads_by_addr:
            this_ad_b = bytes(adv)
            for existing_ad in received_ads_by_addr[addr_text]:
                if this_ad_b == existing_ad[1]:
                    break  # already present
            else:  # Python's unusual for/break/else
                received_ads_by_addr[addr_text].append((adv, bytes(adv)))
                if isinstance(adv, cls_send_ad):
                    send_ad_rxs[addr_text] = True
        else:
            received_ads_by_addr[addr_text] = [(adv, bytes(adv))]
            if isinstance(adv, cls_send_ad):
                send_ad_rxs[addr_text] = True

        d_print(5, "send_ad_rxs", len(send_ad_rxs), "ack", len(acks))

        if awaiting_allrx:
            if receive_n > 0 and len(send_ad_rxs) == receive_n:
                if enable_ack and sequence_number is not None:
                    awaiting_allrx = False
                    awaiting_allacks = True
                    if send_advertising:
                        radio.stop_advertising()
                    d_print(4, "old ack", send_ad.ack, "new ack", sequence_number)
                    send_ad.ack = sequence_number
                    if send_advertising:
                        radio.start_advertising(send_ad, interval=ad_interval)
                    d_print(3, "TXing with ack", send_ad,
                            "ack_count", len(acks))
                else:
                    complete = True
                    break  # packets received but not sending ack nor waiting for acks
        elif awaiting_allacks:
            if len(acks) == receive_n:
                ack_count = 0
                for addr_text, acks_for_addr in acks.items():
                    if maxAck(acks_for_addr) >= sequence_number:
                        ack_count += 1
                if ack_count == receive_n:
                    complete = True
                    break  # all acks received, can stop transmitting now

        if endscan_cb is not None:
            if endscan_cb(addr_text, adv_ss.address, adv_ss):
                complete = True
                break

    return (complete, matching_ads, awaiting_allrx, awaiting_allacks)


def broadcastAndReceive(radio, # pylint: disable=dangerous-default-value
                        send_ad,
                        *receive_ads_types,
                        scan_time=DEF_SEND_TIME_S,
                        ad_interval=MIN_AD_INTERVAL,
                        buffer_size=1800,
                        minimum_rssi=-90,
                        receive_n=0,
                        seq_tx=None,
                        match_locally=False,
                        scan_response_request=False,
                        ad_cb=None,
                        ads_by_addr={},
                        names_by_addr={},
                        name_cb=None,
                        endscan_cb=None
                        ):
    # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    """Send an Advertisement send_ad and then wait for up to scan_time to
       receive receive_n Advertisement packets from other devices.
       If receive_n is 0 then wait for the remaining scan_time.
       Returns list of received Advertisements not necessarily in arrival order and
       dictionary indexed by the compressed text representation of the address with a list
       of tuples of (advertisement, bytes(advertisement)).
       This MODIFIES send_ad by setting sequence_number and ack if those
       properties are present.
       This is likely to run for a fraction of second longer than scan_time.
       The default scan_response_request of False should reduce traffic and
       may reduce collisions.
       The buffer_size of 1800 helps to prevent 1784 MemoryError
       from dict enlargement including the interpreter's symbol table.
       """

    sequence_number = None
    if seq_tx is not None and hasattr(send_ad, "sequence_number"):
        sequence_number = seq_tx[0]
        send_ad.sequence_number = sequence_number
        seq_tx[0] += 1

    # A dict to store unique Advertisement indexed by mac address
    # as text string
    cls_send_ad = type(send_ad)
    received_ads_by_addr = dict(ads_by_addr)  # Will not be a deep copy
    if receive_ads_types:
        rx_ad_classes = receive_ads_types
    else:
        rx_ad_classes = (cls_send_ad,)

    if match_locally:
        ss_rx_ad_classes = (Advertisement,)
    elif scan_response_request:
        ss_rx_ad_classes = rx_ad_classes + (Advertisement,)
    else:
        ss_rx_ad_classes = rx_ad_classes

    blenames_by_addr = dict(names_by_addr)  # Will not be a deep copy

    # Look for packets already received of the cls_send_ad class (type)
    send_ad_rxs = {}
    # And make a list of sequence numbers already acknowledged
    acks = {}
    for addr_text, adsnb_per_addr in received_ads_by_addr.items():
        if cls_send_ad in [type(andb[0]) for andb in adsnb_per_addr]:
            send_ad_rxs[addr_text] = True

        # Pick out any Advertisements with an ack field with a value
        acks_thisaddr = [adnb for adnb in adsnb_per_addr
                         if hasattr(adnb[0], "ack")
                         and isinstance(adnb[0].ack, int)]

        if acks_thisaddr:
            seqs = [adnb[0].ack for adnb in acks_thisaddr]
            acks[addr_text] = seqs
            d_print(5, "Acks received for", addr_text,
                    "of", seqs, "in", acks_thisaddr)

    # Determine whether there is a second phase of sending acks
    enable_ack = hasattr(send_ad, "ack")
    # Set an initial ack for anything previously received
    if enable_ack and acks:
        send_ad.ack = max(max(li) for li in acks.values())
    awaiting_allacks = False
    awaiting_allrx = True

    d_print(2, "TXing", send_ad, "interval", ad_interval)
    matched_ads = 0
    complete = False
    d_print(1, "Listening for", ss_rx_ad_classes)
    start_ns = time.monotonic_ns()
    target_end_ns = start_ns + round(scan_time * NS_IN_S)
    advertising_duration = 0.0

    scan_no = 0
    while not complete and time.monotonic_ns() < target_end_ns:
        if endscan_cb is not None and endscan_cb(None, None, None):
            break
        scan_no += 1
        a_rand = random.random()
        # Decide on whether to transmit Advertisement packets
        # or not - this is a workaround for reception problems
        if scan_no > 1 and a_rand < 0.4:
            send_advertising = False
            duration = 0.5 + 2.5 * a_rand  # 50-150ms
        else:
            send_advertising = True
            duration = 0.9  # 900ms
            advertising_duration += duration

        # Lots of arguments passed here, would be safer as keyword args
        (complete, ss_matched,
         awaiting_allrx,
         awaiting_allacks) = startScan(radio, send_ad, send_advertising,
                                       sequence_number, receive_n,
                                       ss_rx_ad_classes, rx_ad_classes,
                                       duration, ad_interval,
                                       buffer_size, minimum_rssi,
                                       match_locally, scan_response_request,
                                       enable_ack, awaiting_allrx, awaiting_allacks,
                                       ad_cb, name_cb, endscan_cb,
                                       received_ads_by_addr, blenames_by_addr,
                                       send_ad_rxs, acks)
        matched_ads += ss_matched

    if advertising_duration > 0.0:
        radio.stop_advertising()
    radio.stop_scan()
    d_print(2, "Matched ads", matched_ads, "with scans", scan_no)

    end_send_ns = time.monotonic_ns()
    d_print(4, "TXRX time", (end_send_ns - start_ns) / 1e9)

    # Make a single list of all the received adverts from the dict
    received_ads = []
    for ads in received_ads_by_addr.values():
        # Pick out the first value, second value is just bytes() version
        received_ads.extend([a[0] for a in ads])
    return (received_ads, received_ads_by_addr, blenames_by_addr)
