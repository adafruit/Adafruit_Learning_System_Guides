"""
BMP-to-DotStar-ready-bytearrays.
"""

import os

class BMPError(Exception):
    """Used for raising errors in the BMP2LED Class."""
    pass


# pylint: disable=too-few-public-methods
class BMPSpecs:
    """
    Contains vitals of a BMP2LED's active BMP file.
    Returned by the read_header() function.
    """
    def __init__(self, width, height, image_offset, flip):
        """
        BMPSpecs constructor.
        Arguments:
            width (int)        : BMP image width in pixels.
            height (int)       : BMP image height in pixels.
            image_offset (int) : Offset from start of file to first byte of
                                 pixel data.
            flip (boolean)     : True if image is stored bottom-to-top,
                                 vs top-to-bottom.
        """
        self.width = width
        self.height = height
        self.image_offset = image_offset
        self.flip = flip
        self.row_size = (width * 3 + 3) & ~3 # 32-bit line boundary


class BMP2LED:
    """
    Handles conversion of BMP images to a binary file of DotStar-ready
    rows that can be read and passed directly to the SPI write() function.
    Intended for light painting projects.
    """

    def __init__(self, num_pixels, order='brg', gamma=2.6):
        """
        Constructor for BMP2LED Class. Arguments are values that are not
        expected to change over the life of the object.
        Arguments:
            num_pixels (int) : Number of pixels in DotStar strip.
            order (string)   : DotStar data color order. Optional, default
                               is 'brg', used on most strips.
            gamma (float)    : Optional gamma-correction constant, for
                               more perceptually-linear output.
                               Optional; 2.6 if unspecified.
        """
        order = order.lower()
        self.red_index = order.find('r')
        self.green_index = order.find('g')
        self.blue_index = order.find('b')
        self.num_pixels = num_pixels
        self.gamma = gamma
        self.bmpfile = None


    def read_le(self, num_bytes):
        """
        Little-endian read from active BMP file.
        Arguments:
            num_bytes (int) : Number of bytes to read from file and convert
                              to integer value, little-end (least
                              significant byte) first. Typically 2 or 4.
        Returns:
            Converted integer product.
        """
        result = 0
        for byte_index, byte in enumerate(self.bmpfile.read(num_bytes)):
            result += byte << (byte_index * 8)
        return result


    def read_header(self):
        """
        Read and validate BMP file heaader. Throws exception if file
        attributes are incorrect (e.g. unsupported BMP variant).
        Returns:
            BMPSpecs object containing size, offset, etc.
        """
        if self.bmpfile.read(2) != b'BM': # Check signature
            raise BMPError("Not BMP file")

        self.bmpfile.read(8) # Read & ignore file size & creator bytes

        image_offset = self.read_le(4) # Start of image data
        self.bmpfile.read(4) # Read & ignore header size
        width = self.read_le(4)
        height = self.read_le(4)
        # BMPs are traditionally stored bottom-to-top.
        # If bmp_height is negative, image is in top-down order.
        # This is not BMP canon but has been observed in the wild!
        flip = True
        if height < 0:
            height = -height
            flip = False

        if self.read_le(2) != 1:
            raise BMPError("Not single-plane")
        if self.read_le(2) != 24: # bits per pixel
            raise BMPError("Not 24-bit")
        if self.read_le(2) != 0:
            raise BMPError("Compressed file")

        return BMPSpecs(width, height, image_offset, flip)


    def scandir(self, path):
        """
        Scan a given path, looking for compatible BMP image files.
        Arguments:
            path (string) : Directory to search. If '', root path is used.
        Returns:
            List of compatible BMP filenames within path. Path is NOT
            included in names. Subdirectories, non-BMP files and unsupported
            BMP formats (e.g. compressed or paletted) are skipped.
            List will be alphabetically sorted.
        """
        full_list = os.listdir(path)
        valid_list = []
        for entry in full_list:
            try:
                with open(entry, "rb") as self.file:
                    self.read_header()
                    valid_list.append(entry)
            except (OSError, BMPError):
                continue

        valid_list.sort() # Alphabetize
        return valid_list


