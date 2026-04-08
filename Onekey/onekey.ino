// SPDX-FileCopyrightText: 2026 John Park for Adafruit Industries
//
// SPDX-License-Identifier: MIT
// ============================================================
// One Key: NeoKey BFF — Single-Key BLE HID Keyboard
//  
// User editable w serial (or WebSerial webpage)
// setting stored in NVS (non-volatile storage)
//
// Hardware: Adafruit QT Py ESP32 (Pico V3-02) + NeoKey BFF + Lipo Charger BFF
//   Button      : pin A2 (INPUT_PULLUP, LOW = pressed)
//   Key NeoPixel: pin A3 (NeoKey BFF)
//   QT NeoPixel : PIN_NEOPIXEL (onboard QT Py pixel)
//
// NeoPixel status colors:
//   RED             — waiting to connect (not user configurable)
//   BLUE            — going to sleep (not user configurable)
//   GREEN (default) — connected, user configurable via: color:connected:R,G,B
//   PINK  (default) — button pressed, user configurable via: color:pressed:R,G,B
//
// Sleep mode:
//   After sleepMinutes of inactivity the device turns off LEDs
//   and enters deep sleep to save battery. Flip the power switch
//   on the LiPo Charger BFF off and on to wake (full reboot).
//   Default is 10 minutes. To change via Serial Monitor:
//     sleep:10   — set to 10 minutes
//     sleep:0    — disable sleep entirely
//
// Key configuration (Serial Monitor, 115200 baud):
//   Single key       : q
//   Special key      : tab  or  f5  or  return
//   With modifier    : ctrl+z  or  alt+tab  or  shift+f5  or  ctrl+shift+z
//   String           : "hello world"
//   String + key     : "dir"+enter  or  "git status"+return  or  "password"+tab
//   Media key        : volumeup  or  volumedown  or  mute  or  playpause
//                      nexttrack  or  prevtrack  or  stop
//
//   Modifiers : ctrl, shift, alt, gui (gui = Win/Command key)
//   Special keys: tab, return, enter, esc, backspace, delete,
//                 up, down, left, right, f1-f24,
//                 space, home, end, pageup, pagedown, insert
//   Media keys: volumeup, volumedown, mute, playpause,
//               nexttrack, prevtrack, stop
//
// LED configuration (Serial Monitor, 115200 baud):
//   color:connected:0,255,0     — set connected color (default green)
//   color:pressed:255,20,100    — set pressed color (default pink)
//   bright:255                  — set brightness 0-255 (default 255)
//
// Libraries required:
//   - Adafruit NeoPixel         (Library Manager)
//   - sakuls-ESP32-BLE-Keyboard (github.com/sakul-the-one/sakuls-ESP32-BLE-Keyboard)
//
// Board settings (Arduino IDE):
//   Board     : "Adafruit QT Py ESP32-Pico"
//   Partition : "Large SPIFFS"
// ============================================================

#include <BleKeyboard.h>
#include <Adafruit_NeoPixel.h>
#include <Preferences.h>
#include "esp_system.h"

#define NEOPIXEL_PIN          A3
#define BUTTON_PIN            A2
#define DEFAULT_BRIGHT        255
#define DEFAULT_SLEEP_MINUTES 10

BleKeyboard bleKeyboard("ESP32 BLE KB3", "Adafruit", 100);
Adafruit_NeoPixel key_pixel(1, NEOPIXEL_PIN, NEO_GRB + NEO_KHZ800);
Adafruit_NeoPixel qt_pixel(1, PIN_NEOPIXEL, NEO_GRB + NEO_KHZ800);
Preferences prefs;

uint32_t lastActivityMs = 0;
uint8_t  sleepMinutes   = DEFAULT_SLEEP_MINUTES;

// ---- LED color state -----------------------------------
uint8_t bright         = DEFAULT_BRIGHT;
uint8_t connR = 0,   connG = 255, connB = 0;    // connected: green
uint8_t pressR = 255, pressG = 20, pressB = 100; // pressed: pink

