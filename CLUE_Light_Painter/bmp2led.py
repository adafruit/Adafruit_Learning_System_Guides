"""
BMP-to-DotStar-ready-bytearrays.
"""

import os
import ulab

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

    def read_row(self, row):
        """
        Read one row of pixels from BMP file, clipped to minimum of BMP
        image width or LED strip length.
        Arguments:
            row (int): index of row to read (0 to (image height - 1))
        Returns: ulab ndarray (uint8 type) containing pixel data in
        BMP-native order (B,G,R per pixel), no need to reorder to DotStar
        order until later.
        """
        # 'flip' logic is intentionally backwards from typical BMP loader,
        # this makes BMP image prep an easy 90 degree CCW rotation.
        if not bmp.flip:
            row = bmp.height - 1 - row
        self.file.seek(bmp.image_offset + row * bmp.row_size)
        return ulab.array(self.file.read(clipped_row_size), dtype=uint8)


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

        # Allocate a working buffer for DotStar data, sized for LED strip.
        # It's formed just like valid strip data (with header, per-pixel
        # start markers and footer), with colors all '0' to start...these
        # will be filled later.
        dotstar_buffer = bytearray([0] * 4 +
                                   [255, 0, 0, 0] * num_pixels +
                                   [255] * ((num_pixels + 15) // 16))
        dotstar_row_size = len(dotstar_buffer)

        # Delete old temporary file, if any
        try:
            os.remove(output_filename)
        except OSError:
            pass

        # Determine free space on drive
        stats = os.statvfs('/')
        bytes_free = stats[0] * stats[4] # block size, free blocks
        if not loop:                       # If not looping, leave space
            bytes_free -= dotstar_row_size # for 'off' LED data at end.
        # Clip the maximum number of output rows based on free space and
        # the size (in bytes) of each DotStar row.
        rows = min(rows, bytes_free // dotstar_row_size)

        try:
            with open(input_filename, 'rb') as file_in:
                #print("File opened")

                bmp = self.read_header()

                #print("WxH: (%d,%d)" % (bmp.width, bmp.height))
                #print("Image format OK, reading data...")

                # Constrain row width to pixel strip length
                clipped_width = min(bmp.width, self.num_pixels)

                # Each output row is interpolated from two BMP rows,
                # we'll call them 'a' and 'b' here.
                row_a_data, row_b_data = None, None
                prev_row_a_index, prev_row_b_index = None

                with open(output_filename, 'wb') as file_out:
                    for row in range(rows): # For each output row...
                        position = row / (rows - 1) # 0.0 to 1.0
                        if callback:
                            callback(position)
                        # Scale position into pixel space...
                        if self.loop: # 0 to image height
                            position *= len(self.columns)
                        else:         # 0 to last row
                            position *= (len(self.columns) - 1)

                        # Separate absolute position into several values:
                        # integer 'a' and 'b' row indices, floating 'a' and
                        # 'b' weights (0.0 to 1.0) for interpolation.
                        row_b_weight, row_a_index = modf(position)
                        row_a_index = int(row_a_index)
                        row_b_index = (row_a_index + 1) % bmp.height
                        row_a_weight = 1.0 - row_b_weight

                        # New data ONLY needs reading if row index changed
                        # (else do another interp/dither with existing data)
                        if row_a_index != prev_row_a_index:
                            # If we've advanced exactly one row, reassign
                            # old 'b' data to 'a' row, else read new 'a'.
                            if row_a_index == prev_row_b_index:
                                row_a_data = row_b_data
                            else:
                                row_a_data = self.read(row_a_index)
                            # Read new 'b' data on any row change
                            row_b_data = self.read(row_b_index)
                        prev_row_a_index = row_a_index
                        prev_row_b_index = row_b_index

                        # Pixel values are stored as bytes from 0-255.
                        # Gamma correction requires floats from 0.0 to 1.0.
                        # So there's a scaling operation involved, BUT, as
                        # configurable brightness is also a thing, we can
                        # work that into the same operation. Rather than
                        # dividing pixels by 255, multiply by
                        # brightness / 255. This reduces the two row
                        # interpolation weights from 0.0-1.0 to
                        # 0.0-brightness/255.
                        row_a_weight *= brightness / 255
                        row_b_weight *= brightness / 255

                        # 'want' is an ndarray of the idealized (as in,
                        # floating-point) pixel values resulting from the
                        # interpolation, with gamma correction applied and
                        # scaled back up to the 0-255 range.
                        want = ((row_a_data * row_a_weight +
                                 row_b_data * row_b_weight) **
                                self.gamma * 255.001)

                        # 'got' will be an ndarray of the values that get
                        # issued to the LED strip, formed through several
                        # operations. First, an 'error term' is added to
                        # each pixel, representing how 'wrong' the prior
                        # output was. This is used for error diffusion
                        # dithering. 'got' is floating-point at this stage.
                        got = ulab.array(want + err)
                        # The error term may push some pixel values outside
                        # the required 0-255 range, so clip the result (aka
                        # 'saturate'). (Note to future self: requested a
                        # clip() function in ulab, should be available for
                        # use soon, would replace these two Python ops).
                        got[got < 0] = 0
                        got[got > 255] = 255
                        # ulab.compare.clip(got, 0, 255)
                        # Now quantize the floating-point 'got' to uint8
                        # type. This represents the actual final byte values
                        # that will be issued to the LED strip.
                        got = ulab.array(got, dtype=ulab.uint8)
                        # Make note of the difference...the 'error term'...
                        # between what we ideally wanted (float) and what we
                        # actually got (dithered, clipped and quantized).
                        # This will get used on the next pass through the
                        # loop. Don't keep 100% of the value, or image
                        # 'shimmers' too much...dial back slightly.
                        err = (want - got) * 0.95

                        # Reorder data from BGR to DotStar color order,
                        # allowing for header and start-of-pixel markers
                        # in the DotStar data.
                        for column in range(clipped_width):
                            bmp_pos = x * 3
                            dotstar_pos = 5 + x * 4
                            bgr = data[bmp_pos:bmp_pos + 3]
                            dotstar_buffer[dotstar_pos + blue_index] = bgr[0]
                            dotstar_buffer[dotstar_pos + green_index] = bgr[1]
                            dotstar_buffer[dotstar_pos + red_index] = bgr[2]

                        file_out.write(dotstar_buffer)

                    # If not looping, add an 'all off' row of LED data
                    # at end to ensure last row timing is consistent.
                    if not loop:
                        rows += 1
                        file_out.write(bytearray([0] * 4 +
                                                 [255, 0, 0, 0] * num_pixels +
                                                 [255] * ((num_pixels + 15) //
                                                          16)))

                #print("Loaded OK!")
                return rows

        except OSError as err:
            if err.args[0] == 28:
                raise OSError("OS Error 28 0.25")
            else:
                raise OSError("OS Error 0.5")
        except BMPError as err:
            print("Failed to parse BMP: " + err.args[0])
