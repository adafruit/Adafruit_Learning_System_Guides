""" Configuration data for the skull eyes """
# Photo by Lina White on Unsplash: https://unsplash.com/photos/K9nxgkYf-RI
EYE_PATH = __file__[:__file__.rfind('/') + 1]
EYE_DATA = {
    'eye_image'        : EYE_PATH + 'skull-eyes.bmp',
    'upper_lid_image'  : EYE_PATH + 'skull-upper-lids.bmp',
    'lower_lid_image'  : EYE_PATH + 'skull-lower-lids.bmp',
    'stencil_image'    : EYE_PATH + 'skull-stencil.bmp',
    'transparent'      : (255, 0, 0), # Transparent color in above images
    'eye_move_min'     : (1, -4),     # eye_image (left, top) move limit
    'eye_move_max'     : (11, 5),     # eye_image (right, bottom) move limit
    'upper_lid_open'   : (11, -6),    # upper_lid_image pos when open
    'upper_lid_center' : (11, -3),    # " when eye centered
    'upper_lid_closed' : (11, 5),     # " when closed
    'lower_lid_open'   : (11, 17),    # lower_lid_image pos when open
    'lower_lid_center' : (11, 16),    # " when eye centered
    'lower_lid_closed' : (11, 13),    # " when closed
}
