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


import os
import random

from rps_crypto_chacha import ChaCha


def bytesPad(text, size=8, pad=0):
    """Convert a string to bytes and add pad value if necessary to make the length up to size.
       """
    text_as_bytes = text.encode("utf-8")
    if len(text_as_bytes) >= size:
        return text_as_bytes
    else:
        return text_as_bytes + bytes([pad] * (size - len(text_as_bytes)))


def strUnpad(text_as_bytes, pad=0):
    """Convert a bytes or bytearray
       to a str removing trailing bytes matching int pad."""
    text_b = bytes(text_as_bytes)  # bytes type has the useful methods
    if pad is not None:
        text_b = text_b.rstrip(bytes([pad]))

    return text_b.decode("utf-8")


def enlargeKey(small_key, mult):
    """Enlarge a key using a primtive, probably risky replication algorithm!"""
    return small_key * mult


def generateOTPadKey(n_bytes):
    """Generate a random key of n_bytes bytes returned as type bytes.
       This uses the hardware TNG on boards with the feature
       like the nRF52840-based CLUE and CPB.
       Others use the PRNG.
       """
    try:
        key = os.urandom(n_bytes)
    except NotImplementedError:
        key = bytes([random.getrandbits(8) for _ in range(n_bytes)])
    return key


def encrypt(plain_text, key, algorithm, *, nonce=None, counter=None):
    """Encrypt plain_text bytes with key bytes using algorithm.
       Algorithm "xor" can be used for stream ciphers.
    """

    key_data = key(len(plain_text)) if callable(key) else key

    if algorithm == "xor":
        return bytes([plain_text[i] ^ key_data[i] for i in range(len(plain_text))])
    elif algorithm == "chacha20":
        c_counter = 0 if counter is None else counter
        algo = ChaCha(key, nonce, counter=c_counter)
        return algo.encrypt(plain_text)
    else:
        return ValueError("Algorithm not implemented")


def decrypt(cipher_text, key, algorithm, *, nonce=None, counter=None):
    """Decrypt plain_text bytes with key bytes using algorithm.
       Algorithm "xor" can be used for stream ciphers.
    """
    key_data = key(len(cipher_text)) if callable(key) else key

    if algorithm == "xor":
        return encrypt(cipher_text, key_data, "xor")  # enc/dec are same
    elif algorithm == "chacha20":
        c_counter = 0 if counter is None else counter
        algo = ChaCha(key, nonce, counter=c_counter)
        return algo.decrypt(cipher_text)
    else:
        return ValueError("Algorithm not implemented")
