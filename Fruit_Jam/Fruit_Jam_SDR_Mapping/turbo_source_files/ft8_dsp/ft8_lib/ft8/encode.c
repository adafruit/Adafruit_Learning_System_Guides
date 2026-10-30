// SPDX-FileCopyrightText: Copyright (c) 2018 Karlis Goba
//
// SPDX-License-Identifier: MIT

#include "encode.h"
#include "constants.h"
#include "crc.h"

#include <stdio.h>

// Returns 1 if an odd number of bits are set in x, zero otherwise
static uint8_t parity8(uint8_t x)
{
    x ^= x >> 4;  // a b c d ae bf cg dh
    x ^= x >> 2;  // a b ac bd cae dbf aecg bfdh
    x ^= x >> 1;  // a ab bac acbd bdcae caedbf aecgbfdh
    return x % 2; // modulo 2
}

// Encode via LDPC a 91-bit message and return a 174-bit codeword.
// The generator matrix has dimensions (87,87).
// The code is a (174,91) regular LDPC code with column weight 3.
// Arguments:
// [IN] message   - array of 91 bits stored as 12 bytes (MSB first)
// [OUT] codeword - array of 174 bits stored as 22 bytes (MSB first)
static void encode174(const uint8_t* message, uint8_t* codeword)
{
    // This implementation accesses the generator bits straight from the packed binary representation in kFTX_LDPC_generator

    // Fill the codeword with message and zeros, as we will only update binary ones later
    for (int j = 0; j < FTX_LDPC_N_BYTES; ++j)
    {
        codeword[j] = (j < FTX_LDPC_K_BYTES) ? message[j] : 0;
    }

    // Compute the byte index and bit mask for the first checksum bit
    uint8_t col_mask = (0x80u >> (FTX_LDPC_K % 8u)); // bitmask of current byte
    uint8_t col_idx = FTX_LDPC_K_BYTES - 1;          // index into byte array

    // Compute the LDPC checksum bits and store them in codeword
    for (int i = 0; i < FTX_LDPC_M; ++i)
    {
        // Fast implementation of bitwise multiplication and parity checking
        // Normally nsum would contain the result of dot product between message and kFTX_LDPC_generator[i],
        // but we only compute the sum modulo 2.
        uint8_t nsum = 0;
        for (int j = 0; j < FTX_LDPC_K_BYTES; ++j)
        {
            uint8_t bits = message[j] & kFTX_LDPC_generator[i][j]; // bitwise AND (bitwise multiplication)
            nsum ^= parity8(bits);                                 // bitwise XOR (addition modulo 2)
        }

        // Set the current checksum bit in codeword if nsum is odd
        if (nsum % 2)
        {
            codeword[col_idx] |= col_mask;
        }

        // Update the byte index and bit mask for the next checksum bit
        col_mask >>= 1;
        if (col_mask == 0)
        {
            col_mask = 0x80u;
            ++col_idx;
        }
    }
}

void ft8_encode(const uint8_t* payload, uint8_t* tones)
{
    uint8_t a91[FTX_LDPC_K_BYTES]; // Store 77 bits of payload + 14 bits CRC

    // Compute and add CRC at the end of the message
    // a91 contains 77 bits of payload + 14 bits of CRC
    ftx_add_crc(payload, a91);

    uint8_t codeword[FTX_LDPC_N_BYTES];
    encode174(a91, codeword);

    // Message structure: S7 D29 S7 D29 S7
    // Total symbols: 79 (FT8_NN)

    uint8_t mask = 0x80u; // Mask to extract 1 bit from codeword
    int i_byte = 0;       // Index of the current byte of the codeword
    for (int i_tone = 0; i_tone < FT8_NN; ++i_tone)
    {
        if ((i_tone >= 0) && (i_tone < 7))
        {
            tones[i_tone] = kFT8_Costas_pattern[i_tone];
        }
        else if ((i_tone >= 36) && (i_tone < 43))
        {
            tones[i_tone] = kFT8_Costas_pattern[i_tone - 36];
        }
        else if ((i_tone >= 72) && (i_tone < 79))
        {
            tones[i_tone] = kFT8_Costas_pattern[i_tone - 72];
        }
        else
        {
            // Extract 3 bits from codeword at i-th position
            uint8_t bits3 = 0;

            if (codeword[i_byte] & mask)
                bits3 |= 4;
            if (0 == (mask >>= 1))
            {
                mask = 0x80u;
                i_byte++;
            }
            if (codeword[i_byte] & mask)
                bits3 |= 2;
            if (0 == (mask >>= 1))
            {
                mask = 0x80u;
                i_byte++;
            }
            if (codeword[i_byte] & mask)
                bits3 |= 1;
            if (0 == (mask >>= 1))
            {
                mask = 0x80u;
                i_byte++;
            }

            tones[i_tone] = kFT8_Gray_map[bits3];
        }
    }
}

void ft4_encode(const uint8_t* payload, uint8_t* tones)
{
    uint8_t a91[FTX_LDPC_K_BYTES]; // Store 77 bits of payload + 14 bits CRC
    uint8_t payload_xor[10];       // Encoded payload data

    // '[..] for FT4 only, in order to avoid transmitting a long string of zeros when sending CQ messages,
    // the assembled 77-bit message is bitwise exclusive-OR’ed with [a] pseudorandom sequence before computing the CRC and FEC parity bits'
    for (int i = 0; i < 10; ++i)
    {
        payload_xor[i] = payload[i] ^ kFT4_XOR_sequence[i];
    }

    // Compute and add CRC at the end of the message
    // a91 contains 77 bits of payload + 14 bits of CRC
    ftx_add_crc(payload_xor, a91);

    uint8_t codeword[FTX_LDPC_N_BYTES];
    encode174(a91, codeword); // 91 bits -> 174 bits

    // Message structure: R S4_1 D29 S4_2 D29 S4_3 D29 S4_4 R
    // Total symbols: 105 (FT4_NN)

    uint8_t mask = 0x80u; // Mask to extract 1 bit from codeword
    int i_byte = 0;       // Index of the current byte of the codeword
    for (int i_tone = 0; i_tone < FT4_NN; ++i_tone)
    {
        if ((i_tone == 0) || (i_tone == 104))
        {
            tones[i_tone] = 0; // R (ramp) symbol
        }
        else if ((i_tone >= 1) && (i_tone < 5))
        {
            tones[i_tone] = kFT4_Costas_pattern[0][i_tone - 1];
        }
        else if ((i_tone >= 34) && (i_tone < 38))
        {
            tones[i_tone] = kFT4_Costas_pattern[1][i_tone - 34];
        }
        else if ((i_tone >= 67) && (i_tone < 71))
        {
            tones[i_tone] = kFT4_Costas_pattern[2][i_tone - 67];
        }
        else if ((i_tone >= 100) && (i_tone < 104))
        {
            tones[i_tone] = kFT4_Costas_pattern[3][i_tone - 100];
        }
        else
        {
            // Extract 2 bits from codeword at i-th position
            uint8_t bits2 = 0;

            if (codeword[i_byte] & mask)
                bits2 |= 2;
            if (0 == (mask >>= 1))
            {
                mask = 0x80u;
                i_byte++;
            }
            if (codeword[i_byte] & mask)
                bits2 |= 1;
            if (0 == (mask >>= 1))
            {
                mask = 0x80u;
                i_byte++;
            }
            tones[i_tone] = kFT4_Gray_map[bits2];
        }
    }
}
