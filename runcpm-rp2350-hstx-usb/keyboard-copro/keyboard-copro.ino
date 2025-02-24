// SPDX-FileCopyrightText: 2023 Jeff Epler for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// pio-usb is required for rp2040 host
#include "pio_usb.h"
#include "Adafruit_TinyUSB.h"
#include "pico/stdlib.h"
#include "Adafruit_dvhstx.h"

DVHSTXText3 display(DVHSTX_PINOUT_DEFAULT);

// Pin D+ for host, D- = D+ + 1
#ifndef PIN_USB_HOST_DP
#define PIN_USB_HOST_DP       16
#endif

// Pin for enabling Host VBUS. comment out if not used
#ifndef PIN_5V_EN
#define PIN_5V_EN        18
#endif

#ifndef PIN_5V_EN_STATE
#define PIN_5V_EN_STATE  1
#endif

// USB Host object
Adafruit_USBH_Host USBHost;

// Serial output for RunCPM
SerialPIO pio_serial(1 /* RX of the sibling board */, SerialPIO::NOPIN);

void setup() {
// ensure text generation interrupt takes place on core0
display.begin();
display.println("Hello hstx\n");
}

void loop() {
}

void setup1() {
while(!display) ; 
delay(10);
display.println("Hello hstx in setup1\n");
  // override tools menu CPU frequency setting
  //set_sys_clock_khz(264'000, true);

Serial.begin(115200);
#if 0
  while ( !Serial ) delay(10);   // wait for native usb
  Serial.println("Core1 setup to run TinyUSB host with pio-usb");
#endif

#ifdef PIN_5V_EN
  pinMode(PIN_5V_EN, OUTPUT);
  digitalWrite(PIN_5V_EN, PIN_5V_EN_STATE);
#endif

  pio_usb_configuration_t pio_cfg = PIO_USB_DEFAULT_CONFIG;
  pio_cfg.pin_dp = PIN_USB_HOST_DP;
  pio_cfg.tx_ch      = dma_claim_unused_channel(true);
  dma_channel_unclaim(pio_cfg.tx_ch);

  USBHost.configure_pio_usb(1, &pio_cfg);

  // run host stack on controller (rhport) 1
  // Note: For rp2040 pico-pio-usb, calling USBHost.begin() on core1 will have most of the
  // host bit-banging processing works done in core1 to free up core0 for other works
  USBHost.begin(1);

  // this `begin` is a void function, no way to check for failure!
  pio_serial.begin(115200);
display.println("end of setup1\n");
display.show_cursor();
}

int old_ascii = -1;
uint32_t repeat_timeout;
// this matches Linux default of 500ms to first repeat, 1/20s thereafter
const uint32_t default_repeat_time = 50;
const uint32_t initial_repeat_time = 500;

void send_ascii(uint8_t code, uint32_t repeat_time=default_repeat_time) {
  old_ascii = code;
  repeat_timeout = millis() + repeat_time;
  if (code >= 32 && code < 127) {
    display.printf("%c", code);
  } else {
    display.printf("\\x%02x", code);
  }
  pio_serial.write(code);
}

void loop1()
{
static bool last_serial;
  if (!last_serial && Serial) {
last_serial = true;
Serial.println("Hello host serial");
  }
  uint32_t now = millis();
  uint32_t deadline = repeat_timeout - now;
  if (old_ascii >= 0 && deadline > INT32_MAX) {
    send_ascii(old_ascii);
    deadline = repeat_timeout - now;
  } else if (old_ascii < 0) {
    deadline = UINT32_MAX;
  }
  tuh_task_ext(deadline, false);
}

// Invoked when device with hid interface is mounted
// Report descriptor is also available for use.
// tuh_hid_parse_report_descriptor() can be used to parse common/simple enough
// descriptor. Note: if report descriptor length > CFG_TUH_ENUMERATION_BUFSIZE,
// it will be skipped therefore report_desc = NULL, desc_len = 0
void tuh_hid_mount_cb(uint8_t dev_addr, uint8_t instance, uint8_t const *desc_report, uint16_t desc_len) {
  (void)desc_report;
  (void)desc_len;
  uint16_t vid, pid;
  tuh_vid_pid_get(dev_addr, &vid, &pid);

  Serial.printf("HID device address = %d, instance = %d is mounted\r\n", dev_addr, instance);
  Serial.printf("VID = %04x, PID = %04x\r\n", vid, pid);

  uint8_t const itf_protocol = tuh_hid_interface_protocol(dev_addr, instance);
  if (itf_protocol == HID_ITF_PROTOCOL_KEYBOARD) {
    Serial.printf("HID Keyboard\r\n");
    if (!tuh_hid_receive_report(dev_addr, instance)) {
      Serial.printf("Error: cannot request to receive report\r\n");
    }
  }
}

// Invoked when device with hid interface is un-mounted
void tuh_hid_umount_cb(uint8_t dev_addr, uint8_t instance) {
  Serial.printf("HID device address = %d, instance = %d is unmounted\r\n", dev_addr, instance);
}

#define FLAG_ALPHABETIC (1)
#define FLAG_SHIFT (2)
#define FLAG_NUMLOCK (4)
#define FLAG_CTRL (8)
#define FLAG_LUT (16)

