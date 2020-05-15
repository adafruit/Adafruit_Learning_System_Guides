[![Build Status](https://travis-ci.com/adafruit/Adafruit_Learning_System_Guides.svg?branch=master)](https://travis-ci.com/adafruit/Adafruit_Learning_System_Guides)
# Introduction

This is a collection of smaller programs and scripts to display "inline" in
[Adafruit Learning System][learn] guides.  Subdirectories here will generally
contain a README with a link to their corresponding guide.

## Testing

The code here is partially [checked by Travis CI][travis] against Pylint (for
CircuitPython code) or the Arduino compilation process using
[travis-ci-arduino][travis-ci-arduino].

Code in directories containing a file called `.circuitpython.skip` will be
skipped by Pylint checks.

Code in directories containing a `.[platformname].test` file, such as
`.uno.test` will be compiled against the corresponding platform.

This is a work in progress.

## Locally checking pylint

On a unix-style system, install python3 with pip and venv support.
Then run `./pylint_install` to install pylint into a virtual environment
(venv).  Once those steps are done, you can check a particular guide's code
with `./pylint_check directory-name`.  Just running `./pylint_check` will
check all Python code.

[learn]: https://learn.adafruit.com/
[travis]: https://travis-ci.com/adafruit/Adafruit_Learning_System_Guides/
[travis-ci-arduino]: https://github.com/adafruit/travis-ci-arduino/
