import time
import math
import displayio
from adafruit_matrixportal.matrix import Matrix

#--| User Config |-----------------------------------------
SINGULARITIES = (
    # type  location  strength
    ('freestream', None, (1, 0)),
    ('source', (26, 16), 3),
    ('source', (38, 16), -3),
    #('doublet', (32, 16), 1),
    #('vortex', (32, 16), 1),
)
SEEDS = (
#   (x, y) starting location
    (0, 0),
    (0, 3),
    (0, 6),
    (0, 9),
    (0, 12),
    (0, 15),
    (0, 17),
    (0, 20),
    (0, 23),
    (0, 26),
    (0, 29),
)
MATRIX_WIDTH = 64
MATRIX_HEIGHT = 32
BACK_COLOR = 0x000000 # background fill
SING_COLOR = 0xADAF00 # singularities
HEAD_COLOR = 0x00FFFF # leading particles
TAIL_COLOR = 0x000A0A # trailing particles
TAIL_LENGTH = 10      # length in pixels
DELAY = 0.01          # smaller = faster
#----------------------------------------------------------

# matrix and displayio setup
matrix = Matrix(width=MATRIX_WIDTH, height=MATRIX_HEIGHT, bit_depth=6)
display = matrix.display
group = displayio.Group()
display.show(group)

bitmap = displayio.Bitmap(display.width, display.height, 4)

palette = displayio.Palette(4)
palette[0] = BACK_COLOR
palette[1] = SING_COLOR
palette[2] = HEAD_COLOR
palette[3] = TAIL_COLOR

tile_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
group.append(tile_grid)

# global to store streamline data
STREAMLINES = []

def compute_velocity(x, y):
    '''Compute resultant velocity induced at (x, y) from all singularities.'''
    vx = vy = 0
    for s in SINGULARITIES:
        if s[0] == 'freestream':
            vx += s[2][0]
            vy += s[2][1]
        else:
            dx = x - s[1][0]
            dy = y - s[1][1]
            r2 = dx*dx + dy*dy
            if s[0] == 'source':
                vx += s[2] * dx / r2
                vy += s[2] * dy / r2
            elif s[0] == 'vortex':
                vx -=  s[2] * dy / r2
                vy +=  s[2] * dx / r2
            elif s[0] == 'doublet':
                vx += s[2] * (dy*dy - dx*dx) / (r2*r2)
                vy -= s[2] * (2*dx*dy) / (r2*r2)
    return vx, vy

def compute_streamlines():
    '''Compute streamline for each starting point (seed) defined.'''
    for seed in SEEDS:
        streamline = []
        x, y = seed
        px = round(x)
        py = round(y)
        vx, vy = compute_velocity(x, y)
        streamline.append( ((px, py), (vx, vy)) )
        steps = 0
        while x < MATRIX_WIDTH and steps < 2 * MATRIX_WIDTH:
            nx = round(x)
            ny = round(y)
            # if we've moved to a new pixel, store the info
            if nx != px or ny != py:
                streamline.append( ((nx, ny), (vx, vy)) )
                px = nx
                py = ny
            vx, vy = compute_velocity(x, y)
            x += vx
            y += vy
            steps += 1
        # add streamline to global store
        STREAMLINES.append(streamline)

def show_singularities():
    '''Draw the singularites.'''
    for s in SINGULARITIES:
        try:
            x, y = s[1]
            bitmap[round(x), round(y)] = 1
        except:
            pass # just don't draw it

def show_streamlines():
    '''Draw the streamlines.'''
    for sl, head in enumerate(HEADS):
        try:
            streamline = STREAMLINES[sl]
            index = round(head)
            length = min(index, TAIL_LENGTH)
            # draw tail
            for data in streamline[index-length:index]:
                x, y = data[0]
                bitmap[round(x), round(y)] = 3
            # draw head
            bitmap[round(x), round(y)] = 2
        except:
            pass # just don't draw it

def animate_streamlines():
    '''Update the current location (head position) along each streamline.'''
    reset_heads = True
    for sl, head in enumerate(HEADS):
        # get associated streamline
        streamline = STREAMLINES[sl]
        # compute index
        index = round(head)
        # get velocity
        if index < len(streamline):
            vx, vy = streamline[index][1]
            reset_heads = False
        else:
            vx, vy = streamline[-1][1]
        # move head
        HEADS[sl] += math.sqrt(vx*vx + vy*vy)
    if reset_heads:
        # all streamlines have reached the end, so reset to start
        for index, _ in enumerate(HEADS):
            HEADS[index] = 0

def update_display():
    '''Update the matrix display.'''
    display.auto_refresh = False
    bitmap.fill(0)
    show_singularities()
    show_streamlines()
    display.auto_refresh = True

#==========
# MAIN
#==========
print('Computing streamlines...', end='')
compute_streamlines()
print('DONE')
HEADS = [0]*len(STREAMLINES)
print('Flowing...')
while True:
    animate_streamlines()
    update_display()
    time.sleep(DELAY)