const char * const lut[] = {
  "!@#$%^&*()",                              /* 0 - shifted numeric keys */
  "\r\x1b\10\t -=[]\\#;'`,./",               /* 1 - symbol keys */
  "\n\x1b\177\t _+{}|~:\"~<>?",              /* 2 - shifted */
  "\12\13\10\22",                            /* 3 - arrow keys RLDU */
  "/*-+\n1234567890.",                       /* 4 - keypad w/numlock */
  "/*-+\n\xff\2\xff\4\xff\3\xff\1\xff\xff.", /* 5 - keypad w/o numlock */
};

struct keycode_mapper {
  uint8_t first, last, code, flags;
} keycode_to_ascii[] = {
  { HID_KEY_A, HID_KEY_Z, 'a', FLAG_ALPHABETIC, },

  { HID_KEY_1, HID_KEY_9, 0, FLAG_SHIFT | FLAG_LUT, },
  { HID_KEY_1, HID_KEY_9, '1', 0, },
  { HID_KEY_0, HID_KEY_0, ')', FLAG_SHIFT, },
  { HID_KEY_0, HID_KEY_0, '0', 0, },

  { HID_KEY_ENTER, HID_KEY_ENTER, '\n', FLAG_CTRL },
  { HID_KEY_ENTER, HID_KEY_SLASH, 2, FLAG_SHIFT | FLAG_LUT, },
  { HID_KEY_ENTER, HID_KEY_SLASH, 1, FLAG_LUT, },

  { HID_KEY_F1, HID_KEY_F1, 0x1e, 0, }, // help key on xerox 820 kbd

  { HID_KEY_ARROW_RIGHT, HID_KEY_ARROW_UP, 3, FLAG_LUT },

  { HID_KEY_KEYPAD_DIVIDE, HID_KEY_KEYPAD_DECIMAL, 4, FLAG_NUMLOCK | FLAG_LUT },
  { HID_KEY_KEYPAD_DIVIDE, HID_KEY_KEYPAD_DECIMAL, 5, FLAG_LUT },
};


bool report_contains(const hid_keyboard_report_t &report, uint8_t key) {
  for (int i = 0; i < 6; i++) {
    if (report.keycode[i] == key) return true;
  }
  return false;
}

hid_keyboard_report_t old_report;

static bool caps, num;
static uint8_t old_leds;
void process_event(uint8_t dev_addr, uint8_t instance, const hid_keyboard_report_t &report) {
  bool alt = report.modifier & 0x44;
  bool shift = report.modifier & 0x22;
  bool ctrl = report.modifier & 0x11;
  uint8_t code = 0;

  if (report.keycode[0] == 1 && report.keycode[1] == 1) {
    // keyboard says it has exceeded max kro
    return;
  }

  // something was pressed or release, so cancel any key repeat
  old_ascii = -1;

  for (auto keycode : report.keycode) {
    if (keycode == 0) continue;
    if (report_contains(old_report, keycode)) continue;

    /* key is newly pressed */
    if (keycode == HID_KEY_NUM_LOCK) {
        Serial.println("toggle numlock");
      num = !num;
    } else if (keycode == HID_KEY_CAPS_LOCK) {
        Serial.println("toggle capslock");
      caps = !caps;
    } else {
      for (const auto &mapper : keycode_to_ascii) {
        if (!(keycode >= mapper.first && keycode <= mapper.last))
          continue;
        if (mapper.flags & FLAG_SHIFT && !shift)
          continue;
        if (mapper.flags & FLAG_NUMLOCK && !num)
          continue;
        if (mapper.flags & FLAG_CTRL && !ctrl)
          continue;
        if (mapper.flags & FLAG_LUT) {
          code = lut[mapper.code][keycode - mapper.first];
        } else {
          code = keycode - mapper.first + mapper.code;
        }
        if (mapper.flags & FLAG_ALPHABETIC) {
          if (shift ^ caps) {
            code ^= ('a' ^ 'A');
          }
        }
        if (ctrl) code &= 0x1f;
        if (alt) code ^= 0x80;
        send_ascii(code, initial_repeat_time);
        break;
      }
    }
  }

  uint8_t leds = (caps << 1) | num;
  if (leds != old_leds) {
    old_leds = leds;
    Serial.printf("Send LEDs report %d (dev:instance = %d:%d)\r\n", leds, dev_addr, instance);
    // no worky
    auto r = tuh_hid_set_report(dev_addr, instance/*idx*/, 0/*report_id*/, HID_REPORT_TYPE_OUTPUT/*report_type*/, &old_leds, sizeof(old_leds));
    Serial.printf("set_report() -> %d\n", (int)r);
  }
  old_report = report;
}

// Invoked when received report from device via interrupt endpoint
void tuh_hid_report_received_cb(uint8_t dev_addr, uint8_t instance, uint8_t const *report, uint16_t len) {
  if ( len != sizeof(hid_keyboard_report_t) ) {
    Serial.printf("report len = %u NOT 8, probably something wrong !!\r\n", len);
  } else {
    process_event(dev_addr, instance, *(hid_keyboard_report_t*)report);
  }
  // continue to request to receive report
  if (!tuh_hid_receive_report(dev_addr, instance)) {
    Serial.printf("Error: cannot request to receive report\r\n");
  }
}
