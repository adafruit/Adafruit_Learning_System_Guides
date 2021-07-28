import time
import board
import displayio
from adafruit_matrixportal.matrixportal import MatrixPortal
from adafruit_matrixportal.matrix import Matrix
import adafruit_imageload

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

print("Party Parrot Twitter Matrix")

#  import your bearer token
bear = secrets['bearer_token']

#  query URL for tweets. looking for hashtag partyparrot sent to a specific username
DATA_SOURCE = 'https://api.twitter.com/2/tweets/search/recent?query=#partyparrot to:blitzcitydiy'
#  json data path to get most recent tweet's ID number
DATA_LOCATION = ["meta", "newest_id"]

#  create MatrixPortal object to grab data/connect to internet
matrixportal = MatrixPortal(
    url=DATA_SOURCE,
    json_path=DATA_LOCATION,
    status_neopixel=board.NEOPIXEL
)

#  create matrix display
matrix = Matrix(width=32, height=32)
display = matrix.display

group = displayio.Group()

#  load in party parrot bitmap
parrot_bit, parrot_pal = adafruit_imageload.load("/partyParrotsTweet.bmp",
                                                 bitmap=displayio.Bitmap,
                                                 palette=displayio.Palette)

parrot_grid = displayio.TileGrid(parrot_bit, pixel_shader=parrot_pal,
                                 width=1, height=1,
                                 tile_height=32, tile_width=32,
                                 default_tile=10,
                                 x=0, y=0)

group.append(parrot_grid)

display.show(group)

#  add bearer token as a header to request
matrixportal.set_headers({'Authorization': 'Bearer ' + bear})

last_value = 0 #  checks last tweet's ID
check = 0 #  time.monotonic() holder
parrot = False #  state to track if an animation is currently running
party = 0 #  time.monotonic() holder
p = 0 #  index for tilegrid
party_count = 0 #  count for animation cycles

while True:
    #  every 30 seconds...
    if (check + 30) < time.monotonic():
        #  store most recent tweet's ID number in value
        value = matrixportal.fetch()
        print("Response is", value)
        #  reset time count
        check = time.monotonic()
        #  compare last tweet ID and current tweet ID
        if last_value != value:
            print("new party!")
            #  if it's new, then it's a party!
            last_value = value
            parrot = True
        else:
            #  if it's not new, then the wait continues
            print("no new party... :(")
    #  when a new tweet comes in...
    if parrot:
        #  every 0.1 seconds...
        if (party + 0.1) < time.monotonic():
            #  the party parrot animation cycles
            parrot_grid[0] = p
            #  p is the tilegrid index location
            p += 1
            party = time.monotonic()
            #  if an animation cycle ends
            if p > 9:
                #  index is reset
                p = 0
                #  animation cycle count is updated
                party_count += 1
                print("party parrot", party_count)
            #  after 16 animations cycles...
            if party_count > 15:
                #  reset states
                parrot = False
                party_count = 0
                p = 0
                #  clear the matrix so that it's blank
                parrot_grid[0] = 10
                print("the party is over")
