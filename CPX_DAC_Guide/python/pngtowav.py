#!/usr/bin/python3

### pngtowav v1.0
"""Convert a list of png images to pseudo composite video in wav file form.

This is Python code not intended for running on a microcontroller board.
"""

### MIT License

### Copyright (c) 2019 Kevin J. Walters

### Permission is hereby granted, free of charge, to any person obtaining a copy
### of this software and associated documentation files (the "Software"), to deal
### in the Software without restriction, including without limitation the rights
### to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
### copies of the Software, and to permit persons to whom the Software is
### furnished to do so, subject to the following conditions:

### The above copyright notice and this permission notice shall be included in all
### copies or substantial portions of the Software.

### THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
### IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
### FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
### AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
### LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
### OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
### SOFTWARE.

import getopt
import sys
import array
import wave

import imageio


### globals
### pylint: disable=invalid-name
### start_offset of 1 can help if triggering on oscilloscope
### is missing alternate lines
debug = 0
verbose = False
movie_file = False
output_filename = "dacanim.wav"
fps = 50
threshold = 128  ### pixel level
replaceforsync = False
start_offset = 1

max_dac_v = 3.3
### 16 bit wav files always use signed representation for data
dac_offtop = 2**15-1  ### 3.30V
dac_sync = -2**15     ### 0.00V
### image from 3.00V to 0.30V
dac_top = round(3.00 / max_dac_v * (2**16-1)) - 2**15
dac_bottom = round(0.30 / max_dac_v * (2**16-1)) - 2**15


def usage(exit_code):  ### pylint: disable=missing-docstring
    print("pngtowav: "
          + "[-d] [-f fps] [-h] [-m] [-o outputfilename] [-r] [-s lineoffset] [-t threshold] [-v]",
          file=sys.stderr)
    if exit_code is not None:
        sys.exit(exit_code)


def image_to_dac(img, row_offset, first_pix, dac_y_range):
    """Convert a single image to DAC output."""
    dac_out = array.array("h", [])

    img_height, img_width = img.shape
    if verbose:
        print("W,H", img_width, img_height)

    for row_o in range(img_height):
        row = (row_o + row_offset) % img_height
        ### Currently using 0 to (n-1)/n range
        y_pos = round(dac_top - row / (img_height - 1) * dac_y_range)
        if verbose:
            print("Adding row", row, "at y_pos", y_pos)
        dac_out.extend(array.array("h",
                                   [dac_sync]
                                   + [y_pos if x >= threshold else dac_offtop
                                      for x in img[row, first_pix:]]))
    return dac_out, img_width, img_height


def write_wav(filename, data, framerate):
    """Create one channel 16bit wav file."""
    wav_file = wave.open(filename, "w")
    nchannels = 1
    sampwidth = 2
    nframes = len(data)
    comptype = "NONE"
    compname = "not compressed"
    if verbose:
        print("Writing wav file", filename, "at rate", framerate,
              "with", nframes, "samples")
    wav_file.setparams((nchannels, sampwidth, framerate, nframes,
                        comptype, compname))
    wav_file.writeframes(data)
    wav_file.close()


def main(cmdlineargs):  ### pylint: disable=too-many-branches
    """main(args)"""
    global debug, fps, movie_file, output_filename, replaceforsync  ### pylint: disable=global-statement
    global threshold, start_offset, verbose  ### pylint: disable=global-statement

    try:
        opts, args = getopt.getopt(cmdlineargs,
                                   "f:hmo:rs:t:v", ["help", "output="])
    except getopt.GetoptError as err:
        print(err,
              file=sys.stderr)
        usage(2)
    for opt, arg in opts:
        if opt == "-d":  ### pylint counts these towards too-many-branches :(
            debug = 1
        elif opt == "-f":
            fps = int(arg)
        elif opt in ("-h", "--help"):
            usage(0)
        elif opt == "-m":
            movie_file = True
        elif opt in ("-o", "--output"):
            output_filename = arg
        elif opt == "-r":
            replaceforsync = True
        elif opt == "-s":
            start_offset = int(arg)
        elif opt == "-t":
            threshold = int(arg)
        elif opt == "-v":
            verbose = True
        else:
            print("Internal error: unhandled option",
                  file=sys.stderr)
            sys.exit(3)

    dac_samples = array.array("h", [])

    ### Decide whether to replace first column with sync pulse
    ### or add it as an additional column
    first_pix = 1 if replaceforsync else 0

    ### Read each frame, either
    ### many single image filenames in args or
    ### one or more video (animated gifs) (needs -m on command line)
    dac_y_range = dac_top - dac_bottom
    row_offset = 0
    for arg in args:
        if verbose:
            print("PROCESSING", arg)
        if movie_file:
            images = imageio.mimread(arg)
        else:
            images = [imageio.imread(arg)]

        for img in images:
            img_output, width, height = image_to_dac(img, row_offset,
                                                     first_pix, dac_y_range)
            dac_samples.extend(img_output)
            row_offset += start_offset

    write_wav(output_filename, dac_samples,
              (width + (1 - first_pix)) * height * fps)


if __name__ == "__main__":
    main(sys.argv[1:])