// ---- Key combo struct ----------------------------------
// mode: 0 = regular key, 1 = string, 2 = media
struct KeyCombo {
  uint8_t  modifier;   // 0 = none, else KEY_LEFT_CTRL etc.
  uint8_t  modifier2;  // optional second modifier
  uint8_t  key;        // main key (mode 0)
  char     str[64];    // text to type (mode 1)
  uint8_t  strTail;    // optional key after string (mode 1), or 0
  uint8_t  mode;       // 0=regular, 1=string, 2=media
  uint16_t mediaKey;   // packed MediaKeyReport (mode 2)
};

KeyCombo currentCombo = { 0, 0, 'q', "", 0, 0, 0 };

// ---- NeoPixel ------------------------------------------
void setPixels(uint8_t r, uint8_t g, uint8_t b) {
  key_pixel.setPixelColor(0, key_pixel.Color(r, g, b));
  key_pixel.show();
  qt_pixel.setPixelColor(0, qt_pixel.Color(r, g, b));
  qt_pixel.show();
}

void pixelWaiting()   { setPixels(255, 0, 0); }                  // red — not configurable
void pixelConnected() { setPixels(connR, connG, connB); }         // user configurable
void pixelPressed()   { setPixels(pressR, pressG, pressB); }      // user configurable
void pixelYawn()      { setPixels(0, 0, 255); }                   // blue — not configurable

// ---- Sleep ---------------------------------------------
void goToSleep() {
  Serial.println("[SLEEP] Inactivity timeout — going to deep sleep.");
  Serial.println("[SLEEP] Flip power switch to wake.");
  Serial.flush();
  pixelYawn();
  delay(1000);
  setPixels(0, 0, 0);
  digitalWrite(NEOPIXEL_POWER, LOW);
  esp_deep_sleep_start();
}

// ---- NVS -----------------------------------------------
void loadSettings() {
  prefs.begin("neokey", true);
  // Key combo
  currentCombo.modifier  = prefs.getUChar("mod1",      0);
  currentCombo.modifier2 = prefs.getUChar("mod2",      0);
  currentCombo.key       = prefs.getUChar("key",       'q');
  currentCombo.strTail   = prefs.getUChar("tail",      0);
  currentCombo.mode      = prefs.getUChar("mode",      0);
  currentCombo.mediaKey  = prefs.getUShort("mediakey", 0);
  prefs.getString("str", currentCombo.str, sizeof(currentCombo.str));
  // Sleep
  sleepMinutes = prefs.getUChar("sleepmin", DEFAULT_SLEEP_MINUTES);
  // LED
  bright  = prefs.getUChar("bright",  DEFAULT_BRIGHT);
  connR   = prefs.getUChar("conn_r",  0);
  connG   = prefs.getUChar("conn_g",  255);
  connB   = prefs.getUChar("conn_b",  0);
  pressR  = prefs.getUChar("press_r", 255);
  pressG  = prefs.getUChar("press_g", 20);
  pressB  = prefs.getUChar("press_b", 100);
  prefs.end();
}

void saveCombo(const KeyCombo& c) {
  prefs.begin("neokey", false);
  prefs.putUChar("mod1",      c.modifier);
  prefs.putUChar("mod2",      c.modifier2);
  prefs.putUChar("key",       c.key);
  prefs.putUChar("tail",      c.strTail);
  prefs.putUChar("mode",      c.mode);
  prefs.putUShort("mediakey", c.mediaKey);
  prefs.putString("str",      c.str);
  prefs.end();
  memcpy(&currentCombo, &c, sizeof(KeyCombo));
}

void saveSleepMinutes(uint8_t m) {
  prefs.begin("neokey", false);
  prefs.putUChar("sleepmin", m);
  prefs.end();
  sleepMinutes = m;
  if (m == 0)
    Serial.println("[CFG] Sleep disabled.");
  else
    Serial.printf("[CFG] Sleep timeout set to %d minute(s).\n", m);
}

void saveBrightness(uint8_t b) {
  prefs.begin("neokey", false);
  prefs.putUChar("bright", b);
  prefs.end();
  bright = b;
  key_pixel.setBrightness(bright);
  qt_pixel.setBrightness(bright);
  // Re-show current pixel state at new brightness
  key_pixel.show();
  qt_pixel.show();
  Serial.printf("[CFG] Brightness set to %d.\n", b);
}

