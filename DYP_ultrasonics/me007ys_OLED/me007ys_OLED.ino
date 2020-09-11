#include <Adafruit_SSD1306.h>
#include <Fonts/FreeSans9pt7b.h>

Adafruit_SSD1306 display = Adafruit_SSD1306(128, 32, &Wire);

// Example code for DYP-ME007YS sensor

#if defined(__AVR__) || defined(ESP8266)
// For UNO and others without hardware serial, we must use software serial...
// pin #2 is IN from sensor (WHITE wire)
// Set up the serial port to use softwareserial..
#include <SoftwareSerial.h>
SoftwareSerial mySerial(2, -1);

#else
// On Leonardo/M0/etc, others with hardware serial, use hardware serial!
// #0 is white wire, data input
#define mySerial Serial1

#endif

#define CONTROL_PIN 5   // This is the YELLOW wire, can be any data line

int16_t distance;  // The last measured distance
bool newData = false; // Whether new data is available from the sensor
uint8_t buffer[4];  // our buffer for storing data
uint8_t idx = 0;  // our idx into the storage buffer

void setup() {
  // Open serial communications and wait for port to open:
  Serial.begin(115200);
  
  if(!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) { // Address 0x3C for 128x32
    Serial.println(F("SSD1306 allocation failed"));
    for(;;); // Don't proceed, loop forever
  }
  display.display();
  delay(500);
  display.setTextColor(WHITE);
  display.setFont(&FreeSans9pt7b);
  display.setTextSize(1);
    
  Serial.println("Adafruit DYP-ME007YS Test");

  // set the data rate for the Serial port, 9600 for the sensor
  mySerial.begin(9600);
  pinMode(CONTROL_PIN, OUTPUT);
  digitalWrite(CONTROL_PIN, HIGH);
}


void loop() { // run over and over
  if (mySerial.available()) {
    uint8_t c = mySerial.read();
    Serial.println(c, HEX);

    // See if this is a header byte
    if (idx == 0 && c == 0xFF) {
      buffer[idx++] = c;
    }
    // Two middle bytes can be anything
    else if ((idx == 1) || (idx == 2)) {
      buffer[idx++] = c;
    }
    else if (idx == 3) {
      uint8_t sum = 0;
      sum = buffer[0] + buffer[1] + buffer[2];
      if (sum == c) {
        distance = ((uint16_t)buffer[1] << 8) | buffer[2];
        newData = true;
      }
      idx = 0;
    }
  }
  
  if (newData) {
    Serial.print("Distance: ");
    Serial.print(distance);
    Serial.println(" mm");
    newData = false;
    display.clearDisplay();
    display.setCursor(0, 13);
    display.print("UART Sonar");
    display.setCursor(0, 30);
    display.print("Dist.: ");
    display.print(distance);
    display.println(" mm");
    display.display();
  }
}
