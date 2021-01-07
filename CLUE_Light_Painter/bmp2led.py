"""
BMP-to-DotStar-ready-bytearrays.
"""

# pylint: disable=import-error
import os
import math
import ulab

BUFFER_ROWS = 32

class BMPError(Exception):
    """Used for raising errors in the BMP2LED Class."""


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

    def __init__(self, num_pixels, order='brg', gamma=2.4):
        """
        Constructor for BMP2LED Class. Arguments are values that are not
        expected to change over the life of the object.
        Arguments:
            num_pixels (int) : Number of pixels in DotStar strip.
            order (string)   : DotStar data color order. Optional, default
                               is 'brg', used on most strips.
            gamma (float)    : Optional gamma-correction constant, for
                               more perceptually-linear output.
                               Optional; 2.4 if unspecified.
        """
        order = order.lower()
        self.red_index = order.find('r')
        self.green_index = order.find('g')
        self.blue_index = order.find('b')
        self.num_pixels = num_pixels
        self.gamma = gamma
        self.bmp_file = None
        self.bmp_specs = None


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
        for byte_index, byte in enumerate(self.bmp_file.read(num_bytes)):
            result += byte << (byte_index * 8)
        return result


    def read_header(self):
        """
        Read and validate BMP file heaader. Throws exception if file
        attributes are incorrect (e.g. unsupported BMP variant).
        Returns:
            BMPSpecs object containing size, offset, etc.
        """
        if self.bmp_file.read(2) != b'BM': # Check signature
            raise BMPError("Not BMP file")

        self.bmp_file.read(8) # Read & ignore file size & creator bytes

        image_offset = self.read_le(4) # Start of image data
        self.bmp_file.read(4) # Read & ignore header size
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
                with open(path + '/' + entry, 'rb') as self.bmp_file:
                    self.read_header()
                    valid_list.append(entry)
            except (OSError, BMPError):
                continue

        valid_list.sort() # Alphabetize
        return valid_list


    def read_row(self, row, dest):
        """
        Read one row of pixels from BMP file, clipped to minimum of BMP
        image width or LED strip length.
        Arguments:
            row (int)            : Index of row to read (0 to (img height-1)).
            dest (uint8 ndarray) : Destination buffer. After reading, buffer
                                   contains pixel data in BMP-native order
                                   (B,G,R per pixel), no need to reorder to
                                   DotStar order until later.
        """
        # 'flip' logic is intentionally backwards from typical BMP loader,
        # this makes BMP image prep an easy 90 degree CCW rotation.
        if not self.bmp_specs.flip:
            row = self.bmp_specs.height - 1 - row
        self.bmp_file.seek(self.bmp_specs.image_offset +
                           row * self.bmp_specs.row_size)
        self.bmp_file.readinto(dest)


    # pylint: disable=too-many-arguments, too-many-locals
    # pylint: disable=too-many-branches, too-many-statements
    def process(self, input_filename, output_filename, rows,
                brightness=1.0, loop=False, callback=None):
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
        dotstar_buffer = ulab.array([0] * 4 +
                                    [255, 0, 0, 0] * self.num_pixels +
                                    [255] * ((self.num_pixels + 15) // 16),
                                    dtype=ulab.uint8)
        dotstar_row_size = len(dotstar_buffer)

        # Output rows are held in RAM and periodically written,
        # marginally faster than writing each row separately.
        output_buffer = bytearray(BUFFER_ROWS * dotstar_row_size)
        output_position = 0

        # Delete old temporary file, if any
        try:
            os.remove(output_filename)
        except OSError:
            pass

        # Determine free space on drive
        stats = os.statvfs('/')
        bytes_free = stats[0] * stats[4]   # block size, free blocks
        if not loop:                       # If not looping, leave space
            bytes_free -= dotstar_row_size # for 'off' LED data at end.
        # Clip the maximum number of output rows based on free space and
        # the size (in bytes) of each DotStar row.
        rows = min(rows, bytes_free // dotstar_row_size)

        try:
            with open(input_filename, 'rb') as self.bmp_file:
                #print("File opened")

                self.bmp_specs = self.read_header()

                #print("WxH: (%d,%d)" % (self.bmp_specs.width,
                #                        self.bmp_specs.height))
                #print("Image format OK, reading data...")

                # Constrain bytes-to-read to pixel strip length
                clipped_width = min(self.bmp_specs.width, self.num_pixels)
                row_bytes = 3 * clipped_width

                # Each output row is interpolated from two BMP rows,
                # we'll call them 'a' and 'b' here.
                row_a_data = ulab.zeros(row_bytes, dtype=ulab.uint8)
                row_b_data = ulab.zeros(row_bytes, dtype=ulab.uint8)
                prev_row_a_index, prev_row_b_index = None, None

                with open(output_filename, 'wb') as led_file:
                    # To avoid continually appending to output file (a slow
                    # operation), seek to where the end of the file would
                    # be, write a nonsense byte there, then seek back to
                    # the beginning. Significant improvement!
                    led_file.seek((dotstar_row_size * rows) - 1)
                    led_file.write(b'\0')
                    led_file.seek(0)
                    err = 0
                    for row in range(rows): # For each output row...
                        # Scale position into pixel space...
                        if loop: # 0 to <image height
                            position = self.bmp_specs.height * row / rows
                        else:    # 0 to last row.0
                            position = (row / (rows - 1) *
                                        (self.bmp_specs.height - 1))

                        # Separate absolute position into several values:
                        # integer 'a' and 'b' row indices, floating 'a' and
                        # 'b' weights (0.0 to 1.0) for interpolation.
                        row_b_weight, row_a_index = math.modf(position)
                        row_a_index = min(int(row_a_index),
                                          self.bmp_specs.height - 1)
                        row_b_index = (row_a_index + 1) % self.bmp_specs.height
                        row_a_weight = 1.0 - row_b_weight

                        # New data ONLY needs reading if row index changed
                        # (else do another interp/dither with existing data)
                        if row_a_index != prev_row_a_index:
                            # If we've advanced exactly one row, reassign
                            # old 'b' data to 'a' row (swap, so buffers
                            # remain distinct), else read new 'a'.
                            if row_a_index == prev_row_b_index:
                                row_a_data, row_b_data = row_b_data, row_a_data
                            else:
                                self.read_row(row_a_index, row_a_data)
                            # Read new 'b' data on any row change
                            self.read_row(row_b_index, row_b_data)

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
                        # scaled back up to 8-bit range. Scaling to 254.999
                        # (not 255) lets us avoid a subsequent clip check.
                        want = ((((row_a_data * row_a_weight) +
                                  (row_b_data * row_b_weight)) **
                                 self.gamma) * 254.999)

                        # 'got' will be an ndarray of the values that get
                        # issued to the LED strip, formed through several
                        # operations. First, the 'want' values are quantized
                        # to uint8's -- so these will always be slightly
                        # dimmer (v. occasionally equal) to the 'want' vals.
                        got = ulab.array(want, dtype=ulab.uint8)
                        # Note: naive 'foo = foo + bar' syntax used in this
                        # next section is intentional. ndarrays don't seem
                        # to always play well with '+=' syntax.
                        # The difference between what we want and what we
                        # got will be an ndarray of values from 0.0 to <1.0.
                        # This is accumulated into the error ndarray to be
                        # applied to this and subsequent rows.
                        err = err + want - got
                        # Accumulated error vals will all now be 0.0 to <2.0.
                        # Quantizing err into a new uint8 ndarray, all values
                        # will be 0 or 1.
                        err_bits = ulab.array(err, dtype=ulab.uint8)
                        # Add the 1's back into 'got', increasing the
                        # brightness of certain pixels by 1. Because the max
                        # value in 'got' is 254 (not 255), no clipping need
                        # be performed, everything still fits in uint8.
                        got = got + err_bits
                        # Subtract those applied 1's from the error array,
                        # leaving residue in the range 0.0 to <1.0 which
                        # will be used on subsequent rows.
                        err = err - err_bits

                        # Reorder data from BGR to DotStar color order,
                        # allowing for header and start-of-pixel markers
                        # in the DotStar data.
                        dotstar_buffer[5 + self.blue_index:
                                       5 + 4 * clipped_width:4] = got[0::3]
                        dotstar_buffer[5 + self.green_index:
                                       5 + 4 * clipped_width:4] = got[1::3]
                        dotstar_buffer[5 + self.red_index:
                                       5 + 4 * clipped_width:4] = got[2::3]
                        output_buffer[output_position:output_position +
                                      dotstar_row_size] = memoryview(
                                          dotstar_buffer)

                        # Add converted data to output buffer.
                        # Periodically write when full.
                        output_position += dotstar_row_size
                        if output_position >= len(output_buffer):
                            led_file.write(output_buffer)
                            if callback:
                                callback(row / (rows - 1))
                            output_position = 0

                    # Write any remaining buffered data
                    if output_position:
                        led_file.write(output_buffer[:output_position])
                        if callback:
                            callback(1.0)

                    # If not looping, add an 'all off' row of LED data
                    # at end to ensure last row timing is consistent.
                    if not loop:
                        rows += 1
                        led_file.write(bytearray([0] * 4 +
                                                 [255, 0, 0, 0] *
                                                 self.num_pixels +
                                                 [255] *
                                                 ((self.num_pixels + 15) //
                                                  16)))

                #print("Loaded OK!")
                return rows

        except OSError as err:
            if err.args[0] == 28:
                raise OSError("OS Error 28 0.25") from err
            raise OSError("OS Error 0.5") from err
        except BMPError as err:
            print("Failed to parse BMP: " + err.args[0])
