import random
import sys
import terminalio
from displayio import Group, TileGrid, Bitmap, release_displays, Palette
import supervisor
import bitmaptools
from adafruit_display_text.bitmap_label import Label
import picodvi
import framebufferio
import board
from micropython import const
import adafruit_imageload

# how strong the gravity is
FALL_SPEED = 1

# how powerful the jump is
JUMP_SPEED = 5

# maximum gravity speed
TERMINAL_VELOCITY = 7

# make "close calls" more likely by fudging the collision check
# in favor of the player a bit
COLLIDE_FUDGE_FACTOR = 8

# how many scaled pixels wide the trail will be
TRAIL_LENGTH = 20

# current score
score = 0

# initialize display
release_displays()

fb = picodvi.Framebuffer(
    320,
    240,
    clk_dp=board.CKP,
    clk_dn=board.CKN,
    red_dp=board.D0P,
    red_dn=board.D0N,
    green_dp=board.D1P,
    green_dn=board.D1N,
    blue_dp=board.D2P,
    blue_dn=board.D2N,
    color_depth=16,
)
display = framebufferio.FramebufferDisplay(fb)

# initialize groups to hold visual elements
main_group = Group()

# any elements in this Group will be scaled up 2x
scaled_group = Group(scale=2)
main_group.append(scaled_group)


class Post(Group):
    # gap location constants
    GAP_TOP = const(0)
    GAP_MID = const(1)
    GAP_BOTTOM = const(2)

    def __init__(self, spritesheet, gap_location=GAP_MID):
        """
        A pair of scratching posts, aligned vertically. This class
        holds the visual elements, and provides collision checking.

        :param Union[Bitmap,OnDiskBitmap] spritesheet: The Bitmap containing the post sprite sheet.
        :param gap_location: Where the gap should be. Must be one of GAP_TOP, GAP_MID, GAP_BOTTOM.
        """
        super().__init__()
        # start out not visible
        self.hidden = True

        # hold a reference to the spritesheet Bitmap
        self.sprites = spritesheet

        # check which gap location was specified and
        # set the post heights accordingly
        if gap_location == Post.GAP_MID:
            top_height = 4
            bottom_height = 4
        elif gap_location == Post.GAP_BOTTOM:
            top_height = 7
            bottom_height = 1
        elif gap_location == Post.GAP_TOP:
            top_height = 1
            bottom_height = 7
        else:
            raise ValueError("Invalid gap_location")

        # initialize top post TileGrid
        self.top_post = TileGrid(
            post_sprites,
            pixel_shader=post_sprites_pixel_shader,
            height=top_height,
            width=1,
            tile_width=16,
            tile_height=16,
            default_tile=3,
        )

        # set the tiles for the top post.
        # Normal double ended post tiles with
        # the bottom cap tile below them.
        for i in range(top_height):
            if i == top_height - 1:
                self.top_post[0, i] = 2
            else:
                self.top_post[0, i] = 1

        # initialize bottom post TileGrid
        self.bottom_post = TileGrid(
            post_sprites,
            pixel_shader=post_sprites_pixel_shader,
            height=bottom_height,
            width=1,
            tile_width=16,
            tile_height=16,
            default_tile=3,
        )

        # set the tiles for the bottom post.
        # Normal double ended post tiles
        # with the top cap tile above them
        for i in range(bottom_height):
            if i == 0:
                self.bottom_post[0, i] = 0
            else:
                self.bottom_post[0, i] = 1

        # move the bottom post to the bottom of the display
        self.bottom_post.y = 240 - bottom_height * 16

        # append both post TileGrids to super class Group instance
        self.append(self.top_post)
        self.append(self.bottom_post)

    def check_collision(self, sprite):
        """
        Check if either of our top or bottom posts are colliding with the given sprite
        :param sprite: The sprite to check collision against.
        :return: True if sprite is colliding with a post, false otherwise.
        """
        # if the sprite is horizontally aligned with the posts
        if (
            (sprite.x * 2) - self.top_post.tile_width
            <= self.x
            <= (sprite.x * 2) + (sprite.tile_width * 2)
        ):

            # if the sprite is within the vertical range for either top or bottom post
            if (
                sprite.y * 2
            ) + COLLIDE_FUDGE_FACTOR <= self.top_post.tile_height * self.top_post.height or (
                sprite.y * 2
            ) - COLLIDE_FUDGE_FACTOR >= self.bottom_post.y - (
                sprite.tile_height * 2
            ):
                return True

        return False  # no collision


