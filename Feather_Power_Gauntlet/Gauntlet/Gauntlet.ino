#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_LSM303_U.h>
#include <Adafruit_NeoPixel.h>

#define LEDpin 6

#define SFX_start 13
#define SFX_PowerUp 12
#define SFX_Fire 11
#define SFX_PowerDown 10

#define SFX_Playing 9

#define button 5

Adafruit_NeoPixel strip = Adafruit_NeoPixel(19, LEDpin, NEO_GRB + NEO_KHZ800);


/* Assign a unique ID to this sensor at the same time */
Adafruit_LSM303_Accel_Unified accel = Adafruit_LSM303_Accel_Unified(54321);


// #####Light Flicker
int alpha; // Current value of the pixels
int dir = 1; // Direction of the pixels... 1 = getting brighter, 0 = getting dimmer
int flip; // Randomly flip the direction every once in a while
int minAlpha = 50; // Min value of brightness
int maxAlpha = 75; // Max value of brightness
int alphaDelta = 1; // Delta of brightness between times through the loop
int Coffset;


void setup()
{
#ifndef ESP8266
 // while (!Serial);     // will pause Zero, Leonardo, etc until serial console opens
#endif
  Serial.begin(9600);
  Serial.println("Accelerometer Test"); Serial.println("");

  /* Initialise the sensor */
  if(!accel.begin())
  {
    /* There was a problem detecting the ADXL345 ... check your connections */
    Serial.println("Ooops, no LSM303 detected ... Check your wiring!");
    while(1);
  }

  /* Display some basic information on this sensor */
  displaySensorDetails();

  pinMode(SFX_Playing, INPUT_PULLUP);
   pinMode(button, INPUT_PULLUP);

  pinMode(SFX_start, OUTPUT);
  pinMode(SFX_PowerUp, OUTPUT);
  pinMode(SFX_Fire, OUTPUT);
  pinMode(SFX_PowerDown, OUTPUT);
   delay(500);
  digitalWrite(SFX_start, HIGH);
  digitalWrite(SFX_PowerUp, HIGH);
  digitalWrite(SFX_Fire, HIGH);
  digitalWrite(SFX_PowerDown, HIGH);

  strip.begin();
  strip.show(); // Initialize all pixels to 'off'

  strip.setBrightness(255);
}

int ReadX;
int PowerUp = 0;
int DotVal = 10;

int ButtonPress = 1;


