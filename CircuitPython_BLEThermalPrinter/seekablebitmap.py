# SPDX-FileCopyrightText: 2021 Jeff Epler for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import struct

class SeekableBitmap:
    """Allow random access to an uncompressed bitmap file on disk"""
    def __init__(
        self,
        image_file,
        width,
        height,
        bits_per_pixel,
        *,
        bytes_per_row=None,
        data_start=None,
        stride=None,
        palette=None,
    ):
        """Construct a SeekableBitmap"""
        self.image_file = image_file
        self.width = width
        self.height = height
        self.bits_per_pixel = bits_per_pixel
        self.bytes_per_row = (
            bytes_per_row if bytes_per_row else (bits_per_pixel * width + 7) // 8
        )
        self.stride = stride if stride else self.bytes_per_row
        self.palette = palette
        self.data_start = data_start if data_start else image_file.tell()

    def get_row(self, row):
        self.image_file.seek(self.data_start + row * self.stride)
        return self.image_file.read(self.bytes_per_row)


def _pnmopen(filename):
    """
    Scan for netpbm format info, skip over comments, and read header data.

    Return the format, header, and the opened file positioned at the start of
    the bitmap data.
    """
    # pylint: disable=too-many-branches
    image_file = open(filename, "rb")
    magic_number = image_file.read(2)
    image_file.seek(2)
    pnm_header = []
    next_value = bytearray()
    while True:
        # We have all we need at length 3 for formats P2, P3, P5, P6
        if len(pnm_header) == 3:
            return image_file, magic_number, pnm_header

        if len(pnm_header) == 2 and magic_number in [b"P1", b"P4"]:
            return image_file, magic_number, pnm_header

        next_byte = image_file.read(1)
        if next_byte == b"":
            raise RuntimeError("Unsupported image format {}".format(magic_number))
        if next_byte == b"#":  # comment found, seek until a newline or EOF is found
            while image_file.read(1) not in [b"", b"\n"]:  # EOF or NL
                pass
        elif not next_byte.isdigit():  # boundary found in header data
            if next_value:
                # pull values until space is found
                pnm_header.append(int("".join(["%c" % char for char in next_value])))
                next_value = bytearray()  # reset the byte array
        else:
            next_value += next_byte  # push the digit into the byte array


def pnmopen(filename):
    """
    Interpret netpbm format info and construct a SeekableBitmap
    """
    image_file, magic_number, pnm_header = _pnmopen(filename)
    if magic_number == b"P4":
        return SeekableBitmap(
            image_file,
            pnm_header[0],
            pnm_header[1],
            1,
            palette=b"\xff\xff\xff\x00\x00\x00\x00\x00",
        )
    if magic_number == b"P5":
        return SeekableBitmap(
            image_file, pnm_header[0], pnm_header[1], pnm_header[2].bit_length()
        )
    if magic_number == b"P6":
        return SeekableBitmap(
            image_file, pnm_header[0], pnm_header[1], 3 * pnm_header[2].bit_length()
        )
    raise ValueError(f"Unknown or unsupported magic number {magic_number}")


def bmpopen(filename):
    """
    Interpret bmp format info and construct a SeekableBitmap
    """
    image_file = open(filename, "rb")

    header = image_file.read(34)

    data_start, header_size, width, height, _, bits_per_pixel, _ = struct.unpack(
        "<10x4l2hl", header
    )

    bits_per_pixel = bits_per_pixel if bits_per_pixel != 0 else 1

    palette_start = header_size + 14
    image_file.seek(palette_start)
    palette = image_file.read(4 << bits_per_pixel)

    stride = (bits_per_pixel * width + 31) // 32 * 4
    if height < 0:
        height = -height
    else:
        data_start = data_start + stride * (height - 1)
        stride = -stride

    return SeekableBitmap(
        image_file,
        width,
        height,
        bits_per_pixel,
        data_start=data_start,
        stride=stride,
        palette=palette,
    )


def imageopen(filename):
    """
    Open a bmp or pnm file as a seekable bitmap
    """
    if filename.lower().endswith(".bmp"):
        return bmpopen(filename)
    return pnmopen(filename)