void saveConnectedColor(uint8_t r, uint8_t g, uint8_t b) {
  prefs.begin("neokey", false);
  prefs.putUChar("conn_r", r);
  prefs.putUChar("conn_g", g);
  prefs.putUChar("conn_b", b);
  prefs.end();
  connR = r; connG = g; connB = b;
  Serial.printf("[CFG] Connected color set to %d,%d,%d.\n", r, g, b);
}

void savePressedColor(uint8_t r, uint8_t g, uint8_t b) {
  prefs.begin("neokey", false);
  prefs.putUChar("press_r", r);
  prefs.putUChar("press_g", g);
  prefs.putUChar("press_b", b);
  prefs.end();
  pressR = r; pressG = g; pressB = b;
  Serial.printf("[CFG] Pressed color set to %d,%d,%d.\n", r, g, b);
}

// ---- Media key helpers ---------------------------------
uint16_t tokenToMediaKey(const String& t) {
  if (t == "volumeup")   return KEY_MEDIA_VOLUME_UP[0]      | (KEY_MEDIA_VOLUME_UP[1] << 8);
  if (t == "volumedown") return KEY_MEDIA_VOLUME_DOWN[0]    | (KEY_MEDIA_VOLUME_DOWN[1] << 8);
  if (t == "mute")       return KEY_MEDIA_MUTE[0]           | (KEY_MEDIA_MUTE[1] << 8);
  if (t == "playpause")  return KEY_MEDIA_PLAY_PAUSE[0]     | (KEY_MEDIA_PLAY_PAUSE[1] << 8);
  if (t == "nexttrack")  return KEY_MEDIA_NEXT_TRACK[0]     | (KEY_MEDIA_NEXT_TRACK[1] << 8);
  if (t == "prevtrack")  return KEY_MEDIA_PREVIOUS_TRACK[0] | (KEY_MEDIA_PREVIOUS_TRACK[1] << 8);
  if (t == "stop")       return KEY_MEDIA_STOP[0]           | (KEY_MEDIA_STOP[1] << 8);
  return 0;
}

void uint16ToMediaKey(uint16_t v, MediaKeyReport& r) {
  r[0] = v & 0xFF;
  r[1] = (v >> 8) & 0xFF;
}

// ---- Token parser helpers ------------------------------
uint8_t tokenToModifier(const String& t) {
  if (t == "ctrl")  return KEY_LEFT_CTRL;
  if (t == "shift") return KEY_LEFT_SHIFT;
  if (t == "alt")   return KEY_LEFT_ALT;
  if (t == "gui")   return KEY_LEFT_GUI;
  if (t == "cmd")   return KEY_LEFT_GUI;
  if (t == "win")   return KEY_LEFT_GUI;
  return 0;
}

uint8_t tokenToKey(const String& t) {
  if (t == "tab")       return KEY_TAB;
  if (t == "return")    return KEY_RETURN;
  if (t == "enter")     return KEY_RETURN;
  if (t == "esc")       return KEY_ESC;
  if (t == "escape")    return KEY_ESC;
  if (t == "backspace") return KEY_BACKSPACE;
  if (t == "delete")    return KEY_DELETE;
  if (t == "up")        return KEY_UP_ARROW;
  if (t == "down")      return KEY_DOWN_ARROW;
  if (t == "left")      return KEY_LEFT_ARROW;
  if (t == "right")     return KEY_RIGHT_ARROW;
  if (t == "space")     return ' ';
  if (t == "home")      return KEY_HOME;
  if (t == "end")       return KEY_END;
  if (t == "pageup")    return KEY_PAGE_UP;
  if (t == "pagedown")  return KEY_PAGE_DOWN;
  if (t == "insert")    return KEY_INSERT;
  if (t.startsWith("f") && t.length() <= 3) {
    int n = t.substring(1).toInt();
    if (n >= 1 && n <= 24) return KEY_F1 + (n - 1);
  }
  if (t.length() == 1 && isprint(t.charAt(0))) return (uint8_t)t.charAt(0);
  return 0;
}

