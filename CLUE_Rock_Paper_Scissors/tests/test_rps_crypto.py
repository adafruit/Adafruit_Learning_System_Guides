# The MIT License (MIT)
#
# Copyright (c) 2020 Kevin J. Walters
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import sys
import os

import unittest

verbose = int(os.getenv('TESTVERBOSE', '2'))

# Borrowing the dhalbert/tannewt technique from adafruit/Adafruit_CircuitPython_Motor
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# import what we are testing or will test in future
# pylint: disable=unused-import,wrong-import-position
from rps_crypto import encrypt, decrypt


# pylint: disable=protected-access
class Test_Chacha20(unittest.TestCase):

    algo_name = "chacha20"

    def test_encdec_one(self):
        """Test using values from RFC8439 section 2.3.2."""

        key = bytes(range(32))
        nonce = b"\x00\x00\x00\x00\x00\x00\x00\x4a\x00\x00\x00\x00"
        ##nonce = b"\x00\x00\x00\x09\x00\x00\x00\x4a\x00\x00\x00\x00"
        counter = 1
        plain_text = (b"Ladies and Gentlemen of the class of '99: If I could"
                      b" offer you only one tip for the future,"
                      b" sunscreen would be it.")

        cipher_text = encrypt(plain_text, key, self.algo_name,
                              nonce=nonce, counter=counter)

        expected_cipher_text = (
            b"\x6e\x2e\x35\x9a\x25\x68\xf9\x80\x41\xba\x07\x28\xdd\x0d\x69\x81"
            b"\xe9\x7e\x7a\xec\x1d\x43\x60\xc2\x0a\x27\xaf\xcc\xfd\x9f\xae\x0b"
            b"\xf9\x1b\x65\xc5\x52\x47\x33\xab\x8f\x59\x3d\xab\xcd\x62\xb3\x57"
            b"\x16\x39\xd6\x24\xe6\x51\x52\xab\x8f\x53\x0c\x35\x9f\x08\x61\xd8"
            b"\x07\xca\x0d\xbf\x50\x0d\x6a\x61\x56\xa3\x8e\x08\x8a\x22\xb6\x5e"
            b"\x52\xbc\x51\x4d\x16\xcc\xf8\x06\x81\x8c\xe9\x1a\xb7\x79\x37\x36"
            b"\x5a\xf9\x0b\xbf\x74\xa3\x5b\xe6\xb4\x0b\x8e\xed\xf2\x78\x5e\x42"
            b"\x87\x4d")

        self.assertEqual(cipher_text, expected_cipher_text,
                         msg="Checking cipher text matches expected value")

        decrypted_text = decrypt(cipher_text, key, self.algo_name,
                                 nonce=nonce, counter=counter)

        self.assertEqual(plain_text, decrypted_text,
                         msg="Checking decryption of encrypted text gives original plain text")


    def test_encdec_two(self):
        """Test using values approximating that from RPS game."""

        key = b"TPSecret" * 4
        nonce = bytearray(range(12, 0, -1))
        plain_text = b"rock"

        cipher_text = encrypt(plain_text, key, self.algo_name,
                              nonce=nonce)

        decrypted_text = decrypt(cipher_text, key, self.algo_name,
                                 nonce=nonce)

        # It is possible for these to match but very unlikely in the general case
        self.assertNotEqual(plain_text, cipher_text,
                            msg="Check cipher_text is not plain_text")
        self.assertEqual(plain_text, decrypted_text,
                         msg="Checking decryption of encrypted text gives original plain text")


if __name__ == '__main__':
    unittest.main(verbosity=verbose)
