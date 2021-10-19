# SPDX-FileCopyrightText: 2020 John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

""" Configuration data for the skull eyes """
# Photo by Lina White on Unsplash: https://unsplash.com/photos/K9nxgkYf-RI
EYE_PATH = __file__[:__file__.rfind('/') + 1]
EYE_DATA = {
    'eye_image'        : EYE_PATH + 'skull_bigger-eyes.bmp',
    'upper_lid_image'  : EYE_PATH + 'skull_bigger-upper-lids.bmp',
    'lower_lid_image'  : EYE_PATH + 'skull_bigger-lower-lids.bmp',
    'stencil_image'    : EYE_PATH + 'skull_bigger-stencil.bmp',
    'transparent'      : (255, 0, 0), # Transparent color in above images
    'eye_move_min'     : (-14, -6),     # eye_image (left, top) move limit
    'eye_move_max'     : (-10, 6),     # eye_image (right, bottom) move limit
    'upper_lid_open'   : (0, -13),    # upper_lid_image pos when open
    'upper_lid_center' : (0, -10),    # " when eye centered
    'upper_lid_closed' : (0, 7),     # " when closed
    'lower_lid_open'   : (0, 28),    # lower_lid_image pos when open
    'lower_lid_center' : (0, 22),    # " when eye centered
    'lower_lid_closed' : (0, 13),    # " when closed
}
