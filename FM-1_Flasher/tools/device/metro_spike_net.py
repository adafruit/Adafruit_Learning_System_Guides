# SPDX-FileCopyrightText: 2026 John Park for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-only
"""v2 spikes 3 and 4 (docs/PLAN-v2.md): the Metro ESP32-P4's SD card and
WiFi. Copy to CIRCUITPY as code.py with fm1proto, adafruit_requests,
adafruit_connection_manager and adafruit_imageload in lib/, and WiFi in
settings.toml (CIRCUITPY_WIFI_SSID, CIRCUITPY_WIFI_PASSWORD).

1. SD: 1 MB write and read on /sd (the board mounts the card itself).
2. WiFi: fetch the hub's catalog.json, then stream one package to the card.
3. The full package checks on it (fm1proto.prepare, no checked=True).
4. Decode the firmware's hub picture (PNG) with adafruit_imageload.
"""
import gc
import hashlib
import json
import os
import time

import adafruit_connection_manager
import adafruit_requests
import wifi

import fm1proto as P

HUB = "https://thefirmwarehub.com/"
PICK = "sloop"
DIR = "/sd/spike"


def mb_s(n, t):
    return n / t / 1e6 if t else 0


# 1. SD: the board doesn't mount the card itself
import board
import digitalio
import sdioio
import storage

cd = digitalio.DigitalInOut(board.SD_CD)
cd.pull = digitalio.Pull.UP
print("SD card detect pin:", cd.value)
cd.deinit()
if "/sd" not in [m for m in ("/sd",) if os.listdir("/sd") != ["placeholder.txt"]]:
    sd = sdioio.SDCard(clock=board.SD_CLK, command=board.SD_CMD,
                       data=[board.SD_DATA0, board.SD_DATA1, board.SD_DATA2, board.SD_DATA3],
                       frequency=40_000_000)
    storage.mount(storage.VfsFat(sd), "/sd")
    print("mounted /sd:", os.listdir("/sd")[:8])
try:
    os.mkdir(DIR)
except OSError:
    pass
block = bytes(range(256)) * 16  # 4 KB
t = time.monotonic()
with open(DIR + "/test.bin", "wb") as f:
    for _ in range(256):
        f.write(block)
tw = time.monotonic() - t
t = time.monotonic()
n = 0
buf = bytearray(4096)
with open(DIR + "/test.bin", "rb") as f:
    while True:
        k = f.readinto(buf)
        if not k:
            break
        n += k
tr = time.monotonic() - t
print("SD: 1 MB write %.2f s (%.2f MB/s), read %.2f s (%.2f MB/s)" % (tw, mb_s(1 << 20, tw), tr, mb_s(n, tr)))
os.remove(DIR + "/test.bin")

# 2. WiFi
if not wifi.radio.connected:
    t = time.monotonic()
    wifi.radio.connect(os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD"))
    print("WiFi connect: %.2f s" % (time.monotonic() - t))
print("WiFi: connected=%s ip=%s" % (wifi.radio.connected, wifi.radio.ipv4_address))
pool = adafruit_connection_manager.get_radio_socketpool(wifi.radio)
ssl = adafruit_connection_manager.get_radio_ssl_context(wifi.radio)
http = adafruit_requests.Session(pool, ssl)
t = time.monotonic()
r = http.get(HUB + "catalog.json")
cat = r.json()
r.close()
tc = time.monotonic() - t
e = [x for x in cat["firmwares"] if x["id"] == PICK][0]
print("catalog: %d firmwares, updated %s, %.2f s" % (len(cat["firmwares"]), cat.get("updated"), tc))
gc.collect()
print("free RAM:", gc.mem_free())

path = DIR + "/" + e["product"] + ".fwsc"
t = time.monotonic()
h = hashlib.new("sha256")
n = 0
r = http.get(HUB + e["pkg"])
with open(path, "wb") as f:
    for chunk in r.iter_content(chunk_size=8192):
        f.write(chunk)
        h.update(chunk)
        n += len(chunk)
r.close()
td = time.monotonic() - t
ok = h.digest().hex() == e["sha256"] and n == e["size"]
print("download %s %s: %d bytes in %.2f s (%.2f MB/s), sha256 %s" % (
    PICK, e["version"], n, td, mb_s(n, td), "ok" if ok else "MISMATCH"))

# 3. Full package checks (what make_sd.py runs), as meta.json would have it
with open(path, "rb") as f:
    pkg = P.Package(f)
    pkg.inspect(verify=False, strict=False)
    meta = {"schema": 1, "kind": "community", "family": P.FAMILY, "bytes": n,
            "product": e["product"], "sha256": e["sha256"], "loader_sha256": pkg.loader_sha256()}
    t = time.monotonic()
    _, checked = P.prepare(meta, f)
    print("full package checks: %.2f s, loader %s" % (time.monotonic() - t, checked["loader_identity"]))

# 4. The hub's picture
try:
    import adafruit_imageload
    t = time.monotonic()
    r = http.get(HUB + "img/%s.png" % PICK)
    png = r.content
    r.close()
    tg = time.monotonic() - t
    with open(DIR + "/pic.png", "wb") as f:
        f.write(png)
    t = time.monotonic()
    bmp, pal = adafruit_imageload.load(DIR + "/pic.png")
    print("picture: %d bytes, fetch %.2f s, PNG decode %.2f s, %dx%d, palette %s" % (
        len(png), tg, time.monotonic() - t, bmp.width, bmp.height,
        len(pal) if pal is not None and hasattr(pal, "__len__") else pal))
except Exception as ex:
    print("picture: failed: %r" % ex)
print("spike done")
