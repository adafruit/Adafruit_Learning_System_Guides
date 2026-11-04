# SPDX-FileCopyrightText: 2026 John Park for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-only
"""Update firmwares: bring the card up to date with the FM-1 Firmware Hub over
WiFi (docs/PLAN-v2.md, Phase 2).

The work is a generator (job()) that the screen advances a step at a time
from tick(), so the screen keeps drawing and Stop works between steps: one
download chunk, a few rows of a picture, one removal.

net is passed in: .connect() -> None or an error message; .get_json(url);
.get(url) -> bytes; .stream(url) -> a generator of byte chunks. Errors are
OSError (network) or ValueError.
"""
# Disabled for the Learn Guides lint check: screens make their widgets in build(), each time
# they're shown; modules are imported where they're needed, to keep RAM free and start-up quick;
# some drawing and protocol functions are long by nature.
# pylint: disable=attribute-defined-outside-init,import-outside-toplevel,too-many-branches
# pylint: disable=too-many-locals,too-many-statements
import os
import time

import displayio

import fm1catalog as K
from fm1ui import catalog as C
from fm1ui import ui
from fm1ui.layout import L

PIC = "thumb.bmp"
NO_PIC = "thumb.none"  # the hub has no picture for this one: don't ask again
BYTES_PER_S = 200_000  # measured: 0.21 MB/s to the card (docs/PLAN-v2.md)
CHECK_S = 3  # the full package checks, per firmware


def needs_picture(root, slug):
    d = root + "/" + slug
    return not (K.exists(d + "/" + PIC) or K.exists(d + "/" + NO_PIC))


def picture_list(root, plan):
    """Catalogue ids on the card (after the plan runs) without a picture yet."""
    fresh = set(e["id"] for e in plan.downloads)
    out = []
    for e in plan.same + plan.downloads:
        if e["id"] == K.STOCK_ID:
            continue
        if e["id"] in fresh or needs_picture(root, e["id"]):
            out.append(e)
    return out


def estimate_s(plan, pictures):
    return plan.bytes // BYTES_PER_S + CHECK_S * len(plan.downloads) + 3 * len(pictures)


def job(root, plan, net, stats):
    """A generator: download, then fetch pictures, yielding (phase, done,
    total, name) as it goes. Counts land in `stats`. Nothing is removed."""
    K.clean_parts(root)

    for i, e in enumerate(plan.dated):  # cards from before the lists sorted by date
        yield ("Adding dates", i, len(plan.dated), e.get("name") or e["id"])
        K.set_dates(root, e)

    total = plan.bytes
    base = 0
    since_index = 0
    for e in plan.downloads:
        name = e.get("name") or e["id"]
        yield ("Downloading", base, total, name)
        dl = K.download(root, e, net.stream)
        try:
            for n in dl:
                yield ("Downloading", base + n, total, name)
            for old in (PIC, NO_PIC, "large.bmp"):  # a new version may have a new picture
                try:
                    os.remove(root + "/" + e["id"] + "/" + old)
                except OSError:
                    pass
            stats["new" if e in plan.new else "updated"] += 1
            since_index += 1
            if since_index >= 10:  # so a power cut loses little of the list
                K.write_index(root)
                since_index = 0
        # A bad download or package: skip it and go on.
        except Exception as ex:  # pylint: disable=broad-except
            print("update: %s failed: %r" % (e["id"], ex))
            stats["failed"].append(e["id"])
            if (
                isinstance(ex, OSError)
                and len(stats["failed"]) >= 3
                and stats["new"] + stats["updated"] == 0
            ):
                raise  # the network is down, not one package
        finally:
            dl.close()  # on Stop: closes its file and download (MicroPython
            # doesn't close a dropped generator for us)
        base += e.get("size", 0)
    K.write_index(root, plan.updated_at)
    stats["index"] = True

    import fm1pic
    pics = [e for e in picture_list(root, plan) if K.exists(root + "/" + e["id"] + "/meta.json")]
    for i, e in enumerate(pics):
        name = e.get("name") or e["id"]
        yield ("Pictures", i, len(pics), name)
        d = root + "/" + e["id"]
        try:
            data = net.get(K.HUB + "img/%s.png" % e["id"])
        except OSError as ex:
            if "404" in str(ex):
                with open(d + "/" + NO_PIC, "w") as f:
                    f.write("404\n")
            else:
                print("update: picture %s: %r" % (e["id"], ex))
            continue
        try:
            for _ in fm1pic.convert(data, d + "/" + PIC):
                yield ("Pictures", i, len(pics), name)
            stats["pictures"] += 1
        except (ValueError, MemoryError, OSError) as ex:
            print("update: picture %s: %r" % (e["id"], ex))
        data = None


