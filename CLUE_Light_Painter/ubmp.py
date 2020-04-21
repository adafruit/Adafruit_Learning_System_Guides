"""
BMP-to-ulab-columns code, originally adapted from HalloWing Light Paintstick
but it's mutated through several generations since then. This version uses
ulab ndarrays (rather than bytearrays) to facilitate cool stuff.
"""

# pylint: disable=import-error
from os import listdir
from ulab import array, uint8


class BMPError(Exception):
    """Used for raising errors in the UBMP Class."""
    pass


# pylint: disable=too-few-public-methods
class BMPSpec:
    """
    Contains vitals of a UBMP's active BMP file.
    Returned by the read_header() function.
    """
    def __init__(self, width, height, image_offset, flip):
        """
        BMPSpec constructor.
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


class UBMP:
    """
    Handles conversion of BMP images to a list of ulab uint8 ndarrays
    (representing columns) that can be processed/interpolated and/or
    passed directly to the low-level neopixel_write() function.
    Intended for light painting projects.
    """

    def __init__(self, num_pixels, order='grb'):
        """
        Constructor for UBMP Class.
        Arguments:
            num_pixels (int) : Number of pixels in LED strip, expected
                               to not change over the life of the object.
            order (string)   : LED pixel data color order; grb on most
                               strips, but sometimes others exist.
        """

        self.num_pixels = num_pixels
        self.file = None
        self.bytes_per_pixel = len(order) # Handle RGB vs RGBW
        order = order.lower()
        self.red_index = order.find('r')
        self.green_index = order.find('g')
        self.blue_index = order.find('b')
        # W, if present, will be ignored. Only RGB data from BMP is used.


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
        for byte_index, byte in enumerate(self.file.read(num_bytes)):
            result += byte << (byte_index * 8)
        return result


    def read_header(self):
        """
        Read and validate BMP file heaader. Throws exception if file
        attributes are incorrect (e.g. unsupported BMP variant).
        Returns:
            BMPSpec object containing size, offset, etc.
        """
        if self.file.read(2) != b'BM': # Check signature
            raise BMPError("Not BMP file")

        self.file.read(8) # Read & ignore file size & creator bytes

        image_offset = self.read_le(4) # Start of image data
        self.file.read(4) # Read & ignore header size
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

        return BMPSpec(width, height, image_offset, flip)


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
        full_list = listdir(path)
        valid_list = []
        for entry in full_list:
            try:
                with open(path + '/' + entry, "rb") as self.file:
                    self.read_header()
                    valid_list.append(entry)
            except (OSError, BMPError):
                continue

        valid_list.sort() # Alphabetize
        return valid_list


    def load(self, filename, callback=None):
        """
        Load 24-bit uncompressed BMP file, returning as a list of ulab uint8
        ndarrays that can be processed or passed directly to the low-level
        neopixel_write() function. If BMP image is taller than length of
        LED strip, image will be cropped. If shorter, will be displayed at
        end (not start) of strip. It is recommended to call gc.collect()
        after this function for smoothest playback.

        Arguments:
            filename (string) : Full path and filename of BMP image.
            callback (func)   : Callback function for displaying load
                                progress, will be passed a float ranging
                                from 0.0 to 1.0.
        Returns
            List of ulab uint8 ndarrays  that can be further processed or
            sequentially passed to neopixel_write().
        """

        try:
            print("Loading", filename)
            with open(filename, "rb") as self.file:

                #print("File opened")

                bmp = self.read_header()

                #print("WxH: (%d,%d)" % (bmp.width, bmp.height))
                #print("Image format OK, reading data...")

                # Constrain rows loaded to pixel strip length
                clipped_height = min(bmp.height, self.num_pixels)

                # Allocate per-column pixel buffers, sized for LED strip:
                zerocol = bytearray(self.num_pixels * self.bytes_per_pixel)
                columns = [array(zerocol, dtype=uint8)
                           for _ in range(bmp.width)]

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
                        column[idx + self.blue_index] = bgr[0]
                        column[idx + self.green_index] = bgr[1]
                        column[idx + self.red_index] = bgr[2]
                    idx -= self.bytes_per_pixel # Advance (back) one pixel
                    if callback:
                        callback((row + 1) / clipped_height)

                #print("Loaded OK!")
                return columns

        except OSError as err:
            if err.args[0] == 28:
                raise OSError("OS Error 28 0.25")
            else:
                raise OSError("OS Error 0.5")
        except BMPError as err:
            print("Failed to parse BMP: " + err.args[0])
