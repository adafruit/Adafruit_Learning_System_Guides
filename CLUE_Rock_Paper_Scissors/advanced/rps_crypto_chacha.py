# Copyright (c) 2015 Hubert Kario (code from tlslite-ng library)
# Copyright (c) 2020 Kevin J. Walters (very minor CP tweaks)

# GNU Lesser General Public License, version 2.1
# https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html


"""Pure Python implementation of ChaCha cipher
Implementation that follows RFC 7539 closely.
"""

import struct

MASK32 = 0xffffffff


class ChaCha():
    """Pure python implementation of ChaCha cipher"""

    constants = [0x61707865, 0x3320646e, 0x79622d32, 0x6b206574]

    # pylint: disable=invalid-name
    @staticmethod
    def rotl32(v, c):
        """Rotate left a 32 bit integer v by c bits"""
        return ((v << c) & MASK32) | (v >> (32 - c))

    @staticmethod
    def quarter_round(x, a, b, c, d):
        """Perform a ChaCha quarter round"""
        xa = x[a]
        xb = x[b]
        xc = x[c]
        xd = x[d]

        xa = (xa + xb) & MASK32
        xd = xd ^ xa
        xd = ((xd << 16) & MASK32 | (xd >> 16))

        xc = (xc + xd) & MASK32
        xb = xb ^ xc
        xb = ((xb << 12) & MASK32 | (xb >> 20))

        xa = (xa + xb) & MASK32
        xd = xd ^ xa
        xd = ((xd << 8) & MASK32 | (xd >> 24))

        xc = (xc + xd) & MASK32
        xb = xb ^ xc
        xb = ((xb << 7) & MASK32 | (xb >> 25))

        x[a] = xa
        x[b] = xb
        x[c] = xc
        x[d] = xd

    _round_mixup_box = [(0, 4, 8, 12),
                        (1, 5, 9, 13),
                        (2, 6, 10, 14),
                        (3, 7, 11, 15),
                        (0, 5, 10, 15),
                        (1, 6, 11, 12),
                        (2, 7, 8, 13),
                        (3, 4, 9, 14)]

    @classmethod
    def double_round(cls, x):
        """Perform two rounds of ChaCha cipher"""
        for a, b, c, d in cls._round_mixup_box:
            xa = x[a]
            xb = x[b]
            xc = x[c]
            xd = x[d]

            xa = (xa + xb) & MASK32
            xd = xd ^ xa
            xd = ((xd << 16) & MASK32 | (xd >> 16))

            xc = (xc + xd) & MASK32
            xb = xb ^ xc
            xb = ((xb << 12) & MASK32 | (xb >> 20))

            xa = (xa + xb) & MASK32
            xd = xd ^ xa
            xd = ((xd << 8) & MASK32 | (xd >> 24))

            xc = (xc + xd) & MASK32
            xb = xb ^ xc
            xb = ((xb << 7) & MASK32 | (xb >> 25))

            x[a] = xa
            x[b] = xb
            x[c] = xc
            x[d] = xd

    @staticmethod
    def chacha_block(key, counter, nonce, rounds):
        """Generate a state of a single block"""
        state = ChaCha.constants + key + [counter] + nonce

        working_state = state[:]
        dbl_round = ChaCha.double_round
        for _ in range(0, rounds // 2):
            dbl_round(working_state)

        return [(st + wrkSt) & MASK32 for st, wrkSt
                in zip(state, working_state)]

    @staticmethod
    def word_to_bytearray(state):
        """Convert state to little endian bytestream"""
        return bytearray(struct.pack('<LLLLLLLLLLLLLLLL', *state))

    @staticmethod
    def _bytearray_to_words(data):
        """Convert a bytearray to array of word sized ints"""
        ret = []
        for i in range(0, len(data) // 4):
            ret.extend(struct.unpack('<L', data[i*4:(i+1)*4]))
        return ret

    def __init__(self, key, nonce, counter=0, rounds=20):
        """Set the initial state for the ChaCha cipher"""
        if len(key) != 32:
            raise ValueError("Key must be 256 bit long")
        if len(nonce) != 12:
            raise ValueError("Nonce must be 96 bit long")
        self.key = []
        self.nonce = []
        self.counter = counter
        self.rounds = rounds

        # convert bytearray key and nonce to little endian 32 bit unsigned ints
        self.key = ChaCha._bytearray_to_words(key)
        self.nonce = ChaCha._bytearray_to_words(nonce)

    def encrypt(self, plaintext):
        """Encrypt the data"""
        encrypted_message = bytearray()
        for i, block in enumerate(plaintext[i:i + 64] for i
                                  in range(0, len(plaintext), 64)):
            key_stream = ChaCha.chacha_block(self.key,
                                             self.counter + i,
                                             self.nonce,
                                             self.rounds)
            key_stream = ChaCha.word_to_bytearray(key_stream)
            encrypted_message += bytearray(x ^ y for x, y
                                           in zip(key_stream, block))

        return encrypted_message

    def decrypt(self, ciphertext):
        """Decrypt the data"""
        return self.encrypt(ciphertext)
