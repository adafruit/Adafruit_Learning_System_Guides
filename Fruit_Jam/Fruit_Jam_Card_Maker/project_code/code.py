# SPDX-FileCopyrightText: 2025 Tim Cocks for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
Greeting card maker for Fruit Jam. Input messages for the front
and inside of the card and select a custom image for the front,
or use a snowflake image designed right inside the app.
"""
import json
import os
import sys
import time

import displayio
import storage
import supervisor
import terminalio

from adafruit_usb_host_mouse import find_and_init_boot_mouse
from adafruit_fruitjam.peripherals import request_display_config
from adafruit_templateengine import render_template
from adafruit_displayio_layout.layouts.page_layout import PageLayout
from adafruit_display_text.bitmap_label import Label
from adafruit_display_text.text_box import TextBox
from adafruit_checkbox import CheckBox
from adafruit_button import Button

from card_maker_helpers import (
    PointHighlighterCache,
    svg_points,
    fill_polygon,
    draw_snowflake,
    random_polygon,
    distance,
)

# change emoji here if you want to use different ones
emoji = "🎄⛄❄️🌟"

CLICK_COOLDOWN = 0.5  # in seconds, how long to wait before along another mouse click

last_click_time = -1  # when the last mouse click occurred

focused_input = None  # var to hold the input box that is currently focused


def update_color():
    """
    Update the color of the snowflake palette based on the
    value from the color input box
    """
    hex_color_str = snowflake_color_input.text
    try:
        hex_color_int = int(hex_color_str, 16)
    except ValueError:
        return

    palette[0] = hex_color_int


# set the display to 320x240 if it isn't already
request_display_config(320, 240)

# display and main group setup
display = supervisor.runtime.display
main_group = displayio.Group()
display.root_group = main_group

# page layout will hold different pages and allow us to switch between them
page_layout = PageLayout(0, 0)
main_group.append(page_layout)

# create a Group for the snowflake maker screen
snowflake_maker_group = displayio.Group()

# setup snowflake palette
palette = displayio.Palette(3)
palette[0] = 0x3388FF
palette[1] = 0xFFFFFF
palette[2] = 0xFF0000

# setup Bitmap to hold the top left quadrant of the snowflake.
# full snowflake is 240x240, so each quadrant is 120x120
snowflake_bmp = displayio.Bitmap(120, 120, 3)
snowflake_bmp.fill(1)

# TileGrid for the top left quadrant
top_left_tg = displayio.TileGrid(snowflake_bmp, pixel_shader=palette)
snowflake_maker_group.append(top_left_tg)

# TileGrid for the top right quadrant
top_right_tg = displayio.TileGrid(snowflake_bmp, pixel_shader=palette)
# mirror horizontally
top_right_tg.flip_x = True
# place it to the right of the top left quadrant
top_right_tg.x = top_left_tg.x + top_left_tg.tile_width
snowflake_maker_group.append(top_right_tg)

# TileGrid for the bottom left quadrant
bottom_left_tg = displayio.TileGrid(snowflake_bmp, pixel_shader=palette)
# mirror vertically
bottom_left_tg.flip_y = True
# place it below the top left quadrant
bottom_left_tg.y = top_left_tg.y + top_left_tg.tile_height
snowflake_maker_group.append(bottom_left_tg)

# TileGrid for the bottom right quadrant
bottom_right_tg = displayio.TileGrid(snowflake_bmp, pixel_shader=palette)
# mirror both horizontally and vertically
bottom_right_tg.flip_x = True
bottom_right_tg.flip_y = True
# place it below top quadrants, and to the right of bottom left quadrant
bottom_right_tg.x = top_left_tg.x + top_left_tg.tile_width
bottom_right_tg.y = top_left_tg.y + top_left_tg.tile_height
snowflake_maker_group.append(bottom_right_tg)

# setup help text for the right side of the screen
snowflake_maker_info_text = TextBox(terminalio.FONT, 80, 240)
snowflake_maker_info_text.anchor_point = (0, 0)
snowflake_maker_info_text.anchored_position = (242, 0)
snowflake_maker_info_text.text = "Click points, then click back on the first one to cut out.\n\n[del]ete all\n\n[r]andom\n\n[ctrl+z] undo \n\n[esc] back"  # pylint: disable=line-too-long
snowflake_maker_group.append(snowflake_maker_info_text)

# setup a cache for PointHighlighters, used for showing which point
# the user clicked on. The Cache allows them to be re-used.
point_highlighter_cache = PointHighlighterCache(snowflake_maker_group)

# setup mouse
mouse = find_and_init_boot_mouse()
if mouse is None:
    raise RuntimeError("No mouse found connected to USB Host")

# add the mouse TileGrid to the main group
main_group.append(mouse.tilegrid)

# list to hold the points that have been clicked
clicked_points = []

# data object that will get stored as JSON in CPSAVES
# to let the user resume where they left off
card_json_data = {"polygons": []}

# list of polygon points in string format ready to use in a SVG polygon
svg_polygons = []

# check if there is any existing card data json file
if "card_data.json" in os.listdir("/saves/"):
    print("loading card_data.json")
    # read and load the data from the existing file
    with open("/saves/card_data.json", "r") as f:
        card_json_data = json.load(f)

    # Draw each polygon from the data, and build up the list of SVG polygons
    for points in card_json_data["polygons"]:
        svg_polygons.append(svg_points(points))
        fill_polygon(snowflake_bmp, points, 0)

# Group for the card setup screen
card_setup_group = displayio.Group()

# background palette to hold white
background_palette = displayio.Palette(1)
background_palette[0] = 0xFFFFFF

# background Bitmap to put white underneath all UI elements
background_bmp = displayio.Bitmap(32, 24, 1)
background_tg = displayio.TileGrid(
    bitmap=background_bmp, pixel_shader=background_palette
)
background_group = displayio.Group(
    scale=10
)  # scale 10 to save RAM with a smaller Bitmap
background_group.append(background_tg)
card_setup_group.append(background_group)

# label above the front message input box
front_msg_lbl = Label(terminalio.FONT, text="Front Message", color=0x000000)
front_msg_lbl.anchor_point = (0, 0)
front_msg_lbl.anchored_position = (2, 2)
card_setup_group.append(front_msg_lbl)

# front message input box, for the user to type in a message for the front of the card
front_msg_input = TextBox(
    terminalio.FONT,
    120,
    14,
    text="Happy Holidays",
    color=0x000000,
    background_color=0xDDDDDD,
)
front_msg_input.anchor_point = (0, 0)
front_msg_input.anchored_position = (2, 2 + 12 + 6)

# check if there is an outside message in the saved card data
if "outside_message" in card_json_data and card_json_data["outside_message"]:
    # check if the emoji were enabled in the saved outside message by presence of <br> tag
    # set the text on the input box from the saved outside message
    if "<br>" in card_json_data["outside_message"]:
        # show the portion without the emoji in the front message input box
        front_msg_input.text = card_json_data["outside_message"].split("<br>")[1]
    else:
        # show the whole front message in the input box
        front_msg_input.text = card_json_data["outside_message"]
card_setup_group.append(front_msg_input)

# custom  Bitmap used for all CheckBoxes
checkbox_bmp = displayio.OnDiskBitmap("checkbox.bmp")
checkbox_bmp.pixel_shader.make_transparent(0)

# CheckBox to the right of front message input
# allows enable/disable of emoji on front of card
front_emoji_checkbox = CheckBox(
    terminalio.FONT, spritesheet=checkbox_bmp, text="Include Emoji", text_color=0x000000
)
front_emoji_checkbox.anchor_point = (0, 0)
front_emoji_checkbox.anchored_position = (
    front_msg_input.x + front_msg_input.width + 18,
    2,
)
# check if the saved data had emoji in it
if "outside_message" in card_json_data and "<br>" in card_json_data["outside_message"]:
    # check the box to start if saved data had emoji
    front_emoji_checkbox.checked = True
card_setup_group.append(front_emoji_checkbox)

# Label to identify the inside message box
inside_msg_lbl = Label(terminalio.FONT, text="Inside Message", color=0x000000)
inside_msg_lbl.anchor_point = (0, 0)
inside_msg_lbl.anchored_position = (2, front_msg_input.anchored_position[1] + 18)
card_setup_group.append(inside_msg_lbl)

# inside message input box, wider and taller than front message
# because it can fit more text in the inside of the card
inside_msg_input = TextBox(
    terminalio.FONT, 300, 60, text="", color=0x000000, background_color=0xDDDDDD
)
inside_msg_input.anchor_point = (0, 0)
inside_msg_input.anchored_position = (2, inside_msg_lbl.anchored_position[1] + 18)
# load the inside message from saved data if there was one
if "inside_message" in card_json_data and card_json_data["inside_message"]:
    inside_msg_input.text = card_json_data["inside_message"]
card_setup_group.append(inside_msg_input)

# Label to identify the front picture configuration controls
front_img_lbl = Label(terminalio.FONT, text="Front Picture", color=0x000000)
front_img_lbl.anchor_point = (0, 0)
front_img_lbl.anchored_position = (2, inside_msg_input.anchored_position[1] + 66)
card_setup_group.append(front_img_lbl)

# CheckBox to use the snowflake image for the front of the card
front_snowflake_checkbox = CheckBox(
    terminalio.FONT, checkbox_bmp, text="Snowflake", text_color=0x000000, checked=True
)
front_snowflake_checkbox.anchor_point = (0, 0)
front_snowflake_checkbox.anchored_position = (
    2,
    front_img_lbl.anchored_position[1] + 18,
)
# Set the checked state based on saved data
if "front_img" in card_json_data:
    front_snowflake_checkbox.checked = card_json_data["front_img"] == "snowflake.svg"
card_setup_group.append(front_snowflake_checkbox)

# Button for launching the snowflake maker screen
btn_x = (
    front_snowflake_checkbox.anchored_position[0] + front_snowflake_checkbox.width + 10
)
btn_y = front_snowflake_checkbox.anchored_position[1] - (26 // 2 - 16 // 2)
make_snowflake_btn = Button(
    x=btn_x,
    y=btn_y,
    width=96,
    height=26,
    style=Button.ROUNDRECT,
    fill_color=0xBBFFFF,
    outline_color=0x88BBBB,
    label="Make Snowflake",
    label_font=terminalio.FONT,
    label_color=0x000000,
)
card_setup_group.append(make_snowflake_btn)

# input box for hex color code. Selected color is applied to the snowflake cutouts
snowflake_color_input = TextBox(
    terminalio.FONT, 50, 14, text="0x3388ff", color=0x000000, background_color=0xDDDDDD
)
snowflake_color_input.anchor_point = (0, 0.5)
snowflake_color_input.anchored_position = (
    make_snowflake_btn.x + make_snowflake_btn.width + 10,
    front_snowflake_checkbox.anchored_position[1] + 16 // 2,
)
card_setup_group.append(snowflake_color_input)

# preview swatch for the snowflake color from the input box
snowflake_color_preview_bmp = displayio.Bitmap(14, 14, 1)
snowflake_color_preview_tg = displayio.TileGrid(
    snowflake_color_preview_bmp, pixel_shader=palette
)
snowflake_color_preview_tg.x = snowflake_color_input.x + snowflake_color_input.width + 4
snowflake_color_preview_tg.y = (
    front_snowflake_checkbox.anchored_position[1] + 16 // 2 - 14 // 2
)
card_setup_group.append(snowflake_color_preview_tg)

# CheckBox to use custom_front.svg file from CIRCUITPY
# instead of the snowflake for the front of the card
front_custom_svg_checkbox = CheckBox(
    terminalio.FONT, checkbox_bmp, text="custom_front.svg", text_color=0x000000
)
front_custom_svg_checkbox.anchor_point = (0, 0)
front_custom_svg_checkbox.anchored_position = (
    2,
    front_snowflake_checkbox.anchored_position[1] + 26,
)
# set the checked state based on saved data
if (
    "front_img" in card_json_data
    and card_json_data["front_img"] != "snowflake.svg"
    and card_json_data["front_img"].endswith(".svg")
):
    front_custom_svg_checkbox.checked = True
card_setup_group.append(front_custom_svg_checkbox)

# CheckBox to use custom_front.png file from CIRCUITPY
# instead of the snowflake for the front of the card
front_custom_png_checkbox = CheckBox(
    terminalio.FONT, checkbox_bmp, text="custom_front.png", text_color=0x000000
)
front_custom_png_checkbox.anchor_point = (0, 0)
front_custom_png_checkbox.anchored_position = (
    2,
    front_custom_svg_checkbox.anchored_position[1] + 26,
)
if "front_img" in card_json_data and card_json_data["front_img"].endswith(".bmp"):
    front_custom_svg_checkbox.checked = True
card_setup_group.append(front_custom_png_checkbox)

# Remount CPSAVES button in bottom right
btn_x = display.width - 96 - 4
btn_y = display.height - 26 - 4
remount_btn = Button(
    x=btn_x,
    y=btn_y,
    width=96,
    height=26,
    style=Button.ROUNDRECT,
    fill_color=0xD5A0E2,
    outline_color=0x861EBC,
    label="Remount CPSAVES",
    label_font=terminalio.FONT,
    label_color=0x000000,
)
card_setup_group.append(remount_btn)

# Generate Card button above remount button.
btn_x = display.width - 96 - 4
btn_y = remount_btn.y - 26 - 4
generate_card_btn = Button(
    x=btn_x,
    y=btn_y,
    width=96,
    height=26,
    style=Button.ROUNDRECT,
    fill_color=0xD5A0E2,
    outline_color=0x861EBC,
    label="Generate Card",
    label_font=terminalio.FONT,
    label_color=0x000000,
)
card_setup_group.append(generate_card_btn)

# Label to show status to the user when they click generate or remount
status_lbl = Label(terminalio.FONT, text="", color=0x000000)
status_lbl.anchor_point = (1.0, 1.0)
status_lbl.anchored_position = (display.width - 4, generate_card_btn.y - 6)
card_setup_group.append(status_lbl)

# add the Groups for card_setup and snowflake_maker screens to the page_layout
page_layout.add_content(card_setup_group, page_name="card_setup")
page_layout.add_content(snowflake_maker_group, page_name="snowflake_maker")
# show the card setup screen to start
page_layout.show_page("card_setup")

while True:
    # update mouse
    pressed_btns = mouse.update()

    # store current timestamp to check for cooldown
    now = time.monotonic()

    # check if any keyboard events have happened
    kbd_event_available = supervisor.runtime.serial_bytes_available

    # on the snowflake maker screen restrict the mouse to top left quadrant
    if page_layout.showing_page_name == "snowflake_maker":
        mouse.x = min(mouse.x, top_left_tg.x + top_left_tg.tile_width - 1)
        mouse.y = min(mouse.y, top_left_tg.y + top_left_tg.tile_height)

    # if there are keyboard events
    if kbd_event_available:
        # read data from the keyboard input
        inc_kbd_data = sys.stdin.read(kbd_event_available)

        # convert to bytes for when we need to test for non ASCII things
        kbd_event_bytes = inc_kbd_data.encode("utf-8")

        # if user is on the card_setup screen
        if page_layout.showing_page_name == "card_setup":
            # if an input box has focus
            if focused_input is not None:
                # if there is a single key press, and it's in the
                # basic visible ASCII chars range
                if len(inc_kbd_data) == 1 and " " <= inc_kbd_data <= "~":
                    # add the entered character to the focused input box
                    focused_input.text += inc_kbd_data
                    # if the color input box is the focused one, update the snowflake color
                    if focused_input == snowflake_color_input:
                        update_color()

                # if enter was pressed
                elif inc_kbd_data == "\n":
                    # if the color input box is the focused one, update the snowflake color
                    if focused_input == snowflake_color_input:
                        update_color()

                    # set the background color of the input box back to normal
                    focused_input.background_color = 0xDDDDDD
                    # clear out the focused input var
                    focused_input = None

                # if there are multiple keys in the data
                elif len(inc_kbd_data) > 1:
                    # loop over all characters
                    for c in inc_kbd_data:
                        # if current character is in the basic visible ASCII chars range
                        if " " <= c <= "~":
                            # add it to the focused input
                            focused_input.text += c

                # if backspace was pressed
                elif kbd_event_bytes == b"\x08":
                    # remove the last character from the input box
                    focused_input.text = focused_input.text[:-1]

                # unhandled key event
                else:
                    # just print the bytes for easy debugging
                    print(kbd_event_bytes)

            # no input is focused currently
            else:
                # just print the bytes for easy debugging
                print(kbd_event_bytes)

        # if user is on the snowflake maker screen
        if page_layout.showing_page_name == "snowflake_maker":
            # if esc key was pressed
            if kbd_event_bytes == b"\x1b":
                # go back to the card setup screen
                page_layout.show_page("card_setup")

            # if the delete key was pressed
            elif kbd_event_bytes == b"\x1b[3~":
                # clear the lists of polygons
                svg_polygons.clear()
                card_json_data["polygons"].clear()
                # fill the snowflake bitmap with white
                snowflake_bmp.fill(1)

            # if ctrl-z was pressed
            elif kbd_event_bytes == b"\x1a":
                # remove the last polygon from the lists
                svg_polygons.pop()
                removed_polygon = card_json_data["polygons"].pop()

                # blank the snowflake Bitmap to white
                snowflake_bmp.fill(1)

                # re-draw the snowflake sans removed polygon
                draw_snowflake(snowflake_bmp, card_json_data["polygons"], 0)

            # if r key was pressed
            elif inc_kbd_data == "r":
                # generate random points for a polygon
                random_points = random_polygon()

                # add the polygon to both lists
                svg_polygons.append(svg_points(random_points))
                card_json_data["polygons"].append(list(random_points))

                # draw the new polygon in the snowflake Bitmap
                fill_polygon(snowflake_bmp, random_points, 0)

    # -- END Keyboard Handling --

    # if any mouse buttons were pressed
    if pressed_btns:
        # if user is on the snowflake maker screen
        if page_layout.showing_page_name == "snowflake_maker":
            # if left button was pressed, and it's not within the cooldown time
            if "left" in pressed_btns and now >= last_click_time + CLICK_COOLDOWN:
                # update the last clicked timestamp
                last_click_time = now

                # var for the point that was clicked
                cur_clicked_point = (mouse.x, mouse.y)

                # if it's the first point in a polygon
                if len(clicked_points) == 0:
                    # add it to the list of clicked points
                    clicked_points.append(cur_clicked_point)

                    # put a point highlighter at the clicked location
                    highlighter = point_highlighter_cache.get_highlighter(
                        cur_clicked_point
                    )

                    # set the color to green to signify it's the first point
                    highlighter[0] = 1

                    # skip the rest of the mouse handling, goto next iteration of main loop
                    continue

                # if user clicked on or very near the first point again
                if distance(cur_clicked_point, clicked_points[0]) < 10:
                    # add the new polygon to the lists
                    svg_polygons.append(svg_points(clicked_points))
                    card_json_data["polygons"].append(list(clicked_points))

                    # draw the new polygon on the snowflake Bitmap
                    fill_polygon(snowflake_bmp, clicked_points, 0)

                    # clear the list of clicked points
                    clicked_points.clear()

                    # release all point highlighters back to the pool to be re-used
                    point_highlighter_cache.release_all()

                # the clicked point is not on or near the first point
                else:
                    # add the new point to the list of clicked points
                    clicked_points.append(cur_clicked_point)

                    # put a point highlighter on the clicked point
                    highlighter = point_highlighter_cache.get_highlighter(
                        cur_clicked_point
                    )
                    # set the highlighter color to black to signify it is not the first point
                    highlighter[0] = 0

        # if user is on the card setup screen
        elif page_layout.showing_page_name == "card_setup":
            # if left mouse button was pressed and it's not within the cooldown time
            if "left" in pressed_btns and now >= last_click_time + CLICK_COOLDOWN:
                # check if the front message input box was clicked
                front_input_x1, front_input_y1 = front_msg_input.anchored_position
                front_input_x2 = front_input_x1 + front_msg_input.tilegrid.tile_width
                front_input_y2 = front_input_y1 + front_msg_input.tilegrid.tile_height
                if (
                    front_input_x1 <= mouse.x <= front_input_x2
                    and front_input_y1 <= mouse.y <= front_input_y2
                ):
                    # update the background colors and focused input var
                    front_msg_input.background_color = 0xFFDDFF
                    inside_msg_input.background_color = 0xDDDDDD
                    snowflake_color_input.background_color = 0xDDDDDD
                    focused_input = front_msg_input

                # check if the inside message input box was clicked
                inside_input_x1, inside_input_y1 = inside_msg_input.anchored_position
                inside_input_x2 = inside_input_x1 + inside_msg_input.width
                inside_input_y2 = inside_input_y1 + inside_msg_input.height
                if (
                    inside_input_x1 <= mouse.x <= inside_input_x2
                    and inside_input_y1 <= mouse.y <= inside_input_y2
                ):
                    # update the background colors and focused input var
                    inside_msg_input.background_color = 0xFFDDFF
                    front_msg_input.background_color = 0xDDDDDD
                    snowflake_color_input.background_color = 0xDDDDDD
                    focused_input = inside_msg_input

                # check if the color input box was clicked
                color_input_x1, color_input_y1 = snowflake_color_input.anchored_position
                color_input_y1 -= 14 // 2  # account for y anchor point 0.5
                color_input_x2 = color_input_x1 + snowflake_color_input.width
                color_input_y2 = color_input_y1 + snowflake_color_input.height
                if (
                    color_input_x1 <= mouse.x <= color_input_x2
                    and color_input_y1 <= mouse.y <= color_input_y2
                ):
                    # update the background colors and focused input var
                    snowflake_color_input.background_color = 0xFFDDFF
                    inside_msg_input.background_color = 0xDDDDDD
                    front_msg_input.background_color = 0xDDDDDD
                    focused_input = snowflake_color_input

                # if the front emoji CheckBox was clicked
                if front_emoji_checkbox.contains((mouse.x, mouse.y)):
                    # toggle its checked state
                    front_emoji_checkbox.checked = not front_emoji_checkbox.checked

                # if the front snowflake image CheckBox was clicked
                if front_snowflake_checkbox.contains((mouse.x, mouse.y)):
                    # toggle its checked state
                    front_snowflake_checkbox.checked = (
                        not front_snowflake_checkbox.checked
                    )
                    # uncheck the other front image CheckBoxes
                    if front_snowflake_checkbox.checked:
                        front_custom_svg_checkbox.checked = False
                        front_custom_png_checkbox.checked = False

                # if the custom SVG front image CheckBox was clicked
                if front_custom_svg_checkbox.contains((mouse.x, mouse.y)):
                    # toggle its checked state
                    front_custom_svg_checkbox.checked = (
                        not front_custom_svg_checkbox.checked
                    )
                    # uncheck the other front image CheckBoxes
                    if front_custom_svg_checkbox.checked:
                        front_snowflake_checkbox.checked = False
                        front_custom_png_checkbox.checked = False

                # if the custom PNG front image CheckBox was clicked
                if front_custom_png_checkbox.contains((mouse.x, mouse.y)):
                    # toggle its checked state
                    front_custom_png_checkbox.checked = (
                        not front_custom_png_checkbox.checked
                    )
                    # uncheck the other front image CheckBoxes
                    if front_custom_png_checkbox.checked:
                        front_snowflake_checkbox.checked = False
                        front_custom_svg_checkbox.checked = False

                # if the make snowflake button was clicked
                if make_snowflake_btn.contains((mouse.x, mouse.y)):
                    # show the snowflake maker screen
                    page_layout.show_page("snowflake_maker")

                front_img = ""  # var to hold the name of the front image file

                # if the generate card button was clicked
                if generate_card_btn.contains((mouse.x, mouse.y)):
                    # if no front image CheckBoxes are checked
                    if (
                        not front_snowflake_checkbox.checked
                        and not front_custom_png_checkbox.checked
                        and not front_custom_svg_checkbox.checked
                    ):

                        # show an error to the user and skip to the next main loop iteration
                        status_lbl.text = "Must select front image"
                        continue

                    # if the snowflake front image CheckBox is checked
                    if front_snowflake_checkbox.checked:
                        # if there is no saved snowflake, and the polygons list is empty
                        if (
                            "snowflake.svg" not in os.listdir("/saves/")
                            and len(svg_polygons) == 0
                        ):
                            # show an error that there is no snowflake and
                            # skip to next main loop iteration
                            status_lbl.text = "No snowflake image"
                            continue

                        # if there are at least one polygons
                        if len(svg_polygons) > 0:
                            # render snowflake SVG template to string
                            status_lbl.text = "Saving Snowflake"
                            out_svg = render_template(
                                "snowflake.template.svg",
                                context={
                                    "polygons": svg_polygons,
                                    "color": hex(palette[0])[2:],
                                },
                            )

                            # save snowflake SVG file in CPSAVES
                            with open("/saves/snowflake.svg", "w") as f:
                                f.write(out_svg)

                        # set the front image var to the snowflake SVG filename
                        front_img = "snowflake.svg"

                    # if the custom SVG front image CheckBox is checked
                    elif front_custom_svg_checkbox.checked:
                        status_lbl.text = "Saving Custom SVG"
                        # copy custom_front.svg from CIRCUITPY to CPSAVES
                        with open("custom_front.svg", "r") as fin:
                            with open("/saves/custom_front.svg", "w") as fout:
                                fout.write(fin.read())
                        # set the front image var to custom SVG file
                        front_img = "custom_front.svg"

                    # if the custom PNG front image CheckBox is checked
                    elif front_custom_png_checkbox.checked:
                        status_lbl.text = "Saving Custom PNG"
                        # copy custom_front.png from CIRCUITPY to CPSAVES
                        with open("custom_front.png", "rb") as fin:
                            with open("/saves/custom_front.png", "wb") as fout:
                                fout.write(fin.read())
                        # set the front image var to custom PNG file
                        front_img = "custom_front.png"

                    status_lbl.text = "Saving Card"

                    # if the front emoji CheckBox is checked
                    if front_emoji_checkbox.checked:
                        # include emoji in the front message text
                        outside_message = f"{emoji}<br>{front_msg_input.text}"
                    else:
                        # only use the front message from the input box
                        outside_message = f"{front_msg_input.text}"

                    # render the card HTML template to a string
                    out_html = render_template(
                        "card.template.html",
                        context={
                            "outside_message": outside_message,
                            "inside_message": inside_msg_input.text,
                            "color": hex(palette[0]),
                            "timestamp": int(time.monotonic()),
                            "front_img": front_img,
                        },
                    )

                    # save the card HTML file to CPSAVES
                    with open("/saves/card.html", "w") as f:
                        f.write(out_html)

                    # store the card configuration in an object to save
                    card_json_data["outside_message"] = outside_message
                    card_json_data["inside_message"] = inside_msg_input.text
                    card_json_data["color"] = hex(palette[0])
                    card_json_data["front_img"] = front_img

                    # save the card configuration object in a JSON file to CPSAVES
                    with open("/saves/card_data.json", "w") as f:
                        print(f"saving json: {card_json_data}")
                        f.write(json.dumps(card_json_data))

                    status_lbl.text = "Card Saved"

                # if the remount CPSAVES button was clicked
                if remount_btn.contains((mouse.x, mouse.y)):
                    status_lbl.text = "Remounting CPSAVES"
                    # remount the CPSAVES drive partition
                    storage.remount("/saves", readonly=False)
                    status_lbl.text = "Done"
