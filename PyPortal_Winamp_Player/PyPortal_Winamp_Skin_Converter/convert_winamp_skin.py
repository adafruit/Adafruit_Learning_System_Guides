# SPDX-FileCopyrightText: 2022 Tim C, written for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
"""
PyPortal winamp skin converter.
"""
from PIL import Image, ImageDraw
import sys
import json

# get input filename from terminal args
if len(sys.argv) >= 2:
    input_filename = sys.argv[1]
else:
    input_filename = "base.png"

# Opens a image in RGB mode
im = Image.open(input_filename)

newsize = (240, 320)

find_text_color_dict = {}

# scan pixels to get color counts
for i in range(8):
    if im.getpixel((113, 26 + i)) in find_text_color_dict.keys():
        find_text_color_dict[im.getpixel((113, 26 + i))] += 1
    else:
        find_text_color_dict[im.getpixel((113, 26 + i))] = 1
# print(find_text_color_dict)
lowest_pixel_count = None
text_color = None
highest_pixel_count = None

# scan pixel for backdrop color
back_drop_color = im.getpixel((120, 29))
for color in find_text_color_dict.keys():
    if not highest_pixel_count:
        highest_pixel_count = find_text_color_dict[color]
        text_color = color
    elif highest_pixel_count < find_text_color_dict[color]:
        highest_pixel_count = find_text_color_dict[color]
        text_color = color

#print("backdrop: {}".format(back_drop_color))
time_color = text_color
config_data = {
    "text_color": text_color,
    "time_color": time_color
}

find_text_color_dict = {}
for i in range(21):
    if im.getpixel((65, 23 + i)) in find_text_color_dict.keys():
        find_text_color_dict[im.getpixel((65, 23 + i))] += 1
    else:
        find_text_color_dict[im.getpixel((65, 23 + i))] = 1

# rectangle cutout for for current track title
cur_song_shape = ((112, 25), (265, 34))
img_draw = ImageDraw.Draw(im)
img_draw.rectangle(cur_song_shape, fill=back_drop_color)

# rectangle cutouts for clock display
time_shape_size = (9, 13)
time_shape_x_locs = (48, 60, 78, 90)

for x_loc in time_shape_x_locs:
    _cur_time_shape_loc = (x_loc, 26)
    _cur_time_shape = (
        _cur_time_shape_loc, (_cur_time_shape_loc[0] + time_shape_size[0], _cur_time_shape_loc[1] + time_shape_size[1]))
    img_draw.rectangle(_cur_time_shape, fill=back_drop_color)

# rectangle cutout for playlist display
playlist_shape_size = (244, 48)
playlist_shape_loc = (12, 257)
playlist_shape = (
    playlist_shape_loc,
    (playlist_shape_loc[0] + playlist_shape_size[0], playlist_shape_loc[1] + playlist_shape_size[1]))

img_draw.rectangle(playlist_shape, fill=back_drop_color)

# write config json file
f = open(input_filename.replace(".png", "_config.json"), "w")
f.write(json.dumps(config_data))
f.close()

# resize to fit pyportal
im = im.resize(newsize)

# convert to indexed color
im = im.convert(mode="P", palette=Image.WEB)
# save output BMP file
im.save(input_filename.replace(".png", "_240x320.bmp"))
