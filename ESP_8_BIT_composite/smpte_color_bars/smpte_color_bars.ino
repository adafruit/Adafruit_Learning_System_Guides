// SPDX-FileCopyrightText: 2022 John Park for Adafruit
// SPDX-License-Identifier: GPL-3.0-or-later

/*
 Adafruit NTSC SMPTE color bars (resolution is 256x224, colors are approximate at best)
uses composite video generator library on ESP32 by Roger Cheng
Connect GPIO25 (A0 on QT Py ESP32 Pico) to signal line, usually the center of composite video plug.
Please disable PSRAM option before uploading to the board, otherwise there may be vertical jitter.
*/

#include <ESP_8_BIT_GFX.h>


// Create an instance of the graphics library
ESP_8_BIT_GFX videoOut(true /* = NTSC */, 8 /* = RGB332 color */);

uint8_t WHITE = 0xFF ;
uint8_t DIM_WHITE = 0xB6 ;
uint8_t YELLOW =  0xF4 ;
uint8_t TEAL = 0x1C ;
uint8_t GREEN = 0x70 ; 
uint8_t MAGENTA =  0x83 ;
uint8_t RED = 0x82 ; 
uint8_t BLUE =  0x0B ;
uint8_t DARK_BLUE = 0x06 ;
uint8_t PURPLE = 0x23 ;
uint8_t BLACK =  0x00 ;
uint8_t GRAY =  0x24 ;
uint8_t LIGHT_GRAY = 0x29 ;

uint8_t height_tall = 149 ;
uint8_t height_squat = 19 ;
uint8_t height_med = 56 ;

uint8_t width_med = 36 ; 
uint8_t width_large = 46;
uint8_t width_skinny = 12 ;

uint8_t row2_y = height_tall ;
uint8_t row3_y = height_tall + height_squat ;


void setup() {
  // Initial setup of graphics library
  videoOut.begin();
}

void loop() {
    // Wait for the next frame to minimize chance of visible tearing
    videoOut.waitForFrame();
    
    // Clear screen
    videoOut.fillScreen(0);

    // Draw  rectangles
    //row 1
    videoOut.fillRect(0, 0, width_med, height_tall, DIM_WHITE);
    videoOut.fillRect(width_med, 0, width_med, height_tall, YELLOW);
    videoOut.fillRect(width_med*2, 0, width_med, height_tall, TEAL);
    videoOut.fillRect(width_med*3, 0, width_med, height_tall, GREEN);
    videoOut.fillRect(width_med*4, 0, width_med, height_tall, MAGENTA);
    videoOut.fillRect(width_med*5, 0, width_med, height_tall, RED);
    videoOut.fillRect(width_med*6, 0, width_med, height_tall, BLUE);
    //row 2
    videoOut.fillRect(0, row2_y, width_med, height_squat, BLUE);
    videoOut.fillRect(width_med, row2_y, width_med, height_squat, GRAY);
    videoOut.fillRect(width_med*2, row2_y, width_med, height_squat, MAGENTA); 
    videoOut.fillRect(width_med*3, row2_y, width_med, height_squat, GRAY); 
    videoOut.fillRect(width_med*4, row2_y, width_med, height_squat, TEAL); 
    videoOut.fillRect(width_med*5, row2_y, width_med, height_squat, GRAY); 
    videoOut.fillRect(width_med*6, row2_y , width_med, height_squat, DIM_WHITE); 
    //row 3
    videoOut.fillRect(0, row3_y, width_large, height_med, DARK_BLUE);
    videoOut.fillRect(width_large, row3_y, width_large, height_med, WHITE);   
    videoOut.fillRect(width_large*2, row3_y, width_large, height_med, PURPLE);  
    videoOut.fillRect(width_large*3, row3_y, width_large, height_med, GRAY); 
    videoOut.fillRect(width_large*4, row3_y, width_skinny, height_med, BLACK);
    videoOut.fillRect(width_large*4+width_skinny, row3_y, width_skinny, height_med, GRAY);
    videoOut.fillRect(((width_large*4)+(width_skinny*2)), row3_y , width_skinny, height_med, LIGHT_GRAY);
    videoOut.fillRect(width_med*6, row3_y , width_med, height_med, GRAY);
   

    // Draw text
     videoOut.setCursor(144, 180);
     videoOut.setTextColor(0xFF);
     videoOut.print("Adafruit NTSC");
     videoOut.setCursor(144, 190);
     videoOut.setTextColor(0xFF);
     videoOut.print("composite video");
     
}
