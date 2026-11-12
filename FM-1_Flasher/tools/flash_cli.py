#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 John Park for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-only
"""Desktop FM-1 flasher over USB-MIDI (python-rtmidi): the reference for the
CircuitPython device, run from a computer where problems are easy to see.

  flash_cli.py ports                list MIDI ports and which ones would be probed
  flash_cli.py probe                identity (cmd 17) and capability (cmd 49); writes nothing
  flash_cli.py install DIR          install the firmware in DIR (a make_sd.py folder:
                                    meta.json + .fwsc); --dry-run connects and reports
                                    the route without writing anything

Every install writes a log of each read request to logs/install-*.jsonl.
"""

import argparse
import json
import os
import queue
import re
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "FM-1_Flasher_Code", "lib"))
import fm1proto as P  # noqa: E402
import fm1update as U  # noqa: E402

try:
    import rtmidi
except ImportError:
    sys.exit("needs python-rtmidi: .venv/bin/pip install python-rtmidi")

# The Firmware Hub's list of names the FM-1 shows up under, in app and loader
# mode, on macOS, Windows, and Linux ("USB Composite Device" for stock V15).
FM1_PORT = re.compile(r"fm-1|felucca|sloop|clipper|etch|jiant|ota|update|composite|sinco|usb-midi", re.I)


def candidate_pairs(pattern=FM1_PORT):
    """(name, in_index, out_index) for each FM-1-looking port with a same-named output."""
    ins = rtmidi.MidiIn().get_ports()
    outs = rtmidi.MidiOut().get_ports()
    pairs = []
    for i, name in enumerate(ins):
        if not pattern.search(name):
            continue
        same = [j for j, o in enumerate(outs) if o == name]
        if len(same) == 1:
            pairs.append((name, i, same[0]))
    return pairs


class RtMidiTransport:
    """fm1update transport over a python-rtmidi input/output pair."""

    def __init__(self, name, in_index, out_index, log=None):
        self.name = name
        self.q = queue.Queue()
        self.log = log
        self.closed = False
        self._checked = 0
        self._lost = False
        self.mi = rtmidi.MidiIn()
        self.mi.ignore_types(sysex=False, timing=True, active_sense=True)
        self.mi.set_callback(self._on_message)
        self.mi.open_port(in_index)
        self.mo = rtmidi.MidiOut()
        self.mo.open_port(out_index)

    def _on_message(self, event, data=None):
        msg, _ = event
        if msg and msg[0] == 0xF0:
            if self.log:
                self.log("<-", msg)
            self.q.put(bytes(msg))

    @property
    def lost(self):
        if self.closed or self._lost:
            return True
        now = time.monotonic()
        if now - self._checked > 0.25:
            self._checked = now
            self._lost = self.name not in rtmidi.MidiIn().get_ports()
        return self._lost

    def send(self, sysex):
        if self.log:
            self.log("->", sysex)
        self.mo.send_message(list(sysex))

    def recv(self, timeout_ms):
        try:
            if timeout_ms <= 0:
                return self.q.get_nowait()
            return self.q.get(timeout=timeout_ms / 1000)
        except queue.Empty:
            return None

    def close(self):
        if not self.closed:
            self.closed = True
            self.mi.cancel_callback()
            self.mi.close_port()
            self.mo.close_port()


def make_log(verbose):
    if not verbose:
        return None

    def log(direction, msg):
        b = bytes(msg)
        text = b.hex(" ") if len(b) <= 24 else b[:16].hex(" ") + " … (%d bytes)" % len(b)
        p = P.parse(b)
        extra = "  cmd %d, %d data bytes" % (p[0], len(p[1])) if p else ""
        print("  %s %s%s" % (direction, text, extra))
    return log


def cmd_ports(args):
    ins = rtmidi.MidiIn().get_ports()
    outs = rtmidi.MidiOut().get_ports()
    print("inputs: ", ins)
    print("outputs:", outs)
    print("would probe:", [p[0] for p in candidate_pairs()] or "none")


def cmd_probe(args):
    pairs = candidate_pairs()
    if not pairs:
        sys.exit("no FM-1-looking MIDI port; is it on and plugged in? (try: flash_cli.py ports)")
    clock = U.Clock()
    for name, i, o in pairs:
        print("port:", name)
        t = RtMidiTransport(name, i, o, make_log(args.verbose))
        link = U.Link(t, clock)
        try:
            reply = None
            for attempt in range(2):
                try:
                    reply = link.query(P.CMD_IDENTITY, ms=750)
                    break
                except U.FM1Timeout:
                    if attempt:
                        raise
            ident = P.identity(reply)
            print("  identity (cmd 17):   %s" % ident)
            kind = ("loader" if P.is_loader(ident) else "stock V15" if ident == P.STOCK_PRODUCT
                    else "FM1 Open" if P.open_identity(ident)
                    else "community" if P.community_identity(ident) else "unknown")
            print("  identity kind:       %s" % kind)
            try:
                started = time.monotonic()
                cap = P.capability(link.query(P.CMD_CAPABILITY))
                print("  capability (cmd 49): family %d, state %d, build %s (%.0f ms)" % (
                    cap["family"], cap["state"], cap["build"], (time.monotonic() - started) * 1000))
            except U.FM1Timeout:
                print("  capability (cmd 49): no reply (expected for stock and community firmwares)")
        except U.FM1Timeout:
            print("  no reply to cmd 17")
        except P.FM1Error as e:
            print("  error:", e)
        finally:
            link.close()


