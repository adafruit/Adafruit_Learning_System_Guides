#include <Wire.h>
#include "Adafruit_TCS34725.h"
#include <Adafruit_NeoPixel.h>
#include "Flora_Pianoglove.h"


// we only play a note when the clear response is higher than a certain number 
#define CLEARTHRESHHOLD 2000

#define LOWTONE 1000
#define HIGHTONE 2000

// high C
#define LOWKEY 64 
// double high C
#define HIGHKEY 76

// our RGB -> eye-recognized gamma color
byte gammatable[256];

// color sensor
Adafruit_TCS34725 tcs = Adafruit_TCS34725(TCS34725_INTEGRATIONTIME_50MS, TCS34725_GAIN_4X);
// one pixel on pin 6
Adafruit_NeoPixel strip = Adafruit_NeoPixel(1, 6, NEO_GRB + NEO_KHZ800);


void setup() {
  Serial.begin(9600);
  Serial.println("Color Piano!");

  if (tcs.begin()) {
    Serial.println("Found sensor");
  } else {
    Serial.println("No TCS34725 found ... check your connections");
    while (1); // halt!
  }
  
  strip.begin();
  strip.show(); // Initialize all pixels to 'off'

  // thanks PhilB for this gamma table!
  // it helps convert RGB colors to what humans see
  for (int i=0; i<256; i++) {
    float x = i;
    x /= 255;
    x = pow(x, 2.5);
    x *= 255;
      
    gammatable[i] = x;      

    //Serial.println(gammatable[i]);
  }
  
  // tone output on OC1A / D9
  pinMode(9, OUTPUT);
  // toggle output
  TCCR1A = _BV(COM1A1);
  // PWM phase and freq correct
  TCCR1B = _BV(WGM13) | _BV(CS11);  // div by 8
  setFreq(880);
}

void setFreq(uint16_t f) {
  if (f == 0) {
    TCCR1B = 0;  // turn off
  } else {
    TCCR1B = _BV(WGM13) | _BV(CS11);   // div by 8
  }
  uint32_t i = F_CPU / 16;  // div by 8 and 2
  i /= f;
  ICR1 = i;
  OCR1A = i/2;
}

void loop() {
  uint16_t clear, red, green, blue;

  tcs.setInterrupt(false);      // turn on LED

  delay(60);  // takes 50ms to read 
  
  tcs.getRawData(&red, &green, &blue, &clear);

  tcs.setInterrupt(true);  // turn off LED

  // not close enough to colorful item
  if (clear < CLEARTHRESHHOLD) {
    setFreq(0);
    strip.setPixelColor(0, strip.Color(0, 0, 0)); // turn off the LED
    strip.show();
    return;
  }
  
  Serial.print("C:\t"); Serial.print(clear);
  Serial.print("\tR:\t"); Serial.print(red);
  Serial.print("\tG:\t"); Serial.print(green);
  Serial.print("\tB:\t"); Serial.print(blue);

  // Figure out some basic hex code for visualization
  uint32_t sum = red;
  sum += green;
  sum += blue;
  sum = clear;
  float r, g, b;
  r = red; r /= sum;
  g = green; g /= sum;
  b = blue; b /= sum;
  r *= 256; g *= 256; b *= 256;
  if (r > 255) r = 255;
  if (g > 255) g = 255;
  if (b > 255) b = 255;
  
  Serial.print("\t");
  Serial.print((int)r, HEX); Serial.print((int)g, HEX); Serial.print((int)b, HEX); 
  Serial.println();
 
  
  // OK we have to find the two primary colors
  // check if blue is smallest. MEME: fix for 'white'
  float remove, normalize;
  if ((b < g) && (b < r)) {
    remove = b;
    normalize = max(r-b, g-b);
  } else if ((g < b) && (g < r)) {
    remove = g;
    normalize = max(r-g, b-g);
  } else {
    remove = r;
    normalize = max(b-r, g-r);
  }
  // get rid of minority report
  float rednorm = r - remove;
  float greennorm = g - remove;
  float bluenorm = b - remove;
  // now normalize for the highest number
  rednorm /= normalize;
  greennorm /= normalize;
  bluenorm /= normalize;

  Serial.println();
  strip.setPixelColor(0, strip.Color(gammatable[(int)r], gammatable[(int)g], gammatable[(int)b]));
  strip.show();

  Serial.print(rednorm); Serial.print(", "); 
  Serial.print(greennorm); Serial.print(", "); 
  Serial.print(bluenorm); Serial.print(" "); 
  Serial.println();

  float rainbowtone = 0;
  
  if (bluenorm <= 0.1) {
    // between red and green
    if (rednorm >= 0.99) {
      // between red and yellow
      rainbowtone = 0 + 0.2 * greennorm;
    } else {
      // between yellow and green
      rainbowtone = 0.2 + 0.2 * (1.0 - rednorm);
    }
  } else if (rednorm <= 0.1) {
    // between green and blue
    if (greennorm >= 0.99) {
      // between green and teal
      rainbowtone = 0.4 + 0.2 * bluenorm;
    } else {
      // between teal and blue
      rainbowtone = 0.6 + 0.2 * (1.0 - greennorm);
    }
  } else {
    // between blue and violet
    if (bluenorm >= 0.99) {
      // between blue and violet
      rainbowtone = 0.8 + 0.2 * rednorm;
    } else {
      // between teal and blue
      rainbowtone = 0; 
    }
  }
  
  Serial.print("Scalar "); Serial.println(rainbowtone);
  float keynum = LOWKEY + (HIGHKEY - LOWKEY) * rainbowtone;
  Serial.print("Key #"); Serial.println(keynum);
  float freq = pow(2, (keynum - 49) / 12.0) * 440;
  Serial.print("Freq = "); Serial.println(freq);  
  //Serial.print((int)r ); Serial.print(" "); Serial.print((int)g);Serial.print(" ");  Serial.println((int)b );
  setFreq(freq);
}



