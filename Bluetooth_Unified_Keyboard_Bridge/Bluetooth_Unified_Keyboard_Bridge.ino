// SPDX-FileCopyrightText: 2025 John Park for Adafruit Industries
//
// SPDX-License-Identifier: MIT
//
// made with assistance from Claude Sonnet 4
//
// Unified Bluetooth HID Bridge - BT Classic & BLE
// put keyboard in pairing mode, then press reset or BOOT button
// slow blinks mean scanning
// fast blinks mean keyboard detected, press a keyboard key to connect

// === CONFIGURATION ===
#define DEBUG_MODE false   // Set to false to reduce serial output
#define BLINK_MODE true    // Set to false for solid LED (no keypress blinks)
#define SCAN_MODE "Both"   // Options: "BT_Classic", "BLE", "Both"

// Include both Bluetooth stacks
extern "C" {
#include "btstack.h"
}
#include <BluetoothHCI.h>
#include <BluetoothHIDMaster.h>
#include <Keyboard.h>
#include <Mouse.h>

// Connection state management
typedef enum {
    INIT,
    SCANNING_CLASSIC,
    CLASSIC_CONNECTING,
    CLASSIC_CONNECTED,
    SCANNING_BLE,
    BLE_CONNECTED,
    BOTH_FAILED,
    DISCONNECTED
} connection_state_t;

connection_state_t connection_state = INIT;

// BT Classic components
BluetoothHCI hci;
bd_addr_t target_keyboard_addr;
bool target_keyboard_found = false;
uint16_t hid_control_cid = 0;
uint16_t hid_interrupt_cid = 0;
static btstack_packet_callback_registration_t hci_event_callback_registration;

// BLE components
BluetoothHIDMaster ble_hid;
HIDKeyStream keystream;

// Shared state tracking
static uint8_t last_modifiers = 0;
static uint8_t last_keys[6] = {0};
bool keyPressed[256] = {0}; // Track which keys are currently pressed

// LED management
unsigned long ledTimer = 0;
bool ledState = false;
unsigned long ledOffTime = 0;
bool ledBlinking = false;
int pairingBlinks = 0;
unsigned long pairingBlinkTimer = 0;

// Timing management
unsigned long lastScan = 0;
unsigned long stateStartTime = 0;
const unsigned long CLASSIC_SCAN_TIMEOUT = 10000; // 10 seconds
const unsigned long BLE_SCAN_TIMEOUT = 15000;     // 15 seconds

void setup() {
  Serial.begin(115200);
  delay(3000);
  
  Serial.println("=== UNIFIED BLUETOOTH HID BRIDGE ===");
  Serial.printf("Scan mode: %s\n", SCAN_MODE);
  Serial.println("Put your Bluetooth device in pairing mode now");
  
  // Initialize LED
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);
  Serial.println("LED initialized");
  
  // Initialize USB HID
  Keyboard.begin();
  Mouse.begin();
  Serial.println("USB HID initialized");
  
  // Start with LED blinking to show we're alive
  ledTimer = millis();
  ledState = true;
  digitalWrite(LED_BUILTIN, HIGH);
  
  Serial.println("Starting Bluetooth stack initialization...");
  
  // Choose scan mode based on user setting
  if (strcmp(SCAN_MODE, "BT_Classic") == 0) {
    Serial.println("BT Classic only mode");
    connection_state = SCANNING_CLASSIC;
    stateStartTime = millis();
    initAndScanClassic();
  } else if (strcmp(SCAN_MODE, "BLE") == 0) {
    Serial.println("BLE only mode");
    connection_state = SCANNING_BLE;
    stateStartTime = millis();
    initAndScanBLE();
  } else {
    Serial.println("Both protocols mode - trying Classic first");
    connection_state = SCANNING_CLASSIC;
    stateStartTime = millis();
    initAndScanClassic();
  }
}

