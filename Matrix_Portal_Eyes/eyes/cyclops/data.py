""" Configuration data for the cyclops eye """
EYE_PATH = __file__[:__file__.rfind('/') + 1]
EYE_DATA = {
    'eye_image'        : EYE_PATH + 'cyclops-eye.bmp',
    'upper_lid_image'  : EYE_PATH + 'cyclops-upper-lid.bmp',
    'lower_lid_image'  : EYE_PATH + 'cyclops-lower-lid.bmp',
    'stencil_image'    : EYE_PATH + 'cyclops-stencil.bmp',
    'transparent'      : (255, 0, 0), # Transparent color in above images
    'eye_move_min'     : (-4, -15),   # eye_image (left, top) move limit
    'eye_move_max'     : (14, -2),    # eye_image (right, bottom) move limit
    'upper_lid_open'   : (15, -23),   # upper_lid_image pos when open
    'upper_lid_center' : (15, -18),   # " when eye centered
    'upper_lid_closed' : (15, 0),     # " when closed
    'lower_lid_open'   : (15, 24),    # lower_lid_image pos when open
    'lower_lid_center' : (15, 23),    # " when eye centered
    'lower_lid_closed' : (15, 17),    # " when closed
}
