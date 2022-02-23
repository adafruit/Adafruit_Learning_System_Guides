# SPDX-FileCopyrightText: 2020 Phillip Burgess for Adafruit Industries
#
# SPDX-License-Identifier: MIT

#!/usr/bin/env python

"""
Nextbus route finder, for selecting bus routes/stops for use with the other
NextBus-related scripts. Crude textual interface is best used w/terminal
with scroll-back ability. Only need to use this for setup, hence the very
basic implementation. Prompts user for transit agency, bus line, direction
and stop, issues a string which can then be copied & pasted into predictor
program. Not fancy, just uses text prompts, minimal error checking.

THIS IS FOR "FULL" PYTHON USE, NOT CIRCUITPYTHON.
"""

# pylint: disable=superfluous-parens

from xml.dom.minidom import parseString
from six.moves import input     # Python 3 input() vs Python 2 input_raw()
try:
    from urllib import request  # Python 3
except ImportError:
    import urllib as request    # Python 2

def print_numbered_list(items):
    """Given a list, print it with a number (1-N) for each item and
       the value corresponding to the 'title' attribute string."""
    for index, item in enumerate(items):
        print(str(index + 1) + ') ' + item.getAttribute('title'))

def get_number(prompt, upper_limit):
    """Prompt user for a number in a given range 1 to N.
       Return value is actually 0 to N-1."""
    while True:
        number = input('Enter ' + prompt + ' 1-' + str(upper_limit) + ': ')
        try:
            number = int(number) - 1
        except ValueError:
            continue      # Ignore non-numbers
        if 0 <= number < upper_limit:
            return number # and out-of-range values

def req(cmd):
    """Open connection, issue request, read & parse XML response."""
    connection = request.urlopen(
        'http://webservices.nextbus.com'  +
        '/service/publicXMLFeed?command=' + cmd)
    raw = connection.read()
    connection.close()
    return parseString(raw)

# Main application, kinda brute-force code -----------------------------------

# Get list of transit agencies, prompt user for selection, get agency tag.
DOM = req('agencyList')
ELEMENTS = DOM.getElementsByTagName('agency')
print('TRANSIT AGENCIES:')
print_numbered_list(ELEMENTS)
NUMBER = get_number('transit agency', len(ELEMENTS))
AGENCY_TAG = ELEMENTS[NUMBER].getAttribute('tag')

# Get list of routes for selected agency, prompt user, get route tag.
DOM = req('routeList&a=' + AGENCY_TAG)
ELEMENTS = DOM.getElementsByTagName('route')
print('\nROUTES:')
print_numbered_list(ELEMENTS)
NUMBER = get_number('route', len(ELEMENTS))
ROUTE_TAG = ELEMENTS[NUMBER].getAttribute('tag')

# Get list of directions for selected agency & route, prompt user...
DOM = req('routeConfig&a=' + AGENCY_TAG + '&r=' + ROUTE_TAG)
ELEMENTS = DOM.getElementsByTagName('direction')
print('\nDIRECTIONS:')
print_numbered_list(ELEMENTS)
NUMBER = get_number('direction', len(ELEMENTS))
DIR_TITLE = ELEMENTS[NUMBER].getAttribute('title') # Save for later
# ...then get list of stop numbers and descriptions -- these are
# nested in different parts of the XML and must be cross-referenced
STOP_NUMBERS = ELEMENTS[NUMBER].getElementsByTagName('stop')
STOP_DESCRIPTIONS = DOM.getElementsByTagName('stop')

# Cross-reference stop numbers and descriptions to provide a readable
# list of available stops for selected agency, route & direction.
# Prompt user for stop number and get corresponding stop tag.
print('\nSTOPS:')
for INDEX, ITEM in enumerate(STOP_NUMBERS):
    STOP_NUM_TAG = ITEM.getAttribute('tag')
    for desc in STOP_DESCRIPTIONS:
        STOP_DESCRIPTION = desc.getAttribute('tag')
        if STOP_NUM_TAG == STOP_DESCRIPTION:
            print(str(INDEX + 1) + ') ' + desc.getAttribute('title'))
            break
NUMBER = get_number('stop', len(STOP_NUMBERS))
STOP_TAG = STOP_NUMBERS[NUMBER].getAttribute('tag')

# The prediction server wants the stop tag, NOT the stop ID, not sure
# what's up with that.

print('\nCOPY/PASTE INTO APPLICATION SCRIPT:')
print("    ('" + AGENCY_TAG + "', '" + ROUTE_TAG + "', '" + STOP_TAG +
      "', '" + DIR_TITLE + "'),")