void initAndScanClassic() {
  Serial.println("\n=== INITIALIZING BT CLASSIC STACK ===");
  
  // Initialize HCI for Classic
  l2cap_init();
  sm_init();
  gap_set_default_link_policy_settings(LM_LINK_POLICY_ENABLE_SNIFF_MODE | LM_LINK_POLICY_ENABLE_ROLE_SWITCH);
  hci_set_master_slave_policy(HCI_ROLE_MASTER);
  hci_set_inquiry_mode(INQUIRY_MODE_RSSI_AND_EIR);

  Serial.println("BTStack components initialized");

  hci.install();
  hci.begin();
  Serial.println("HCI installed and started");
  
  // Register BTStack event handler
  hci_event_callback_registration.callback = &classic_packet_handler;
  hci_add_event_handler(&hci_event_callback_registration);
  Serial.println("Event handler registered");
  
  // Turn on Bluetooth
  hci_power_control(HCI_POWER_ON);
  Serial.println("Bluetooth power ON");
  
  delay(2000); // Give it time to initialize
  
  Serial.println("Starting BT Classic device scan...");
  scanForClassicDevices();
}

void scanForClassicDevices() {
  Serial.println("Scanning for BT Classic devices...");
  
  auto devices = hci.scan(BluetoothHCI::any_cod);
  
  Serial.printf("Classic scan completed. Found %d devices:\n", devices.size());
  
  if (devices.size() == 0) {
    Serial.println("No Classic devices found. Will try BLE after timeout.");
    return;
  }
  
  Serial.println("Address           | RSSI | Class    | Name");
  Serial.println("------------------|------|----------|------------------");
  
  for (auto device : devices) {
    uint32_t cod = device.deviceClass();
    uint8_t majorClass = (cod >> 8) & 0x1F;
    uint8_t minorClass = (cod >> 2) & 0x3F;
    
    Serial.printf("%s | %4d | %08lx | %s", 
                 device.addressString(), device.rssi(), cod, device.name());
    
    // Look for HID keyboards in Classic scan
    if (majorClass == 5 && (minorClass & 0x10)) {  // HID Keyboard
      Serial.print(" [HID KEYBOARD] *** CONNECTING ***");
      
      // We found a Classic keyboard!
      const char* addrStr = device.addressString();
      sscanf(addrStr, "%hhx:%hhx:%hhx:%hhx:%hhx:%hhx",
             &target_keyboard_addr[0], &target_keyboard_addr[1], &target_keyboard_addr[2],
             &target_keyboard_addr[3], &target_keyboard_addr[4], &target_keyboard_addr[5]);
      target_keyboard_found = true;
      
      Serial.printf("\nFound Classic HID keyboard: %s\n", device.name());
      Serial.printf("Address: %s\n", device.addressString());
      
      // Start Classic connection
      connection_state = CLASSIC_CONNECTING;
      stateStartTime = millis();
      startClassicConnection();
      
      Serial.println();
      return; // Exit the loop - we found our keyboard
    } else {
      // Show device type for debugging
      switch (majorClass) {
        case 1: Serial.print(" [Computer]"); break;
        case 2: Serial.print(" [Phone]"); break;
        case 3: Serial.print(" [Network]"); break;
        case 4: Serial.print(" [Audio/Video]"); break;
        case 5: Serial.print(" [HID Device]"); break;
        default: Serial.printf(" [Class:%d]", majorClass); break;
      }
    }
    Serial.println();
  }
  
  Serial.println("No HID keyboards found in Classic scan.");
}

void fallbackToBLE() {
  Serial.println("\n=== FALLING BACK TO BLE ===");
  connection_state = SCANNING_BLE;
  stateStartTime = millis();
  initAndScanBLE();
}

void initAndScanBLE() {
  Serial.println("Initializing BLE stack...");
  
  // Setup the HID key to ASCII conversion
  keystream.begin();
  Serial.println("KeyStream initialized");

  // Setup BLE callbacks
  setupBLECallbacks();
  Serial.println("BLE callbacks configured");

  // Start BLE HID master
  ble_hid.begin(true);
  Serial.println("BLE HID master started");
  
  // Start BLE connection attempt
  ble_hid.connectBLE();
  Serial.println("BLE connection initiated - waiting for device...");
  Serial.println("(BLE devices will be detected on first keypress)");
}

