// SPDX-FileCopyrightText: 2023 Liz Clark for Adafruit Industries
// SPDX-License-Identifier: MIT

#include <PicoDVI.h>

DVIGFX16 display(DVI_RES_320x240p60, adafruit_feather_dvi_cfg);

// colors
#define BLACK    0x0000
#define BLUE     0x001F
#define RED      0xF800
#define GREEN    0x07E0
#define CYAN     0x07FF
#define MAGENTA  0xF81F
#define YELLOW   0xFFE0 
#define WHITE    0xFFFF

// button and led pins
const int indexPin = 5;
const int ledPin = 6;
const int shebangPin = 9;
const int shebangLed = 10;

//pot pins
int pot0 = A0;
int pot1 = A3;
int pot2 = A2;
int pot3 = A1;

int potVal0;
int potVal1;
int potVal2;
int potVal3;

#define N_TRI 75
struct {
  int16_t pos[2]; // position (X,Y)
  int8_t  vel[2]; // velocity (X,Y)
} tri[N_TRI];

int h;
int w;

int synth_index = 0;
int last_r = 0;
int last_smolR = 0;
int last_c = 0;
int radi;
int cir_color;
int triangle_count = 0;
int sunX = 166;
int sunY = 113;

int index_reading;
bool index_state = false;
bool is_static = false;
bool is_target = false;
bool is_wavylines = false;
bool is_synthwave = false;
bool is_orbits = false;
bool shebang_pressed = false;

int rate1 = 0;
int rate2 = 100;
int rate3 = 50;
int rate4 = 210;

int last_i = 121;

int cycle = 0;

uint8_t r,g,b;
uint16_t rgb;
uint16_t bgr;
uint16_t brg;
uint16_t gbr;

float last_x1 = 100;
float last_y1 = 120;
float last_x2 = 100;
float last_y2 = 120;
float last_x3 = 100;
float last_y3 = 120;
float last_x4 = 100;
float last_y4 = 120;

void setup() { 
  if (!display.begin()) { // Blink LED if insufficient RAM
    pinMode(LED_BUILTIN, OUTPUT);
    for (;;) digitalWrite(LED_BUILTIN, (millis() / 500) & 1);
  }
  
  pinMode(indexPin, INPUT_PULLUP);
  pinMode(ledPin, OUTPUT);
  pinMode(shebangPin, INPUT_PULLUP);
  pinMode(shebangLed, OUTPUT);
  
  w = display.width();
  h = display.height();

  is_target = true;
}

void loop() {
  index_reading = button_listener(indexPin, ledPin);

  if (synth_index == 0) {
    is_orbits = false;
    if (is_target == false) {
      display.fillScreen(BLACK);
      is_target = true;
    }
    else {
    animate_target();
    }
   }
  
  else if (synth_index == 1) {
    is_target = false;
    if (is_static == false) {
      display.fillScreen(BLACK);
      begin_triangles();
    }
    else {
    animate_static();
    }
  }
  else if (synth_index == 2){
    is_static = false;
    if (is_synthwave == false) {
      display.fillScreen(BLACK);
      begin_synthwave();
    }
    else {
    animate_synthwave();
    }
  }
  else if (synth_index == 3){
    is_synthwave = false;
    if (is_wavylines == false) {
      display.fillScreen(BLACK);
      is_wavylines = true;
    }
    else {
    animate_wavylines();
    }
  }
  else {
    is_wavylines = false;
    if (is_orbits == false){
      display.fillScreen(BLACK);
      draw_stars(5000);
      is_orbits = true;
    }
    else {
    animate_orbits();
    }
  }
    
}

int shebang_listener(int pin) {
  int z = digitalRead(pin);
  return z;
}

int button_listener(int pin, int led) {
  int i = digitalRead(pin);
  if (i == LOW and index_state == false) {
    digitalWrite(led, HIGH);
    synth_index++;
    if (synth_index > 4) {
      synth_index = 0;
    }
    index_state = true;
    delay(200);
  }
  if (i == HIGH and index_state == true) {
    index_state = false;
    delay(200);
    digitalWrite(led, LOW);
  }
  return i;
}