// ---- Print combo ---------------------------------------
void printCombo(const KeyCombo& c) {
  if (c.mode == 2) {  // media
    struct { const char* name; const MediaKeyReport* report; } mediaMap[] = {
      { "volumeup",   &KEY_MEDIA_VOLUME_UP },
      { "volumedown", &KEY_MEDIA_VOLUME_DOWN },
      { "mute",       &KEY_MEDIA_MUTE },
      { "playpause",  &KEY_MEDIA_PLAY_PAUSE },
      { "nexttrack",  &KEY_MEDIA_NEXT_TRACK },
      { "prevtrack",  &KEY_MEDIA_PREVIOUS_TRACK },
      { "stop",       &KEY_MEDIA_STOP },
    };
    String mediaDesc = "media:unknown";
    for (auto& m : mediaMap) {
      uint16_t v = (*m.report)[0] | ((*m.report)[1] << 8);
      if (v == c.mediaKey) { mediaDesc = String("media:") + m.name; break; }
    }
    Serial.printf("[CFG] Current combo: %s\n", mediaDesc.c_str());
    return;
  }
  if (c.mode == 1) {  // string
    String strDesc = "\"" + String(c.str) + "\"";
    if (c.strTail) {
      switch (c.strTail) {
        case KEY_RETURN:  strDesc += "+enter"; break;
        case KEY_TAB:     strDesc += "+tab"; break;
        case KEY_ESC:     strDesc += "+esc"; break;
        default:
          if (isprint(c.strTail)) strDesc += "+" + String((char)c.strTail);
          else strDesc += "+0x" + String(c.strTail, HEX);
          break;
      }
    }
    Serial.printf("[CFG] Current combo: %s\n", strDesc.c_str());
    return;
  }
  // mode 0 — regular key
  String keyDesc = "";
  if (c.modifier  == KEY_LEFT_CTRL)  keyDesc += "ctrl+";
  if (c.modifier  == KEY_LEFT_SHIFT) keyDesc += "shift+";
  if (c.modifier  == KEY_LEFT_ALT)   keyDesc += "alt+";
  if (c.modifier  == KEY_LEFT_GUI)   keyDesc += "gui+";
  if (c.modifier2 == KEY_LEFT_CTRL)  keyDesc += "ctrl+";
  if (c.modifier2 == KEY_LEFT_SHIFT) keyDesc += "shift+";
  if (c.modifier2 == KEY_LEFT_ALT)   keyDesc += "alt+";
  if (c.modifier2 == KEY_LEFT_GUI)   keyDesc += "gui+";
  switch (c.key) {
    case KEY_TAB:         keyDesc += "tab"; break;
    case KEY_RETURN:      keyDesc += "return"; break;
    case KEY_ESC:         keyDesc += "esc"; break;
    case KEY_BACKSPACE:   keyDesc += "backspace"; break;
    case KEY_DELETE:      keyDesc += "delete"; break;
    case KEY_UP_ARROW:    keyDesc += "up"; break;
    case KEY_DOWN_ARROW:  keyDesc += "down"; break;
    case KEY_LEFT_ARROW:  keyDesc += "left"; break;
    case KEY_RIGHT_ARROW: keyDesc += "right"; break;
    case KEY_HOME:        keyDesc += "home"; break;
    case KEY_END:         keyDesc += "end"; break;
    case KEY_PAGE_UP:     keyDesc += "pageup"; break;
    case KEY_PAGE_DOWN:   keyDesc += "pagedown"; break;
    case KEY_INSERT:      keyDesc += "insert"; break;
    default:
      if (c.key >= KEY_F1 && c.key <= KEY_F24)
        keyDesc += "f" + String(c.key - KEY_F1 + 1);
      else if (isprint(c.key))
        keyDesc += (char)c.key;
      else
        keyDesc += "0x" + String(c.key, HEX);
      break;
  }
  Serial.printf("[CFG] Current combo: %s\n", keyDesc.c_str());
}

// ---- Send combo ----------------------------------------
void sendCombo(const KeyCombo& c) {
  if (c.mode == 2) {  // media
    MediaKeyReport r;
    uint16ToMediaKey(c.mediaKey, r);
    bleKeyboard.press(r);
    delay(100);
    bleKeyboard.release(r);
    return;
  }
  if (c.mode == 1) {  // string
    bleKeyboard.print(c.str);
    if (c.strTail) {
      delay(50);
      bleKeyboard.press(c.strTail);
      delay(100);
      bleKeyboard.releaseAll();
    }
    return;
  }
  // mode 0 — regular key
  if (c.modifier)  bleKeyboard.press(c.modifier);
  if (c.modifier2) bleKeyboard.press(c.modifier2);
  bleKeyboard.press(c.key);
  delay(100);
  bleKeyboard.releaseAll();
}

