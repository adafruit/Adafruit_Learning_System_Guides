/*
This Arduino sketch combines a serial JPEG camera, data logging shield
and an Eye-Fi wireless SD card in order to provide remote monitoring.
SEE NOTES LATER IN CODE REGARDING "X2" CARDS - MUST EXPLICITLY ENABLE.
After initializing the hardware, the sketch sets the camera to motion-
detect mode and then runs in a loop monitoring for changes.  When
movement is sensed, an image is captured and written to the SD card,
at which point (if the Eye-Fi card is properly configured and a Wi-Fi
internet connection is available), this will be transferred to the
Eye-Fi service -- and in turn to your computer, smartphone, etc.
IMPORTANT DISCLAIMERS: this is a plaything -- do not rely on this for
actual security.  Also, users should observe local privacy ordinances
regarding surveillance.
Written by Adafruit Industries.  Public domain.
Resources:
Adafruit Data logging shield for Arduino:
https://www.adafruit.com/products/243
TTL Serial JPEG Camera with NTSC Video:
https://www.adafruit.com/products/397
 -or-
Weatherproof TTL Serial JPEG Camera with NTSC Video and IR LEDs:
https://www.adafruit.com/products/613
This also requires an Arduino (or Arduino-compatible) board such as
the Arduino Uno or Duemilanove (*NOT COMPATIBLE WITH MEGA*) and a
suitable power supply.  Power uptions include:
9 VDC 1000mA regulated switching power adapter - UL listed:
https://www.adafruit.com/products/63
 -or-
6 x AA battery holder with 5.5mm/2.1mm plug:
https://www.adafruit.com/products/248
 -or-
MintyBoost kit:
http://www.adafruit.com/products/14
*/

// Although this sketch uses the hardware serial UART, it's still necessary
// to #include SoftwareSerial.h/NewSoftSerial.h here.  This is because the
// VC0706 camera library includes support for both "hard" and "soft" serial,
// but cannot #include the right header on its own without some help.  Why?
// From http://arduino.cc/en/Hacking/BuildProcess :
// "The include path includes the sketch's directory [...] the avr include
// directory (<ARDUINO>/hardware/tools/avr/avr/include/), as well as any
// library directories (in <ARDUINO>/hardware/libraries/) which contain a
// header file WHICH IS INCLUDED BY THE MAIN SKETCH FILE." (emphasis mine)
// So including it here makes the VC0706 library happy:
#if ARDUINO >= 100
 #include <SoftwareSerial.h>
#else
 #include <NewSoftSerial.h>
#endif
#include <Adafruit_VC0706.h> // Serial JPEG camera library
#include <SD.h>              // SD card library
#include <RTClib.h>          // Realtime clock library
#include <Wire.h>            // Also needed for RTC

// This sketch uses the hardware serial UART (on pins 0 & 1) for more
// robust communication with the camera.  Unfortunately this means we
// can't use the USB port to issue debugging info to a computer...
// instead, status is conveyed through the green and red LEDs on the
// Data Logging Shield, connected to the following pins:
#define RED_LED   5
#define GREEN_LED 6

// Green LED does a "sleep throb" when camera is idle.  This table
// contains the brightness levels over time (reverse for second half).
PROGMEM byte sleepTab[] = {
      0,   0,   0,   0,   0,   0,   0,   0,   0,   1,
      1,   1,   2,   3,   4,   5,   6,   8,  10,  13,
     15,  19,  22,  26,  31,  36,  41,  47,  54,  61,
     68,  76,  84,  92, 101, 110, 120, 129, 139, 148,
    158, 167, 177, 186, 194, 203, 211, 218, 225, 232,
    237, 242, 246, 250, 252, 254, 255 };

// SD card chip select line varies among boards/shields:
// Adafruit SD shields and modules: pin 10
// Arduino Ethernet shield: pin 4
// Sparkfun SD shield: pin 8
#define chipSel 10

RTC_DS1307      clock;
Adafruit_VC0706 cam = Adafruit_VC0706(&Serial);
char            directory[] = "DCIM/CANON999", // Emulate Canon folder layout
                filename[]  = "DCIM/CANON999/IMG_0000.JPG";
byte            sleepPos; // Current "throb" table position
int             imgNum      = 0;
const int       minFileSize = 20 * 1024; // Eye-Fi requires minimum file size

// -------------------------------------------------------------------------

void setup() {

  pinMode(RED_LED  , OUTPUT);
  pinMode(GREEN_LED, OUTPUT);
  digitalWrite(RED_LED  , LOW);
  digitalWrite(GREEN_LED, HIGH); // "Hello!" indicator

  // All the example sketches for the serial JPEG camera use pins 2 & 3
  // (and SoftwareSerial/NewSoftSerial).  But this sketch uses the hardware
  // UART on pins 0 & 1 for robustness.  If you've permanently wired the
  // cam to pins 2 & 3, this is perfectly fine, you can just use short
  // jumpers between 0 & 2 and 1 & 3 (remove when uploading code).  But
  // make sure those pins are never used as outputs for any features you
  // might add to this sketch!
  pinMode(2,INPUT); pinMode(3,INPUT);

  Wire.begin();  // IMPORTANT: the clock should have previously been set
  clock.begin(); // using the 'ds1307' example sketch included with RTClib.
  SdFile::dateTimeCallback(dateTime); // Register timestamp callback
  if(!clock.isrunning()) error(75);   // Init clock; error = hyper flash
  if(!SD.begin(chipSel)) error(250);  // Init SD card; error = quick flash
  if(!cam.begin())       error(1000); // Init camera; error = slow flash

  // Un-comment this line if using an Eye-Fi X2 card:
  // SD.enableCRC(true);

  // Create image directory if not already present; error = solid red
  if(!SD.exists(directory) && !SD.mkdir(directory)) error(1);

  delay(1000); // Need to pause a moment before camera accepts commands
  cam.setImageSize(VC0706_640x480); // Let's use the largest image size

  // Set up LED "sleep throb" using Timer1 interrupt:
  TCCR1A = _BV(WGM11); // Mode 14 (fast PWM), 64:1 prescale, OC1A off
  TCCR1B = _BV(WGM13) | _BV(WGM12) | _BV(CS11) | _BV(CS10);
  ICR1   = 8333;       // ~30 Hz between sleep throb updates
  sei();                // Enable global interrupts
  // Timer1 interrupt is enabled when loop() starts
}