void begin_synthwave() {
  sunX = 166;
  sunY = 113;
  draw_gradient(0, 0, w, 130);
  display.fillCircle(sunX, sunY, 65, MAGENTA);
  display.fillCircle(sunX, sunY, 60, RED);
  display.fillRect(0, 120, w, h, BLUE);
  display.drawFastHLine(0, 120, w, WHITE);

  display.drawLine(0, 136, 34, 120, WHITE);
  display.drawLine(0, 188, 76, 120, WHITE);
  display.drawLine(34, 240, 113, 120, WHITE);
  display.drawLine(117, 240, 148, 120, WHITE);
  display.drawLine(198, 240, 182, 120, WHITE);
  display.drawLine(294, 240, 216, 120, WHITE);
  display.drawLine(320, 176, 255, 120, WHITE);
  display.drawLine(320, 133, 297, 120, WHITE);

  is_synthwave = true;
}

void animate_synthwave() {
  int s = shebang_listener(shebangPin);
  if (s == LOW) {
    digitalWrite(shebangLed, HIGH);
    shebang_pressed = true;
    for (int i=146; i > 121; i-=2) {
      sunY = sunY - 2;
      index_reading = button_listener(indexPin, ledPin);
      potVal0 = analog_map(pot0, 25, 75);
      display.fillCircle(sunX, sunY, 65, MAGENTA);
      display.fillCircle(sunX, sunY, 60, RED);
      display.fillRect(0, 120, w, h, BLUE);
      display.drawFastHLine(0, 120, w, WHITE);
      
      display.drawFastHLine(0, 120, w, WHITE);
      display.drawLine(0, 136, 34, 120, WHITE);
      display.drawLine(0, 188, 76, 120, WHITE);
      display.drawLine(34, 240, 113, 120, WHITE);
      display.drawLine(117, 240, 148, 120, WHITE);
      display.drawLine(198, 240, 182, 120, WHITE);
      display.drawLine(294, 240, 216, 120, WHITE);
      display.drawLine(320, 176, 255, 120, WHITE);
      display.drawLine(320, 133, 297, 120, WHITE);
      display.drawFastHLine(0, 120, w, WHITE);
      display.drawFastHLine(0, last_i, w, BLUE);
      display.drawFastHLine(0, i, w, WHITE);
      display.drawFastHLine(0, last_i+25, w, BLUE);
      display.drawFastHLine(0, i+25, w, WHITE);
      display.drawFastHLine(0, last_i+50, w, BLUE);
      display.drawFastHLine(0, i+50, w, WHITE);
      display.drawFastHLine(0, last_i+75, w, BLUE);
      display.drawFastHLine(0, i+75, w, WHITE);
      display.drawFastHLine(0, last_i+100, w, BLUE);
      display.drawFastHLine(0, i+100, w, WHITE);
      last_i = i;
      if (index_reading == LOW) {
        break;
      }
      millisDelay(potVal0);
    }
  }
  else {
    if (shebang_pressed == true) {
        sunX = 166;
        sunY = 113;
        draw_gradient(0, 0, w, 130);
        display.fillCircle(sunX, sunY, 65, MAGENTA);
        display.fillCircle(sunX, sunY, 60, RED);
        display.fillRect(0, 120, w, h, BLUE);
        display.drawFastHLine(0, 120, w, WHITE);
        shebang_pressed = false;
      }
    digitalWrite(shebangLed, LOW);
    
    for (int i=121; i < 146; i+=2) {
      index_reading = button_listener(indexPin, ledPin);
      potVal0 = analog_map(pot0, 25, 75);
      
      display.drawFastHLine(0, 120, w, WHITE);
      display.drawLine(0, 136, 34, 120, WHITE);
      display.drawLine(0, 188, 76, 120, WHITE);
      display.drawLine(34, 240, 113, 120, WHITE);
      display.drawLine(117, 240, 148, 120, WHITE);
      display.drawLine(198, 240, 182, 120, WHITE);
      display.drawLine(294, 240, 216, 120, WHITE);
      display.drawLine(320, 176, 255, 120, WHITE);
      display.drawLine(320, 133, 297, 120, WHITE);
      display.drawFastHLine(0, 120, w, WHITE);
      display.drawFastHLine(0, last_i, w, BLUE);
      display.drawFastHLine(0, i, w, WHITE);
      display.drawFastHLine(0, last_i+25, w, BLUE);
      display.drawFastHLine(0, i+25, w, WHITE);
      display.drawFastHLine(0, last_i+50, w, BLUE);
      display.drawFastHLine(0, i+50, w, WHITE);
      display.drawFastHLine(0, last_i+75, w, BLUE);
      display.drawFastHLine(0, i+75, w, WHITE);
      display.drawFastHLine(0, last_i+100, w, BLUE);
      display.drawFastHLine(0, i+100, w, WHITE);
      last_i = i;
      if (index_reading == LOW) {
        break;
      }
      millisDelay(potVal0);
    }
    sunX = 166;
    sunY = 113;
  }
}