// ---- Parse R,G,B from string ---------------------------
bool parseRGB(const String& s, uint8_t& r, uint8_t& g, uint8_t& b) {
  int c1 = s.indexOf(',');
  if (c1 < 0) return false;
  int c2 = s.indexOf(',', c1 + 1);
  if (c2 < 0) return false;
  r = (uint8_t)constrain(s.substring(0, c1).toInt(), 0, 255);
  g = (uint8_t)constrain(s.substring(c1 + 1, c2).toInt(), 0, 255);
  b = (uint8_t)constrain(s.substring(c2 + 1).toInt(), 0, 255);
  return true;
}

// ---- Serial input --------------------------------------
void checkSerial() {
  if (!Serial.available()) return;
  String input = Serial.readStringUntil('\n');
  input.trim();
  if (input.length() == 0) return;
  lastActivityMs = millis();

  // Sleep command: sleep:5  or  sleep:0
  if (input.startsWith("sleep:")) {
    int val = input.substring(6).toInt();
    if (val < 0 || val > 255) {
      Serial.println("[CFG] Invalid sleep value. Use 0-255 minutes.");
      return;
    }
    saveSleepMinutes((uint8_t)val);
    return;
  }

  // Brightness: bright:128
  if (input.startsWith("bright:")) {
    int val = input.substring(7).toInt();
    if (val < 0 || val > 255) {
      Serial.println("[CFG] Invalid brightness. Use 0-255.");
      return;
    }
    saveBrightness((uint8_t)val);
    return;
  }

  // Color: color:connected:R,G,B  or  color:pressed:R,G,B
  if (input.startsWith("color:")) {
    String rest = input.substring(6);
    uint8_t r, g, b;
    if (rest.startsWith("connected:")) {
      if (!parseRGB(rest.substring(10), r, g, b)) {
        Serial.println("[CFG] Format: color:connected:R,G,B");
        return;
      }
      saveConnectedColor(r, g, b);
      pixelConnected();  // preview new color immediately
    } else if (rest.startsWith("pressed:")) {
      if (!parseRGB(rest.substring(8), r, g, b)) {
        Serial.println("[CFG] Format: color:pressed:R,G,B");
        return;
      }
      savePressedColor(r, g, b);
    } else {
      Serial.println("[CFG] Unknown color target. Use: connected or pressed");
    }
    return;
  }

  // String mode: "hello"  or  "dir"+enter
  if (input.startsWith("\"")) {
    int closeQuote = input.indexOf('"', 1);
    if (closeQuote < 0) { Serial.println("[CFG] Missing closing quote."); return; }
    String s = input.substring(1, closeQuote);
    if (s.length() == 0) { Serial.println("[CFG] Empty string — no changes made."); return; }
    if (s.length() >= sizeof(currentCombo.str)) {
      Serial.printf("[CFG] String too long (max %d chars).\n", (int)sizeof(currentCombo.str) - 1);
      return;
    }
    KeyCombo parsed = { 0, 0, 0, "", 0, 1, 0 };
    s.toCharArray(parsed.str, sizeof(parsed.str));
    String tail = input.substring(closeQuote + 1);
    tail.trim();
    if (tail.startsWith("+")) {
      String tailToken = tail.substring(1);
      tailToken.trim();
      tailToken.toLowerCase();
      uint8_t tailKey = tokenToKey(tailToken);
      if (tailKey == 0) {
        Serial.printf("[CFG] Unrecognized tail key: '%s'\n", tailToken.c_str());
        return;
      }
      parsed.strTail = tailKey;
    }
    saveCombo(parsed);
    Serial.print("[CFG] Saved! ");
    printCombo(currentCombo);
    return;
  }

  // Combo / media / single key mode
  input.toLowerCase();
  KeyCombo parsed = { 0, 0, 0, "", 0, 0, 0 };
  uint8_t modCount = 0;
  String token = "";
  input += "+";  // sentinel

  for (int i = 0; i < (int)input.length(); i++) {
    char ch = input.charAt(i);
    if (ch == '+') {
      if (token.length() == 0) { token = ""; continue; }
      uint16_t mk = tokenToMediaKey(token);
      if (mk) {
        parsed.mode     = 2;
        parsed.mediaKey = mk;
        break;
      }
      uint8_t mod = tokenToModifier(token);
      if (mod) {
        if (modCount == 0) { parsed.modifier  = mod; modCount++; }
        else               { parsed.modifier2 = mod; modCount++; }
      } else {
        parsed.key = tokenToKey(token);
        if (parsed.key == 0) {
          Serial.printf("[CFG] Unrecognized key token: '%s'\n", token.c_str());
          Serial.println("[CFG] No changes made.");
          return;
        }
      }
      token = "";
    } else {
      token += ch;
    }
  }

  if (parsed.mode != 2 && parsed.key == 0) {
    Serial.println("[CFG] No valid key found. Format: q  or  ctrl+z  or  volumeup");
    return;
  }

  saveCombo(parsed);
  Serial.print("[CFG] Saved! ");
  printCombo(currentCombo);
}

