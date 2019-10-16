#!/usr/bin/python3

### svgtopy v1.0
"""Print vectors from an SVG input file in python list format
for easy pasting into a program.

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


### it only understands M and L in SVG

### Worth looking at SVG libraries to see if they
### can parse/transform SVG data

import getopt
import sys
import re
##import fileinput
import xml.etree.ElementTree as ET

### globals
### pylint: disable=invalid-name
debug = 0
verbose = False


def usage(exit_code):  ### pylint: disable=missing-docstring
    print("""Usage: svgtopy [-d] [-h] [-v] [--help]
Convert an svg file from from standard input to comma-separated tuples
on standard output for inclusion as a list in a python program.""",
          file=sys.stderr)
    if exit_code is not None:
        sys.exit(exit_code)


def search_path_d(svgdata, point_groups):
    """Look for M and L in the SVG d attribute of a path node"""

    points = []
    for match in re.finditer(r"([A-Za-z])([\d\.]+)\s+([\d\.]+)\s*", svgdata):
        if match:
            cmd = match.group(1)
            if cmd == "M":  ### Start of a new part
                mx, my = match.group(2, 3)
                if points:
                    point_groups.append(points)
                    points = []
                points.append((float(mx), float(my)))
                if debug:
                    print("M pos", mx, my)

            elif cmd == "L":  ### Continuation of current part
                lx, ly = match.group(2, 3)
                points.append((float(lx), float(ly)))
                if debug:
                    print("L pos", lx, ly)

            else:
                print("SVG cmd not implemented:", cmd,
                      file=sys.stderr)
        else:
            print("some parsing issue",
                  file=sys.stderr)

    # Add the last part to point_groups
    if points:
        point_groups.append(points)
        points = []


def main(cmdlineargs):
    """main(args)"""
    global debug, verbose  ### pylint: disable=global-statement

    try:
        opts, _ = getopt.getopt(cmdlineargs,
                                "dhv", ["help"])
    except getopt.GetoptError as err:
        print(err,
              file=sys.stderr)
        usage(2)
    for opt, _ in opts:
        if opt == "-d":
            debug = True
        elif opt == "-v":
            verbose = True
        elif opt in ("-h", "--help"):
            usage(0)
        else:
            print("Internal error: unhandled option",
                  file=sys.stderr)
            sys.exit(3)

    xml_ns = {"svg": "http://www.w3.org/2000/svg"}
    tree = ET.parse(sys.stdin)
    point_groups = []
    for path in tree.findall("svg:path", xml_ns):
        svgdata = path.attrib["d"]
        if verbose:
            print("Processing path with {0:d} length".format(len(svgdata)))
        search_path_d(svgdata, point_groups)



    for idx, points in enumerate(point_groups):
        print("# Group", idx + 1)
        for point in points:
            print("     ", point, ",", sep="")

if __name__ == "__main__":
    main(sys.argv[1:])