void animate_orbits() {
    index_reading = button_listener(indexPin, ledPin);
    potVal1 = analog_map(pot1, 1, 8);
    potVal2 = analog_map(pot2, 1, 8);
    potVal3 = analog_map(pot3, 1, 8);
    potVal0 = analog_map(pot0, 1, 8);
    int s = shebang_listener(shebangPin);
    if (s == HIGH) {
      if (shebang_pressed == true) {
        display.fillScreen(BLACK);
        draw_stars(5000);
        shebang_pressed = false;
      }
      digitalWrite(shebangLed, LOW);
      rate1 = rate1 + potVal1;
      if (rate1 > 360) {
        rate1 = 1;
      }
      rate2 = rate2 + potVal2;
      if (rate2 > 361) {
        rate2 = 1;
      }
      rate3 = rate3 + potVal3;
      if (rate3 > 361) {
        rate3 = 1;
      }
      rate4 = rate4 + potVal0;
      if (rate4 > 361) {
        rate4 = 1;
      }
      display.fillCircle(160, 120, 20, YELLOW);
      display.fillCircle(last_x1, last_y1, 4, 0);
      float x1 = sin(2*rate1*2*3.14/100);
      float y1 = cos(2*rate1*2*3.14/100);
      display.fillCircle(160+45*x1, 120-45*y1, 4, BLUE);
      last_x1 = 160+45*x1;
      last_y1 = 120-45*y1;
  
      display.fillCircle(last_x2, last_y2, 10, 0);
      float x2 = sin(2*rate2*2*3.14/100);
      float y2 = cos(2*rate2*2*3.14/100);
      display.fillCircle(160+60*x2, 120-60*y2, 10, RED);
      last_x2 = 160+60*x2;
      last_y2 = 120-60*y2;
  
      display.fillCircle(last_x3, last_y3, 8, 0);
      float x3 = sin(2*rate3*2*3.14/100);
      float y3 = cos(2*rate3*2*3.14/100);
      display.fillCircle(160+95*x3, 120-95*y3, 8, MAGENTA);
      last_x3 = 160+95*x3;
      last_y3 = 120-95*y3;
  
      display.fillCircle(last_x4, last_y4, 14, 0);
      float x4 = sin(2*rate4*2*3.14/100);
      float y4 = cos(2*rate4*2*3.14/100);
      display.fillCircle(160+150*x4, 120-150*y4, 14, GREEN);
      last_x4 = 160+150*x4;
      last_y4 = 120-150*y4;
    }
    else {
      digitalWrite(shebangLed, HIGH);
      shebang_pressed = true;
      int black_hole = 1;
      int falling_y1 = last_y1;
      int falling_y2 = last_y2;
      int falling_y3 = last_y3;
      int falling_y4 = last_y4;
      for (int i = 0; i < 250; i ++) {
        s = shebang_listener(shebangPin);
        draw_stars(500);
        display.fillCircle(last_x1, falling_y1 + i, 4, BLUE);
        display.fillCircle(last_x2, falling_y2 + i, 10, RED);
        display.fillCircle(last_x3, falling_y3 + i, 8, MAGENTA);
        display.fillCircle(last_x4, falling_y4 + i, 14, GREEN);
        display.fillCircle(160, 120, black_hole + i, BLACK);
        if (s == HIGH) {
          break;
        }
        millisDelay(50);
      }
      display.fillScreen(BLACK);
      draw_stars(5000);
    }

    millisDelay(75);
}