void loop()
{

  while (!digitalRead(button)){
    if(ButtonPress){
      ButtonPress = 0;
      digitalWrite(SFX_PowerDown, LOW);
      while(digitalRead(SFX_Playing));
      digitalWrite(SFX_PowerDown, HIGH);
      while(!digitalRead(SFX_Playing));
    }else{
      ButtonPress = 1;
      digitalWrite(SFX_start, LOW);
      while(digitalRead(SFX_Playing));
      digitalWrite(SFX_start, HIGH);
      while(!digitalRead(SFX_Playing));
    }
  }
flip = random(32);
  if(flip > 20) {
    dir = 1 - dir;
  }
  // Some example procedures showing how to display to the pixels:
  if (dir == 1) {
    alpha += alphaDelta;
  }
  if (dir == 0) {
    alpha -= alphaDelta;
  }
  if (alpha < minAlpha) {
    alpha = minAlpha;
    dir = 1;
  }
  if (alpha > maxAlpha) {
    alpha = maxAlpha;
    dir = 0;
  }
  //DotVal = alpha/8

  Coffset = random(10);
  colorWipe(strip.Color(alpha-Coffset, alpha-Coffset, alpha));
  colorWipeDot(strip.Color(10, 10, alpha/2));

  sensors_event_t event;
  accel.getEvent(&event);
  Serial.print("X: "); Serial.print(event.acceleration.x); Serial.print("  ");
  Serial.print("Y: "); Serial.print(event.acceleration.y); Serial.print("  ");
  Serial.print("Z: "); Serial.print(event.acceleration.z); Serial.print("  ");Serial.println("m/s^2 ");
  ReadX=event.acceleration.y;
  if(ReadX < 10.5 && ReadX > 8 && ButtonPress){
    PowerUp = 1;
    digitalWrite(SFX_PowerUp, LOW);
    while(digitalRead(SFX_Playing));
    digitalWrite(SFX_PowerUp, HIGH);
    while(!digitalRead(SFX_Playing)){
      alpha = alpha+1;
      if(alpha<254){
        colorWipe(strip.Color(alpha-Coffset, alpha-Coffset, alpha));
        colorWipeDot(strip.Color(alpha-Coffset/2, alpha-Coffset/2, alpha/2));
      }
      
    }
    sensors_event_t event;
    accel.getEvent(&event);
    Serial.print("X: "); Serial.print(event.acceleration.x); Serial.print("  ");
    Serial.print("Y: "); Serial.print(event.acceleration.y); Serial.print("  ");
    Serial.print("Z: "); Serial.print(event.acceleration.z); Serial.print("  ");Serial.println("m/s^2 ");
    ReadX=event.acceleration.y;
    delay(50);
    if(ReadX < 10.5 && ReadX > 8 ){
      digitalWrite(SFX_Fire, LOW);
      while(digitalRead(SFX_Playing)){
        alpha = alpha-8;
        if(alpha>10){
          colorWipe(strip.Color(alpha-Coffset, alpha-Coffset, alpha));
          colorWipeDot(strip.Color(alpha-Coffset, alpha-Coffset, alpha));
        }
      }
      digitalWrite(SFX_Fire, HIGH);
      alpha = 255;
      while(!digitalRead(SFX_Playing)){
        alpha = alpha - 2;
        if(alpha>10){
          colorWipe(strip.Color(alpha-Coffset, alpha-Coffset, alpha));
          colorWipeDot(strip.Color(alpha-Coffset, alpha-Coffset, alpha));
        }
      }
      colorWipeDot(strip.Color(alpha-Coffset/2, alpha-Coffset/2, alpha/2));
      delay(1000);
    }else{
      digitalWrite(SFX_PowerDown, LOW);
      while(digitalRead(SFX_Playing));
      digitalWrite(SFX_PowerDown, HIGH);
      while(!digitalRead(SFX_Playing)){
        alpha = alpha - 1;
        DotVal = alpha - 8;
        if(alpha>10){
          colorWipe(strip.Color(alpha-Coffset, alpha-Coffset, alpha));
          colorWipeDot(strip.Color(DotVal-Coffset, DotVal-Coffset, DotVal));
        }
      }

      delay(300);
      
      
    }
  }
  //digitalWrite(SFX_PowerUp, HIGH);


  //delay(50);
}


// Fill the dots one after the other with a color
void colorWipe(uint32_t c) {
  for(uint16_t i=0; i<16; i++) {
      strip.setPixelColor(i, c);
      strip.show();
  }
}

// Fill the dots one after the other with a color
void colorWipeDot(uint32_t c) {
  for(uint16_t i=16; i<19; i++) {
      strip.setPixelColor(i, c);
      strip.show();
  }
}

void displaySensorDetails()
{
  sensor_t sensor;
  accel.getSensor(&sensor);
  Serial.println("------------------------------------");
  Serial.print  ("Sensor:       "); Serial.println(sensor.name);
  Serial.print  ("Driver Ver:   "); Serial.println(sensor.version);
  Serial.print  ("Unique ID:    "); Serial.println(sensor.sensor_id);
  Serial.print  ("Max Value:    "); Serial.print(sensor.max_value); Serial.println(" m/s^2");
  Serial.print  ("Min Value:    "); Serial.print(sensor.min_value); Serial.println(" m/s^2");
  Serial.print  ("Resolution:   "); Serial.print(sensor.resolution); Serial.println(" m/s^2");
  Serial.println("------------------------------------");
  Serial.println("");
  delay(500);
}