class UpdateScreen:
    """Connect to WiFi, read the hub's catalogue, show what would change,
    then run the update with a progress bar and a Stop button."""

    STEP_S = 0.05  # work per tick before the screen gets a look in

    def __init__(self, app):
        self.app = app
        self.group = None
        self.mode = "start"  # start, plan, run, done, error
        self.plan = None
        self.pics = []
        self.message = ""
        self.work = None
        self.stats = None
        self.t0 = 0
        self.last_draw = 0
        self.stopping = False

    # -- the Screen protocol (fm1ui.screens.Screen) ------------------------------

    def release(self):
        self.group = None

    def build(self):
        W, H = L.W, L.H
        g = displayio.Group()
        g.append(ui.rect(0, 0, W, H, ui.BG))
        g.append(ui.rect(0, 0, W, 3, ui.CYAN))
        self.title = ui.text(
            ui.TITLE, "Update firmwares", ui.FG, W // 2, L.PROGRESS_TITLE_Y, (0.5, 0)
        )
        g.append(self.title)
        self.sub = ui.text(ui.BODY, " ", ui.DIM, W // 2, L.PROGRESS_SUB_Y, (0.5, 0))
        g.append(self.sub)
        bx, by, bw, bh = L.BAR
        self.phase = ui.text(ui.NAME, " ", ui.FG, bx, by - 10, (0, 1))
        g.append(self.phase)
        self.pct = ui.text(ui.NAME, " ", ui.FG, bx + bw, by - 10, (1, 1))
        g.append(self.pct)
        self.bar_group = displayio.Group()
        self.bar_group.append(ui.outlined(bx, by, bw, bh, ui.PANEL, ui.LINE))
        self.fill = ui.rect(bx + 3, by + 3, 1, bh - 6, ui.CYAN)
        self.fill_group = displayio.Group()
        self.fill_group.append(self.fill)
        self.bar_group.append(self.fill_group)
        g.append(self.bar_group)
        self.info = ui.text(ui.SMALL, " ", ui.DIM, bx, by + bh + 14, (0, 0.5))
        g.append(self.info)
        self.note = ui.text(ui.BODY, " ", ui.TEXT, W // 2, L.PROGRESS_NOTE_Y, (0.5, 0.5))
        self.note2 = ui.text(ui.BODY, " ", ui.TEXT, W // 2, L.PROGRESS_NOTE_Y + 18, (0.5, 0.5))
        g.append(self.note)
        g.append(self.note2)
        self.lines_at = len(g)
        g.append(displayio.Group())  # the plan's or an error's lines (_lines)
        cx, _, cw, ch = L.CANCEL_BTN
        gx, _, gw, gh = L.GO_BTN
        by2 = L.OK_BTN[1]
        self.mid = None
        if self.mode == "plan" and self.plan.offered:  # Back | Details | Update
            gap = 8
            w = (gx + gw - cx - 2 * gap) // 3
            self.left = ui.Button("Back", cx, by2, w, ch)
            self.mid = ui.Button("Details", cx + w + gap, by2, w, ch)
            self.right = ui.Button(
                "Update", gx + gw - w, by2, w, gh, fill=ui.CYAN, edge=ui.CYAN, color=ui.BG
            )
            g.append(self.mid.group)
        else:
            self.left = ui.Button("Back", cx, by2, cw, ch)
            self.right = ui.Button(
                "Update", gx, by2, gw, gh, fill=ui.CYAN, edge=ui.CYAN, color=ui.BG
            )
        g.append(self.left.group)
        g.append(self.right.group)
        self.group = g
        self._show()
        return g

    def _set_note(self, s, color=ui.TEXT):
        width_of = lambda t: ui.width(ui.BODY, t)  # noqa: E731
        parts = C.wrap(s, width_of, L.W - 24) if width_of(s) > L.W - 24 else [s]
        for label, part in ((self.note, parts[0] or " "), (self.note2, " ".join(parts[1:]) or " ")):
            label.color = color
            label.set(part)

    def _bar(self, done, total, color=ui.CYAN):
        bw = L.BAR[2] - 6
        w = max(1, bw * done // total) if total else 1
        self.fill.width = min(w, bw)
        self.fill.pixel_shader = ui.palette(color)
        self.fill_group.hidden = not total or done <= 0
        self.pct.set("%d%%" % (100 * done // total) if total else " ")

    def _lines(self, items):
        """Centred lines under the subtitle, for the plan and errors: items
        are (font, text, colour), each wrapped to the screen."""
        g = displayio.Group()
        y = L.PROGRESS_SUB_Y + 40
        for name, s, color in items:
            for part in C.wrap(s, lambda t, n=name: ui.width(n, t), L.W - 24):
                g.append(ui.text(name, part, color, L.W // 2, y, (0.5, 0)))
                y += 20
            y += 6
        self.group[self.lines_at] = g

    def _buttons(self, left, right):
        """Labels for the two buttons, or None to hide one."""
        for b, label in ((self.left, left), (self.right, right)):
            b.group.hidden = label is None
            if label:
                b.label.set(label)

    def _show(self):
        """Lay the screen out for the current mode."""
        m = self.mode
        self.bar_group.hidden = m not in ("run", "done")
        self.phase.hidden = self.pct.hidden = m not in ("run", "done")
        self._lines(())
        if m == "start":
            self.sub.set("Connecting to WiFi...")
            self._set_note(" ")
            self.info.set(" ")
            self._buttons("Back", None)
        elif m == "plan":
            p = self.plan
            self.sub.set("Catalog " + C.nice_date(p.updated_at))
            self._set_note(" ")
            self.info.set(" ")
            if p.downloads or self.pics:
                counts = []
                for n, what in ((p.picked(p.new), "new"), (p.picked(p.changed), "updated")):
                    if n:
                        counts.append("%d %s" % (n, what))
                if p.skip:
                    counts.append("%d unticked" % len(p.skip))
                size = []
                if p.bytes:
                    size.append("%.1f MB to download" % (p.bytes / 1e6))
                if self.pics:
                    size.append("%d pictures" % len(self.pics))
                mins = max(1, (estimate_s(p, self.pics) + 30) // 60)
                self._lines(((ui.NAME, ", ".join(counts) or "Firmwares up to date", ui.FG),
                             (ui.BODY, ", ".join(size), ui.TEXT),
                             (ui.BODY, "About %d min. Keep the flasher powered." % mins, ui.DIM)))
                self._buttons("Back", "Update")
            elif p.offered and not p.skip <= self.app.state.removed:
                self._lines(((ui.NAME, "Nothing picked", ui.WARN),
                             (ui.BODY, "Tick firmwares in Details to download them.", ui.TEXT)))
                self._buttons("Back", None)
            elif p.offered:  # only firmwares removed on the device
                n = len(p.skip)
                self._lines(
                    (
                        (ui.NAME, "Up to date", ui.OK),
                        (
                            ui.BODY,
                            "%d you removed %s left out. Tick %s in Details to get %s back."
                            % (
                                n,
                                "is" if n == 1 else "are",
                                "it" if n == 1 else "them",
                                "it" if n == 1 else "them",
                            ),
                            ui.TEXT,
                        ),
                    )
                )
                self._buttons("Back", None)
            else:
                self._lines(
                    (
                        (ui.NAME, "Up to date", ui.OK),
                        (
                            ui.BODY,
                            "The card has all %d firmwares on the hub." % len(p.same),
                            ui.TEXT,
                        ),
                    )
                )
                self._buttons("Back", None)
        elif m == "run":
            self.sub.set(" ")
            self._set_note(
                "You can keep using the flasher afterwards; Stop keeps what's done.", ui.DIM
            )
            self._buttons(None, "Stop")
        elif m == "done":
            s = self.stats
            done = []
            for k, label in (("new", "added"), ("updated", "updated"), ("pictures", "pictures")):
                if s[k]:
                    done.append("%d %s" % (s[k], label))
            failed = s["failed"]
            self.title.set("Stopped" if self.stopping else "Card updated")
            self.title.color = ui.WARN if (failed or self.stopping) else ui.OK
            self.sub.set(", ".join(done) or "Nothing changed")
            if failed:
                self._set_note("Failed: %s. Try again later." % ", ".join(failed[:4]), ui.WARN)
            elif self.stopping:
                self._set_note("What finished is on the card; Update again to go on.", ui.DIM)
            else:
                self._set_note(" ")
            self._buttons(None, "OK")
        elif m == "error":
            self.title.set("Update firmwares")
            self.sub.set(" ")
            self._set_note(" ")
            self._lines(((ui.BODY, self.message, ui.WARN),))
            self._buttons("Back", "Try again")

    def _mid_shown(self):
        return self.mid is not None and self.mode == "plan"

    def target(self, x, y):
        if self._mid_shown() and self.mid.hit(x, y, 4):
            return self.mid.group
        for b in (self.left, self.right):
            if not b.group.hidden and b.hit(x, y, 4 if self.mid else 10):
                return b.group
        return None

    def tap(self, x, y):
        if self._mid_shown() and self.mid.hit(x, y, 4):
            self.app.push(PlanScreen(self.app, self.plan, self.picked))
        elif not self.left.group.hidden and self.left.hit(x, y, 4 if self.mid else 10):
            self.app.pop()
        elif not self.right.group.hidden and self.right.hit(x, y, 4 if self.mid else 10):
            if self.mode == "plan":
                self.start_run()
            elif self.mode == "run":
                self.stopping = True
                self.right.label.set("Stopping")
                self.app.refresh()
            elif self.mode == "done":
                self.app.reload_index()
                self.app.home()
            elif self.mode == "error":
                self.mode = "start"
                self._show()
                self.app.refresh()
                self.t0 = 0

    def swipe(self, dx):
        pass

    def fm1_changed(self):
        pass

    # -- work ------------------------------------------------------------------

    def tick(self, now):
        if self.mode == "start" and self.group is not None:
            if not self.t0:  # draw "Connecting" first; the next tick blocks
                self.t0 = now
                return
            self.check()
        elif self.mode == "run":
            self.advance(now)

    def check(self):
        """Connect and read the catalogue: blocks a few seconds."""
        app = self.app
        err = app.updater.connect()
        if err is None:
            self.sub.set("Reading the hub's catalog...")
            app.refresh()
            try:
                cat = app.updater.get_json(K.HUB + "catalog.json")
                self.plan = K.Plan(cat, app.root)
                cat = None
                gone = app.state.removed  # removed on the device: left out unless ticked
                self.plan.skip = set(e["id"] for e in self.plan.offered if e["id"] in gone)
                self.pics = picture_list(app.root, self.plan)
            except (OSError, ValueError, KeyError) as e:
                err = "Couldn't read the hub's catalog (%s)." % (str(e) or repr(e))
            if err is None and self.plan.dated and not (self.plan.downloads or self.pics):
                self.add_dates()
        self.message = err or ""
        self.mode = "error" if err else "plan"
        app.show()  # the plan has its own buttons (Details)

    def add_dates(self):
        """Nothing to download, but the card's firmwares lack the catalogue's
        dates (the list's New and Updated sorts): add them now, once."""
        plan, app = self.plan, self.app
        self.sub.set("Adding dates to the list...")
        app.refresh()
        try:
            for e in plan.dated:
                K.set_dates(app.root, e)
            K.write_index(app.root, plan.updated_at)
            app.reload_index()
        except OSError as e:
            print("update: dates: %r" % e)
        plan.dated = []

    def picked(self):
        """Back from Details: the ticks changed what the update fetches."""
        self.pics = picture_list(self.app.root, self.plan)

    def start_run(self):
        st = self.app.state
        back = set(e["id"] for e in self.plan.downloads) & st.removed
        if back:  # ticked again: no longer removed
            st.removed -= back
            st.save()
        if self.mid is not None:
            self.mid.group.hidden = True
        self.mode = "run"
        self.stats = {"new": 0, "updated": 0, "pictures": 0, "failed": [], "index": False}
        self.work = job(self.app.root, self.plan, self.app.updater, self.stats)
        self.t0 = time.monotonic()
        self._show()
        self.app.refresh()

    def advance(self, now):
        end = now + self.STEP_S
        status = None
        try:
            while time.monotonic() < end and not self.stopping:
                status = next(self.work)
        except StopIteration:
            self.finish()
            return
        except Exception as e:  # pylint: disable=broad-except  # the network went away
            print("update: stopped: %r" % e)
            self.stats["failed"].append("network")
            self.finish()
            return
        if self.stopping:
            self.finish()
            return
        if status is not None:
            phase, done, total, name = status
            self.phase.set(phase)
            self.sub.set(C.ellipsize(name, lambda s: ui.width(ui.BODY, s), L.W - 24))
            self._bar(done, total)
            if phase == "Downloading":
                self.info.set("%.1f of %.1f MB" % (done / 1e6, total / 1e6))
            else:
                self.info.set("%d of %d" % (done + 1, total))
        if now - self.last_draw >= 0.5:
            self.last_draw = now
            self.app.refresh()

    def finish(self):
        work, self.work = self.work, None
        if work is not None:
            try:
                work.close()  # closes an open download
            except Exception:  # pylint: disable=broad-except
                pass
        if not self.stats["index"]:  # stopped: the list, without a new date
            try:
                K.write_index(self.app.root)
            except OSError as e:
                print("update: index: %r" % e)
        self.mode = "done"
        self._bar(1, 1, ui.WARN if (self.stopping or self.stats["failed"]) else ui.OK)
        self.phase.set("Done" if not self.stopping else "Stopped")
        s = int(time.monotonic() - self.t0)
        self.info.set("Took %d:%02d" % (s // 60, s % 60))
        self._show()
        self.app.refresh()


class PlanScreen:
    """The plan's firmwares, from Details on the Update screen: the new ones
    first, then the updated ones with the version on the card and the new
    one. Each has a tick box (a tap anywhere on the line toggles it); unticked
    ones aren't downloaded. Info at a line's right end shows that firmware's
    description (plan_info). The genre button (as on the list) shows
    one genre at a time, and All and None tick or untick the lines it shows.
    done() runs on Back when the ticks changed."""

    ROW_H, PITCH, TOP = 24, 24, 40
    BOX = 14  # the tick box
    INFO_W = 40  # the Info button

    def __init__(self, app, plan, done=None):
        from fm1ui.settings import _Paged
        self.app = app
        self.plan = plan
        self.done = done
        self.changed_ticks = False
        self.group = None
        self.page = 0
        self.tag = None  # a genre, or None for all
        rows = []
        counts = {}
        name = lambda e: (e.get("name") or e["id"]).lower()  # noqa: E731
        for e in sorted(plan.new, key=name) + sorted(plan.changed, key=name):
            if e in plan.new:
                change, color = "new  " + str(e.get("version", "")), ui.OK
            else:
                old = (K.read_meta(app.root + "/" + e["id"]) or {}).get("version")
                new = str(e.get("version", ""))
                change = "%s, new build" % new if old == new else "%s > %s" % (old or "?", new)
                color = ui.DIM
            kind = e.get("kind")
            tags = kind if isinstance(kind, list) else [kind] if kind else []
            for t in tags:
                counts[t] = counts.get(t, 0) + 1
            rows.append((e["id"], e.get("name") or e["id"], change, color, tags))
        self.rows = rows
        self.by_id = dict((e["id"], e) for e in plan.offered)
        self.tags = [t for t, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]
        self._paged = _Paged  # its page arrows, borrowed

    def release(self):
        self.group = None

    def per_page(self):
        return max(1, (L.H - 36 - self.TOP) // self.PITCH)

    def build(self):
        from fm1ui.screens import tag_label
        W = L.W
        g = displayio.Group()
        g.append(ui.rect(0, 0, W, L.H, ui.BG))
        bx, by, bw, bh = L.BACK_BTN
        self.back = ui.Button("Back", bx, by, bw, bh)
        g.append(self.back.group)
        w = 48
        self.none_btn = ui.Button("None", W - bx - w, by, w, bh)
        self.all_btn = ui.Button("All", W - bx - 2 * w - 6, by, w, bh)
        g.append(self.all_btn.group)
        g.append(self.none_btn.group)
        tx = bx + bw + 6
        tag_color = ui.kind_color(self.tag) if self.tag else ui.CYAN
        self.tag_btn = ui.Button(
            tag_label(self.tag) if self.tag else "All Types",
            tx,
            by,
            min(120, self.all_btn.rect[0] - 6 - tx),
            bh,
            edge=tag_color,
            color=tag_color if self.tag else ui.FG,
        )
        g.append(self.tag_btn.group)
        rows = self.visible()
        self._paged.arrows(self, g, len(rows))
        per = self.per_page()
        skip, box = self.plan.skip, self.BOX
        self.shown = []  # (id, rect)
        self.infos = []  # (id, its Info button)
        for i, (cid, label, change, color, _) in enumerate(C.page_slice(rows, self.page, per)):
            y = self.TOP + i * self.PITCH
            if i:
                g.append(ui.rect(12, y, W - 24, 1, ui.LINE))  # a hairline between lines
            on = cid not in skip
            cy = y + (self.ROW_H - box) // 2 + 1
            g.append(ui.outlined(12, cy, box, box, ui.BG, ui.CYAN if on else ui.LINE, cut=0))
            if on:
                g.append(ui.rect(15, cy + 3, box - 6, box - 6, ui.CYAN))
            left = 12 + box + 8
            ix = W - 12 - self.INFO_W
            info = ui.Button("Info", ix, y + 3, self.INFO_W, self.ROW_H - 4, name=ui.SMALL)
            g.append(info.group)
            right = ix - 8  # the change ends here
            room = right - left
            change = C.ellipsize(change, lambda s: ui.width(ui.SMALL, s), room // 2)
            cw = ui.width(ui.SMALL, change)
            g.append(
                ui.text(
                    ui.NAME,
                    C.ellipsize(label, lambda s: ui.width(ui.NAME, s), room - cw - 10),
                    ui.FG if on else ui.DIM,
                    left,
                    y + self.ROW_H // 2,
                    (0, 0.5),
                )
            )
            g.append(
                ui.text(
                    ui.SMALL, change, color if on else ui.LINE, right, y + self.ROW_H // 2, (1, 0.5)
                )
            )
            self.infos.append((cid, info))
            self.shown.append((cid, (0, y, W, self.PITCH)))
        n = len(self.rows)
        parts = ["%d of %d ticked" % (n - len(skip), n)]
        if self.pages > 1:
            parts.append("%d/%d" % (self.page + 1, self.pages))
        g.append(ui.text(ui.SMALL, "  ".join(parts), ui.FG, W // 2, L.H - 18, (0.5, 0.5)))
        self.group = g
        return g

    def visible(self):
        """The lines the genre button shows."""
        if self.tag is None:
            return self.rows
        return [r for r in self.rows if self.tag in r[4]]

    def next_tag(self):
        """All -> each genre, most common first -> All."""
        i = self.tags.index(self.tag) + 1 if self.tag in self.tags else 0
        return self.tags[i] if i < len(self.tags) else None

    def _info_at(self, x, y):
        """The Info button a tap is on: its width and a few px to its left,
        the row's height (the rows are close together)."""
        for cid, b in self.infos:
            bx, by, _, bh = b.rect
            if bx - 6 <= x and by - 3 <= y < by + bh + 1:
                return cid, b
        return None, None

    def _row_at(self, x, y):
        for cid, (rx, ry, rw, rh) in self.shown:
            if rx <= x < rx + rw and ry <= y < ry + rh:
                return cid
        return None

    def target(self, x, y):
        b = self._button_at(x, y)
        if b is not None:
            return b.group
        a = self._paged.arrow_at(self, x, y)
        if a:
            return self.prev_g if a < 0 else self.next_g
        _, info = self._info_at(x, y)
        if info is not None:
            return info.group
        return None  # a line: its box changing is the feedback

    def _button_at(self, x, y):
        """Back, the genre, All or None: the one the tap is on, else the nearest
        within a fingertip's slack."""
        for slack in (0, 10):
            for b in (self.back, self.tag_btn, self.all_btn, self.none_btn):
                if b.hit(x, y, slack):
                    return b
        return None

    def _tick(self, skip):
        self.plan.skip = skip
        self.changed_ticks = True
        self.app.show()

    def tap(self, x, y):
        b = self._button_at(x, y)
        if b is self.back:
            if self.changed_ticks and self.done:
                self.done()
            self.app.pop()
        elif b is self.tag_btn:
            self.tag = self.next_tag()
            self.page = 0
            self.app.show()
        elif b is self.all_btn:  # the lines shown: this genre, or every one
            self._tick(self.plan.skip - set(r[0] for r in self.visible()))
        elif b is self.none_btn:
            self._tick(self.plan.skip | set(r[0] for r in self.visible()))
        else:
            a = self._paged.arrow_at(self, x, y)
            if a:
                self._paged.turn(self, a)
                return
            cid, info = self._info_at(x, y)
            if info is not None:
                self.app.push(plan_info(self.app, self.by_id[cid]))
                return
            cid = self._row_at(x, y)
            if cid is not None:
                skip = set(self.plan.skip)
                if cid in skip:
                    skip.remove(cid)
                else:
                    skip.add(cid)
                self._tick(skip)

    def swipe(self, dx):
        if dx < 0:
            self._paged.turn(self, 1)
        elif dx > 0:
            self._paged.turn(self, -1)

    def tick(self, now):
        pass

    def fm1_changed(self):
        pass




def plan_info(app, e):
    """One firmware from Update > Details, as the hub's catalogue describes
    it (it may not be on the card yet): name, author, version, types and the
    description, on a TextScreen (Back returns)."""
    from fm1ui.settings import TextScreen
    kind = e.get("kind")
    tags = kind if isinstance(kind, list) else [kind] if kind else []
    size = e.get("size")
    info = "  ".join(s for s in (C.version_label(str(e.get("version") or "")), e.get("product"),
                                 "%d KB" % (size // 1024) if size else "",
                                 ", ".join(tags), "beta" if e.get("beta") else "") if s)
    items = []
    if e.get("author"):
        items.append((ui.BODY, "by " + e["author"], ui.DIM))
    items.append((ui.SMALL, info, ui.DIM))
    items.append((ui.BODY, C.plain(e.get("what") or "No description."), ui.TEXT))
    return TextScreen(app, e.get("name") or e["id"], items)