// ---- Setup ---------------------------------------------
void setup() {
  Serial.begin(115200);
  delay(750);

  esp_reset_reason_t reason = esp_reset_reason();
  Serial.printf("[BOOT] Reset reason: %d", reason);
  switch (reason) {
    case ESP_RST_PANIC:    Serial.println(" (PANIC/crash)"); break;
    case ESP_RST_INT_WDT:  Serial.println(" (interrupt watchdog)"); break;
    case ESP_RST_TASK_WDT: Serial.println(" (task watchdog)"); break;
    case ESP_RST_WDT:      Serial.println(" (other watchdog)"); break;
    case ESP_RST_BROWNOUT: Serial.println(" (brownout)"); break;
    default:               Serial.println(" (normal/power-on)"); break;
  }

  pinMode(NEOPIXEL_POWER, OUTPUT);
  digitalWrite(NEOPIXEL_POWER, HIGH);
  key_pixel.begin();
  qt_pixel.begin();

  loadSettings();

  key_pixel.setBrightness(bright);
  qt_pixel.setBrightness(bright);
  pixelWaiting();

  pinMode(BUTTON_PIN, INPUT_PULLUP);

  Serial.print("[CFG] Loaded — ");
  printCombo(currentCombo);
  Serial.printf("[CFG] Connected color: %d,%d,%d\n", connR, connG, connB);
  Serial.printf("[CFG] Pressed color:   %d,%d,%d\n", pressR, pressG, pressB);
  Serial.printf("[CFG] Brightness:      %d\n", bright);
  if (sleepMinutes > 0)
    Serial.printf("[CFG] Sleep timeout: %d minute(s). To change: sleep:10\n", sleepMinutes);
  else
    Serial.println("[CFG] Sleep disabled. To enable: sleep:5");
  Serial.println("[CFG] Examples: q    ctrl+z    f5    \"hello\"    volumeup    sleep:5");
  Serial.println("[CFG]           color:connected:0,255,0    color:pressed:255,20,100    bright:128");

  bleKeyboard.set_vendor_id(0x05AC);
  bleKeyboard.set_product_id(0x0220);
  bleKeyboard.set_version(0x0111);
  bleKeyboard.begin();
  Serial.println("[BLE] Advertising...");

  lastActivityMs = millis();
}

// ---- Loop ----------------------------------------------
void loop() {
  static bool lastBtn       = HIGH;
  static bool lastConnected = false;

  checkSerial();

  if (sleepMinutes > 0) {
    if (millis() - lastActivityMs > (uint32_t)sleepMinutes * 60 * 1000) {
      goToSleep();
    }
  }

  bool connected = bleKeyboard.isConnected();
  bool reading   = digitalRead(BUTTON_PIN);

  if (connected && !lastConnected) {
    Serial.println("[BLE] Connected");
    pixelConnected();
  } else if (!connected && lastConnected) {
    Serial.println("[BLE] Disconnected");
    pixelWaiting();
  }
  lastConnected = connected;

  if (reading == LOW && lastBtn == HIGH) {
    lastActivityMs = millis();
    pixelPressed();
    if (connected) {
      Serial.print("[KEY] Sending — ");
      printCombo(currentCombo);
      sendCombo(currentCombo);
    } else {
      Serial.println("[BTN] Not connected");
    }
  }
  if (reading == HIGH && lastBtn == LOW) {
    connected ? pixelConnected() : pixelWaiting();
  }

  lastBtn = reading;
  delay(10);
}