void setupBLECallbacks() {
  // BLE Mouse callbacks
  ble_hid.onMouseMove([](void *cbdata, int dx, int dy, int dw) {
    (void) cbdata;
    if (DEBUG_MODE) {
      Serial.printf("BLE Mouse: X:%d  Y:%d  Wheel:%d\n", dx, dy, dw);
    }
    Mouse.move(dx, dy);
    if (dw != 0) Mouse.move(0, 0, dw);
    blinkOnActivity();
  });

  ble_hid.onMouseButton([](void *cbdata, int butt, bool down) {
    (void) cbdata;
    if (DEBUG_MODE) {
      Serial.printf("BLE Mouse: Button %d %s\n", butt, down ? "DOWN" : "UP");
    }
    if (down) {
      if (butt == 1) Mouse.press(MOUSE_LEFT);
      else if (butt == 2) Mouse.press(MOUSE_RIGHT);
      else if (butt == 3) Mouse.press(MOUSE_MIDDLE);
    } else {
      if (butt == 1) Mouse.release(MOUSE_LEFT);
      else if (butt == 2) Mouse.release(MOUSE_RIGHT);
      else if (butt == 3) Mouse.release(MOUSE_MIDDLE);
    }
    blinkOnActivity();
  });

  // BLE Keyboard callbacks
  ble_hid.onKeyDown([](void *cbdata, int key) {
    handleBLEKey(key, true);
  }, (void *)true);

  ble_hid.onKeyUp([](void *cbdata, int key) {
    handleBLEKey(key, false);
  }, (void *)false);
}

void startClassicConnection() {
  if (!target_keyboard_found) {
    Serial.println("ERROR: No Classic target keyboard found");
    fallbackToBLE();
    return;
  }
  
  Serial.println("=== STARTING CLASSIC HID CONNECTION ===");
  Serial.println("Creating L2CAP Control channel...");
  
  // Create control channel first
  l2cap_create_channel(&classic_packet_handler, target_keyboard_addr, BLUETOOTH_PSM_HID_CONTROL, 
                       48, &hid_control_cid);
}

void handleBLEKey(int key, bool state) {
  if (DEBUG_MODE) {
    Serial.printf("BLE Keyboard: %02x %s\n", key, state ? "DOWN" : "UP");
  }
  
  if (key >= 256) return; // Bounds check
  
  // Check if this is the first BLE key press (connection detection)
  if (connection_state == SCANNING_BLE) {
    Serial.printf("\n*** BLE KEYBOARD DETECTED ON FIRST KEYPRESS ***\n");
    Serial.printf("=== BLE DEVICE CONNECTED ===\n");
    Serial.printf("Ready to forward BLE input to USB.\n");
    Serial.printf("========================\n");
    
    connection_state = BLE_CONNECTED;
    celebrationBlinks(8); // 4 blinks for BLE
    
    // After celebration, LED will go solid (handled in LED patterns)
  }
  
  // Forward the key to USB
  forwardBLEKeyToUSB(key, state);
  blinkOnActivity();
}

