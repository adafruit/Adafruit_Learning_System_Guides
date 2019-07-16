/*****************************************************************************
Sketch for testing WS2801 LED strands - lights one LED along length of strand.
Because only one LED is lit at a time, can safely be powered from Arduino +5V.
*****************************************************************************/

#include "SPI.h"

int nPixels = 150;

void setup() {
  SPI.begin();
  SPI.setBitOrder(MSBFIRST);
  SPI.setDataMode(SPI_MODE0);
  SPI.setClockDivider(SPI_CLOCK_DIV16); // 1 MHz
}

int p = 0; // Current pixel being lit

void loop() {
  int  i, j;

  // Issue data for all LEDs in strand regardless  
  for (i=0; i < nPixels; i++) {
    // Each LED = 3 bytes; white if current pixel, else off
    for(j=0; j < 3; j++) {
      SPI.transfer((i == p) ? 0xff : 0x00);
    }
  }

  // LEDs automatically latch on pause
  delay(25);

  // Advance to next pixel, then back to start
  if(++p >= nPixels) p = 0;
}
