// SPDX-FileCopyrightText: 2019 Phillip Burgess for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// Very infrequently the jobStatus member in Adafruit_ZeroDMA gets out of
// sync and the screen DMA updates lock up. This is a hacky workaround.
// jobStatus is a protected member of Adafruit_ZeroDMA, we can't reset it
// directly in the sketch, but a subclass can. So we have this minimal
// subclass with a DMA-channel-toggle-off-on-and-jobStatus-reset function.

class DMAbuddy : public Adafruit_ZeroDMA {
 public:
  // Call this function when a DMA stall is detected:
  void fix(void) {
    // We literally just switch the channel off and on again to fix it...
    DMAC->Channel[channel].CHCTRLA.bit.ENABLE = 0; // Disable channel
    DMAC->Channel[channel].CHCTRLA.bit.ENABLE = 1; // Enable channel
    jobStatus = DMA_STATUS_OK; // Back in business!
  }
};