void classic_packet_handler(uint8_t packet_type, uint16_t channel, uint8_t *packet, uint16_t size) {
  UNUSED(size);
  
  if (packet_type == HCI_EVENT_PACKET) {
    uint8_t event = hci_event_packet_get_type(packet);
    
    switch (event) {
      case BTSTACK_EVENT_STATE:
        if (btstack_event_state_get_state(packet) == HCI_STATE_WORKING) {
          Serial.println("Classic BTstack ready");
        }
        break;
        
      case L2CAP_EVENT_CHANNEL_OPENED:
        {
          uint16_t cid = l2cap_event_channel_opened_get_local_cid(packet);
          uint16_t psm = l2cap_event_channel_opened_get_psm(packet);
          uint8_t status = l2cap_event_channel_opened_get_status(packet);
          
          if (status) {
            Serial.printf("Classic L2CAP connection failed, status 0x%02x\n", status);
            handleClassicConnectionError(status);
            return;
          }
          
          Serial.printf("Classic L2CAP channel opened: CID=0x%04x, PSM=0x%04x\n", cid, psm);
          
          if (psm == BLUETOOTH_PSM_HID_CONTROL) {
            hid_control_cid = cid;
            Serial.println("Classic HID Control channel established");
            Serial.println("Creating L2CAP Interrupt channel...");
            
            // Create interrupt channel
            l2cap_create_channel(&classic_packet_handler, target_keyboard_addr, BLUETOOTH_PSM_HID_INTERRUPT, 
                                48, &hid_interrupt_cid);
          } else if (psm == BLUETOOTH_PSM_HID_INTERRUPT) {
            hid_interrupt_cid = cid;
            Serial.println("Classic HID Interrupt channel established");
            Serial.println("*** CLASSIC HID CONNECTION COMPLETE ***");
            connection_state = CLASSIC_CONNECTED;
            
            celebrationBlinks(6); // 3 blinks for Classic
            
            // After celebration, LED will go solid (handled in LED patterns)
          }
        }
        break;
        
      case L2CAP_EVENT_CHANNEL_CLOSED:
        {
          uint16_t cid = l2cap_event_channel_closed_get_local_cid(packet);
          Serial.printf("Classic L2CAP channel closed: CID=0x%04x\n", cid);
          
          if (cid == hid_control_cid) {
            hid_control_cid = 0;
          } else if (cid == hid_interrupt_cid) {
            hid_interrupt_cid = 0;
          }
          
          if (hid_control_cid == 0 && hid_interrupt_cid == 0) {
            Serial.println("Classic HID connection lost.");
            connection_state = DISCONNECTED;
            target_keyboard_found = false;
          }
        }
        break;
        
      default:
        break;
    }
  } else if (packet_type == L2CAP_DATA_PACKET) {
    // Classic HID input data
    if (channel == hid_interrupt_cid) {
      if (DEBUG_MODE) {
        Serial.printf("Classic HID Input Data (%d bytes): ", size);
        for (int i = 0; i < size; i++) {
          Serial.printf("%02X ", packet[i]);
        }
        Serial.println();
      }
      
      processClassicHIDReport(packet, size);
    }
  }
}

void handleClassicConnectionError(uint8_t status) {
  Serial.printf("Classic connection failed with status 0x%02x - ", status);
  switch (status) {
    case 0x04: Serial.println("Page timeout"); break;
    case 0x05: Serial.println("Authentication failure"); break;
    case 0x08: Serial.println("Connection timeout"); break;
    default: Serial.printf("Error code 0x%02x\n", status); break;
  }
  
  Serial.println("Trying BLE fallback...");
  fallbackToBLE();
}

void processClassicHIDReport(uint8_t *report, uint16_t length) {
  if (length < 10) {
    Serial.printf("Invalid Classic HID report length: %d\n", length);
    return;
  }
  
  uint8_t modifiers = report[2];
  uint8_t *keys = &report[4];
  
  // Forward to USB HID
  forwardClassicToUSB(modifiers, keys);
  blinkOnActivity();
}

