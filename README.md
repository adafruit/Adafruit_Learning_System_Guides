[![Build Status](https://travis-ci.com/adafruit/Adafruit_Learning_System_Guides.svg?branch=main)](https://travis-ci.com/adafruit/Adafruit_Learning_System_Guides)
# Introduction

This is a collection of smaller programs and scripts to display "inline" in
[Adafruit Learning System][learn] guides.  Subdirectories here will generally
contain a README with a link to their corresponding guide.

## Testing

The code here is partially checked by GitHub Actions against Pylint (for
CircuitPython code) or the Arduino compilation process.

Code in directories containing a file called `.circuitpython.skip` will be
skipped by Pylint checks.

Code in directories containing a `.[platformname].test` file, such as
`.uno.test` will be compiled against the corresponding platform.

This is a work in progress.

[learn]: https://learn.adafruit.com/

