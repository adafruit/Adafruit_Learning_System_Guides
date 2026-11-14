# SPDX-FileCopyrightText: 2026 John Park for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-only
"""Will the firmware the FM-1 runs refuse this install, because of the flash head?

A few packages carry M-VAVE's own update loader (V15, Bubba, Amenity, Clatter
on the hub in November 2026). It writes the whole flash image, including the
head: the first 16 KiB, the FM-1's start-up code. Firmwares built on Felucca
(SLOOP, ZP12, Duell...) stage such a package only when its head is the one the
FM-1 has ("update failed -5" on SLOOP), and the head is whatever the last of
those packages wrote. Firmwares built on V15 don't check. Bubba Machine has an
updater of its own that takes only packages with M-VAVE's loader, and only with
the FM-1's head (its hal/fm1/fm1_update.c: -5, -7). advice() says when an
install will be refused and which firmware on the card gets round it: one whose
head is the FM-1's, which the running firmware accepts and which then installs
anything (docs/PLAN-v2.md, Phase 3).
"""
# Disabled for the Learn Guides lint check: modules are imported where they're needed, to keep RAM
# free and start-up quick.
# pylint: disable=import-outside-toplevel
import json

from fm1ui.catalog import V16_PRODUCT

STOCK_PRODUCT = "FM-1_015"
# Firmwares whose updater can't be told from their package: (identity) -> what
# it takes. "official": only packages with M-VAVE's loader and the FM-1's head.
UPDATERS = {"FM-1_003": "official",  # Bubba Machine (hal/fm1/fm1_update.c)
            V16_PRODUCT: "any"}  # M-VAVE's V16: its updater is V15's
# The flash head V16 writes: fm1proto.flash_head of M-VAVE's FM-1.fwsc 016 (SHA-256 d017fb65...).
# M-VAVE's updater installs V16, so the flasher records it when it sees V16 running (seen()).
V16_HEAD = 0x22B0
_cache = {}  # (slug, version) -> (official loader, head CRC or None)


def info(app, slug):
    """(official loader, head CRC or None) for a firmware on the card, or None
    when its package can't be read. Read once per version."""
    e = app.entry(slug) if slug else None
    if e is None:
        return None
    key = (slug, e.version)
    if key not in _cache:
        import fm1proto as P
        try:
            with open(app.path(slug, "meta.json")) as f:
                name = json.load(f)["file"]
            with open(app.path(slug, name), "rb") as f:
                pkg = P.Package(f)
                pkg.inspect(verify=False, strict=False)
                official = P.official_loader(pkg)
                _cache[key] = (official, P.flash_head(pkg) if official else None)
        except (OSError, ValueError, KeyError, P.FM1Error):
            return None
    return _cache[key]


def seen(app):
    """Record V16's head when the FM-1 is found running V16: M-VAVE's updater
    put it there, not the flasher. Returns True when the record changed."""
    rec = app.state.head or {}
    if app.identity != V16_PRODUCT or rec.get("head") == V16_HEAD:
        return False
    app.state.head = {"head": V16_HEAD, "slug": V16_PRODUCT}
    app.state.save()
    return True


def _stock_slug(app):
    found = app.index.with_product(STOCK_PRODUCT)
    return found[0] if found else None


def _running(app):
    """(name, slug or None, what its updater takes) for the firmware the FM-1
    runs: "any" (built on V15), "head" (built on Felucca: M-VAVE-loader
    packages only with the FM-1's head), "official" (UPDATERS), or None when
    it's nothing we know."""
    import fm1proto as P
    ident = app.identity
    known = app.installed_slug()
    slugs = [known] if known else app.index.with_product(ident)
    runs = [i for i in (info(app, s) for s in slugs) if i]
    if ident in UPDATERS:
        takes = UPDATERS[ident]
    elif any(i[0] for i in runs):
        takes = "any"
    elif runs or P.community_identity(ident):
        takes = "head"
    else:
        takes = None
    from fm1ui import catalog as C
    return (app.entry(known).name if known else C.running_name(ident)), known, takes


def _fm1_head(app):
    """(head, recorded, slug that wrote it): what the last install with
    M-VAVE's loader wrote, as recorded; without a record, V15's, as the FM-1
    leaves the factory."""
    rec = app.state.head
    if rec:
        return rec.get("head"), True, rec.get("slug")
    slug = _stock_slug(app)
    stock = info(app, slug)
    return (stock[1] if stock else None), False, slug


def _bridges(app, slug, head):
    """Can firmware `slug` be the way round: M-VAVE's loader with the FM-1's
    head (so the running firmware takes it), and an updater that then takes
    anything?"""
    e = app.entry(slug) if slug else None
    i = info(app, slug)
    return bool(e and i and i[0] and i[1] == head and e.product not in UPDATERS)


def advice(app, entry):
    """A warning for the confirm screen, or None: the way round first, so it
    shows even when the screen has room for only part of it."""
    target = info(app, entry.slug)
    if not app.identity or not target:
        return None
    running, run_slug, takes = _running(app)
    head, sure, via = _fm1_head(app)
    now = info(app, run_slug)
    if now and now[0]:  # it runs a firmware with M-VAVE's loader: the head is its own
        head, sure, via = now[1], True, run_slug
    if takes == "official" and not target[0]:
        refuse = "%s will refuse it: it installs only firmwares packaged like V15" % running
    elif takes in ("head", "official") and target[0] and head is not None and head != target[1]:
        refuse = "%s will %srefuse it: the FM-1's start-up code differs" % (
            running, "" if sure else "probably ")
    else:
        return None
    # A way round: a firmware on the card that the running one takes (M-VAVE's
    # loader, the FM-1's head) and that then installs anything.
    bridge = None
    for s in (_stock_slug(app), via):
        if s not in (entry.slug, run_slug) and _bridges(app, s, head):
            bridge = app.entry(s).name
            break
    if bridge is None and via == V16_PRODUCT:
        bridge = "M-VAVE V16 (with M-VAVE's updater)"
    if bridge:
        return "Install %s first, then %s, otherwise %s." % (bridge, entry.name, refuse)
    return "%s. Install the firmware that last changed it first." % (refuse[0].upper() + refuse[1:])