// Shared key mapping function
uint8_t hidToUsbKey(uint8_t hidKey) {
  switch (hidKey) {
    // Letters
    case 0x04: return 'a';    case 0x05: return 'b';    case 0x06: return 'c';    case 0x07: return 'd';
    case 0x08: return 'e';    case 0x09: return 'f';    case 0x0A: return 'g';    case 0x0B: return 'h';
    case 0x0C: return 'i';    case 0x0D: return 'j';    case 0x0E: return 'k';    case 0x0F: return 'l';
    case 0x10: return 'm';    case 0x11: return 'n';    case 0x12: return 'o';    case 0x13: return 'p';
    case 0x14: return 'q';    case 0x15: return 'r';    case 0x16: return 's';    case 0x17: return 't';
    case 0x18: return 'u';    case 0x19: return 'v';    case 0x1A: return 'w';    case 0x1B: return 'x';
    case 0x1C: return 'y';    case 0x1D: return 'z';
    
    // Numbers
    case 0x1E: return '1';    case 0x1F: return '2';    case 0x20: return '3';    case 0x21: return '4';
    case 0x22: return '5';    case 0x23: return '6';    case 0x24: return '7';    case 0x25: return '8';
    case 0x26: return '9';    case 0x27: return '0';
    
    // Special keys
    case 0x28: return KEY_RETURN;        case 0x29: return KEY_ESC;
    case 0x2A: return KEY_BACKSPACE;     case 0x2B: return KEY_TAB;
    case 0x2C: return ' ';               case 0x39: return KEY_CAPS_LOCK;
    
    // Symbols
    case 0x2D: return '-';    case 0x2E: return '=';    case 0x2F: return '[';    case 0x30: return ']';
    case 0x31: return '\\';   case 0x33: return ';';    case 0x34: return '\'';   case 0x35: return '`';
    case 0x36: return ',';    case 0x37: return '.';    case 0x38: return '/';
    
    // Function keys
    case 0x3A: return KEY_F1;     case 0x3B: return KEY_F2;     case 0x3C: return KEY_F3;
    case 0x3D: return KEY_F4;     case 0x3E: return KEY_F5;     case 0x3F: return KEY_F6;
    case 0x40: return KEY_F7;     case 0x41: return KEY_F8;     case 0x42: return KEY_F9;
    case 0x43: return KEY_F10;    case 0x44: return KEY_F11;    case 0x45: return KEY_F12;
    
    // Arrow keys
    case 0x4F: return KEY_RIGHT_ARROW;   case 0x50: return KEY_LEFT_ARROW;
    case 0x51: return KEY_DOWN_ARROW;    case 0x52: return KEY_UP_ARROW;
    
    // Navigation
    case 0x49: return KEY_INSERT;        case 0x4A: return KEY_HOME;
    case 0x4B: return KEY_PAGE_UP;       case 0x4C: return KEY_DELETE;
    case 0x4D: return KEY_END;           case 0x4E: return KEY_PAGE_DOWN;
    
    // Modifiers
    case 0xE0: return KEY_LEFT_CTRL;     case 0xE1: return KEY_LEFT_SHIFT;
    case 0xE2: return KEY_LEFT_ALT;      case 0xE3: return KEY_LEFT_GUI;
    case 0xE4: return KEY_RIGHT_CTRL;    case 0xE5: return KEY_RIGHT_SHIFT;
    case 0xE6: return KEY_RIGHT_ALT;     case 0xE7: return KEY_RIGHT_GUI;
    
    default: return 0;
  }
}