void begin_triangles() {
  for (int i=0; i<N_TRI; i++) {
    tri[i].pos[0] = 10 + random(w - 20);
    tri[i].pos[1] = 10 + random(h - 20);
    do {
      tri[i].vel[0] = 2 - random(5);
      tri[i].vel[1] = 2 - random(5);
    } while ((tri[i].vel[0] == 0) && (tri[i].vel[1] == 0));
  }
  is_static = true;
}

void animate_static() {
  index_reading = button_listener(indexPin, ledPin);
  potVal1 = analog_map(pot1, 0, 255);
  potVal2 = analog_map(pot2, 0, 255);
  potVal3 = analog_map(pot3, 0, 255);
  potVal0 = analog_map(pot0, 0, N_TRI);
  
  for (int i = 1; i < triangle_count; i++) {
    make_triangle(tri[i].pos[0], tri[i].pos[1], 20, 20, bgr);
    tri[i].pos[0] += tri[i].vel[0];
    if ((tri[i].pos[0] <= 0) || (tri[i].pos[0] >= display.width())) {
      tri[i].vel[0] *= -1;
    }
    tri[i].pos[1] += tri[i].vel[1];
    if ((tri[i].pos[1] <= 0) || (tri[i].pos[1] >= display.height())) {
      tri[i].vel[1] *= -1;
    }
  }
  int s = shebang_listener(shebangPin);
  if (s == LOW) {
    digitalWrite(shebangLed, HIGH);
    triangle_count = N_TRI;
    clear_static();
  }
  else {
    digitalWrite(shebangLed, LOW);
    triangle_count = potVal0;
    draw_static(1000, rgb);
  }
}

void animate_target() {
  radi = 0;
  for (int i=0; i<240; i+=10){
    index_reading = button_listener(indexPin, ledPin);
    
    potVal1 = analog_map(pot1, 0, 255);
    potVal2 = analog_map(pot2, 0, 255);
    potVal3 = analog_map(pot3, 0, 255);
    potVal0 = analog_map(pot0, 25, 75);
    rgb = color_mixer(potVal1, potVal2, potVal3);
    bgr = color_mixer(potVal3, potVal2, potVal1);
    rgb = rgb*3;
    bgr = bgr*2;
    int s = shebang_listener(shebangPin);
    if (s == LOW) {
      digitalWrite(shebangLed, HIGH);
      radi = random(5, 75);
      display.fillCircle(160, 120, last_r, BLACK);
    }
    else {
      digitalWrite(shebangLed, LOW);
      radi = radi + 2;
    }
    display.fillCircle(160, 120, radi, rgb);  
    display.drawLine(160, 120, 320, i, bgr);
    last_r = radi;
    if (index_reading == LOW) {
      break;
    }
    millisDelay(potVal0);
    }
  
  for (int i=320; i>0; i-=10){
    index_reading = button_listener(indexPin, ledPin);
    potVal1 = analog_map(pot1, 0, 255);
    potVal2 = analog_map(pot2, 0, 255);
    potVal3 = analog_map(pot3, 0, 255);
    potVal0 = analog_map(pot0, 25, 75);
    rgb = color_mixer(potVal1, potVal2, potVal3);
    bgr = color_mixer(potVal3, potVal2, potVal1);
    rgb = rgb*3;
    bgr = bgr*2;
    int s = shebang_listener(shebangPin);
    if (s == LOW) {
      digitalWrite(shebangLed, HIGH);
      radi = random(5, 75);
      display.fillCircle(160, 120, last_r, BLACK);
    }
    else {
      digitalWrite(shebangLed, LOW);
      radi = radi + 2;
      if (radi > 120) {
        radi = 120;
      }
    }
    display.fillCircle(160, 120, radi, rgb);
    display.drawLine(160, 120, i, 240, bgr);
    last_r = radi;
    if (index_reading == LOW) {
      break;
    }
    millisDelay(potVal0);
  }
  
  for (int i=240; i>0; i-=10){
    index_reading = button_listener(indexPin, ledPin);
    potVal1 = analog_map(pot1, 0, 255);
    potVal2 = analog_map(pot2, 0, 255);
    potVal3 = analog_map(pot3, 0, 255);
    potVal0 = analog_map(pot0, 25, 75);
    rgb = color_mixer(potVal1, potVal2, potVal3);
    bgr = color_mixer(potVal3, potVal2, potVal1);
    rgb = rgb*3;
    bgr = bgr*2;
    int s = shebang_listener(shebangPin);
    if (s == LOW) {
      digitalWrite(shebangLed, HIGH);
      radi = random(5, 75);
    }
    else {
      digitalWrite(shebangLed, LOW);
      radi = radi - 3;
    }
    display.fillCircle(160, 120, last_r, BLACK);
    display.fillCircle(160, 120, radi, rgb);
    display.drawLine(160, 120, 0, i, bgr);
    last_r = radi;
    if (index_reading == LOW) {
      break;
    }
    millisDelay(potVal0);
  }
  
  for (int i=0; i<320; i+=10){
    index_reading = button_listener(indexPin, ledPin);
    potVal1 = analog_map(pot1, 0, 255);
    potVal2 = analog_map(pot2, 0, 255);
    potVal3 = analog_map(pot3, 0, 255);
    potVal0 = analog_map(pot0, 25, 75);
    rgb = color_mixer(potVal1, potVal2, potVal3);
    bgr = color_mixer(potVal3, potVal2, potVal1);
    rgb = rgb*3;
    bgr = bgr*2;
    int s = shebang_listener(shebangPin);
    if (s == LOW) {
      digitalWrite(shebangLed, HIGH);
      radi = random(5, 75);
    }
    else {
      digitalWrite(shebangLed, LOW);
      radi = radi - 2;
      if (radi < 1) {
        radi = 1;
      }
    }
    display.fillCircle(160, 120, last_r, BLACK);
    display.fillCircle(160, 120, radi, rgb);
    display.drawLine(160, 120, i, 0, bgr);
    last_r = radi;
    if (index_reading == LOW) {
      break;
    }
    millisDelay(potVal0);
  }
}