RgbColor HsvToRgb(HsvColor hsv)
{
    RgbColor rgb;
    unsigned char region, remainder, p, q, t;

    if (hsv.s == 0)
    {
        rgb.r = hsv.v;
        rgb.g = hsv.v;
        rgb.b = hsv.v;
        return rgb;
    }

    region = hsv.h / 43;
    remainder = (hsv.h - (region * 43)) * 6; 

    p = (hsv.v * (255 - hsv.s)) >> 8;
    q = (hsv.v * (255 - ((hsv.s * remainder) >> 8))) >> 8;
    t = (hsv.v * (255 - ((hsv.s * (255 - remainder)) >> 8))) >> 8;

    switch (region)
    {
        case 0:
            rgb.r = hsv.v; rgb.g = t; rgb.b = p;
            break;
        case 1:
            rgb.r = q; rgb.g = hsv.v; rgb.b = p;
            break;
        case 2:
            rgb.r = p; rgb.g = hsv.v; rgb.b = t;
            break;
        case 3:
            rgb.r = p; rgb.g = q; rgb.b = hsv.v;
            break;
        case 4:
            rgb.r = t; rgb.g = p; rgb.b = hsv.v;
            break;
        default:
            rgb.r = hsv.v; rgb.g = p; rgb.b = q;
            break;
    }

    return rgb;
}

HsvColor RgbToHsv(RgbColor rgb)
{
    HsvColor hsv;
    unsigned char rgbMin, rgbMax;

    rgbMin = rgb.r < rgb.g ? (rgb.r < rgb.b ? rgb.r : rgb.b) : (rgb.g < rgb.b ? rgb.g : rgb.b);
    rgbMax = rgb.r > rgb.g ? (rgb.r > rgb.b ? rgb.r : rgb.b) : (rgb.g > rgb.b ? rgb.g : rgb.b);

    hsv.v = rgbMax;
    if (hsv.v == 0)
    {
        hsv.h = 0;
        hsv.s = 0;
        return hsv;
    }

    hsv.s = 255 * long(rgbMax - rgbMin) / hsv.v;
    if (hsv.s == 0)
    {
        hsv.h = 0;
        return hsv;
    }

    if (rgbMax == rgb.r)
        hsv.h = 0 + 43 * (rgb.g - rgb.b) / (rgbMax - rgbMin);
    else if (rgbMax == rgb.g)
        hsv.h = 85 + 43 * (rgb.b - rgb.r) / (rgbMax - rgbMin);
    else
        hsv.h = 171 + 43 * (rgb.r - rgb.g) / (rgbMax - rgbMin);

    return hsv;
}
