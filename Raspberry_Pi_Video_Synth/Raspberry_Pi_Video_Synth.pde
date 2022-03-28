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
int pizzaCount = 32;
int catCount = 32;
int emojiCount = 32;

PImage[] cats = new PImage[catCount];
PImage[] pizzas = new PImage[pizzaCount];

float[] moveX = new float[emojiCount];
float[] moveY = new float[emojiCount];

float last_speed;

float[] x_dir = new float[emojiCount];
float[] y_dir = new float[emojiCount];
float[] x_speeds = new float[emojiCount];
float[] y_speeds = new float[emojiCount];

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
  
  // adding pizza and cat emojis to their arrays
  for (int slice = 0; slice  < 15; slice ++) {
    pizzas[slice] = pizza_img;
  }
  for (int claw = 16; claw< catCount; claw++) {
    cats[claw] = cat_img;
  }
  // creating arrays of coordinates and speed for pizzaCat
  for (int z = 0; z < emojiCount; z ++) {
    x_dir[z] = random(width);
    y_dir[z] = random(height);
    x_speeds[z] = random(5, 20);
    y_speeds[z] = random(5, 20);
    moveX[z] = x_speeds[z];
    moveY[z] = y_speeds[z];
  }
  
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
      println(index);
    }
    //if the string begins with 'red'
    //aka is from the red neoslider
    if (inString.startsWith("red")) {
      //the red value is stored in red
      String[] r = splitTokens(inString);
      red = int(r[1]);
      println(red);
    }
    //if the string begins with 'green'
    //aka is from the green neoslider
    if (inString.startsWith("green")) {
      // the green value is stored in green
      String[] g = splitTokens(inString);
      green = int(g[1]);
      println(green);
    }
    //if the string begins with 'blue'
    //aka is from the blue neoslider
    if (inString.startsWith("blue")) {
      //the blue value is stored in blue
      String[] b = splitTokens(inString);
      blue = int(b[1]);
      println(blue);
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
  if (index == 3) {
    circles();
    }

  if (index == 1) {
    cube();
    }
  if (index == 2) {
    dancingTriangles();
    }
  if (index == 0) {
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
//pizza and cat face emojis bounce around the screen
//emojis are from the OpenMoji emoji library (https://openmoji.org/)
//the background color is affected by the sliders
//the speed of the emojis are affected by the V53L4CD
//green slider affects # of cats
//blue slider affects # of pizzas
void pizzaCat() { 
  background(red, green, blue);
  float meow = map(green, 0, 255, 32, 16);
  float pie = map(blue, 0, 255, 15, 0);
  float speed = map(flight, 0, 45, 0, 25);
  
    for (int e = 16; e < meow; e++) {
      if (last_speed != speed) {
        moveX[e] = x_speeds[e] + speed;
        moveY[e] = y_speeds[e] + speed;
      }
      else {
        moveX[e] = moveX[e];
        moveY[e] = moveY[e];
      }
      x_dir[e] += moveX[e];
      if (x_dir[e] < 0 || x_dir[e] > width) {
        moveX[e] *= -1;
        
      }
      if (x_dir[e] > width) {
        x_dir[e] = (width - 2);
      }
      y_dir[e] += moveY[e];
      if(y_dir[e] < 0 || y_dir[e] > height) {
        moveY[e] *= -1;
        
      }
      if (y_dir[e] > height) {
        y_dir[e] = (height - 2);
      }

    image(cats[e], x_dir[e], y_dir[e]);
    
    }
    for (int p = 1; p < pie; p++) {
      if (last_speed != speed) {
        moveX[p] = x_speeds[p] + speed;
        moveY[p] = y_speeds[p] + speed;
      }
      else {
        moveX[p] = moveX[p];
        moveY[p] = moveY[p];
      }
      x_dir[p] += moveX[p];
      if (x_dir[p] < 0 || x_dir[p] > width) {
          moveX[p] *= -1;
      }
      if (x_dir[p] > width) {
        x_dir[p] = (width - 2);
      }
      y_dir[p] += moveY[p];
      if(y_dir[p] < 0 || y_dir[p] > height) {
        moveY[p] *= -1;
      }
      if (y_dir[p] > height) {
        y_dir[p] = (height - 2);
      }

    image(pizzas[p], x_dir[p], y_dir[p]);
    }
    last_speed = speed;
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
