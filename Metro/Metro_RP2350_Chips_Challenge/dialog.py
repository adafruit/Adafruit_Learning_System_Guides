# SPDX-FileCopyrightText: 2025 Melissa LeBlanc-Williams
#
# SPDX-License-Identifier: MIT
from micropython import const
import displayio
import bitmaptools
from adafruit_display_text import bitmap_label
from adafruit_display_text.text_box import TextBox

BORDER_STYLE_INSET = 0
BORDER_STYLE_OUTSET = 1
BORDER_STYLE_FLAT = 2
BORDER_STYLE_LIGHT_OUTLINE = 3
BORDER_STYLE_DARK_OUTLINE = 4

def add_border(bitmap, border_color_ul, border_color_br):
    if border_color_ul is not None:
        for x in range(bitmap.width):
            bitmap[x, 0] = border_color_ul
        for y in range(bitmap.height):
            bitmap[0, y] = border_color_ul
    if border_color_br is not None:
        for x in range(bitmap.width):
            bitmap[x, bitmap.height - 1] = border_color_br
        for y in range(bitmap.height):
            bitmap[bitmap.width - 1, y] = border_color_br
    return bitmap

def convert_padding(padding):
    if isinstance(padding, int):    # Top, Right, Bottom Left (same as CSS)
        padding = {
            "top": padding // 2,
            "right": padding // 2,
            "bottom": padding // 2,
            "left": padding // 2
        }
    elif isinstance(padding, (tuple, list)) and len(padding) == 2:  # Top/Bottom, Left/Right
        padding = {
            "top": padding[0],
            "right": padding[1],
            "bottom": padding[0],
            "left": padding[1]
        }
    elif isinstance(padding, (tuple, list)) and len(padding) == 4:  # Top, Right, Bottom, Left
        padding = {
            "top": padding[0],
            "right": padding[1],
            "bottom": padding[2],
            "left": padding[3]
        }
    return padding

def text_bounding_box(text, font, line_spacing=0.75):
    temp_label = bitmap_label.Label(
        font,
        text=text,
        line_spacing=line_spacing,
        background_tight=True
    )
    return temp_label.bounding_box

class InputFields:

    ALPHANUMERIC = const(0)
    ALPHA = const(1)
    NUMERIC = const(2)

    """Class to keep track of input fields in a dialog"""
    def __init__(self):
        self._input_fields = []
        self._active_field = 0

    def add(self, label, field_type=ALPHANUMERIC, value=""):
        value_type = int if isinstance(value, int) else str
        if value in ("", 0):
            value = " "
        if value_type not in (str, int):
            raise ValueError("value_type must be str or int")
        key = label.lower().replace(" ", "_")
        focused = len(self._input_fields) == 0
        self._input_fields.append({
            "key": key,
            "label": label,
            "font": None,
            "value": str(value),
            "x": 0,
            "y": 0,
            "width": 0,
            "height": 0,
            "color_index": None,
            "bgcolor_index": None,
            "padding": 10,
            "redraw": True, # This is to keep track of whether to redraw the field or not
            "max_length": None,
            "type": field_type,
            "buffer": None,
            "focused": focused,
            "value_type": value_type,
        })

    def redraw_all(self):
        for field in self._input_fields:
            field["redraw"] = True

    def clear(self):
        self._active_field = 0
        self._input_fields = []

    def get_field(self, key):
        for field in self._input_fields:
            if field["key"] == key:
                return field
        return None

    def next_field(self):
        self._input_fields[self._active_field]["focused"] = False
        self._input_fields[self._active_field]["redraw"] = True
        self._active_field = (self._active_field + 1) % len(self._input_fields)
        self._input_fields[self._active_field]["focused"] = True
        self._input_fields[self._active_field]["redraw"] = True

    def get_value(self, key):
        field = self.get_field(key)
        if field is None:
            return None
        value = field["value"]
        if value == " ":
            return "" if field["value_type"] == str else 0
        return field["value_type"](value)

    @property
    def active_field(self):
        return self._input_fields[self._active_field]

    @property
    def active_field_value(self):
        if self.active_field["value"] == " ":
            return ""
        return self.active_field["value"]

    @active_field_value.setter
    def active_field_value(self, value):
        if value == "":
            value = " "
        self.active_field["value"] = value
        self.active_field["redraw"] = True

    @property
    def fields(self):
        return self._input_fields

