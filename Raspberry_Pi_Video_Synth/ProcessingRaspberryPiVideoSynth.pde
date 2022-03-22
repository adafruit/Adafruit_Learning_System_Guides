// SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// Processing library for Networking
// make sure that you have the library installed!
import processing.net.*;

// HTTP client
Client myClient;

// variables for receiving data from Blinka socket
int index;
String inString;

// holding the red, green, blue data
String[] r;
String[] g;
String[] b;
int red;
int green;
int blue;

// holding the VL53L4CD data
String[] f;
int flight;

// cat and pizza images
//emojis are from the OpenMoji emoji library (https://openmoji.org/)
PImage cat_img; 
PImage pizza_img;

// colors for Circles animation
color c_red = color(255, 0, 0);
color c_green = color(0, 255, 0);
color c_blue = color(0, 0, 255);
color c_yellow = color(255, 125, 0);
color c_aqua = color(0, 125, 255);
color c_purple = color(255, 0, 255);

IntList colors; 

// float for Cube animation
float i = 0.0;

// variables for Circles animation
int rad = 60;        
float xpos, ypos;       

float xspeed = 2.8;  
float yspeed = 10;  

int xdirection = 1;  
int ydirection = 1;  

// variables for pizzaCat animation
float pizza_speed = 20;  
float cat_speed = 30;  

float pizza_pos, cat_pos;

int img_w = 10;

int pizza_dir = 1;
int cat_dir = 1;
int num_cats;

// variables for dancingTriangles animation
int x1;
int y1;
int x2; 
int y2;
int x3;
int y3;

void setup() 
{
  // setting animations to run fullscreen with P3D
  fullScreen(P3D);
  // RGB color mode with value range of 0-255
  colorMode(RGB, 255);
  ellipseMode(RADIUS);
  // setting xpos and ypos in center
  xpos = width/2;
  ypos = height/2;
  
  // creating array of colors
  // this is used for the Circles animation
  colors = new IntList();
  colors.append(c_red);
  colors.append(c_yellow);
  colors.append(c_green);
  colors.append(c_aqua);
  colors.append(c_blue);
  colors.append(c_purple);
  
  // loading the cat and pizza images
  cat_img = loadImage("cat.png");
  pizza_img = loadImage("pizza.png");
  
  // connecting to socket to communicate with Blinka script
  myClient = new Client(this, "127.0.0.1", 12345);

}

// void draw() is the loop in Processing
void draw() 
{
  //if data is coming in over the socket...
  if (myClient.available() > 0) {
    //string data is stored in inString
    inString = myClient.readString();
    //if the string begins with 'enc'
    //aka is a msg from the rotary encoder...
    if (inString.startsWith("enc")) {
      // the encoder pos is stored in index
      String[] q = splitTokens(inString);
      index = int(q[1]);
    }
    //if the string begins with 'red'
    //aka is from the red neoslider
    if (inString.startsWith("red")) {
      //the red value is stored in red
      String[] r = splitTokens(inString);
      red = int(r[1]);
    }
    //if the string begins with 'green'
    //aka is from the green neoslider
    if (inString.startsWith("green")) {
      // the green value is stored in green
      String[] g = splitTokens(inString);
      green = int(g[1]);
    }
    //if the string begins with 'blue'
    //aka is from the blue neoslider
    if (inString.startsWith("blue")) {
      //the blue value is stored in blue
      String[] b = splitTokens(inString);
      blue = int(b[1]);
    }
    //if the string begins with flight
    //aka is from the VL53L4CD
    if (inString.startsWith("flight")) {
      //the time of flight value is stored in flight
      String[] f = splitTokens(inString);
      flight = int(f[1]);
    }
  }
  //the encoder's position corresponds with which animation plays
  if (index == 0) {
    circles();
    }

  if (index == 1) {
    cube();
    }
  if (index == 2) {
    dancingTriangles();
    }
  if (index == 3) {
    pizzaCat();
    }
  }
    
//the Circles animation
//colorful circles randomly appear in the middle of the screen
//background color is affected by the sliders
//the circles' size is affected by the VL53L4CD
void circles() {
  background(red, green, blue);
  strokeWeight(1);
  
  ypos = ypos + ( yspeed * ydirection );
  
  if (ypos > height-rad || ypos < rad) {
    ydirection *= +1;
  }

  int size = int(map(flight, 0, 45, 300, 25));
  
  for (int i = 0; i < 10; i++) {
    for (int z = 0; z < 6; z++) {
      fill(colors.get(z));
      circle(width/2, random(ypos), random(size));
    }
  }
}

//the Cube animation
//a 3D cube spins in the center of the screen
//background color is affected by the sliders
//the speed of the spinning cube is affected by the VL53L4CD
void cube() {
  strokeWeight(5);
  
  float speed = map(flight, 0, 45, 10, 0.1);
  
  background(red, green, blue);
  translate(width/2, height/2, 0);
  
  i = i + speed;
  if (i > 180) {
    i = 0.0;
  }
    rotateY(radians(i));
    noFill();
    box(500);
}

//the Pizza Cat animation
//pizza and cat face emojis go back and forth across the screen
//emojis are from the OpenMoji emoji library (https://openmoji.org/)
//the background color is affected by the sliders
//the speed of the cat emojis are affected by the V53L4CD
void pizzaCat() { 
  background(red, green, blue);
  int num_cats = int(map(flight, 0, 45, 65, 15));

  pizza_pos = pizza_pos + ( pizza_speed * pizza_dir );
  cat_pos = cat_pos + ( num_cats * cat_dir );

  if (pizza_pos + img_w > width || pizza_pos < img_w) {
    pizza_dir *= -1;
  }
  if (cat_pos + img_w > height || cat_pos < img_w) {
    cat_dir *= -1;
  }
  
  for (int p = 0; p < 25; p++) {
    image(cat_img, pizza_pos-10, cat_pos*p);
    image(pizza_img, pizza_pos*p, cat_pos+10);
  }
}

// the dancingTriangles animation
// triangles are randomly generated in the center of the screen
//the background is affected by the sliders
// the speed of new triangles being added are affected by the V53L4CD
void dancingTriangles() {
  int speed = int(map(flight, 0, 45, 25, 100));
  
  background(red, green, blue);
  strokeWeight(30);
  
  for (int w = 800; w < 1000; w ++) {
    for (int h = 1100; h < 1500; h++) {
    
      x1 = int(random(h));
      y1 = int(random(w));
    
      x2 = int(random(h));
      y2 = int(random(w));
    
      x3 = int(random(h));
      y3 = int(random(w));
     }
   }
  noFill();
  triangle(x1, y1, x2, y2, x3, y3);
  delay(speed);
}
