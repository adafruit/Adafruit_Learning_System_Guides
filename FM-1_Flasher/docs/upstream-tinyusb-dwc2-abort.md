# TinyUSB issue: posted as hathach/tinyusb#4405 (Nov 2, 2026)

**Title:** dwc2 host (DMA): aborting a running bulk IN doesn't stop it; it later completes with the next data

**Body:**

On an ESP32-P4 (Adafruit Metro ESP32-P4, DWC2 high-speed core, host DMA on, as CircuitPython builds it), a bulk IN transfer that's aborted while the device is NAKing keeps running. It later completes with the device's next data and reports that as a normal completion, so the next transfer on the device gets the wrong result.

**Seen from CircuitPython** (`usb.core`, which calls `tuh_edpt_abort_xfer()` when a read times out), with a full-speed USB-MIDI device on the USB-A port. The script sends a query and reads with a 3 s timeout, five rounds. On a fresh connection:

```
round 0: write 16 of 16 bytes
  read 56 after 0.001 s: <reply>
  read timeout after 3.000 s        <- aborted while the device NAKs
round 1: write 56 of 16 bytes       <- the aborted IN completed with the reply
  read timeout after 3.000 s        <- the reply never reaches this read
round 2: write 56 of 16 bytes
  ...
```

Every round after the first timeout fails the same way until the device is replugged.

**Cause, as far as I can tell** (`src/portable/synopsys/dwc2/hcd_dwc2.c`): for a non-periodic DMA channel, `hcd_edpt_abort_xfer()` calls `channel_disable()` and returns. The resulting halt usually arrives with `HCINT_NAK` set, so `handle_channel_in_dma()` handles it as a NAK and calls `channel_xfer_in_retry()`, which re-arms the IN token. The channel keeps polling, and when the device sends data the transfer completes through `hcd_event_xfer_complete()`. Meanwhile `tuh_edpt_abort_xfer()` has already cleared the endpoint's busy state, and the caller may have freed the buffer the DMA later writes to.

Periodic DMA channels already avoid this: they're marked `aborting`, and `handle_channel_irq()` retires them at the halt with no completion event.

**Fix that works here:** mark a running non-periodic DMA channel `aborting` too before disabling it, and wait (bounded) for the halt to retire it, so the endpoint can take a new transfer and the buffer is no longer in use when the abort returns. With it: 5 of 5 query/timeout rounds answered, 800 back-to-back reads with 1-20 ms timeouts all returned clean timeouts, and full firmware installs (~1,200 SysEx round trips each) ran with no lost replies.

```diff
diff --git a/src/portable/synopsys/dwc2/hcd_dwc2.c b/src/portable/synopsys/dwc2/hcd_dwc2.c
index 09878a2b9..4212ae835 100644
--- a/src/portable/synopsys/dwc2/hcd_dwc2.c
+++ b/src/portable/synopsys/dwc2/hcd_dwc2.c
@@ -949,6 +949,28 @@ bool hcd_edpt_abort_xfer(uint8_t rhport, uint8_t dev_addr, uint8_t ep_addr) {
     }
   }
 
+  // A non-periodic DMA channel (control/bulk) is halted with channel disable. Its halt usually arrives with NAK set,
+  // which handle_channel_in_dma() would retry: the aborted transfer would keep polling and later complete with the
+  // device's next data. Mark it aborting so handle_channel_irq() retires the channel at the halt instead, with no
+  // completion event, as for periodic channels above.
+  if (dma_host_enabled(dwc2)) {
+    const uint8_t ch_id = channel_find_enabled(dwc2, dev_addr, ep_num, ep_dir);
+    if (ch_id < 16) {
+      hcd_xfer_t* xfer = &_hcd_data.xfer[ch_id];
+      edpt->aborting = 1;
+      xfer->aborting = true;
+      channel_disable(dwc2, &dwc2->channel[ch_id]);
+      hcd_int_enable(rhport);
+
+      // Wait for the halt, so the endpoint can take a new transfer and the controller no longer writes to the aborted
+      // transfer's buffer when this returns. It comes within a (micro)frame; give up after ~8 frame-counter ticks.
+      const uint32_t start = dwc2->hfnum & HFNUM_FRNUM_Msk;
+      while (xfer->aborting && (((dwc2->hfnum & HFNUM_FRNUM_Msk) - start) & HCD_FRAME_NUMBER_MASK) < 8) {
+      }
+      return true;
+    }
+  }
+
   hcd_int_enable(rhport);
 
   // Channel disable may wait for request-queue space in slave mode.
```

Open points I'm not sure about:
- Split transactions: the DMA comment in `channel_disable()` says a split channel mustn't be disabled at random. This path only checks for DMA; a split IN behind a high-speed hub may need different handling.
- The busy-wait in `hcd_edpt_abort_xfer()` relies on the channel interrupt running while it spins (it does in CircuitPython, which calls abort from task context).

I can open a PR if this approach looks right.

Environment: TinyUSB at efab607b8 (as pinned by CircuitPython main, Nov 2 2026); upstream master to ed8adb054 has no change in this path. CircuitPython 11.0.0-alpha.2-64 for the Metro ESP32-P4.

---

**CircuitPython cross-reference (adafruit/circuitpython), short:**

**Title:** Metro ESP32-P4: `usb.core` read timeout leaves the transfer running (TinyUSB dwc2 host abort)

On the Metro ESP32-P4, after a `usb.core` `read()` times out on a bulk IN endpoint, the next transfers on the device report wrong results and reads stop completing until a replug. The cause is in TinyUSB's dwc2 host abort: hathach/tinyusb#4405. Note that `_handle_timed_transfer_callback()` frees the bounce buffer after `tuh_edpt_abort_xfer()` returns true, which with this bug can leave DMA writing into freed memory.
