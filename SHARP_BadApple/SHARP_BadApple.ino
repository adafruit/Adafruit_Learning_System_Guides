// SPDX-FileCopyrightText: 2020 Melissa LeBlanc-Williams for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// Bad Apple for ESP32 with OLED SSD1306 | 2018 by Hackerspace-FFM.de | MIT-License.
// Adapted for Sharp Memory display + Itsy Bitsy M4 - put video.hs on QSPI storage using CircuitPython
#include "heatshrink_decoder.h"

#include "SdFat.h"
#include "Adafruit_SPIFlash.h"
#include <Adafruit_SharpMem.h>
#define BLACK 0
#define WHITE 1

#define SCALE 3


#if HEATSHRINK_DYNAMIC_ALLOC
#error HEATSHRINK_DYNAMIC_ALLOC must be false for static allocation test suite.
#endif

static heatshrink_decoder hsd;

// global storage for putPixels 
int16_t curr_x = 0;
int16_t curr_y = 0;

// global storage for decodeRLE
int32_t runlength = -1;
int32_t c_to_dup = -1;

uint32_t lastRefresh = 0;

#define SHARP_SS   A5
Adafruit_SharpMem display(&SPI, SHARP_SS, 400, 240, 3000000);
#define X_OFFSET (400 - SCALE*128) / 2
#define Y_OFFSET (240 - SCALE*64) / 2
  
Adafruit_FlashTransport_QSPI flashTransport;
Adafruit_SPIFlash flash(&flashTransport);
FatFileSystem fatfs;


void putPixels(uint8_t c, int32_t len) {
  static uint8_t color;
  uint8_t b = 0;
  while(len--) {
    b = 128;
    for (int i=0; i<8; i++) {
      if (c & b) {
        color = WHITE;  
      } else {
        color = BLACK; 
      }
      b >>= 1;
      if (color == BLACK) {
        // we clear the buffer each frame so only black pixels need to be drawn
        display.fillRect(X_OFFSET+curr_x*SCALE, Y_OFFSET+curr_y*SCALE, SCALE, SCALE, color);
      }
      curr_x++;
      if(curr_x >= 128) {
        curr_x = 0;
        curr_y++;
        if(curr_y >= 64) {
          curr_y = 0;
          display.refresh();
          display.clearDisplayBuffer();
          // 30 fps target rate
          //if(digitalRead(0)) while((millis() - lastRefresh) < 33) ;
          //lastRefresh = millis();
        }
      }
    }
  }
}

void decodeRLE(uint8_t c) {
    if(c_to_dup == -1) {
      if((c == 0x55) || (c == 0xaa)) {
        c_to_dup = c;
      } else {
        putPixels(c, 1);
      }
    } else {
      if(runlength == -1) {
        if(c == 0) {
          putPixels(c_to_dup & 0xff, 1);
          c_to_dup = -1;
        } else if((c & 0x80) == 0) {
          if(c_to_dup == 0x55) {
            putPixels(0, c);
          } else {
            putPixels(255, c);
          }
          c_to_dup = -1;
        } else {
          runlength = c & 0x7f;
        }
      } else {
        runlength = runlength | (c << 7);
          if(c_to_dup == 0x55) {
            putPixels(0, runlength);
          } else {
            putPixels(255, runlength);
          }
          c_to_dup = -1;  
          runlength = -1;        
      }
    }
}

#define RLEBUFSIZE 4096
#define READBUFSIZE 2048
void readFile(const char * path){
    static uint8_t rle_buf[RLEBUFSIZE];
    size_t rle_bufhead = 0;
    size_t rle_size = 0; 
  
    size_t filelen = 0;
    size_t filesize;
    static uint8_t compbuf[READBUFSIZE];
    
    Serial.printf("Reading file: %s\n", path);
    File file = fatfs.open(path);
    if(!file || file.isDirectory()){
        Serial.println("Failed to open file for reading");
        display.println("File open error. Upload video.hs using CircuitPython"); 
        display.refresh();
        return;
    }
    filelen = file.size();
    filesize = filelen;
    Serial.printf("File size: %d\n", filelen);

    // init display, putPixels and decodeRLE
    display.clearDisplay();
    display.refresh();
    curr_x = 0;
    curr_y = 0;
    runlength = -1;
    c_to_dup = -1;   
    lastRefresh = millis(); 

    // init decoder
    heatshrink_decoder_reset(&hsd);
    size_t   count  = 0;
    uint32_t sunk   = 0;
    size_t toRead;
    size_t toSink = 0;
    uint32_t sinkHead = 0;
    

    // Go through file...
    while(filelen) {
      if(toSink == 0) {
        toRead = filelen;
        if(toRead > READBUFSIZE) toRead = READBUFSIZE;
        file.read(compbuf, toRead);
        filelen -= toRead;
        toSink = toRead;
        sinkHead = 0;
      }

      // uncompress buffer
      HSD_sink_res sres;
      sres = heatshrink_decoder_sink(&hsd, &compbuf[sinkHead], toSink, &count);
      //Serial.print("^^ sinked ");
      //Serial.println(count);      
      toSink -= count;
      sinkHead = count;        
      sunk += count;
      if (sunk == filesize) {
        heatshrink_decoder_finish(&hsd);
      }
        
      HSD_poll_res pres;
      do {
          rle_size = 0;
          pres = heatshrink_decoder_poll(&hsd, rle_buf, RLEBUFSIZE, &rle_size);
          //Serial.print("^^ polled ");
          //Serial.println(rle_size);
          if(pres < 0) {
            Serial.print("POLL ERR! ");
            Serial.println(pres);
            return;
          }

          rle_bufhead = 0;
          while(rle_size) {
            rle_size--;
            if(rle_bufhead >= RLEBUFSIZE) {
              Serial.println("RLE_SIZE ERR!");
              return;
            }
            decodeRLE(rle_buf[rle_bufhead++]);
          }
      } while (pres == HSDR_POLL_MORE);
    }
    file.close();
    Serial.println("Done.");
}



void setup(){
    Serial.begin(115200);
    //while (!Serial) delay(10);
    Serial.println("Bad apple");

    flash.begin();
    // Init file system on the flash
    fatfs.begin(&flash);
  
    display.begin();
    display.clearDisplay();
    display.setTextColor(BLACK, WHITE);
    display.setTextSize(2);
    display.println("Scaled Bad Apple For SHARP Memory");
    display.refresh();       

    readFile("/video.hs");
}

void loop(){

}