void animate_wavylines() {
  for (int i=0; i<h; i+=10){
    index_reading = button_listener(indexPin, ledPin);
    
    potVal1 = analog_map(pot1, 0, 255);
    potVal2 = analog_map(pot2, 0, 255);
    potVal3 = analog_map(pot3, 0, 255);
    potVal0 = analog_map(pot0, 25, 75);
    rgb = color_mixer(potVal1, potVal2, potVal3);
    gbr = color_mixer(potVal2, potVal3, potVal1);
    int s = shebang_listener(shebangPin);
    if (s == LOW) {
      digitalWrite(shebangLed, HIGH);
      shebang_pressed = true;
      display.drawLine(random(0, w), random(0, h), w, i, rgb*3);
    }
    else {
      digitalWrite(shebangLed, LOW);
      if (shebang_pressed == true) {
        display.fillScreen(BLACK);
        cycle = 0;
        shebang_pressed = false;
      }
      for (int i=1; i<400; i++){
        display.drawPixel(random(0, w), random(0, h), gbr);
      }
      display.drawLine(0, 0, w, i, rgb*3);
    }
      if (index_reading == LOW) {
        break;
      }
    millisDelay(potVal0);
  }
  for (int i=w; i>0; i-=10){
    index_reading = button_listener(indexPin, ledPin);
    potVal1 = analog_map(pot1, 0, 255);
    potVal2 = analog_map(pot2, 0, 255);
    potVal3 = analog_map(pot3, 0, 255);
    potVal0 = analog_map(pot0, 25, 75);
    rgb = color_mixer(potVal1, potVal2, potVal3);
    int s = shebang_listener(shebangPin);
    if (s == LOW) {
      digitalWrite(shebangLed, HIGH);
      shebang_pressed = true;
      display.drawLine(random(0, w), random(0, h), i, h, rgb*3);
    }
    else {
      digitalWrite(shebangLed, LOW);
      if (shebang_pressed == true) {
        display.fillScreen(BLACK);
        cycle = 0;
        shebang_pressed = false;
      }
      display.drawLine(0, 0, i, h, rgb*3);
    }
    if (index_reading == LOW) {
      break;
    }
    millisDelay(potVal0);
  }
  for (int i=0; i<w; i+=10){
    index_reading = button_listener(indexPin, ledPin);
    
    potVal1 = analog_map(pot1, 0, 255);
    potVal2 = analog_map(pot2, 0, 255);
    potVal3 = analog_map(pot3, 0, 255);
    potVal0 = analog_map(pot0, 25, 75);
    brg = color_mixer(potVal3, potVal1, potVal2);
    int s = shebang_listener(shebangPin);
    if (s == LOW) {
      digitalWrite(shebangLed, HIGH);
      shebang_pressed = true;
      display.drawLine(random(0, w), random(0, h), i, h, rgb*3);
    }
    else {
      digitalWrite(shebangLed, LOW);
      if (shebang_pressed == true) {
        display.fillScreen(BLACK);
        cycle = 0;
        shebang_pressed = false;
      }
      display.drawLine(0, 0, i, h, brg*3);
    }
    if (index_reading == LOW) {
      break;
    }
    millisDelay(potVal0);
  }
  for (int i=h; i>0; i-=10){
    index_reading = button_listener(indexPin, ledPin);
    
    potVal1 = analog_map(pot1, 0, 255);
    potVal2 = analog_map(pot2, 0, 255);
    potVal3 = analog_map(pot3, 0, 255);
    potVal0 = analog_map(pot0, 25, 75);
    brg = color_mixer(potVal3, potVal1, potVal2);
    int s = shebang_listener(shebangPin);
    if (s == LOW) {
      digitalWrite(shebangLed, HIGH);
      shebang_pressed = true;
      display.drawLine(random(0, w), random(0, h), w, i, rgb*3);
    }
    else {
      digitalWrite(shebangLed, LOW);
      if (shebang_pressed == true) {
        display.fillScreen(BLACK);
        cycle = 0;
        shebang_pressed = false;
      }
      display.drawLine(0, 0, w, i, brg*3);
    }
    if (index_reading == LOW) {
      break;
    }
    millisDelay(potVal0);
  }
  clear_static();
  cycle++;
  if (cycle > 4) {
    display.fillScreen(BLACK);
    cycle = 0;
  }
}

