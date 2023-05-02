
/*
DotStar POV poi using Adafruit Feather RP2040 RFM. Unlike prior POV poi
projects, rather than compile in graphics in arrays, they're stored in BMP
format on the board's CIRCUITPY flash filesystem.

Run-time configuration is stored in CIRCUITPY/poi.cfg and resembles:

{
  "dotstar_length" : 36,
  "dotstar_data"   : 3,
  "dotstar_clock"  : 2,
  "dotstar_order"  : "BGR",
  "brightness"     : 255,
  "gamma"          : 2.6,
  "path"           : "images",
  "program" : [[ "one.bmp", 5.0, 5.0 ],
               [ "two.bmp", 10.0, 3.0 ],
               [ "three.bmp", 1.0, 3.0 ]]
}

Be warned that JSON is notoriously picky, and even a single missing or
excess comma will stop everything in its tracks (the format isn't really
designed for human editing, but there's a robust, ready-made JSON library
that saves us a TON of would-be config-parsing code).
*/


//34567890123456789012345678901234567890123456789012345678901234567890123456



#include <Adafruit_DotStar.h>
#include <RH_RF69.h>
#include <Adafruit_CPFS.h>
#include <ArduinoJson.h>

// Extern functions in bmp.cpp:
extern bool bmpHeight(FatVolume *fs, char *filename, int32_t *height);
extern bool loadBMP(FatVolume *fs, char *filename, uint8_t *dest,
                    const uint16_t dest_width, const uint8_t rOffset,
                    const uint8_t gOffset, const uint8_t bOffset,
                    const float brightness, const float gamma);

// Some general global stuff -----------------------------------------------
FatVolume           *fs;                // CIRCUITPY filesystem
volatile bool        core1_wait = true; // For syncing RP2040's two cores
int                  error_code = 0;    // >= 1 on startup error
DeserializationError json_error;        // For JSON-specific errors
struct {
  char    *msg; // Error message to Serial console
  uint16_t ms;  // LED blink rate, milliseconds
} err[] = {
  "poi.cfg syntax error"        , 250, // json_error will be set
  "poi.cfg not found"           , 250,
  "Can't access CIRCUITPY drive", 100,
  "Radio init error"            , 500,
};

// DotStar- and image-related stuff ----------------------------------------
typedef struct {         // Per-image structure:
  uint32_t   usec_pass;  // Time for each pass of image, microseconds
  uint32_t   total_usec; // Total display time of image, microseconds
  int32_t    height;     // Image height in pixels
  union {
    char     name[30];   // BMP filename (within path), not used after load
    uint8_t *data;       // -> first scanline, not used before load
  };
} img;
Adafruit_DotStar *strip              = NULL;  // DotStar alloc'd after config
uint16_t          dotstar_length     = 36;    // Default = 1/4m of 144 strip
int8_t            dotstar_clock      = 2;     // " = SDA pin on Feather RP2040
int8_t            dotstar_data       = 3;     // " = SCL pin on Feather RP2040
uint8_t           dotstar_order      = DOTSTAR_BRG;
float             dotstar_brightness = 255.0;
float             dotstar_gamma      = 2.6;
uint8_t           rOffset            = 1;
uint8_t           gOffset            = 2;
uint8_t           bOffset            = 0;
char              path[50]           = "";   // Path to images ("" = root)
uint16_t          num_images         = 1;    // Image count (1 for "off" image)
uint32_t          total_height       = 1;    // Sum of image heights (1 for "off")
img              *imglist            = NULL; // Image array (allocated before load)
uint8_t          *linebuf            = NULL; // Data for ALL images
volatile uint16_t imgnum             = 0;
volatile uint32_t last_change        = 0;
// linebuf is dynamically allocated after config read to contain ALL POV
// data used in performance; images are NOT loaded dynamically as needed.
// This is to help ensure quick program change and keep all the poi in
// better sync. Free RAM on RP2040 after code's needs is about 250K.
// At 3 bytes/pixel, a 36-pixel poi can hold a bit over 2,000 lines.

// Radio-related stuff -----------------------------------------------------

#define ENCRYPTKEY  "sampleEncryptKey" // Use same 16 char on ALL nodes
#define IS_RFM69HCW true               // Set true if using RFM69HCW module
#define RFM69_CS    16                 // Chip-select pin
#define RFM69_RST   17                 // Radio reset pin
#define RFM69_INT   21                 // Interrupt pin
#define NETWORKID   1
#define NODEID      255
#define INTERVAL    250000             // Broadcast interval, microseconds
#define LATENCY     1000               // Encode, xmit, decode microseconds

RH_RF69 *radio;
bool     sender = false; // Radio send vs receive
uint32_t last_xmit   = 0;

// The PRIMARY CORE runs all the non-deterministic grunt work --
// Filesystem/config init, talking to the radio and infrared,
// keeping the CIRCUITPY filesystem alive.

