# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Map tiles for aprs_ui_map.py: slippy-map tile maths, a cache on the SD
card, downloads, and PNG -> 8-bit BMP conversion.

Tiles are the usual 256x256 web-map tiles ({z}/{x}/{y}, Web Mercator),
from OpenStreetMap's standard tile server by default
(https://operations.osmfoundation.org/policies/tiles/: an identifying
User-Agent, keep what was downloaded, show "(C) OpenStreetMap
contributors"). They are kept in the cache folder in the same layout:

    /sd/tiles/osm/9/122/196.png     as downloaded
    /sd/tiles/osm/9/122/196.bmp     the same, 8-bit RGB332 (the DVI
                                    framebuffer's colours), rows top-down

Only the BMP is read while the receiver runs: its rows go straight into
the map bitmap. Converting a PNG takes ~1.5 s on the board (zlib, then a
palette lookup per pixel in Python) and a download ~2.5 s, so both happen
once per tile, with the radio stream paused. Tiles copied to the card
from a PC (PNG or BMP, same layout) are used as they are.

Plain Python apart from the download: the PC tests use the conversion
and the maths.
"""
import math
import os
import struct
import zlib

# pylint: disable=import-outside-toplevel, too-many-locals, too-many-branches, too-many-statements

TILE = 256
BMP_HEADER = 14 + 40 + 1024          # file header, BITMAPINFOHEADER, 256-colour palette
USER_AGENT = 'FruitJam-APRS-receiver/1.0 CircuitPython'


# ----------------------------------------------------------------- maths

def world_x(lon, zoom):
    """Longitude -> x in pixels on the whole map at this zoom."""
    return (lon + 180.0) / 360.0 * (TILE << zoom)


def mercator(lat):
    """Latitude -> Mercator y, -0.5 (85.05N) .. 0.5 (85.05S)."""
    lat = max(-85.05, min(85.05, lat))
    s = math.sin(math.radians(lat))
    return -math.log((1 + s) / (1 - s)) / (4 * math.pi)


def unmercator(y):
    """Mercator y -> latitude (mercator()'s inverse)."""
    k = math.exp(-4 * math.pi * max(-0.5, min(0.5, y)))
    return math.degrees(math.asin((k - 1) / (k + 1)))


def world_y(lat, zoom):
    """Latitude -> y in pixels on the whole map at this zoom."""
    return (0.5 + mercator(lat)) * (TILE << zoom)


def metres_per_pixel(lat, zoom):
    return 156543.034 * math.cos(math.radians(lat)) / (1 << zoom)


# ------------------------------------------------------------ colours

def rgb332(r, g, b):
    return (r & 0xe0) | (g & 0xe0) >> 3 | b >> 6


def rgb332_colour(v):
    """RGB332 value -> 0xRRGGBB."""
    return ((v >> 5) * 255 // 7) << 16 | ((v >> 2 & 7) * 255 // 7) << 8 | (v & 3) * 85


def bmp_header(width, height):
    """8-bit top-down BMP header with the RGB332 palette."""
    h = bytearray(BMP_HEADER)
    stride = (width + 3) & ~3
    struct.pack_into('<2sIHHI', h, 0, b'BM', BMP_HEADER + stride * height, 0, 0, BMP_HEADER)
    struct.pack_into('<IiiHHIIiiII', h, 14, 40, width, -height, 1, 8, 0, stride * height,
                     2835, 2835, 256, 0)
    for v in range(256):
        c = rgb332_colour(v)
        struct.pack_into('<BBBB', h, 54 + 4 * v, c & 255, c >> 8 & 255, c >> 16, 0)
    return h


# ---------------------------------------------------------------- PNG

def _unfilter(f, cur, prev, bpp):
    """Undo one PNG row filter in place (prev: the row above, unfiltered)."""
    n = len(cur)
    if f == 1:
        for i in range(bpp, n):
            cur[i] = (cur[i] + cur[i - bpp]) & 255
    elif f == 2:
        for i in range(n):
            cur[i] = (cur[i] + prev[i]) & 255
    elif f == 3:
        for i in range(n):
            a = cur[i - bpp] if i >= bpp else 0
            cur[i] = (cur[i] + ((a + prev[i]) >> 1)) & 255
    elif f == 4:
        for i in range(n):
            a = cur[i - bpp] if i >= bpp else 0
            c = prev[i - bpp] if i >= bpp else 0
            b = prev[i]
            p = a + b - c
            pa = abs(p - a)
            pb = abs(p - b)
            pc = abs(p - c)
            cur[i] = (cur[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
    elif f:
        raise ValueError('PNG filter %d' % f)


def png_to_bmp(data, out):
    """A PNG (bytes) -> an RGB332 BMP written to the open file out.
    Indexed (1-8 bit), grey (1-8 bit) and 8-bit RGB, RGBA and grey+alpha;
    transparent pixels become white. Returns (width, height)."""
    if bytes(data[:8]) != b'\x89PNG\r\n\x1a\n':
        raise ValueError('not a PNG')
    mv = memoryview(data)
    pos = 8
    idat = bytearray()
    plte = trns = None
    width = 0
    while pos + 8 <= len(data):
        ln = int.from_bytes(bytes(mv[pos:pos + 4]), 'big')
        kind = bytes(mv[pos + 4:pos + 8])
        body = mv[pos + 8:pos + 8 + ln]
        if kind == b'IHDR':
            width, height, depth, ctype, _, _, interlace = struct.unpack('>IIBBBBB', bytes(body))
        elif kind == b'PLTE':
            plte = bytes(body)
        elif kind == b'tRNS':
            trns = bytes(body)
        elif kind == b'IDAT':
            idat.extend(body)
        elif kind == b'IEND':
            break
        pos += 12 + ln
    if not width:
        raise ValueError('no IHDR')
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(ctype)
    if channels is None or interlace or depth > 8 or (depth < 8 and ctype not in (0, 3)):
        raise ValueError('PNG type %d depth %d interlace %d' % (ctype, depth, interlace))
    raw = zlib.decompress(idat)
    del idat
    stride = (width * channels * depth + 7) // 8
    if len(raw) < (stride + 1) * height:
        raise ValueError('PNG data short')
    bpp = max(1, channels * depth // 8)
    # Indexed and grey: one lookup per pixel value.
    lut = None
    if ctype == 3:
        lut = bytearray(b'\xff' * 256)
        for i in range(min(256, len(plte or b'') // 3)):
            if trns is None or i >= len(trns) or trns[i] >= 128:
                lut[i] = rgb332(plte[3 * i], plte[3 * i + 1], plte[3 * i + 2])
    elif ctype == 0:
        levels = (1 << depth) - 1
        lut = bytearray(256)
        for i in range(levels + 1):
            v = i * 255 // levels
            lut[i] = rgb332(v, v, v)
    pad = (width + 3) & ~3
    row = bytearray(pad)
    prev = bytearray(stride)
    out.write(bmp_header(width, height))
    per_byte = 8 // depth
    mask = (1 << depth) - 1
    for y in range(height):
        at = y * (stride + 1)
        f = raw[at]
        cur = bytearray(raw[at + 1:at + 1 + stride])
        if f:
            _unfilter(f, cur, prev, bpp)
        if lut is not None and depth == 8:
            for x in range(width):
                row[x] = lut[cur[x]]
        elif lut is not None:
            for x in range(width):
                shift = 8 - depth * (x % per_byte + 1)
                row[x] = lut[cur[x // per_byte] >> shift & mask]
        elif ctype == 2:
            for x in range(width):
                k = 3 * x
                row[x] = rgb332(cur[k], cur[k + 1], cur[k + 2])
        elif ctype == 6:
            for x in range(width):
                k = 4 * x
                row[x] = rgb332(cur[k], cur[k + 1], cur[k + 2]) if cur[k + 3] >= 128 else 0xff
        else:   # grey + alpha
            for x in range(width):
                v = cur[2 * x]
                row[x] = rgb332(v, v, v) if cur[2 * x + 1] >= 128 else 0xff
        out.write(row)
        prev = cur
    return width, height


# -------------------------------------------------------------- cache

def _exists(path):
    try:
        os.stat(path)
        return True
    except OSError:
        return False


def _makedirs(path):
    at = ''
    for part in path.strip('/').split('/'):
        at += '/' + part
        try:
            os.mkdir(at)
        except OSError:
            pass


def wifi_session():
    """An adafruit_requests session through wifi.radio, which the
    supervisor connects with Wi-Fi in settings.toml."""
    if not os.getenv('CIRCUITPY_WIFI_SSID'):
        # (and leave wifi alone: on the Metro ESP32-P4 the board crashes
        # at the next soft reset once wifi has been imported)
        raise RuntimeError('no Wi-Fi: set CIRCUITPY_WIFI_SSID/PASSWORD in settings.toml')
    import wifi
    import adafruit_connection_manager
    import adafruit_requests
    if not wifi.radio.connected:
        raise RuntimeError('Wi-Fi is not connected')
    pool = adafruit_connection_manager.get_radio_socketpool(wifi.radio)
    ssl = adafruit_connection_manager.get_radio_ssl_context(wifi.radio)
    return adafruit_requests.Session(pool, ssl)


class TileCache:
    """Tiles on the SD card (folder), fetched from url ('{z}', '{x}', '{y}')
    when missing."""

    def __init__(self, folder, url, user_agent=USER_AGENT):
        self.folder = folder
        self.url = url
        self.user_agent = user_agent
        self._session = None
        self.fetched = 0
        self.converted = 0

    def path(self, z, x, y, ext='bmp'):
        return '%s/%d/%d/%d.%s' % (self.folder, z, x, y, ext)

    def ready(self, z, x, y):
        """True if the tile's BMP is on the card."""
        return _exists(self.path(z, x, y))

    def has_png(self, z, x, y):
        return _exists(self.path(z, x, y, 'png'))

    def session(self):
        """An adafruit_requests session through the ESP32-C6 that the
        core shares (nina-fw makes the TLS connection), or on boards with
        the wifi module (the Metro ESP32-P4) through wifi.radio."""
        if self._session is None:
            try:
                import _airlift  # pylint: disable=unused-import
            except ImportError:
                self._session = wifi_session()
                return self._session
            from adafruit_esp32spi import adafruit_esp32spi
            import adafruit_esp32spi.adafruit_esp32spi_socketpool as esp_socketpool
            import adafruit_connection_manager
            import adafruit_requests
            esp = adafruit_esp32spi.ESP_SPIcontrol()
            if not esp.is_connected:
                raise RuntimeError('Wi-Fi is not connected')
            pool = esp_socketpool.SocketPool(esp)
            ssl = adafruit_connection_manager.get_radio_ssl_context(esp)
            self._session = adafruit_requests.Session(pool, ssl)
        return self._session

    def fetch(self, z, x, y):
        """Download the tile's PNG to the card; returns its bytes."""
        url = self.url.format(z=z, x=x, y=y)
        r = self.session().get(url, headers={'User-Agent': self.user_agent})
        try:
            if r.status_code != 200:
                raise OSError('HTTP %d for %s' % (r.status_code, url))
            data = r.content
        finally:
            r.close()
        path = self.path(z, x, y, 'png')
        _makedirs(path[:path.rfind('/')])
        with open(path + '.tmp', 'wb') as f:
            f.write(data)
        os.rename(path + '.tmp', path)
        self.fetched += 1
        return data

    def convert(self, z, x, y, data=None):
        """The tile's PNG (data, or the cached file) -> its BMP."""
        if data is None:
            with open(self.path(z, x, y, 'png'), 'rb') as f:
                data = f.read()
        path = self.path(z, x, y)
        _makedirs(path[:path.rfind('/')])
        with open(path + '.tmp', 'wb') as f:
            size = png_to_bmp(data, f)
        if size != (TILE, TILE):
            os.remove(path + '.tmp')
            raise ValueError('tile is %dx%d' % size)
        os.rename(path + '.tmp', path)
        self.converted += 1
