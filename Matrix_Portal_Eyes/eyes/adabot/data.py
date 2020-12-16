""" Configuration data for the Adabot eyes """
EYE_PATH = __file__[:__file__.rfind('/') + 1]
EYE_DATA = {
    'eye_image'        : EYE_PATH + 'adabot-eyes.bmp',
    'upper_lid_image'  : EYE_PATH + 'adabot-upper-lids.bmp',
    'lower_lid_image'  : EYE_PATH + 'adabot-lower-lids.bmp',
    'stencil_image'    : EYE_PATH + 'adabot-stencil.bmp',
    'transparent'      : (255, 0, 0), # Transparent color in above images
    'eye_move_min'     : (5, -1),     # eye_image (left, top) move limit
    'eye_move_max'     : (13, 7),     # eye_image (right, bottom) move limit
    'upper_lid_open'   : (13, -5),    # upper_lid_image pos when open
    'upper_lid_center' : (13, -5),    # " when eye centered
    'upper_lid_closed' : (13, 7),     # " when closed
    'lower_lid_open'   : (13, 22),    # lower_lid_image pos when open
    'lower_lid_center' : (13, 22),    # " when eye centered
    'lower_lid_closed' : (13, 15),    # " when closed
}