void forwardClassicToUSB(uint8_t modifiers, uint8_t *keys) {
  // Handle modifier changes
  uint8_t modifier_changes = modifiers ^ last_modifiers;
  
  // Process each modifier bit
  if (modifier_changes & 0x01) (modifiers & 0x01) ? Keyboard.press(KEY_LEFT_CTRL) : Keyboard.release(KEY_LEFT_CTRL);
  if (modifier_changes & 0x02) (modifiers & 0x02) ? Keyboard.press(KEY_LEFT_SHIFT) : Keyboard.release(KEY_LEFT_SHIFT);
  if (modifier_changes & 0x04) (modifiers & 0x04) ? Keyboard.press(KEY_LEFT_ALT) : Keyboard.release(KEY_LEFT_ALT);
  if (modifier_changes & 0x08) (modifiers & 0x08) ? Keyboard.press(KEY_LEFT_GUI) : Keyboard.release(KEY_LEFT_GUI);
  if (modifier_changes & 0x10) (modifiers & 0x10) ? Keyboard.press(KEY_RIGHT_CTRL) : Keyboard.release(KEY_RIGHT_CTRL);
  if (modifier_changes & 0x20) (modifiers & 0x20) ? Keyboard.press(KEY_RIGHT_SHIFT) : Keyboard.release(KEY_RIGHT_SHIFT);
  if (modifier_changes & 0x40) (modifiers & 0x40) ? Keyboard.press(KEY_RIGHT_ALT) : Keyboard.release(KEY_RIGHT_ALT);
  if (modifier_changes & 0x80) (modifiers & 0x80) ? Keyboard.press(KEY_RIGHT_GUI) : Keyboard.release(KEY_RIGHT_GUI);
  
  // Handle key releases
  for (int i = 0; i < 6; i++) {
    if (last_keys[i] != 0) {
      bool still_pressed = false;
      for (int j = 0; j < 6; j++) {
        if (keys[j] == last_keys[i]) {
          still_pressed = true;
          break;
        }
      }
      if (!still_pressed) {
        uint8_t usb_key = hidToUsbKey(last_keys[i]);
        if (usb_key != 0) Keyboard.release(usb_key);
      }
    }
  }
  
  // Handle key presses
  for (int i = 0; i < 6; i++) {
    if (keys[i] != 0) {
      bool already_pressed = false;
      for (int j = 0; j < 6; j++) {
        if (last_keys[j] == keys[i]) {
          already_pressed = true;
          break;
        }
      }
      if (!already_pressed) {
        uint8_t usb_key = hidToUsbKey(keys[i]);
        if (usb_key != 0) Keyboard.press(usb_key);
      }
    }
  }
  
  // Save current state
  last_modifiers = modifiers;
  memcpy(last_keys, keys, 6);
}

void forwardBLEKeyToUSB(int key, bool state) {
  if (key >= 256) return;
  
  bool isModifier = (key >= 0xE0 && key <= 0xE7);
  
  if (isModifier) {
    uint8_t usbKey = hidToUsbKey(key);
    if (state) Keyboard.press(usbKey);
    else Keyboard.release(usbKey);
    return;
  }
  
  // Handle regular keys
  uint8_t usbKey = hidToUsbKey(key);
  if (usbKey != 0) {
    if (state && !keyPressed[key]) {
      keyPressed[key] = true;
      Keyboard.press(usbKey);
    } else if (!state && keyPressed[key]) {
      keyPressed[key] = false;
      Keyboard.release(usbKey);
    }
  }
}

void celebrationBlinks(int count) {
  pairingBlinks = count;
  pairingBlinkTimer = millis();
  digitalWrite(LED_BUILTIN, HIGH);
}

void blinkOnActivity() {
  if (BLINK_MODE && pairingBlinks == 0 && (connection_state == CLASSIC_CONNECTED || connection_state == BLE_CONNECTED)) {
    digitalWrite(LED_BUILTIN, LOW);  // Turn OFF briefly to show activity
    ledBlinking = true;
    ledOffTime = millis() + 50;      // Stay off for 50ms
  }
}

void loop() {
  unsigned long currentTime = millis();
  
  // Handle state timeouts
  handleStateTimeouts(currentTime);
  
  // Handle LED patterns
  handleLEDPatterns(currentTime);
  
  // Handle BOOTSEL button
  handleBootselButton();
  
  delay(10);
}

void handleStateTimeouts(unsigned long currentTime) {
  switch (connection_state) {
    case SCANNING_CLASSIC:
      if (currentTime - stateStartTime > CLASSIC_SCAN_TIMEOUT) {
        if (strcmp(SCAN_MODE, "BT_Classic") == 0) {
          Serial.println("Classic scan timeout - BT Classic only mode, retrying...");
          stateStartTime = currentTime;
          scanForClassicDevices(); // Retry Classic scan
        } else {
          Serial.println("Classic scan timeout - falling back to BLE");
          fallbackToBLE();
        }
      }
      break;
      
    case SCANNING_BLE:
      if (currentTime - stateStartTime > BLE_SCAN_TIMEOUT) {
        if (strcmp(SCAN_MODE, "BLE") == 0) {
          Serial.println("BLE scan timeout - BLE only mode, retrying...");
          stateStartTime = currentTime;
          initAndScanBLE(); // Retry BLE scan
        } else {
          Serial.println("BLE scan timeout - restarting from Classic");
          connection_state = BOTH_FAILED;
          stateStartTime = currentTime;
        }
      }
      break;
      
    case BOTH_FAILED:
      if (currentTime - stateStartTime > 5000) { // Wait 5 seconds before retry
        Serial.println("Retrying scan sequence...");
        connection_state = SCANNING_CLASSIC;
        stateStartTime = currentTime;
        initAndScanClassic();
      }
      break;
  }
}