class PostPool:
    def __init__(self):
        """
        A pool of Post objects to pull from and recycle back into.
        """

        # list to store the Posts in
        self.pool = []

        # start with 2 of each gap location
        self.pool.append(Post(post_sprites, Post.GAP_MID))
        self.pool.append(Post(post_sprites, Post.GAP_MID))
        self.pool.append(Post(post_sprites, Post.GAP_BOTTOM))
        self.pool.append(Post(post_sprites, Post.GAP_BOTTOM))
        self.pool.append(Post(post_sprites, Post.GAP_TOP))
        self.pool.append(Post(post_sprites, Post.GAP_TOP))

    def get_post(self, index=None):
        """
        Get an available Post from the pool.

        :param index: The index of the post to return.
            Default is None, which means random.

        :return: An available Post object.
        """
        # if index is none, generate a random index
        if index is None:
            rnd_idx = random.randint(0, len(self.pool) - 1)

        else:  # index not None
            # use the provided index.
            rnd_idx = index

        # select a Post and remove it from the pool
        next_post = self.pool.pop(rnd_idx)

        # make the post visible
        next_post.hidden = False

        # return the post
        return next_post

    def recycle_post(self, post):
        """
        Recycle a Post back into the pool

        :param Post post: The post to recycle.

        :return: None
        """
        # set the post to not visible
        post.hidden = True

        # add the post to the pool
        self.pool.append(post)


# palette of colors for the trail
trail_palette = Palette(10)
# rainbow colors
trail_palette[0] = 0x000000
trail_palette[1] = 0xE71C1F
trail_palette[2] = 0xF39816
trail_palette[3] = 0xF1E610
trail_palette[4] = 0x6DB52F
trail_palette[5] = 0x428CCB
trail_palette[6] = 0x4B4C9C

# trans flag colors
trail_palette[7] = 0xF5ABB9
trail_palette[8] = 0x5BCFFA
trail_palette[9] = 0xFFFFFF

# setup color index 0 for transparency
trail_palette.make_transparent(0)

# Bitmap that holds 1 pixel width of the trail
trail_bmp = Bitmap(1, 6, 7)

# initialize the Bitmap pixels to the rainbow colors
trail_bmp[0, 0] = 1
trail_bmp[0, 1] = 2
trail_bmp[0, 2] = 3
trail_bmp[0, 3] = 4
trail_bmp[0, 4] = 5
trail_bmp[0, 5] = 6

# Bitmap for the background, 1/10 of 160x120 which is the
# of the display area accounting for the 2x from the scaled_group
bg_bmp = Bitmap(16, 12, 1)

# palette for the background
bg_palette = Palette(1)
bg_palette[0] = 0x00014F  # dark blue
bg_tilegrid = TileGrid(bg_bmp, pixel_shader=bg_palette)

# Group for the background scaled to 10x
bg_group = Group(scale=10)

# add the background to it's group and add that to the scaled_group
bg_group.append(bg_tilegrid)
scaled_group.append(bg_group)

# load the sprite sheet for the posts
post_sprites, post_sprites_pixel_shader = adafruit_imageload.load(
    "scratch_post_sprites.bmp"
)

# set up color index 0 for transparency
post_sprites_pixel_shader.make_transparent(0)

# initialize a PostPool() which will start with 2 posts
# of each gap location
post_pool = PostPool()

# add all posts to the main_group. Note, not the scaled_group.
# posts are displayed at 1x size.
for _post in post_pool.pool:
    main_group.append(_post)

# get the first_post out of the pool
first_post = post_pool.get_post()

# move it to the right edge
first_post.x = 320 - 16

# second post starts near the cat, so we want it to be
# middle gap to start with always. middle gap starts in index 0.
second_post = post_pool.get_post(0)

# move it to the center
second_post.x = 160

# Group with an additional 2x scaling to hold the rainbow trail
canvas_group = Group(scale=2)

