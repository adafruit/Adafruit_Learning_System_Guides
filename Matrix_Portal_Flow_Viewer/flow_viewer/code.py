#======
# NOTE: Run this on the Matrix Portal.
#======
import time
import math
import displayio
from adafruit_matrixportal.matrix import Matrix

from flow_solution import solution

#--| User Config |-----------------------------------------
SEEDS = (
#   (x, y) starting location
    (0, 1),
    (0, 3),
    (0, 5),
    (0, 7),
    (0, 9),
    (0, 11),
    (0, 13),
    (0, 15),
    (0, 17),
    (0, 19),
    (0, 21),
    (0, 23),
    (0, 25),
    (0, 27),
    (0, 29),
)
BACK_COLOR = 0x000000 # background fill
SOLI_COLOR = 0xADAF00 # solids
HEAD_COLOR = 0x00FFFF # leading particles
TAIL_COLOR = 0x000A0A # trailing particles
TAIL_LENGTH = 10      # length in pixels
DELAY = 0.02          # smaller = faster
#----------------------------------------------------------

# use solution to define other items
VX = solution['VX']
VY = solution['VY']
MATRIX_WIDTH = len(VX[0])
MATRIX_HEIGHT = len(VX)
# meh...too lazy to list comp
SOLIDS = []
for row in range(len(VX)):
    for col, v in enumerate(VX[row]):
        if v is None:
            SOLIDS.append((col, row))

# matrix and displayio setup
matrix = Matrix(width=MATRIX_WIDTH, height=MATRIX_HEIGHT, bit_depth=6)
display = matrix.display
group = displayio.Group()
display.show(group)

bitmap = displayio.Bitmap(display.width, display.height, 4)

palette = displayio.Palette(4)
palette[0] = BACK_COLOR
palette[1] = SOLI_COLOR
palette[2] = HEAD_COLOR
palette[3] = TAIL_COLOR

tile_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
group.append(tile_grid)

# global to store streamline data
STREAMLINES = []

def compute_streamlines():
    '''Compute streamline for each starting point (seed) defined.'''
    for seed in SEEDS:
        streamline = []
        x, y = seed
        px = round(x)
        py = round(y)
        vx = VX[py][px]
        vy = VY[py][px]
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
            if 0 <= nx < MATRIX_WIDTH and 0 <= ny < MATRIX_HEIGHT:
                vx = VX[ny][nx]
                vy = VY[ny][nx]
            if vx is None or vy is None:
                break
            x += vx
            y += vy
            steps += 1
        # add streamline to global store
        STREAMLINES.append(streamline)

def show_solids():
    for s in SOLIDS:
        try:
            x, y = s
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
    show_solids()
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
