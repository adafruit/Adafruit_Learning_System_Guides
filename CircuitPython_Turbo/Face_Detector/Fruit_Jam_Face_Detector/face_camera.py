# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""MJPEG camera session built on adafruit_usb_host_camera"""

import time

import adafruit_usb_host_camera
import displayio
import jpegio


class CameraSession:
    """One streaming session. ``bitmap`` holds the newest decoded frame"""

    def __init__(self, mode_width=320, mode_height=240, scale=1,
                 read_timeout_ms=5, stale_seconds=5):
        if (isinstance(read_timeout_ms, bool) or not isinstance(read_timeout_ms, int)
                or not 1 <= read_timeout_ms <= 100):
            raise ValueError("read timeout must be 1..100 ms")
        if not 1 <= stale_seconds <= 120:
            raise ValueError("stale deadline must be 1..120 seconds")
        if scale not in (0, 1, 2, 3):
            raise ValueError("scale must be 0..3 (1, 1/2, 1/4 or 1/8 size)")
        self.closed = self.valid = False
        self.mode = None
        self._camera = None
        self.mode_width, self.mode_height = mode_width, mode_height
        self.scale = scale
        self.width = mode_width >> scale
        self.height = mode_height >> scale
        self._timeout = read_timeout_ms / 1000
        self._stale_ns = int(stale_seconds * 1_000_000_000)
        self._decode_errors_in_row = 0
        self._stats = {
            "polls": 0,
            "frames": 0,
            "no_frame_yet": 0,
            "decode_errors": 0,
            "max_poll_ns": 0,
            "max_decode_ns": 0,
        }
        # Raises ValueError when no UVC camera is attached.
        self._camera = adafruit_usb_host_camera.UVCCamera()
        try:
            mode = self._camera.find_mode(mode_width, mode_height,
                                          adafruit_usb_host_camera.FORMAT_MJPEG)
            if mode is None or (mode.width, mode.height) != (mode_width, mode_height):
                raise ValueError(
                    f"camera has no {mode_width}x{mode_height} MJPEG mode (closest: {mode})"
                )
            self._camera.start(mode)
            self.mode = mode
            self.bitmap = displayio.Bitmap(self.width, self.height, 65536)
            self._decoder = jpegio.JpegDecoder()
        except BaseException:
            self.close()
            raise
        self._started_ns = self._last_frame_ns = time.monotonic_ns()

    def poll(self):
        """Take in whatever code.py has buffered. Returns True when a new
        frame was decoded into ``bitmap``; False when none is complete yet."""
        if self.closed:
            raise RuntimeError("camera closed")
        start = time.monotonic_ns()
        if start - self._last_frame_ns >= self._stale_ns:
            self.close()
            raise RuntimeError("camera stale: no frame for too long")
        self._stats["polls"] += 1
        try:
            frame = self._camera.capture(timeout=self._timeout)
        except RuntimeError:
            self._stats["no_frame_yet"] += 1
            return False
        finally:
            elapsed = time.monotonic_ns() - start
            self._stats["max_poll_ns"] = max(self._stats["max_poll_ns"], elapsed)

        try:
            started = time.monotonic_ns()
            jpeg = self._camera.add_huffman_tables(frame)
            if self._decoder.open(jpeg) != (self.mode_width, self.mode_height):
                raise ValueError("unexpected JPEG dimensions")
            self._decoder.decode(self.bitmap, scale=self.scale)
            decoded = time.monotonic_ns()
            self._stats["max_decode_ns"] = max(self._stats["max_decode_ns"], decoded - started)
        except (RuntimeError, ValueError, OSError) as error:
            self._stats["decode_errors"] += 1
            self._decode_errors_in_row += 1
            self.valid = False
            if self._decode_errors_in_row >= 5:
                self.close()
                raise RuntimeError("repeated camera decode failure") from error
            return False
        self._decode_errors_in_row = 0
        self.valid = True
        self._last_frame_ns = decoded
        self._stats["frames"] += 1
        return True

    def snapshot(self):
        """Counters for the serial report."""
        result = dict(self._stats)
        camera = self._camera
        lost = camera.lost_packets if camera else 0
        bad = camera.dropped_frames if camera else 0
        result.update(
            {
                "valid": self.valid,
                "closed": self.closed,
                "mode": repr(self.mode),
                "partial_frames_dropped": lost + bad,
                "lost_packets": lost,
                "invalid_frames": bad,
                "read_errors": camera.read_errors if camera else 0,
                "elapsed_ns": time.monotonic_ns() - self._started_ns,
            }
        )
        return result

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.valid = False
        camera = self._camera
        if camera is not None:
            try:
                camera.stop()
            except (OSError, RuntimeError):
                pass