# Bitmap for the trail canvas 1/4 display size for 2x from scaled_group
# and 2x from canvas_group
trail_canvas_bmp = Bitmap(display.width // 4, display.height // 4, 10)

# TileGrid for the trail canvas
trail_canvas_tg = TileGrid(trail_canvas_bmp, pixel_shader=trail_palette)

# add the canvas tilegrid to it's group, and add that to the scaled_group
canvas_group.append(trail_canvas_tg)
scaled_group.append(canvas_group)

# load nyan cat Bitmap
nyan_bmp, nyan_bmp_pixel_shader = adafruit_imageload.load("nyancat_16x12.bmp")
# set color index 0 transparent
nyan_bmp_pixel_shader.make_transparent(0)
# TileGrid for cat
nyan_tg = TileGrid(bitmap=nyan_bmp, pixel_shader=nyan_bmp_pixel_shader)
# add cat to scaled_group
scaled_group.append(nyan_tg)

# move cat near the center
nyan_tg.x = 80
nyan_tg.y = 50

# text label for the current score
score_lbl = Label(terminalio.FONT, text="0", color=0xFFFFFF, scale=2)
# move it to the bottom left corner
score_lbl.anchor_point = (0, 1)
score_lbl.anchored_position = (2, display.height - 2)

# add it to the main_group
main_group.append(score_lbl)

# set the main_group to show on the display
display.root_group = main_group

# disable auto_refresh
display.auto_refresh = False

# list to store coordinates of each horizontal pixel of the trail
trail_coords = []

# cat_speed variable holds pixels per tick to move downward for gravity
cat_speed = FALL_SPEED

# print(f"memfree: {gc.mem_free()}")


def swap_trail():
    """
    Swap the trail graphic between rainbow and trans flag colored.
    """
    # if the top pixel is red
    if trail_bmp[0, 0] == 1:
        # change to the trans flag colors
        trail_bmp[0, 0] = 0
        trail_bmp[0, 1] = 8
        trail_bmp[0, 2] = 7
        trail_bmp[0, 3] = 9
        trail_bmp[0, 4] = 7
        trail_bmp[0, 5] = 8
    else:
        # change to rainbow colors
        trail_bmp[0, 0] = 1
        trail_bmp[0, 1] = 2
        trail_bmp[0, 2] = 3
        trail_bmp[0, 3] = 4
        trail_bmp[0, 4] = 5
        trail_bmp[0, 5] = 6


def draw_trail():
    """
    draw the trail in its current location
    """
    # loop over the coordinates of the horizontal pixels
    for coord in trail_coords:
        # blit a copy of the trail Bitmap into the canvas
        # Bitmap at the current coordinate
        bitmaptools.blit(trail_canvas_bmp, trail_bmp, coord[0], coord[1])


def erase_trail():
    """
    Erase the trail in its current location
    """
    # loop over the coordinates of the horizontal pixels
    for coord in trail_coords:
        # fill a region the size of trail Bitmap with color_index 0
        # to make it transprent
        bitmaptools.fill_region(
            trail_canvas_bmp, coord[0], coord[1], coord[0] + 1, coord[1] + 6, 0
        )


def shift_trail():
    """
    shift the coordinates of the trail to the left one pixel
    """
    # loop over indexes within the trail coordinates list
    for _ in range(len(trail_coords)):
        # update the x value of the current coordinate by -1
        trail_coords[_][0] -= 1


def shift_post(post):
    """
    shift the coordinates of a post to the left
    :param Post post: The Post to shift
    :return: The shifted Post instance, or the new Post if the old one
        went off the left edge
    """
    # global score variable so we can update it
    global score  # pylint: disable=global-statement

    # if the post is at the left edge
    if post.x <= 0:
        # add bonus points for each post that makes it to the left edge
        score += 10

        # recycle the Post object back into the pool
        post_pool.recycle_post(post)

        # get another Post out of the pool
        new_post = post_pool.get_post()

        # move it to the right edge
        new_post.x = 320 - 16

        # return the new post
        return new_post

    else:  # post is not at the left edge
        # move it left, getting faster for every 100 score points
        # maxing out at 8 pixels per shift
        post.x -= min((3 + score // 100), 8)

        # return the shifted post
        return post


# initial display refresh
display.refresh(target_frames_per_second=30)
print("Press space to jump")

# boolean to have the game paused to start and wait for the player to begin
playing = False

while True:

    # if the player hasn't started yet
    if not playing:
        while True:
            # check if any keys were pressed
            available = supervisor.runtime.serial_bytes_available

            # if one or more keys was pressed
            if available:
                # read the value
                cur_btn_val = sys.stdin.read(available)
            else:
                cur_btn_val = None

            # if spacebar was pressed
            if cur_btn_val == " ":
                # do the first jump
                cat_speed = -JUMP_SPEED

                # set playing to true and breakout of the pause loop
                playing = True
                break

    # check if the cat is touching the first post
    if first_post.check_collision(nyan_tg):
        raise KeyboardInterrupt(
            f"Kitty got distracted by the scratchers post. Score: {score}"
        )

    # check if the cat is touching the second post
    if second_post.check_collision(nyan_tg):
        raise KeyboardInterrupt(
            f"Kitty got distracted by the scratchers post. Score: {score}"
        )

    # check if any keyboard data is available
    available = supervisor.runtime.serial_bytes_available
    if available:
        # read the data if there is some available
        cur_btn_val = sys.stdin.read(available)
    else:
        cur_btn_val = None

    # apply gravity to the cat, maxing out at terminal velocity
    cat_speed = min(cat_speed + FALL_SPEED, TERMINAL_VELOCITY)

    # if there is keyboard data and spacebar was pressed
    if cur_btn_val is not None and " " in cur_btn_val:
        cat_speed = -JUMP_SPEED

        # award a point for each jump
        score += 1
    elif cur_btn_val is not None and "s" in cur_btn_val:
        swap_trail()
        # award a point for swapping the trail
        score += 1

    # move the cat down by cat_speed amount of pixels
    nyan_tg.y += cat_speed

    # if the cat has touched the top or bottom edge
    if nyan_tg.y > display.height // 2 or nyan_tg.y < 0:
        raise KeyboardInterrupt(f"Kitty wandered away. Score: {score}")

    # current coordinates of the cat
    draw_coords = [nyan_tg.x // 2, nyan_tg.y // 2]

    # erase the trail
    erase_trail()

    # shift the trail coordinates over
    shift_trail()

    # add new coordinates to the trail at the cats current location
    trail_coords.append(draw_coords)

    # if the trail is at its maximum length
    if len(trail_coords) > TRAIL_LENGTH:
        # remove the oldest coordinate from the trail coordinates list.
        trail_coords.pop(0)

    # draw the trail
    draw_trail()

    # shift the posts over
    first_post = shift_post(first_post)
    second_post = shift_post(second_post)

    # update the score label
    score_lbl.text = str(score)

    # refresh the display
    display.refresh(target_frames_per_second=30)
