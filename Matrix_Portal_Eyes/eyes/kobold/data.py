""" Configuration data for the kobold eyes """
EYE_PATH = __file__[:__file__.rfind('/') + 1]
EYE_DATA = {
    'eye_image'        : EYE_PATH + 'kobold-eyes.bmp',
    'upper_lid_image'  : EYE_PATH + 'kobold-upper-lids.bmp',
    'lower_lid_image'  : EYE_PATH + 'kobold-lower-lids.bmp',
    'stencil_image'    : EYE_PATH + 'kobold-stencil.bmp',
    'transparent'      : (255, 0, 0), # Transparent color in above images
    'eye_move_min'     : (-10, -9),   # eye_image (left, top) move limit
    'eye_move_max'     : (6, 6),      # eye_image (right, bottom) move limit
    'upper_lid_open'   : (6, -7),     # upper_lid_image pos when open
    'upper_lid_center' : (6, -4),     # " when eye centered
    'upper_lid_closed' : (6, 6),      # " when closed
    'lower_lid_open'   : (6, 25),     # lower_lid_image pos when open
    'lower_lid_center' : (6, 23),     # " when eye centered
    'lower_lid_closed' : (6, 15),     # " when closed
}
