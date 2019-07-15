"""
Copied and tweaked from micropython-lib
"""

PAD = '='

#pylint:disable=invalid-name,line-too-long
table_a2b_base64 = b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff>\xff\xff\xff?456789:;<=\xff\xff\xff\xff\xff\xff\xff\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\xff\xff\xff\xff\xff\xff\x1a\x1b\x1c\x1d\x1e\x1f !"#$%&\'()*+,-./0123\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
#pylint:enable=line-too-long

assert len(table_a2b_base64) == 256

def a2b_base64(ascii_data):
    "Decode a line of base64 data."

    res = []
    quad_pos = 0
    leftchar = 0
    leftbits = 0
    last_char_was_a_pad = False

    for c in ascii_data:
        c = chr(c)
        if c == PAD:
            if quad_pos > 2 or (quad_pos == 2 and last_char_was_a_pad):
                break      # stop on 'xxx=' or on 'xx=='
            last_char_was_a_pad = True
        else:
            n = ord(table_a2b_base64[ord(c)])
            if n == 0xff:
                continue    # ignore strange characters
            #
            # Shift it in on the low end, and see if there's
            # a byte ready for output.
            quad_pos = (quad_pos + 1) & 3
            leftchar = (leftchar << 6) | n
            leftbits += 6
            #
            if leftbits >= 8:
                leftbits -= 8
                res.append((leftchar >> leftbits).to_bytes(1, 'big'))
                leftchar &= ((1 << leftbits) - 1)
            #
            last_char_was_a_pad = False
    else:
        if leftbits != 0:
            raise Exception("Incorrect padding")

    return b''.join(res)

# ____________________________________________________________

table_b2a_base64 = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/")

def b2a_base64(bin_data):
    "Base64-code line of data."

    newlength = (len(bin_data) + 2) // 3
    newlength = newlength * 4 + 1
    res = []

    leftchar = 0
    leftbits = 0
    for c in bin_data:
        # Shift into our buffer, and output any 6bits ready
        leftchar = (leftchar << 8) | c
        leftbits += 8
        res.append(table_b2a_base64[(leftchar >> (leftbits-6)) & 0x3f])
        leftbits -= 6
        if leftbits >= 6:
            res.append(table_b2a_base64[(leftchar >> (leftbits-6)) & 0x3f])
            leftbits -= 6
    #
    if leftbits == 2:
        res.append(table_b2a_base64[(leftchar & 3) << 4])
        res.append(PAD)
        res.append(PAD)
    elif leftbits == 4:
        res.append(table_b2a_base64[(leftchar & 0xf) << 2])
        res.append(PAD)
    return ''.join(res).encode('ascii')
