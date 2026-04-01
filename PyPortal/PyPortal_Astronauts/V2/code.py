# SPDX-FileCopyrightText: 2019 Limor Fried for Adafruit Industries
# SPDX-FileCopyrightText: 2026 Anne Barela for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
This example will access the Space Devs astronaut API, display the number of
humans currently in space and their names and agency on a PyPortal screen.
"""
import time
import board
import gc
import json
import supervisor
from adafruit_pyportal import PyPortal
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text.label import Label
from adafruit_portalbase.network import HttpError

# Set up where we'll be fetching data from
DATA_SOURCE = (
    "https://ll.thespacedevs.com/2.2.0/astronaut/"
    "?mode=list&in_space=true&limit=16&type=human"
)

# Determine the current working directory
cwd = ("/"+__file__).rsplit('/', 1)[0]

# Initialize the pyportal object - no json_path since we parse manually
pyportal = PyPortal(url=DATA_SOURCE,
                    status_neopixel=board.NEOPIXEL,
                    default_bg=cwd+"/astronauts_background.bmp")
gc.collect()

# Font for names and count label
names_font = bitmap_font.load_font(cwd+"/fonts/Helvetica-Bold-10.bdf")
names_font.load_glyphs(
    b'abcdefghjiklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789- ()'
)

# Display positions and colors
names_position = (6, 140)
names_color = 0xFF00FF
count_color = 0xFFFFFF
count_position = (180, 108)

# Layout constants
screen_width = 320
col_gap = 6
char_width = 7  # slightly wider estimate for Helvetica Bold proportional font
font_height = 12
max_rows = 8

# Agency name to abbreviation lookup
AGENCY_ABBREV = {
    "National Aeronautics and Space Administration": "USA",
    "Russian Federal Space Agency (ROSCOSMOS)": "RUS",
    "European Space Agency": "ESA",
    "China National Space Administration": "CHN",
    "Japan Aerospace Exploration Agency": "JAX",
    "Canadian Space Agency": "CSA",
    "SpaceX": "SpX",
    "Boeing": "Boe",
}

gc.collect()

def make_count_label(count):
    lbl = Label(names_font, text="{} People in Space".format(count))
    lbl.color = count_color
    lbl.x = count_position[0]
    lbl.y = count_position[1]
    return lbl

def fetch_astronauts():
    """Fetch and parse astronaut data, filtering out non-humans."""
    gc.collect()
    raw = pyportal.fetch()
    if isinstance(raw, str):
        data = json.loads(raw)
    else:
        data = raw
    astronauts = [
        a for a in data["results"]
        if a.get("type", {}).get("name") != "Non-Human"
    ]
    count = len(astronauts)
    del data
    del raw
    gc.collect()
    return count, astronauts

def build_name_list(astronauts):
    """Build display strings from astronaut records."""
    result = []
    for a in astronauts:
        agency_full = a.get("agency", "")
        abbrev = AGENCY_ABBREV.get(agency_full, agency_full[:4])
        result.append("%s (%s)" % (a["name"], abbrev))
    return result

def calculate_columns(names):
    """Calculate column widths and positions based on name lengths.
    Col1 names are truncated to fit; col2 start is fixed from col1 width.
    """
    col1_x = names_position[0]
    col2_names = names[max_rows:]

    col2_max_px = (
        max(len(n) * char_width for n in col2_names) if col2_names else 0
    )

    total_available = screen_width - col1_x - col_gap

    if col2_names:
        # Allocate col2 what it needs, give the rest to col1
        col2_width = min(col2_max_px, total_available // 2)
        col2_width = max(col2_width, 0)
        col1_width = total_available - col2_width - col_gap
        col2_x = col1_x + col1_width + col_gap
    else:
        col1_width = total_available
        col2_x = screen_width  # unused

    # col1 max_chars is the hard truncation limit
    max_chars_col1 = col1_width // char_width
    max_chars_col2 = col2_width // char_width if col2_names else 0

    return col2_x, max_chars_col1, max_chars_col2, bool(col2_names)

def display_astronauts(count, names):
    """Create and append all labels, return list for later cleanup."""
    labels = []

    # Count label
    lbl = make_count_label(count)
    pyportal.root_group.append(lbl)
    labels.append(lbl)

    col2_x, max_chars_col1, max_chars_col2, has_col2 = (
        calculate_columns(names)
    )
    y_start = names_position[1]

    for i, name in enumerate(names):
        in_col2 = i >= max_rows
        max_chars = max_chars_col2 if in_col2 else max_chars_col1
        if len(name) > max_chars:
            name = name[:max_chars - 1] + "~"
        lbl = Label(names_font, text=name)
        lbl.color = names_color
        lbl.x = col2_x if in_col2 else names_position[0]
        lbl.y = (
            y_start + (i - max_rows) * font_height
            if in_col2
            else y_start + i * font_height
        )
        pyportal.root_group.append(lbl)
        labels.append(lbl)

    return labels

def clear_labels(labels):
    """Remove all labels from the display group."""
    for lbl in labels:
        pyportal.root_group.pop()


# Main loop
while True:
    try:
        count, astronauts = fetch_astronauts()
        names = build_name_list(astronauts)
        del astronauts
        gc.collect()
        print("People in space:", count)
        for n in names:
            print(" ", n)
    except HttpError as e:
        print("Rate limited, backing off! -", e)
        time.sleep(300)  # wait 5 minutes before retrying
        supervisor.reload()
    except (RuntimeError, KeyError, ValueError) as e:
        print("Fetch error, retrying! -", e)
        time.sleep(30)
        supervisor.reload()

    labels = display_astronauts(count, names)
    time.sleep(3600)  # display for 1 hour - data changes infrequently
    clear_labels(labels)
    gc.collect()
    supervisor.reload()