void handleLEDPatterns(unsigned long currentTime) {
  // Handle pairing celebration blinks first
  if (pairingBlinks > 0) {
    if (currentTime - pairingBlinkTimer >= 150) {
      pairingBlinks--;
      bool state = (pairingBlinks % 2 == 0);
      digitalWrite(LED_BUILTIN, state);
      pairingBlinkTimer = currentTime;
    }
    return;
  }
  
  // Handle activity blinks
  if (ledBlinking && currentTime >= ledOffTime) {
    digitalWrite(LED_BUILTIN, HIGH); // Turn back ON after brief off period
    ledBlinking = false;
    return;
  }
  
  // Handle state-based LED patterns
  switch (connection_state) {
    case SCANNING_CLASSIC:
    case SCANNING_BLE:
      // Slow blink while scanning (1 second cycle)
      if (currentTime - ledTimer >= 1000) {
        ledState = !ledState;
        digitalWrite(LED_BUILTIN, ledState);
        ledTimer = currentTime;
      }
      break;
      
    case CLASSIC_CONNECTING:
      // Fast blink while connecting - tells user to press a key
      if (currentTime - ledTimer >= 250) {
        ledState = !ledState;
        digitalWrite(LED_BUILTIN, ledState);
        ledTimer = currentTime;
      }
      break;
      
    case CLASSIC_CONNECTED:
    case BLE_CONNECTED:
      // Solid ON while connected (unless doing activity blinks)
      if (!ledBlinking) {
        digitalWrite(LED_BUILTIN, HIGH);
      }
      break;
      
    case BOTH_FAILED:
    case DISCONNECTED:
      // Very slow pulse when failed/disconnected (2 second cycle)
      if (currentTime - ledTimer >= 2000) {
        ledState = !ledState;
        digitalWrite(LED_BUILTIN, ledState);
        ledTimer = currentTime;
      }
      break;
  }
}

void handleBootselButton() {
  if (BOOTSEL) {
    while (BOOTSEL) delay(1);
    
    Serial.println("\nBOOTSEL pressed - restarting scan sequence");
    
    // Clean up current connections
    if (connection_state == CLASSIC_CONNECTED) {
      if (hid_control_cid) l2cap_disconnect(hid_control_cid);
      if (hid_interrupt_cid) l2cap_disconnect(hid_interrupt_cid);
    } else if (connection_state == BLE_CONNECTED) {
      ble_hid.disconnect();
      ble_hid.clearPairing();
    }
    
    // Reset all state
    Keyboard.releaseAll();
    Mouse.release(MOUSE_LEFT | MOUSE_RIGHT | MOUSE_MIDDLE);
    
    for (int i = 0; i < 256; i++) keyPressed[i] = false;
    memset(last_keys, 0, 6);
    last_modifiers = 0;
    
    target_keyboard_found = false;
    hid_control_cid = 0;
    hid_interrupt_cid = 0;
    pairingBlinks = 0;
    ledBlinking = false;
    
    // Restart from appropriate scan mode
    if (strcmp(SCAN_MODE, "BT_Classic") == 0) {
      connection_state = SCANNING_CLASSIC;
      Serial.println("Restarting BT Classic scan...");
      initAndScanClassic();
    } else if (strcmp(SCAN_MODE, "BLE") == 0) {
      connection_state = SCANNING_BLE;
      Serial.println("Restarting BLE scan...");
      initAndScanBLE();
    } else {
      connection_state = SCANNING_CLASSIC;
      Serial.println("Restarting unified scan...");
      initAndScanClassic();
    }
  }
}