void make_triangle(uint16_t x1, uint16_t y1, uint16_t side_1, uint16_t side_2,uint16_t color) {
  color = color_mixer(potVal3, potVal2, potVal1);
  uint16_t x2 = x1 + side_1;
  uint16_t y2 = y1 + side_2;
  display.fillTriangle(x1, y1, x2, y2, x2, y1, color*2);
}

int analog_map(int x, int minMap, int maxMap) {
    int z = analogRead(x);
    z = map(z, 0, 1023, minMap, maxMap);
    return z;
  }

uint16_t color_mixer(int int_r, int int_g, int int_b) {
  uint16_t mixed = ((int_r & 0xf8) << 8) + ((int_g & 0xfc) << 3) + (int_b >>3);
  return mixed;
}

void draw_static(int num_stars, uint16_t color_order) {
  color_order = color_mixer(potVal1, potVal2, potVal3);
  for (int i=1; i<num_stars; i++){
    display.drawPixel(random(0, 320), random(0, 240), color_order*3);
    display.drawPixel(random(0, 320), random(0, 240), 0x0000);
  }
}

void draw_stars(int num_stars) {
  for (int i=1; i<num_stars; i++){
    display.drawPixel(random(0, 320), random(0, 240), WHITE);
  }
}

void clear_static() {
  for (int i=1; i<15000; i++){
    display.drawPixel(random(0, 320), random(0, 240), 0x0000);
  }
}

uint16_t gradient_colors(int degree, int _w, int _h) {
    uint8_t r, g, b;
    r = map(degree, _w, _h, 255, 0);
    g = 0;
    b = map(degree, _w, _h, 0, 255);
    uint16_t mixed = color_mixer(r, g, b);
    return mixed;
}

void draw_gradient(int x, int y, int w, int h) {
    for (int row = 1; row < h - 1; row++) {
        display.drawFastHLine(x + 1, y + row, w - 2, gradient_colors(row, 0, h));
    }
}

void millisDelay(int delayTime){
  int start_time = millis();
  while ( millis() - start_time < delayTime) ;
}
