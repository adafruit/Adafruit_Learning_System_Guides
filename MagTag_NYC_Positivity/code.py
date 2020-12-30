# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
import time
from adafruit_magtag.magtag import MagTag

# Set up where we'll be fetching data from
# pylint: disable=line-too-long
DATA_SOURCE = "https://raw.githubusercontent.com/nychealth/coronavirus-data/master/latest/pp-by-modzcta.csv"

magtag = MagTag()
magtag.network.connect()

magtag.add_text(
    text_font="Arial-Bold-12.bdf",
    text_position=(10, 15),
    line_spacing=0.75,
)

magtag.graphics.qrcode(b"https://www1.nyc.gov/site/doh/covid/covid-19-data.page",
                       qr_size=2, x=220, y=50)

timestamp = None

while True:
    header = None
    latest = None

    if not timestamp or (time.monotonic() - timestamp) > 60:  # once a minute
        print("Try connecting...")
        try:
            response = magtag.network.requests.get(DATA_SOURCE)
            text = response.text.split("\r\n")
            header = text[0].split(",")
            latest = text[-2].split(",")
            for i, txt in enumerate(header):
                header[i] = txt.strip('\"')
            #print(header, latest)

            man_idx = header.index("Manhattan")
            bx_idx = header.index("Bronx")
            bk_idx = header.index("Brooklyn")
            qn_idx = header.index("Queens")
            si_idx = header.index("Staten Island")
            nyc_idx = header.index("Citywide")
        except (ValueError, RuntimeError) as e:
            print("Some error occured, retrying! -", e)
            continue

        print("Date:", latest[0])
        mh_pp = float(latest[man_idx])
        bx_pp = float(latest[bx_idx])
        bk_pp = float(latest[bk_idx])
        qn_pp = float(latest[qn_idx])
        si_pp = float(latest[si_idx])
        nyc_pp = float(latest[nyc_idx])
        print("Manhattan:", mh_pp)
        print("Bronx:", bx_pp)
        print("Brooklyn:", bk_pp)
        print("Queens:", qn_pp)
        print("Staten Island:", si_pp)
        print("Citywide:", nyc_pp)

        print("Done!")
        magtag.set_text("Date: %s / Citywide: %0.2f%%\nManhattan: %0.2f%%\nBronx: %0.2f%%\nBrooklyn: %0.2f%%\nQueens: %0.2f%%\nStaten: %0.2f%%" % \
                         (latest[0], nyc_pp, mh_pp, bx_pp, bk_pp, qn_pp, si_pp))
        timestamp = time.monotonic()

    time.sleep(0.01)