class Dialog:
    def __init__(self, color_index, shader):
        self._color_index = color_index
        self.shader = shader

    def _reassign_indices(self, bitmap, foreground_color_index, background_color_index):
        # This will reassign the indices in the bitmap to match the palette
        new_bitmap = displayio.Bitmap(bitmap.width, bitmap.height, len(self.shader))
        if background_color_index is not None:
            for x in range(bitmap.width):
                for y in range(bitmap.height):
                    if bitmap[(x, y)] == 0:
                        new_bitmap[(x, y)] = background_color_index
        if foreground_color_index is not None:
            for x in range(bitmap.width):
                for y in range(bitmap.height):
                    if bitmap[(x, y)] == 1:
                        new_bitmap[(x, y)] = foreground_color_index
        return new_bitmap

    def _draw_button(self, buffer, text, font, x_position, y_position,
                     width=None, height=None, center_button=True, **kwargs):
        del kwargs["center_dialog_vertically"]
        del kwargs["center_dialog_horizontally"]
        if "padding" not in kwargs:
            kwargs["padding"] = 10
        return self.display_simple(
            text,
            font,
            width,
            height,
            x_position,
            y_position,
            buffer,
            border_dark_index=self._color_index["dark_gray"],
            background_color_index=self._color_index["light_gray"],
            center_dialog_horizontally=center_button,
            center_dialog_vertically=False,
            **kwargs)

    def _draw_background(
            self,
            x_position,
            y_position,
            width,
            height,
            buffer,
            *,
            border_style=BORDER_STYLE_OUTSET,
            background_color_index=None,
            border_light_index=None,
            border_dark_index=None,
        ):
        # Draw a background for the dialog
        # This will be a simple rectangle with a border

        if border_light_index is None:
            # The index of the light border color in the palette
            border_light_index = self._color_index["bounding_box_light"]
        if border_dark_index is None:
            # The index of the dark border color in the palette
            border_dark_index = self._color_index["bounding_box_dark"]
        if background_color_index is None:
            background_color_index = self._color_index["dialog_background"]

        if border_style == BORDER_STYLE_OUTSET:
            (border_color_ul, border_color_br) = (border_light_index, border_dark_index)
        elif border_style == BORDER_STYLE_INSET:
            border_color_ul, border_color_br = border_dark_index, border_light_index
        elif border_style == BORDER_STYLE_DARK_OUTLINE:
            border_color_ul, border_color_br = border_dark_index, border_dark_index
        elif border_style == BORDER_STYLE_LIGHT_OUTLINE:
            border_color_ul, border_color_br = border_light_index, border_light_index
        else:
            border_color_ul, border_color_br = None, None

        background_bitmap = displayio.Bitmap(width, height, len(self.shader))
        background_bitmap.fill(background_color_index)
        background_bitmap = add_border(background_bitmap, border_color_ul, border_color_br)
        bitmaptools.blit(buffer, background_bitmap, x_position, y_position)

    def display_simple(
            self,
            text,       # the text to display in the dialog
            font,       # the font to use for the dialog
            width,      # the width of the dialog
            height,     # the height of the dialog
            x_position,   # the x coordinate the dialog should be centered on in the buffer
            y_position,   # the y coordinate the dialog should be centered on in the buffer
            buffer,
            *,
            center_dialog_horizontally=False, # x position in center of the dialog
            center_dialog_vertically=False,   # y position in center of the dialog
            horizontal_text_alignment=TextBox.ALIGN_CENTER,   # The alignment of the text
            center_text_vertically=True,     # whether the text should be centered vertically
            background_color_index=None,    # the index of the background color in the palette
            font_color_index=None,          # the index of the font color in the palette
            padding=10,                     # the padding around the text
            border_light_index=None,
            border_dark_index=None,
            line_spacing=0.75,                  # Space between each line of text in pixels
            border_style=BORDER_STYLE_OUTSET,  # The style of the border
        ):
        #pylint: disable=too-many-locals, too-many-branches

        border_width = 1
        if horizontal_text_alignment is None:
            horizontal_text_alignment = TextBox.ALIGN_CENTER
        if font_color_index is None:
            font_color_index = self._color_index["default_dialog_text_color"]
        if background_color_index is None:
            background_color_index = self._color_index["dialog_background"]

        padding = convert_padding(padding)

        if text is not None:
            text_area_padding = (0, 0)
            if width is None:
                # Create a regular bitmap label with the text to get the width
                text_width = text_bounding_box(text, font, line_spacing=line_spacing)[2]
                text_area_padding = (-padding["left"], -padding["right"])
            else:
                text_width = width - padding["right"] - padding["left"] - border_width * 2
            # Colors don't matter for bitmap fonts
            text_area = TextBox(
                font,
                text_width,
                TextBox.DYNAMIC_HEIGHT,
                align=horizontal_text_alignment,
                text=text,
                background_tight=True,
                line_spacing=line_spacing,
                padding_left=text_area_padding[0],
                padding_right=text_area_padding[1],
            )

            text_bmp = self._reassign_indices(
                text_area.bitmap, font_color_index, background_color_index
            )
            if width is None:
                width = text_bmp.width + padding["right"] + padding["left"] + border_width * 2
            if height is None:
                height = text_bmp.height + padding["top"] + padding["bottom"] + border_width * 2

            text_bitmap_position = [padding["left"] + border_width, padding["top"] + border_width]
            if center_text_vertically:
                text_bitmap_position[1] = (height - text_bmp.height) // 2
        else:
            text_bmp = None
            if width is None:
                width = padding["right"] + padding["left"] + border_width * 2
            if height is None:
                height = padding["top"] + padding["bottom"] + border_width * 2

        if x_position is None:
            x_position = (buffer.width - width) // 2
        elif center_dialog_horizontally and x_position is not None:
            x_position = x_position - width // 2

        if y_position is None:
            y_position = (buffer.height - height) // 2
        elif center_dialog_vertically and y_position is not None:
            y_position = y_position - height // 2

        # Draw the background
        self._draw_background(
            x_position,
            y_position,
            width,
            height,
            border_style=border_style,
            background_color_index=background_color_index,
            border_light_index=border_light_index,
            border_dark_index=border_dark_index,
            buffer=buffer,
        )
        if text_bmp:
            bitmaptools.blit(
                buffer, text_bmp, x_position + text_bitmap_position[0],
                y_position + text_bitmap_position[1]
            )

        # return the width and height of the dialog in a tuple
        return width, height, text_bmp.height if text_bmp else 0

    def display_message(self, text, font, width, height, x_position, y_position, buffer, **kwargs):
        #pylint: disable=too-many-locals
        button_font = font
        button_text = "OK"
        if "button_font" in kwargs:
            button_font = kwargs.pop("button_font")
        if "button_text" in kwargs:
            button_text = kwargs.pop("button_text")
        padding = convert_padding(kwargs.get("padding", 5))
        control_spacing = 5
        button_height = button_font.get_bounding_box()[1] + control_spacing + padding["bottom"]

        # Draw dialog and text
        dialog_width, dialog_height, _ = self.display_simple(
            text,
            font,
            width,
            height,
            x_position,
            y_position,
            buffer,
            padding=(
                padding["top"], padding["right"],
                button_height + padding["bottom"], padding["left"]
            ),
            center_text_vertically=False,
            border_light_index=self._color_index["light_gray"],
            border_dark_index=self._color_index["black"],
            **kwargs
        )

        if x_position is None:
            if kwargs.get("center_dialog_horizontally", True):
                x_position = buffer.width // 2
            else:
                x_position = (buffer.width - dialog_width) // 2

        # Draw a button
        if y_position is None:
            y_position = (buffer.height - dialog_height) // 2
        y_position += dialog_height - button_height
        self._draw_button(buffer, button_text, button_font, x_position, y_position, **kwargs)

    def draw_field(self, field, first_draw=False):
        # Draw a singular field
        # A field should draw a label and a box to enter text
        # The label should be on the left of the coordinates
        # The box should be on the right of the coordinates
        # The width and height should be the size of the box
        # The font should be the font to use for the label and the text box
        if first_draw:
            # draw the label
            label = TextBox(
                field["font"],
                text_bounding_box(field["label"], field["font"])[2],
                TextBox.DYNAMIC_HEIGHT,
                align=TextBox.ALIGN_RIGHT,
                text=field["label"],
                background_tight=True,
                line_spacing=0.75,
                padding_left=-field["padding"]["left"],
                padding_right=-field["padding"]["right"],
            )
            label_bmp = self._reassign_indices(
                label.bitmap,
                field["color_index"],
                field["bgcolor_index"],
            )
            bitmaptools.blit(
                field["buffer"], label_bmp, field["x"] - label_bmp.width - 3, field["y"]
            )
        if field["redraw"]:
            # draw the text box
            # This will draw a border around the text box
            textbox = TextBox(
                field["font"],
                field["width"],
                TextBox.DYNAMIC_HEIGHT,
                align=TextBox.ALIGN_LEFT,
                text=field["value"],
                line_spacing=0.75,
                padding_left=field["padding"]["left"],
                padding_right=field["padding"]["right"],
                padding_top=-7,
                padding_bottom=-1,
            )
            textbox_bmp = self._reassign_indices(
                textbox.bitmap,
                field["color_index"],
                field["bgcolor_index"],
            )
            col_index = self._color_index
            if field["focused"]:
                border_color_ul, border_color_br = col_index["black"], col_index["black"]
            else:
                border_color_ul, border_color_br = col_index["light_gray"], col_index["light_gray"]
            textbox_bmp = add_border(textbox_bmp, border_color_ul, border_color_br)
            bitmaptools.blit(field["buffer"], textbox_bmp, field["x"], field["y"] - 2)
            field["redraw"] = False

    def display_input(self, text, font, fields, buttons, width,
                      height, x_position, y_position, buffer, **kwargs):
        #pylint: disable=too-many-locals
        button_font = font
        padding = 10
        if "button_font" in kwargs:
            button_font = kwargs.pop("button_font")
        padding = convert_padding(kwargs.get("padding", 10))
        control_spacing = 8
        button_height = button_font.get_bounding_box()[1] + control_spacing + padding["bottom"]

        # Calculate total field height
        field_height = text_bounding_box(fields[0]["label"], font, line_spacing=0.75)[3]
        field_area_height = (field_height + control_spacing )* len(fields)

        # Draw dialog (and text if present)
        dialog_width, dialog_height, message_height = self.display_simple(
            text,
            font,
            width,
            height,
            x_position,
            y_position,
            buffer,
            padding=(
                padding["top"], padding["right"],
                field_area_height + button_height + padding["bottom"], padding["left"]
            ),
            center_text_vertically=False,
            border_light_index=self._color_index["light_gray"],
            border_dark_index=self._color_index["black"],
            **kwargs
        )

        max_field_label_width = 0
        for field in fields:
            max_field_label_width = max(
                max_field_label_width,
                text_bounding_box(
                    field["label"], font)[2] + padding["right"] + padding["left"]
            )

        if x_position is None:
            if kwargs.get("center_dialog_horizontally", True):
                x_position = buffer.width // 2
            else:
                x_position = (buffer.width - dialog_width) // 2

        if y_position is None:
            y_position = buffer.height // 2
            if kwargs.get("center_dialog_vertically", True):
                y_position -= dialog_height // 2

        y_position += padding["top"] + message_height

        # Add field parameters and draw
        field_width = 100
        y_position += control_spacing
        field_x_position = (x_position + (
            max_field_label_width - (field_width + padding["right"] + padding["left"])
        ) // 2)
        for field in fields:
            field["font"] = font
            field["width"] = field_width
            field["height"] = field_height
            field["y"] = y_position
            field["x"] = field_x_position
            field["color_index"] = self._color_index["default_dialog_text_color"]
            field["bgcolor_index"] = self._color_index["dialog_background"]
            field["padding"] = padding
            field["max_length"] = 9
            field["buffer"] = buffer
            y_position += field_height + control_spacing
            self.draw_field(field, True)

        # Draw buttons
        # Figure out the maximum width of the buttons by checking the bounding box of their text
        total_button_width = 0
        for button_text in buttons:
            total_button_width += text_bounding_box(
                button_text, button_font)[2] + padding["right"] + padding["left"] + 2

        button_spacing = (dialog_width - total_button_width) // (len(buttons) + 1)
        if kwargs.get("center_dialog_horizontally", True):
            x_position -= dialog_width // 2
        x_position += button_spacing
        for button_text in buttons:
            # Calculate X-position so that the buttons are spaced evenly apart and within the width
            button_width, _, _ = self._draw_button(
                buffer, button_text, button_font, x_position,
                y_position, None, None, False, **kwargs
            )
            x_position += button_spacing + button_width