void setup() { // Core 0 start-up code

  // Start the CIRCUITPY flash filesystem first. Very important!
  fs = Adafruit_CPFS::begin();

  Serial.begin(115200);
  // while (!Serial);

  if (fs) { // Filesystem OK?
    StaticJsonDocument<1024> doc;
    FatFile                  file;

    // Open configuration file and attempt to decode JSON data within.
    if ((file = fs->open("poi.cfg", FILE_READ))) {
      json_error = deserializeJson(doc, file);
      file.close();
      if (!json_error) {
        // Config is valid, override defaults in program variables...
        dotstar_length     = doc["dotstar_length"] | dotstar_length;
        dotstar_clock      = doc["dotstar_clock"]  | dotstar_clock;
        dotstar_data       = doc["dotstar_data"]   | dotstar_data;
        dotstar_brightness = doc["brightness"]     | dotstar_brightness;
        dotstar_gamma      = doc["gamma"]          | dotstar_gamma;
        JsonVariant v      = doc["dotstar_order"];
        if (v.is<const char *>()) { // Present and is a string?
          const struct {
            const char *key; // String version of color order, e.g. "RGB"
            uint8_t     val; // Numeric version of same, e.g. DOTSTAR_RGB
            uint8_t     offset[3]; // Red, green, blue indices
          } dict[] = {
            "RGB", DOTSTAR_RGB, { 0, 1, 2 },
            "RBG", DOTSTAR_RBG, { 0, 2, 1 },
            "GRB", DOTSTAR_GRB, { 1, 0, 2 },
            "GBR", DOTSTAR_GBR, { 2, 0, 1 },
            "BRG", DOTSTAR_BRG, { 1, 2, 0 },
            "BGR", DOTSTAR_BGR, { 2, 1, 0 },
          };
          for (uint8_t i=0; i< sizeof dict / sizeof dict[0]; i++) {
            if (!strcasecmp(v, dict[i].key)) {
              dotstar_order = dict[i].val;
              rOffset       = dict[i].offset[0];
              gOffset       = dict[i].offset[1];
              bOffset       = dict[i].offset[2];
              break;
            }
          }
        }
  
        // Validate inputs; clip to ranges
        rOffset            = min(max(rOffset           , 0  ),  2   );
        gOffset            = min(max(gOffset           , 0  ),  2   );
        bOffset            = min(max(bOffset           , 0  ),  2   );
        dotstar_data       = min(max(dotstar_data      , 0  ),  29  );
        dotstar_clock      = min(max(dotstar_clock     , 0  ),  29  );
        dotstar_brightness = min(max(dotstar_brightness, 0.0), 255.0);

        sender = doc["sender"] | sender; // true if xmit, false if recv

        v = doc["path"];
        if (v.is<const char *>()) {
          strncpy(path, v, sizeof path - 1);
          path[sizeof path - 1] = 0;
          // Strip trailing / if present
          int n = strlen(path) - 1;
          while ((n >= 0) && (path[n] == '/')) path[n--] = 0;
        }

        v = doc["program"];
        if (v.is<JsonArray>()) {
          num_images += v.size();
          if ((imglist = (img *)malloc(num_images * sizeof(img)))) {
            for (int i=1; i<num_images; i++) {
              JsonVariant v2 = v[i - 1];
              if (v2.is<JsonArray>() && (v2.size() == 3)) {
                char filename[80];
                strncpy(imglist[i].name, (char *)v2[0].as<const char*>(), sizeof imglist[i].name);
                imglist[i].name[sizeof imglist[i].name - 1] = 0;
                float reps_sec = v2[1].as<float>();
                if (reps_sec > 0.0) {
                  imglist[i].usec_pass = (uint32_t)(1000000.0 / reps_sec);
                } else {
                  imglist[i].usec_pass = 1;
                }
                imglist[i].total_usec = (uint32_t)(1000000.0 * fabs(v2[2].as<float>()));
                sprintf(filename, "%s/%s", path, imglist[i].name);
                if (bmpHeight(fs, filename, &imglist[i].height))
                  total_height += imglist[i].height;
              }
            }
          }
        }
      } else error_code = 1; // end JSON decode
    } else   error_code = 2; // end config file open
  } else     error_code = 3; // end filesys

  // If Dotstar data and clock pins are on the same SPI instance,
  // and form a valid TX/SCK pair...
  if ((((dotstar_data / 8) & 1) == ((dotstar_clock / 8) & 1)) &&
      ((dotstar_data & 3) == 3) && ((dotstar_clock & 3) == 2)) {
    // Use hardware SPI for writing pixels. Most likely is spi0, NOT shared w/radio.
    spi_inst_t     *inst = ((dotstar_data / 8) & 1) ? spi1 : spi0;
    SPIClassRP2040 *spi  = new SPIClassRP2040(spi0, -1, -1, dotstar_clock, dotstar_data);
    strip = new Adafruit_DotStar(dotstar_length, dotstar_order, (SPIClass *)spi);
  } else { // Use bitbang for writing pixels (slower, but any 2 pins)
    strip = new Adafruit_DotStar(dotstar_length, dotstar_data, dotstar_clock, dotstar_order);
  }

  // If no image alloc above, make a single "off" image instance:
  if (!imglist) imglist = (img *)malloc(sizeof(img));

  if ((linebuf = (uint8_t *)calloc(dotstar_length * total_height, 3))) {
    uint8_t *dest = linebuf + dotstar_length * 3;
    for (int i=1; i<num_images; i++) {
      char filename[80];
      sprintf(filename, "%s/%s", path, imglist[i].name);
      if (loadBMP(fs, filename, dest, dotstar_length, rOffset,
                  gOffset, bOffset, dotstar_brightness, dotstar_gamma)) {
        imglist[i].data = dest;
        dest           += imglist[i].height * dotstar_length * 3;
      } else {
        // Image load error is not fatal; set data to the "off" image:
        imglist[i].data   = linebuf;
        imglist[i].height = 1;
      }
    }
  } else {
    // If all-images alloc fails, alloc just the single "off" image:
    linebuf = (uint8_t *)calloc(dotstar_length, 3);
  }

  // Initialize the "off" image:
  imglist[0].data       = linebuf;
  imglist[0].height     = 1;
  imglist[0].usec_pass  = 1;
  imglist[0].total_usec = 1000000;

  imgnum      = 0;
  last_change = micros();

  if (strip) {
    strip->begin();
    core1_wait = false; // All initialized, core 1 can proceed
  }

  radio = new RH_RF69(RFM69_CS, RFM69_INT);

  pinMode(LED_BUILTIN, OUTPUT);     
  digitalWrite(LED_BUILTIN, LOW);     
  pinMode(RFM69_RST, OUTPUT);
  digitalWrite(RFM69_RST, LOW);

  // Manual reset of radio
  digitalWrite(RFM69_RST, HIGH);
  delay(10);
  digitalWrite(RFM69_RST, LOW);
  delay(10);

  // Initialize radio
  if (radio) {
    radio->init();
    radio->setFrequency(915.0);
    radio->setTxPower(14, true);
    radio->setEncryptionKey((uint8_t *)ENCRYPTKEY);
  } else error_code = 4;
}