void loop() {

  sleepPos = sizeof(sleepTab);   // Start up LED "sleep throb" at top
  TIMSK1  |= _BV(TOIE1);         // Enable Timer1 interrupt for throb
  nextFilename();                // Scan directory for next name
  cam.resumeVideo();             // Enable composite live output
  cam.setMotionDetect(true);     // Enable motion detection
  while(!cam.motionDetected());  // Wait for motion trigger ... ... ...

  // Motion detected!
  cam.setMotionDetect(false);    // Turn it off while we work 
  TIMSK1 &= ~_BV(TOIE1);         // And stop the pulsing LED
  digitalWrite(GREEN_LED, HIGH); // Just show solid green

  delay(500); // Pause half a sec between motion sense & capture
 
  if(!cam.takePicture()) {
    // Failed to take picture.  Show RED (+GREEN above) for 5 sec:
    digitalWrite(RED_LED, HIGH);
    delay(5000);
    digitalWrite(RED_LED, LOW);
    return; // Resume motion detection
  }

  File imgFile = SD.open(filename, FILE_WRITE);
  if(imgFile == NULL) {
    // Couldn't open file.  Show RED (no GREEN) for 5 sec:
    digitalWrite(GREEN_LED, LOW);
    digitalWrite(RED_LED  , HIGH);
    delay(5000);
    digitalWrite(RED_LED  , LOW);
    return; // Resume motion detection
  }

  uint16_t jpegLen = cam.frameLength();
  uint16_t bytesRemaining;
  uint8_t  b, *ptr;

  // Transfer data from camera to SD file:
  for(bytesRemaining = jpegLen; bytesRemaining ; bytesRemaining -= b) {
    b   = min(32, bytesRemaining); // Max of 32 bytes at a time
    ptr = cam.readPicture(b);      // From camera
    imgFile.write(ptr, b);         // To SD card
    digitalWrite(GREEN_LED, (bytesRemaining & 256) ? HIGH : LOW);
  }

  // Pad file to minimum Eye-Fi file size if required:
  if(jpegLen < minFileSize) {
    for(bytesRemaining  = minFileSize - jpegLen; bytesRemaining ;
        bytesRemaining -= b) {
      b = min(32, bytesRemaining); // Max of 32 bytes at a time
      imgFile.write(ptr, b);       // Just repeat last data, it's ignored
      digitalWrite(GREEN_LED, (bytesRemaining & 256) ? HIGH : LOW);
    }
  }

  imgFile.close();
}


// Handler for unrecoverable errors (e.g. during hardware init).
// Flashes red LED at given speed.  Does not return!
void error(int time) {
  digitalWrite(GREEN_LED, LOW);  // Green LED off
  for(;;) {                      // Red LED flashes indefinitely
    digitalWrite(RED_LED, HIGH);
    delay(time);                 // Speed indicates error type
    digitalWrite(RED_LED, LOW); 
    delay(time);
  }
}


// Scans image directory for next unused, available image filename.
// This is somewhat hacky-tacky...fine for an Arduino novelty sketch,
// but not totally bulletproof (e.g. does not create new directories
// if the current one is completely full, hardcoded index to image
// number, etc.).  On return, global var 'filename' contains the full
// absolute path to the next available image name.  The file is not
// opened here -- that's the responsibility of the calling function.
void nextFilename(void) {
  // filename format is "DCIM/CANON999/IMG_nnnn.JPG";
  // Start of image # is at pos            ^ 18
  // If you decide to change the path or name, the index into
  // filename[] will need to be changed to suit.
  for(;;) {
    // Screwy things will happen if over 10,000 images in folder.
    // As explained above, this is not industrial-grade code.  It's
    // expecting other limits (e.g. FAT16 stuff) will be hit first.

    // sprintf() is a costly function to invoke (about 2K of code),
    // so this instead assembles the filename manually:
    filename[18] = '0' +  imgNum / 1000;
    filename[19] = '0' + (imgNum /  100) % 10;
    filename[20] = '0' + (imgNum /   10) % 10;
    filename[21] = '0' +  imgNum         % 10;
    if(!SD.exists(filename)) return; // Name available!
    imgNum++;                        // Keep looking
  }
}


// Callback function for timestamps on SD files.
// Thanks to forum user 'fat16lib' for guidance!
void dateTime(uint16_t* date, uint16_t* time) {
  DateTime now = clock.now();
  *date = FAT_DATE(now.year(), now.month(), now.day());
  *time = FAT_TIME(now.hour(), now.minute(), now.second());
}


// Timer1 interrupt handler for sleep throb
ISR(TIMER1_OVF_vect, ISR_NOBLOCK) {
  // Sine table contains only first half...reflect for second half...
  analogWrite(GREEN_LED, pgm_read_byte(&sleepTab[
    (sleepPos >= sizeof(sleepTab)) ?
    ((sizeof(sleepTab) - 1) * 2 - sleepPos) : sleepPos]));
  if(++sleepPos >= ((sizeof(sleepTab) - 1) * 2)) sleepPos = 0; // Roll over
  TIFR1 |= TOV1; // Clear Timer1 interrupt flag
}