def spans(reads):
    """Coalesce (address, n) reads into contiguous [start, end) spans."""
    out = []
    for a, n in sorted(reads):
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], a + n)
        else:
            out.append([a, a + n])
    return out


def cmd_install(args):
    meta_path = os.path.join(args.dir, "meta.json") if os.path.isdir(args.dir) else args.dir
    meta = json.load(open(meta_path))
    f = open(os.path.join(os.path.dirname(meta_path), meta["file"]), "rb")
    pkg, meta = P.prepare(meta, f, verify=True)
    print("package:  %s %s (%s), %d bytes, %s route, loader %s" % (
        meta.get("name", meta["product"]), meta.get("version", ""), meta["product"], meta["bytes"],
        meta.get("kind"), meta["loader_identity"]))

    os.makedirs(args.log_dir, exist_ok=True)
    log_path = os.path.join(args.log_dir, "install-%s-%s.jsonl" % (time.strftime("%Y%m%d-%H%M%S"), meta["product"]))
    logf = open(log_path, "w")
    t0 = time.monotonic()
    state = {"phase": None, "pct": -10, "reads": {}}

    def record(event, *values):
        logf.write(json.dumps({"t": round(time.monotonic() - t0, 3), "event": event, "values": values}) + "\n")
        logf.flush()

    def trace(event, *values):
        record(event, *values)
        if event == "read":
            state["reads"].setdefault(state["phase"], []).append(values)
        elif event == "found":
            print("  found: %s" % values[0])

    def status(phase, pct):
        if phase != state["phase"]:
            state["phase"] = phase
            state["pct"] = -10
            record("phase", phase)
            print("%s ..." % phase)
        if pct >= state["pct"] + 10 or pct == 100:
            state["pct"] = pct
            print("  %3d%%  (%.1f s)" % (pct, time.monotonic() - t0))

    def finder():
        found = []
        for name, i, o in candidate_pairs():
            try:
                found.append(RtMidiTransport(name, i, o, make_log(args.verbose)))
            except Exception as e:  # a port that vanished while re-enumerating
                record("open-failed", name, str(e))
        return found

    up = U.Updater(finder, pkg, meta, status=status)
    up.trace = trace
    info = up.connect(force=args.force)
    record("connect", info, up.mode)
    print("device:   %s, mode: %s" % (info["identity"], up.mode))
    if info.get("migration"):
        up.disconnect()
        sys.exit("this replaces %s with a different firmware family: rerun with --force to confirm"
                 % info["identity"])
    if info.get("same"):
        print("note:     the device already runs %s" % meta["product"])
    if args.dry_run:
        up.disconnect()
        print("dry run: nothing was sent beyond identity/capability queries")
        return
    if not args.yes:
        print("Keep both devices powered until this finishes. Interrupting a write can leave the FM-1")
        print("unbootable (rescue: the Pico Transporter, see PLAN.md).")
        if input("Type INSTALL to write %s to the FM-1: " % meta["product"]).strip() != "INSTALL":
            up.disconnect()
            sys.exit("canceled; nothing was written")
    try:
        up.install(force=args.force)
    except P.FM1Error as e:
        record("error", str(e))
        print("FAILED: %s" % e)
        print("log: %s" % log_path)
        sys.exit(1)
    finally:
        for phase, reads in state["reads"].items():
            sp = spans(reads)
            sizes = sorted({n for _, n in reads})
            record("summary", phase, len(reads), sp, sizes)
            print("%s: %d requests, sizes %s, spans %s" % (
                phase, len(reads), sizes, ", ".join("0x%x-0x%x" % (a, b) for a, b in sp)))
        logf.close()
    print("installed %s in %.0f s; log: %s" % (meta["product"], time.monotonic() - t0, log_path))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-v", "--verbose", action="store_true", help="print every SysEx message")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ports").set_defaults(fn=cmd_ports)
    sub.add_parser("probe").set_defaults(fn=cmd_probe)
    ins = sub.add_parser("install")
    ins.add_argument("dir", help="firmware folder (meta.json + .fwsc) or a meta.json")
    ins.add_argument("--dry-run", action="store_true", help="connect and report the route; write nothing")
    ins.add_argument("--force", action="store_true", help="allow a migration (leaving stock, or another family)")
    ins.add_argument("--yes", action="store_true", help="skip the typed confirmation")
    ins.add_argument("--log-dir", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs"))
    ins.set_defaults(fn=cmd_install)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