uint8_t buf[RH_RF69_MAX_MESSAGE_LEN] __attribute__ ((aligned(4)));

void loop() {
  uint32_t now = micros();

  if (error_code) {
    digitalWrite(LED_BUILTIN, (now / (err[error_code - 1].ms * 1000)) & 1);
    if ((now - last_change) >= 1000000) {
      Serial.printf("ERROR: %s\r\n", err[error_code - 1].msg);
      if (json_error) {
        Serial.print("JSON error: ");
        Serial.println(json_error.c_str());
      }
      last_change = now;
    }
  } else if (sender) {
    bool     xmit    = false; // Will be set true if it's time to send
    uint32_t elapsed = now - last_change;

    if (elapsed >= imglist[imgnum].total_usec) {
      elapsed -= imglist[imgnum].total_usec; // Partly into new image
      if (++imgnum >= num_images) imgnum = 1;
      last_change = now;
      xmit        = true;
    } else if ((now - last_xmit) >= INTERVAL) {
      xmit = true;
    }
    if (xmit) {
      radio->waitPacketSent();
      memcpy(&buf[0], &elapsed        , 4);
      memcpy(&buf[4], (void *)&imgnum , 2);
      memcpy(&buf[6], &buf[0]         , 6); // Rather than checksum, send data 2X
      last_xmit = now;
      radio->send((uint8_t *)buf, 12);
    }
  } else {
    if (radio->waitAvailableTimeout(250)) { 
      uint8_t len;
      if (radio->recv(buf, &len)) {
        Serial.print("got reply: ");
        Serial.println((char*)buf);
        if ((len == 12) && !memcmp(&buf[0], &buf[6], 6)) {
          uint32_t t = *(uint32_t *)(&buf[0]);
          uint16_t n = *(uint16_t *)(&buf[4]);
          if (n != imgnum) {
            imgnum      = n;
            last_change = now - t - LATENCY;
          } else {
            // Compare last change time against
            // our perception of elapsed time.
          }
        }
      } else {
        Serial.println("recv failed");
      }
    } else {
      Serial.println("No reply, is rf69_server running?");
    }
  }
}

// The SECOND CORE is then FULLY DEDICATED to keeping the LEDs
// continually refreshed, does not have to pause for other tasks.

void setup1() {
  while (core1_wait); // Wait for setup() to complete before going to loop1()
}

// TO DO: compensate for clock difference
void loop1() {
  // core1_wait won't release unless strip is non-NULL, this is OK...
  uint32_t row = imglist[imgnum].height * ((micros() - last_change) % imglist[imgnum].usec_pass) / imglist[imgnum].usec_pass;  
  memcpy(strip->getPixels(), imglist[imgnum].data + row * dotstar_length * 3, dotstar_length * 3);
  strip->show();
}