# old file will be overwritten.
# gamma is stored in self,
# brightness and loop will be passed in.
# Oh...also need to pass in number of rows to stretch.
# Number of LEDs is known from constructor. These are the items:
# self.red_index = order.find('r')
# self.green_index = order.find('g')
# self.blue_index = order.find('b')
# self.num_pixels = num_pixels
# self.gamma = gamma
# self.file = None
# Delete existing tempfile before checking free space.

    def process(self, input_filename, output_filename, rows,
             brightness=None, loop=False, callback=None):
        """
        Process a 24-bit uncompressed BMP file into a series of
        DotStar-ready rows of bytes (including header and footer) written
        to a binary file. The input image is stretched to a specified
        number of rows, applying linear interpolation and error diffusion
        dithering along the way. If BMP rows are narrower than LED strip
        length, image be displayed at start of strip. If BMP rows are
        wider, image will be cropped. Strongly recommended to call
        gc.collect() after this function for smoothest playback.
        Arguments:
            input_filename (string)  : Full path and filename of BMP image.
            output_filename (string) : Full path and filename of binary
                                       output file (DotStar-ready rows).
                                       EXISTING FILE WILL BE RUDELY AND
                                       IMMEDIATELY DELETED (and contents
                                       likely replaced), even if function
                                       fails to finish.
            rows (int)               : Number of rows to write to output
                                       file; image will be stretched.
                                       Actual number of rows may be less
                                       than this depending on storage space.
            brightness (float)       : Overall brightness adjustment, from 0.0
                                       (off) to 1.0 (maximum brightness),
                                       or None to use default (1.0). Since
                                       app is expected to call spi.write()
                                       directly, the conventional DotStar
                                       brightness setting is not observed,
                                       only the value specified here.
            loop (boolean)           : If True, image playback to DotStar
                                       strip will be repeated (end of list
                                       needs to be represented differently
                                       for looped vs. non-looped playback).
            callback (func)          : Callback function for displaying load
                                       progress, will be passed a float
                                       ranging from 0.0 (start) to 1.0 (end).
        Returns: actual number of rows in output file (may be less than
                 number of rows requested, depending on storage space.
        """

        try:
            # Delete output file, then gauge available space on filesystem.
            os.remove(output_filename)
            stats = os.statvfs('/')
            bytes_free = stats[0] * stats[4] # block size, free blocks
            # Clip the maximum number of output rows based on free space and
            # the size (in bytes) of each DotStar row.
            dotstar_row_size = 4 + num_pixels * 4 + ((num_pixels + 15) // 16)
            rows = min(rows, bytes_free // dotstar_buffer_size)

            with open(input_filename, 'rb') as file_in:
                #print("File opened")

                bmp = self.read_header()

                #print("WxH: (%d,%d)" % (bmp.width, bmp.height))
                #print("Image format OK, reading data...")

                # Constrain row width to pixel strip length
                clipped_width = min(bmp.width, self.num_pixels)

                # Progress ratio along image ranges from 0.0 to 1.0 (if
                # looping playback) or a bit under 1.0 (one row relative to
                # full image height) if not looping.
                divisor = (bmp.height - 1) if loop else bmp.height

                with open(output_filename, 'wb') as file_out:
                    for row in range(rows): # For each row...
                        progress = row / divisor # 0.0 to 1.0-ish
row_1 = int((bmp.height - 1) * progress)
row_2 = (row_1 + 1) % bmp.height
#read row_1 and row_2 data if needed



# Open input and output files
# Don't use 'with' with two files, second won't close
# Look at ExitStack(), or use two nested with's.

        try:
            print("Loading", filename)
            with open(filename, "rb") as self.file:



                # Image is displayed at END (not start) of NeoPixel strip,
                # this index works incrementally backward in column buffers...
                idx = (self.num_pixels - 1) * self.bytes_per_pixel
                for row in range(clipped_height): # For each scanline...
                    # Seek to start of scanline
                    if bmp.flip: # Bottom-to-top order (normal BMP)
                        self.file.seek(bmp.image_offset +
                                       (bmp.height - 1 - row) * bmp.row_size)
                    else: # BMP is stored top-to-bottom
                        self.file.seek(bmp.image_offset + row * bmp.row_size)
                    for column in columns: # For each pixel of scanline...
                        # BMP files use BGR color order
                        bgr = self.file.read(3) # Blue, green, red
                        # Rearrange into NeoPixel strip's color order,
                        # while handling brightness & gamma correction:
                        column[idx + self.blue_index] = lut[bgr[0]]
                        column[idx + self.green_index] = lut[bgr[1]]
                        column[idx + self.red_index] = lut[bgr[2]]
                    idx -= self.bytes_per_pixel # Advance (back) one pixel
                    if callback:
                        callback((row + 1) / clipped_height)

                # Add one more column with no color data loaded.  This is used
                # to turn the strip off at the end of the painting operation.
                # It's done this way (rather than checking for last column and
                # clearing LEDs in the painting code) so timing of the last
                # column is consistent and looks good for photos.
                if not loop:
                    columns.append(bytearray(self.num_pixels *
                                             self.bytes_per_pixel))

                #print("Loaded OK!")
                return columns

        except OSError as err:
            if err.args[0] == 28:
                raise OSError("OS Error 28 0.25")
            else:
                raise OSError("OS Error 0.5")
        except BMPError as err:
            print("Failed to parse BMP: " + err.args[0])
