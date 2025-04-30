// SPDX-FileCopyrightText: 2025 John Park and Claude
//
// SPDX-License-Identifier: MIT
// Computer Space simulation for Arduino

// For Adafruit Feather M4 with OLED display

#include <SPI.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1305.h>

// Display setup
#define OLED_CS     5
#define OLED_DC     6
#define OLED_RESET  9
Adafruit_SSD1305 display(128, 64, &SPI, OLED_DC, OLED_RESET, OLED_CS, 7000000UL);

// Game constants
#define GAME_WIDTH  85     // Game area width - for 4:3 aspect ratio
#define GAME_HEIGHT 64     // Game area height
#define SCREEN_WIDTH  128  // Physical display width
#define SCREEN_HEIGHT 64   // Physical display height
#define GAME_X_OFFSET ((SCREEN_WIDTH - GAME_WIDTH) / 2)  // Center the game area
#define GAME_Y_OFFSET 0
#define WHITE          1
#define BLACK          0

// Score positions - all inside game area
#define SCORE_Y_TOP    18  // Player score
#define SCORE_Y_MIDDLE 32  // Saucer score
#define SCORE_Y_BOTTOM 46  // Timer

// Score fonts are 3x5 pixels
#define DIGIT_WIDTH   3
#define DIGIT_HEIGHT  5
#define DIGIT_SPACING 5   // Total width including spacing

// Scores
int player_score = 0;  // Starting scores at 0 as requested
int saucer_score = 0;
unsigned long game_timer = 0;  // Starting from 00 and counting up to 99
const unsigned long GAME_DURATION = 99000; // 99 seconds

// Number of stars (similar to PDP-1 Spacewar!)
#define NUM_STARS      40

// Ship and saucer states
#define ALIVE     0
#define EXPLODING 1
#define RESPAWNING 2
#define EXPLOSION_FRAMES 12 // Number of frames for explosion animation

// Screen flash effect
bool screen_flash = false;
int flash_frames = 0;
#define FLASH_DURATION 3  // How long to flash the screen

// Game objects
// Ship
float ship_x, ship_y;
float ship_vx, ship_vy;
float ship_rotation = 0;
float target_rotation = 0;
const float ship_thrust = 0.13;  // 33% slower than original 0.2
bool ship_thrusting = false;
int ship_state = ALIVE;
int ship_explosion_frame = 0;
unsigned long ship_respawn_time = 0;

// Saucers (moving in formation)
float saucer1_x, saucer1_y;
float saucer2_x, saucer2_y;
float saucer_vertical_distance; // Distance between saucers (maintained)
unsigned long direction_change_time = 0;
int saucer1_state = ALIVE;
int saucer2_state = ALIVE;
int saucer1_explosion_frame = 0;
int saucer2_explosion_frame = 0;
unsigned long saucer1_respawn_time = 0;
unsigned long saucer2_respawn_time = 0;

// Diagonal movement table 
const int8_t MOVEMENT_TABLE[][2] = {
  { 1,  0},  // Right
  {-1,  0},  // Left
  { 0, -1},  // Up
  { 0,  1},  // Down
  { 1,  1},  // Down-Right
  {-1, -1},  // Up-Left
  {-1,  1},  // Down-Left
  { 1, -1}   // Up-Right
};
uint8_t current_movement = 0;

// Bullets
bool player_bullet_active = false;
float player_bullet_x, player_bullet_y;
float player_bullet_vx, player_bullet_vy;
unsigned long player_bullet_expire = 0;
float player_bullet_tracking_factor = 0.08; // How much the bullet tracks ship rotation

bool saucer1_bullet_active = false;
float saucer1_bullet_x, saucer1_bullet_y;
float saucer1_bullet_vx, saucer1_bullet_vy;
unsigned long saucer1_bullet_expire = 0;

bool saucer2_bullet_active = false;
float saucer2_bullet_x, saucer2_bullet_y;
float saucer2_bullet_vx, saucer2_bullet_vy;
unsigned long saucer2_bullet_expire = 0;

// Shooting cooldowns
unsigned long player_fire_cooldown = 0;
unsigned long saucer_fire_cooldown = 0;
const unsigned long PLAYER_COOLDOWN = 700;   // milliseconds
const unsigned long SAUCER_COOLDOWN = 1500;  // milliseconds
const unsigned long BULLET_LIFETIME = 2000;  // 2 seconds as requested
const float BULLET_SPEED = 42.0;             // Much faster than ship movement

// Respawn timing
const unsigned long RESPAWN_DELAY = 2000; // 2 seconds

// Game timing
unsigned long last_time = 0;
unsigned long auto_rotation_time = 0;
unsigned long auto_thrust_time = 0;
unsigned long game_start_time = 0;
unsigned long timer_update_time = 0;

// Star coordinates
uint8_t stars[NUM_STARS][2];

// Background counter for star flicker (PDP-1 style)
uint8_t bg_counter = 0;

// Digit patterns for 0-9 (3x5 pixels, 1 for pixel on, 0 for pixel off)
const uint8_t DIGITS[10][DIGIT_HEIGHT][DIGIT_WIDTH] = {
  // 0
  {
    {1, 1, 1},
    {1, 0, 1},
    {1, 0, 1},
    {1, 0, 1},
    {1, 1, 1}
  },
  // 1
  {
    {0, 1, 0},
    {0, 1, 0},
    {0, 1, 0},
    {0, 1, 0},
    {0, 1, 0}
  },
  // 2
  {
    {1, 1, 1},
    {0, 0, 1},
    {1, 1, 1},
    {1, 0, 0},
    {1, 1, 1}
  },
  // 3
  {
    {1, 1, 1},
    {0, 0, 1},
    {1, 1, 1},
    {0, 0, 1},
    {1, 1, 1}
  },
  // 4
  {
    {1, 0, 1},
    {1, 0, 1},
    {1, 1, 1},
    {0, 0, 1},
    {0, 0, 1}
  },
  // 5
  {
    {1, 1, 1},
    {1, 0, 0},
    {1, 1, 1},
    {0, 0, 1},
    {1, 1, 1}
  },
  // 6
  {
    {1, 1, 1},
    {1, 0, 0},
    {1, 1, 1},
    {1, 0, 1},
    {1, 1, 1}
  },
  // 7
  {
    {1, 1, 1},
    {0, 0, 1},
    {0, 0, 1},
    {0, 0, 1},
    {0, 0, 1}
  },
  // 8
  {
    {1, 1, 1},
    {1, 0, 1},
    {1, 1, 1},
    {1, 0, 1},
    {1, 1, 1}
  },
  // 9
  {
    {1, 1, 1},
    {1, 0, 1},
    {1, 1, 1},
    {0, 0, 1},
    {1, 1, 1}
  }
};

// Explosion pattern data - expanding circle animation
const uint8_t EXPLOSION_RADIUS[] = {1, 2, 3, 4, 5, 6, 6, 5, 4, 3, 2, 1};
const uint8_t EXPLOSION_POINTS = 8; // Points to draw in the circle

// Function prototypes
void drawDigit(int digit, int x, int y);
void drawScore(int score, int x, int y);
void drawScores();
void clearScoreArea();
void drawStars();
void clearShip();
void clearSaucer(float x, float y);
bool checkCollision(float x1, float y1, float x2, float y2, float radius);
bool isAimedAtSaucer(float ship_x, float ship_y, float ship_rotation, float saucer_x, float saucer_y, float tolerance = 0.6);
void drawShip(float x, float y, float rotation);
void drawSaucer(float x, float y);
void updateSaucerBullet(bool &active, float &x, float &y, float &vx, float &vy, unsigned long &expire, float dt, unsigned long current_time);
float normalizeAngle(float angle);
float getAngleDifference(float a1, float a2);
float getAngleToTarget(float x1, float y1, float x2, float y2);
void updateSaucers(float dt, unsigned long current_time);
void updateTimer();
void drawExplosion(float x, float y, int frame);
void respawnShip();
void respawnSaucer(int saucer_num);
void triggerScreenFlash();

void setup() {
  Serial.begin(9600);
  
  // Initialize display
  if (!display.begin()) {
    Serial.println("SSD1305 allocation failed");
    while (1);
  }
  
  // Show intro text
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(WHITE);
  display.setCursor(10, 10);
  display.println("Computer Space");
  display.setCursor(32, 30);
  display.println("PDP-1 Style");
  display.setCursor(32, 50);
  display.println("Demo Mode");
  display.display();
  delay(2000);
  
  display.clearDisplay();
  
  // Initialize stars (PDP-1 style - fewer stars)
  randomSeed(analogRead(0));
  for (int i = 0; i < NUM_STARS; i++) {
    stars[i][0] = GAME_X_OFFSET + random(0, GAME_WIDTH);
    stars[i][1] = GAME_Y_OFFSET + random(0, GAME_HEIGHT);
  }
  
  // Initialize game objects
  respawnShip();
  
  // Initialize saucers in formation (one above the other)
  respawnSaucer(1);
  respawnSaucer(2);
  saucer_vertical_distance = saucer2_y - saucer1_y;
  
  direction_change_time = millis() + random(2000, 5000);
  game_start_time = millis();
  timer_update_time = millis();
  
  // Draw the stars and initial score display
  drawStars();
  drawScores();
  display.display();
  
  last_time = millis();
}

void loop() {
  unsigned long current_time = millis();
  float dt = (current_time - last_time) / 1000.0; // Convert to seconds
  last_time = current_time;
  
  // Cap dt to prevent large jumps
  if (dt > 0.1) dt = 0.1;
  
  // Update timer
  updateTimer();
  
  // Handle screen flash effect
  if (screen_flash) {
    // Flash the entire screen white
    if (flash_frames == 0) {
      display.fillRect(GAME_X_OFFSET, GAME_Y_OFFSET, GAME_WIDTH, GAME_HEIGHT, WHITE);
      display.display();
      delay(50); // Short delay to make flash visible
    }
    
    flash_frames++;
    if (flash_frames >= FLASH_DURATION) {
      screen_flash = false;
      flash_frames = 0;
      // Clear screen after flash
      display.fillRect(GAME_X_OFFSET, GAME_Y_OFFSET, GAME_WIDTH, GAME_HEIGHT, BLACK);
    }
  }
  
  // Clear previous objects
  clearShip();
  clearSaucer(saucer1_x, saucer1_y);
  clearSaucer(saucer2_x, saucer2_y);
  
  if (player_bullet_active) {
    display.drawPixel(player_bullet_x, player_bullet_y, BLACK);
  }
  if (saucer1_bullet_active) {
    display.drawPixel(saucer1_bullet_x, saucer1_bullet_y, BLACK);
  }
  if (saucer2_bullet_active) {
    display.drawPixel(saucer2_bullet_x, saucer2_bullet_y, BLACK);
  }
  
  // Process ship based on its state
  if (ship_state == ALIVE) {
    // Simulate AI decisions for the player ship (PDP-1 style)
    if (current_time > auto_rotation_time) {
      // Choose a target to aim at (50% chance for each saucer if they're alive)
      if (saucer1_state == ALIVE && saucer2_state == ALIVE) {
        if (random(100) > 50) {
          target_rotation = getAngleToTarget(ship_x, ship_y, saucer1_x, saucer1_y);
        } else {
          target_rotation = getAngleToTarget(ship_x, ship_y, saucer2_x, saucer2_y);
        }
      } else if (saucer1_state == ALIVE) {
        target_rotation = getAngleToTarget(ship_x, ship_y, saucer1_x, saucer1_y);
      } else if (saucer2_state == ALIVE) {
        target_rotation = getAngleToTarget(ship_x, ship_y, saucer2_x, saucer2_y);
      } else {
        // Both saucers exploding/respawning, just pick a random direction
        target_rotation = random(0, 628) / 100.0; // Random angle between 0 and 2*PI
      }
      
      // Add some randomness to make it less precise (PDP-1 style)
      target_rotation += random(-30, 30) * 0.01;
      target_rotation = normalizeAngle(target_rotation);
      
      auto_rotation_time = current_time + random(1000, 3000);
    }
    
    if (current_time > auto_thrust_time) {
      // Thrusting decision based on aim
      float angle_diff = abs(getAngleDifference(ship_rotation, target_rotation));
      if (angle_diff < 0.2) {
        // If aimed correctly, thrust for a while
        ship_thrusting = true;
        auto_thrust_time = current_time + random(300, 800);
      } else {
        // If not aimed correctly, don't thrust
        ship_thrusting = false;
        auto_thrust_time = current_time + random(100, 300);
      }
    }
    
    // Update ship rotation with smoother movement (PDP-1 style)
    float angle_diff = getAngleDifference(ship_rotation, target_rotation);
    if (abs(angle_diff) > 0.05) {
      // Rotate at a maximum of 0.05 radians per frame for smoother movement
      ship_rotation += (angle_diff > 0 ? 1 : -1) * min(abs(angle_diff), 0.05f);
      ship_rotation = normalizeAngle(ship_rotation);
    }
    
    // Apply thrust to ship ONLY in the direction it's pointing
    if (ship_thrusting) {
      // Since the rocket points up (negative y) when rotation=0, 
      // we need to adjust the thrust direction by 90 degrees
      ship_vx += cos(ship_rotation - PI/2) * ship_thrust;
      ship_vy += sin(ship_rotation - PI/2) * ship_thrust;
    }
    
    // Update position based on velocity (inertia - PDP-1 style physics)
    ship_x += ship_vx * dt;
    ship_y += ship_vy * dt;
    
    // Apply very slight drag (just to prevent perpetual motion)
    ship_vx *= 0.995;
    ship_vy *= 0.995;
    
    // Wrap ship around game area
    if (ship_x < GAME_X_OFFSET) {
      ship_x = GAME_X_OFFSET + GAME_WIDTH - 1;
    } else if (ship_x >= GAME_X_OFFSET + GAME_WIDTH) {
      ship_x = GAME_X_OFFSET;
    }
    
    if (ship_y < GAME_Y_OFFSET) {
      ship_y = GAME_Y_OFFSET + GAME_HEIGHT - 1;
    } else if (ship_y >= GAME_Y_OFFSET + GAME_HEIGHT) {
      ship_y = GAME_Y_OFFSET;
    }
    
    // Check for collision with saucers
    if (saucer1_state == ALIVE && checkCollision(ship_x, ship_y, saucer1_x, saucer1_y, 8)) {
      // Collided with saucer 1
      ship_state = EXPLODING;
      ship_explosion_frame = 0;
      saucer1_state = EXPLODING;
      saucer1_explosion_frame = 0;
      
      // Increment saucer score
      saucer_score++;
      if (saucer_score > 9) saucer_score = 9; // Cap at 9
      
      // Trigger screen flash
      triggerScreenFlash();
    }
    else if (saucer2_state == ALIVE && checkCollision(ship_x, ship_y, saucer2_x, saucer2_y, 8)) {
      // Collided with saucer 2
      ship_state = EXPLODING;
      ship_explosion_frame = 0;
      saucer2_state = EXPLODING;
      saucer2_explosion_frame = 0;
      
      // Increment saucer score
      saucer_score++;
      if (saucer_score > 9) saucer_score = 9; // Cap at 9
      
      // Trigger screen flash
      triggerScreenFlash();
    }
    
    // Player shooting - only when aimed at a saucer
    if (!player_bullet_active && current_time > player_fire_cooldown && random(100) > 90) {
      // Check if aimed at any saucer
      bool can_fire = false;
      
      if (saucer1_state == ALIVE && isAimedAtSaucer(ship_x, ship_y, ship_rotation, saucer1_x, saucer1_y)) {
        can_fire = true;
      } else if (saucer2_state == ALIVE && isAimedAtSaucer(ship_x, ship_y, ship_rotation, saucer2_x, saucer2_y)) {
        can_fire = true;
      }
      
      if (can_fire) {
        player_bullet_active = true;
        player_bullet_x = ship_x + cos(ship_rotation - PI/2) * 6;
        player_bullet_y = ship_y + sin(ship_rotation - PI/2) * 6;
        player_bullet_vx = cos(ship_rotation - PI/2) * BULLET_SPEED;
        player_bullet_vy = sin(ship_rotation - PI/2) * BULLET_SPEED;
        player_bullet_expire = current_time + BULLET_LIFETIME;
        player_fire_cooldown = current_time + PLAYER_COOLDOWN;
      }
    }
  }
  else if (ship_state == EXPLODING) {
    // Ship is exploding, update animation
    ship_explosion_frame++;
    if (ship_explosion_frame >= EXPLOSION_FRAMES) {
      ship_state = RESPAWNING;
      ship_respawn_time = current_time + RESPAWN_DELAY;
    }
  }
  else if (ship_state == RESPAWNING) {
    // Check if it's time to respawn
    if (current_time > ship_respawn_time) {
      respawnShip();
    }
  }

  // Update saucers based on state
  if (saucer1_state == ALIVE && saucer2_state == ALIVE) {
    // Update saucers (in formation, PDP-1 style)
    updateSaucers(dt, current_time);
  }
  else if (saucer1_state == EXPLODING) {
    // Saucer 1 is exploding, update animation
    saucer1_explosion_frame++;
    if (saucer1_explosion_frame >= EXPLOSION_FRAMES) {
      saucer1_state = RESPAWNING;
      saucer1_respawn_time = current_time + RESPAWN_DELAY;
    }
  }
  else if (saucer1_state == RESPAWNING) {
    // Check if it's time to respawn saucer 1
    if (current_time > saucer1_respawn_time) {
      respawnSaucer(1);
      
      // If saucer 2 is also active, update the formation distance
      if (saucer2_state == ALIVE) {
        saucer_vertical_distance = saucer2_y - saucer1_y;
      }
    }
  }
  
  if (saucer2_state == EXPLODING) {
    // Saucer 2 is exploding, update animation
    saucer2_explosion_frame++;
    if (saucer2_explosion_frame >= EXPLOSION_FRAMES) {
      saucer2_state = RESPAWNING;
      saucer2_respawn_time = current_time + RESPAWN_DELAY;
    }
  }
  else if (saucer2_state == RESPAWNING) {
    // Check if it's time to respawn saucer 2
    if (current_time > saucer2_respawn_time) {
      respawnSaucer(2);
      
      // If saucer 1 is also active, update the formation distance
      if (saucer1_state == ALIVE) {
        saucer_vertical_distance = saucer2_y - saucer1_y;
      }
    }
  }
  
  // Update player bullet with tracking behavior
  if (player_bullet_active) {
    // If ship is alive, update bullet direction to track ship's rotation
    if (ship_state == ALIVE) {
      // Calculate the target velocity based on current ship rotation
      float target_vx = cos(ship_rotation - PI/2) * BULLET_SPEED;
      float target_vy = sin(ship_rotation - PI/2) * BULLET_SPEED;
      
      // Gradually adjust bullet velocity to track the ship's rotation
      player_bullet_vx += (target_vx - player_bullet_vx) * player_bullet_tracking_factor;
      player_bullet_vy += (target_vy - player_bullet_vy) * player_bullet_tracking_factor;
      
      // Normalize velocity to maintain constant speed
      float speed = sqrt(player_bullet_vx * player_bullet_vx + player_bullet_vy * player_bullet_vy);
      if (speed > 0) {
        player_bullet_vx = (player_bullet_vx / speed) * BULLET_SPEED;
        player_bullet_vy = (player_bullet_vy / speed) * BULLET_SPEED;
      }
    }
    
    // Update position
    player_bullet_x += player_bullet_vx * dt;
    player_bullet_y += player_bullet_vy * dt;
    
    // Wrap bullet within game area
    if (player_bullet_x < GAME_X_OFFSET) {
      player_bullet_x = GAME_X_OFFSET + GAME_WIDTH - 1;
    } else if (player_bullet_x >= GAME_X_OFFSET + GAME_WIDTH) {
      player_bullet_x = GAME_X_OFFSET;
    }
    
    if (player_bullet_y < GAME_Y_OFFSET) {
      player_bullet_y = GAME_Y_OFFSET + GAME_HEIGHT - 1;
    } else if (player_bullet_y >= GAME_Y_OFFSET + GAME_HEIGHT) {
      player_bullet_y = GAME_Y_OFFSET;
    }
    
    // Check collisions with saucers
    if (saucer1_state == ALIVE && checkCollision(player_bullet_x, player_bullet_y, saucer1_x, saucer1_y, 4)) {
      player_bullet_active = false;
      saucer1_state = EXPLODING;
      saucer1_explosion_frame = 0;
      
      // Increment player score
      player_score++;
      if (player_score > 9) player_score = 9; // Cap at 9
      
      // Trigger screen flash
      triggerScreenFlash();
    }
    else if (saucer2_state == ALIVE && checkCollision(player_bullet_x, player_bullet_y, saucer2_x, saucer2_y, 4)) {
      player_bullet_active = false;
      saucer2_state = EXPLODING;
      saucer2_explosion_frame = 0;
      
      // Increment player score
      player_score++;
      if (player_score > 9) player_score = 9; // Cap at 9
      
      // Trigger screen flash
      triggerScreenFlash();
    }
    
    // Bullet lifetime
    if (current_time > player_bullet_expire) {
      player_bullet_active = false;
    }
  }
  
  // Update saucer bullets
  if (saucer1_state == ALIVE) {
    updateSaucerBullet(saucer1_bullet_active, saucer1_bullet_x, saucer1_bullet_y, 
                     saucer1_bullet_vx, saucer1_bullet_vy, saucer1_bullet_expire, dt, current_time);
  }
  
  if (saucer2_state == ALIVE) {
    updateSaucerBullet(saucer2_bullet_active, saucer2_bullet_x, saucer2_bullet_y, 
                     saucer2_bullet_vx, saucer2_bullet_vy, saucer2_bullet_expire, dt, current_time);
  }
  
  // Saucer shooting (PDP-1 style random timing)
  if (!saucer1_bullet_active && !saucer2_bullet_active && current_time > saucer_fire_cooldown) {
    if (random(100) > 50 && saucer1_state == ALIVE && ship_state == ALIVE) {
      // Saucer 1 shoots
      saucer1_bullet_active = true;
      saucer1_bullet_x = saucer1_x;
      saucer1_bullet_y = saucer1_y;
      
      // Aim towards player with some randomness (PDP-1 style accuracy)
      float angle = atan2(ship_y - saucer1_y, ship_x - saucer1_x) + 
                   (random(-50, 50) / 100.0);
      saucer1_bullet_vx = cos(angle) * BULLET_SPEED * 0.7;
      saucer1_bullet_vy = sin(angle) * BULLET_SPEED * 0.7;
      saucer1_bullet_expire = current_time + BULLET_LIFETIME;
    } else if (saucer2_state == ALIVE && ship_state == ALIVE) {
      // Saucer 2 shoots
      saucer2_bullet_active = true;
      saucer2_bullet_x = saucer2_x;
      saucer2_bullet_y = saucer2_y;
      
      // Aim towards player with some randomness
      float angle = atan2(ship_y - saucer2_y, ship_x - saucer2_x) + 
                   (random(-50, 50) / 100.0);
      saucer2_bullet_vx = cos(angle) * BULLET_SPEED * 0.7;
      saucer2_bullet_vy = sin(angle) * BULLET_SPEED * 0.7;
      saucer2_bullet_expire = current_time + BULLET_LIFETIME;
    }
    saucer_fire_cooldown = current_time + SAUCER_COOLDOWN;
  }
  
  // Update background counter for star flicker effect (PDP-1 style)
  bg_counter++;
  
  // Draw stars only on certain frames (PDP-1 style)
  if (bg_counter % 2 == 0) {
    drawStars();
  }
  
  // Only draw game objects if not in a screen flash
  if (!screen_flash) {
    // Draw game objects based on their state
    if (ship_state == ALIVE) {
      drawShip(ship_x, ship_y, ship_rotation);
    } else if (ship_state == EXPLODING) {
      drawExplosion(ship_x, ship_y, ship_explosion_frame);
    }
    
    if (saucer1_state == ALIVE) {
      drawSaucer(saucer1_x, saucer1_y);
    } else if (saucer1_state == EXPLODING) {
      drawExplosion(saucer1_x, saucer1_y, saucer1_explosion_frame);
    }
    
    if (saucer2_state == ALIVE) {
      drawSaucer(saucer2_x, saucer2_y);
    } else if (saucer2_state == EXPLODING) {
      drawExplosion(saucer2_x, saucer2_y, saucer2_explosion_frame);
    }
    
    // Draw bullets
    if (player_bullet_active) {
      display.drawPixel(player_bullet_x, player_bullet_y, WHITE);
    }
    if (saucer1_bullet_active) {
      display.drawPixel(saucer1_bullet_x, saucer1_bullet_y, WHITE);
    }
    if (saucer2_bullet_active) {
      display.drawPixel(saucer2_bullet_x, saucer2_bullet_y, WHITE);
    }
    
    // Clear score area and draw scores
    clearScoreArea();
    drawScores();
  }
  
  // Update display
  display.display();
  
  // Small delay for performance
  delay(20); // ~50 FPS - Similar to PDP-1 refresh rate
}

// Trigger a white screen flash effect
void triggerScreenFlash() {
  screen_flash = true;
  flash_frames = 0;
}

// Draw a PDP-1 style explosion animation
void drawExplosion(float x, float y, int frame) {
  int radius = EXPLOSION_RADIUS[frame];
  
  // Draw expanding circle with points
  for (int i = 0; i < EXPLOSION_POINTS; i++) {
    float angle = i * (2.0 * PI / EXPLOSION_POINTS);
    int px = x + radius * cos(angle);
    int py = y + radius * sin(angle);
    
    // Only draw if within game area
    if (px >= GAME_X_OFFSET && px < GAME_X_OFFSET + GAME_WIDTH &&
        py >= GAME_Y_OFFSET && py < GAME_Y_OFFSET + GAME_HEIGHT) {
      display.drawPixel(px, py, WHITE);
    }
    
    // Add some randomly placed debris particles
    if (frame > 2 && frame < 10) {
      float debris_angle = angle + random(-30, 30) * 0.01;
      float debris_dist = random(1, radius + 2);
      int dx = x + debris_dist * cos(debris_angle);
      int dy = y + debris_dist * sin(debris_angle);
      
      if (dx >= GAME_X_OFFSET && dx < GAME_X_OFFSET + GAME_WIDTH &&
          dy >= GAME_Y_OFFSET && dy < GAME_Y_OFFSET + GAME_HEIGHT) {
        display.drawPixel(dx, dy, WHITE);
      }
    }
  }
}

// Respawn ship at a random position
void respawnShip() {
  ship_x = GAME_X_OFFSET + random(GAME_WIDTH/4, 3*GAME_WIDTH/4);
  ship_y = GAME_Y_OFFSET + random(GAME_HEIGHT/4, 3*GAME_HEIGHT/4);
  ship_vx = ship_vy = 0;
  ship_state = ALIVE;
}

// Respawn saucer at a new position
void respawnSaucer(int saucer_num) {
  if (saucer_num == 1) {
    saucer1_x = GAME_X_OFFSET + random(10, GAME_WIDTH - 10);
    saucer1_y = GAME_Y_OFFSET + random(10, GAME_HEIGHT/2 - 10);
    saucer1_state = ALIVE;
  } else {
    saucer2_x = GAME_X_OFFSET + random(10, GAME_WIDTH - 10);
    saucer2_y = GAME_Y_OFFSET + random(GAME_HEIGHT/2 + 10, GAME_HEIGHT - 10);
    saucer2_state = ALIVE;
  }
}

// Draw a single digit using our custom font
void drawDigit(int digit, int x, int y) {
  if (digit < 0 || digit > 9) return; // Only support 0-9
  
  // Draw the digit pixel by pixel
  for (int row = 0; row < DIGIT_HEIGHT; row++) {
    for (int col = 0; col < DIGIT_WIDTH; col++) {
      if (DIGITS[digit][row][col] == 1) {
        display.drawPixel(x + col, y + row, WHITE);
      }
    }
  }
}

// Draw a score with multiple digits
void drawScore(int score, int x, int y) {
  // Handle single and double digit scores
  if (score < 10) {
    // Single digit - add leading zero for timer
    if (y == SCORE_Y_BOTTOM) {
      // This is the timer, draw leading zero
      drawDigit(0, x - DIGIT_SPACING, y);
      drawDigit(score, x, y);
    } else {
      // Single digit score
      drawDigit(score, x, y);
    }
  } else if (score < 100) {
    // Double digits
    int tens = score / 10;
    int ones = score % 10;
    drawDigit(tens, x - DIGIT_SPACING, y);
    drawDigit(ones, x, y);
  }
}

// Update game timer - always counts up from 00 to 99
void updateTimer() {
  unsigned long current_time = millis();
  
  // Update timer only once per second
  if (current_time - timer_update_time >= 1000) {
    timer_update_time = current_time;
    
    // Always increment timer
    game_timer++;
    if (game_timer >= 100) {
      game_timer = 0; // Reset to 00 when reaching 100
    }
  }
}

// Clear the score area more thoroughly
void clearScoreArea() {
  // Define score display areas
  for (int i = 0; i < 3; i++) {
    int y_pos;
    switch (i) {
      case 0: y_pos = SCORE_Y_TOP; break;
      case 1: y_pos = SCORE_Y_MIDDLE; break;
      case 2: y_pos = SCORE_Y_BOTTOM; break;
    }
    
    // Clear area for double-digit score (including spacing)
    for (int y = y_pos; y < y_pos + DIGIT_HEIGHT; y++) {
      for (int x = GAME_X_OFFSET + GAME_WIDTH - 12; x < GAME_X_OFFSET + GAME_WIDTH; x++) {
        display.drawPixel(x, y, BLACK);
      }
    }
  }
}

// Draw scores with custom font, positioned at edge of game area
void drawScores() {
  // Position scores a few pixels from the right edge of game area
  int score_x = GAME_X_OFFSET + GAME_WIDTH - 5;
  
  // Player score at top position
  drawScore(player_score, score_x, SCORE_Y_TOP);
  
  // Saucer score at middle position
  drawScore(saucer_score, score_x, SCORE_Y_MIDDLE);
  
  // Timer at bottom position (always show as 2 digits)
  drawScore(game_timer, score_x, SCORE_Y_BOTTOM);
}

// Update saucers using the PDP-1 style zig-zag formation movement
void updateSaucers(float dt, unsigned long current_time) {
  // Check if it's time to change direction
  if (current_time > direction_change_time) {
    // Select a new movement pattern from the table
    current_movement = random(0, 8); // 8 possible movement directions
    
    // Set next direction change time
    direction_change_time = current_time + random(1500, 3000);
  }
  
  // Apply current movement pattern
  float speed_factor = 25.0 * dt;
  float dx = MOVEMENT_TABLE[current_movement][0] * speed_factor;
  float dy = MOVEMENT_TABLE[current_movement][1] * speed_factor;
  
  // Update saucer positions, maintaining their formation
  saucer1_x += dx;
  saucer1_y += dy;
  
  // Always keep saucer2 at the same position relative to saucer1
  saucer2_x = saucer1_x;
  saucer2_y = saucer1_y + saucer_vertical_distance;
  
  // Wrap saucers around the game area
  if (saucer1_x < GAME_X_OFFSET) {
    saucer1_x = GAME_X_OFFSET + GAME_WIDTH - 1;
    saucer2_x = saucer1_x;
  } else if (saucer1_x >= GAME_X_OFFSET + GAME_WIDTH) {
    saucer1_x = GAME_X_OFFSET;
    saucer2_x = saucer1_x;
  }
  
  if (saucer1_y < GAME_Y_OFFSET) {
    saucer1_y = GAME_Y_OFFSET + GAME_HEIGHT - 1;
    saucer2_y = saucer1_y + saucer_vertical_distance;
  } else if (saucer1_y >= GAME_Y_OFFSET + GAME_HEIGHT) {
    saucer1_y = GAME_Y_OFFSET;
    saucer2_y = saucer1_y + saucer_vertical_distance;
  }
  
  // Also wrap saucer2 if it goes off screen
  if (saucer2_y >= GAME_Y_OFFSET + GAME_HEIGHT) {
    saucer2_y = GAME_Y_OFFSET + (saucer2_y - (GAME_Y_OFFSET + GAME_HEIGHT));
    saucer1_y = saucer2_y - saucer_vertical_distance;
  } else if (saucer2_y < GAME_Y_OFFSET) {
    saucer2_y = GAME_Y_OFFSET + GAME_HEIGHT - (GAME_Y_OFFSET - saucer2_y);
    saucer1_y = saucer2_y - saucer_vertical_distance;
  }
}

// Normalize angle to [0, 2π]
float normalizeAngle(float angle) {
  while (angle < 0) angle += 2 * PI;
  while (angle >= 2 * PI) angle -= 2 * PI;
  return angle;
}

// Get the shortest angle difference between two angles
float getAngleDifference(float a1, float a2) {
  float diff = normalizeAngle(a2 - a1);
  if (diff > PI) diff -= 2 * PI;
  return diff;
}

// Get angle from point 1 to point 2
float getAngleToTarget(float x1, float y1, float x2, float y2) {
  return atan2(y2 - y1, x2 - x1);
}

// Helper function to update saucer bullets
void updateSaucerBullet(bool &active, float &x, float &y, float &vx, float &vy, 
                        unsigned long &expire, float dt, unsigned long current_time) {
  if (active) {
    x += vx * dt;
    y += vy * dt;
    
    // Wrap bullet within game area
    if (x < GAME_X_OFFSET) {
      x = GAME_X_OFFSET + GAME_WIDTH - 1;
    } else if (x >= GAME_X_OFFSET + GAME_WIDTH) {
      x = GAME_X_OFFSET;
    }
    
    if (y < GAME_Y_OFFSET) {
      y = GAME_Y_OFFSET + GAME_HEIGHT - 1;
    } else if (y >= GAME_Y_OFFSET + GAME_HEIGHT) {
      y = GAME_Y_OFFSET;
    }
    
    // Check collision with player
    if (ship_state == ALIVE && checkCollision(x, y, ship_x, ship_y, 4)) {
      active = false;
      ship_state = EXPLODING;
      ship_explosion_frame = 0;
      
      // Increment saucer score
      saucer_score++;
      if (saucer_score > 9) saucer_score = 9; // Cap at 9
      
      // Trigger screen flash
      triggerScreenFlash();
    }
    
    // Bullet lifetime
    if (current_time > expire) {
      active = false;
    }
  }
}

// Draw stars
void drawStars() {
  for (int i = 0; i < NUM_STARS; i++) {
    // Only draw stars within the game area
    if (stars[i][0] >= GAME_X_OFFSET && stars[i][0] < GAME_X_OFFSET + GAME_WIDTH &&
        stars[i][1] >= GAME_Y_OFFSET && stars[i][1] < GAME_Y_OFFSET + GAME_HEIGHT) {
      display.drawPixel(stars[i][0], stars[i][1], WHITE);
    }
  }
}

// Improved collision detection using distance formula
bool checkCollision(float x1, float y1, float x2, float y2, float radius) {
  return sqrt((x1 - x2) * (x1 - x2) + (y1 - y2) * (y1 - y2)) < radius;
}

// Check if ship is aimed at a saucer
bool isAimedAtSaucer(float ship_x, float ship_y, float ship_rotation, 
                     float saucer_x, float saucer_y, float tolerance) {
  // Calculate angle to saucer
  float angle_to_saucer = atan2(saucer_y - ship_y, saucer_x - ship_x);
  
  // Calculate the difference between angles
  float angle_diff = getAngleDifference(ship_rotation - PI/2, angle_to_saucer);
  
  // Check if angle difference is within tolerance
  return abs(angle_diff) < tolerance;
}

// Draw player ship as a dot pattern (PDP-1 style)
void drawShip(float x, float y, float rotation) {
  int orig_x = (int)x;
  int orig_y = (int)y;
  
  // Define the rocket shape points in its local coordinate system (PDP-1 style)
  const int NUM_SHIP_POINTS = 15;
  const int8_t points[][2] = {
    {0, -6},      // Top point
    {-2, -4}, {2, -4},  // Upper row
    {-3, -2}, {3, -2},  // Mid-upper row
    {-3, 0}, {3, 0},    // Middle row
    {-2, 1}, {2, 1},    // Mid-lower row
    {-4, 2}, {0, 2}, {4, 2},  // Lower body row
    {-3, 4}, {3, 4}     // Bottom fins
  };
  
  // Draw each point after rotation (PDP-1 style)
  for (int i = 0; i < NUM_SHIP_POINTS; i++) {
    // Rotate point
    float rx = points[i][0] * cos(rotation) - points[i][1] * sin(rotation);
    float ry = points[i][0] * sin(rotation) + points[i][1] * cos(rotation);
    
    // Calculate pixel position
    int px = orig_x + (int)rx;
    int py = orig_y + (int)ry;
    
    // Only draw if within game area
    if (px >= GAME_X_OFFSET && px < GAME_X_OFFSET + GAME_WIDTH &&
        py >= GAME_Y_OFFSET && py < GAME_Y_OFFSET + GAME_HEIGHT) {
      display.drawPixel(px, py, WHITE);
    }
  }
  
  // Add exhaust flame if thrusting - pointing from bottom of rocket
  if (ship_thrusting) {
    // Calculate bottom center position of the rocket
    float bottom_x = 0 * cos(rotation) - 4 * sin(rotation);
    float bottom_y = 0 * sin(rotation) + 4 * cos(rotation);
    
    // Add flame a bit below the bottom center
    float flame_x = bottom_x + 2 * sin(rotation); // Perpendicular to rotation
    float flame_y = bottom_y - 2 * cos(rotation); // Perpendicular to rotation
    
    int px = orig_x + (int)flame_x;
    int py = orig_y + (int)flame_y;
    
    // Only draw if within game area
    if (px >= GAME_X_OFFSET && px < GAME_X_OFFSET + GAME_WIDTH &&
        py >= GAME_Y_OFFSET && py < GAME_Y_OFFSET + GAME_HEIGHT) {
      display.drawPixel(px, py, WHITE);
    }
  }
}

// Helper to clear ship (draws in black)
void clearShip() {
  // We'll use a larger area to ensure we cover the ship in any rotation
  for (int dy = -8; dy <= 8; dy++) {
    for (int dx = -8; dx <= 8; dx++) {
      int x = ship_x + dx;
      int y = ship_y + dy;
      
      // Only clear points within the game area
      if (x >= GAME_X_OFFSET && x < GAME_X_OFFSET + GAME_WIDTH &&
          y >= GAME_Y_OFFSET && y < GAME_Y_OFFSET + GAME_HEIGHT) {
        // Don't erase stars
        bool is_star = false;
        for (int i = 0; i < NUM_STARS; i++) {
          if (stars[i][0] == x && stars[i][1] == y) {
            is_star = true;
            break;
          }
        }
        if (!is_star) {
          display.drawPixel(x, y, BLACK);
        }
      }
    }
  }
}

// Draw saucer as a dot pattern (PDP-1 style)
void drawSaucer(float x, float y) {
  int orig_x = (int)x;
  int orig_y = (int)y;
  
  // Define saucer points (PDP-1 style dot pattern)
  const int NUM_SAUCER_POINTS = 18;
  const int8_t points[][2] = {
    // Top dome
    {-1, -2}, {1, -2},
    // Mid-top row
    {-4, -1}, {-3, -1}, {3, -1}, {4, -1},
    // Middle row (widest)
    {-5, 0}, {-2, 0}, {-1, 0}, {1, 0}, {2, 0}, {5, 0},
    // Mid-bottom row
    {-4, 1}, {-3, 1}, {3, 1}, {4, 1},
    // Bottom
    {-1, 2}, {1, 2}
  };
  
  // Draw each point
  for (int i = 0; i < NUM_SAUCER_POINTS; i++) {
    int px = orig_x + points[i][0];
    int py = orig_y + points[i][1];
    
    // Only draw if within game area
    if (px >= GAME_X_OFFSET && px < GAME_X_OFFSET + GAME_WIDTH &&
        py >= GAME_Y_OFFSET && py < GAME_Y_OFFSET + GAME_HEIGHT) {
      display.drawPixel(px, py, WHITE);
    }
  }
}

// Helper to clear saucer
void clearSaucer(float x, float y) {
  // Clear a rectangle around the saucer
  for (int dy = -6; dy <= 6; dy++) {
    for (int dx = -6; dx <= 6; dx++) {
      int px = x + dx;
      int py = y + dy;
      
      // Only clear points within the game area
      if (px >= GAME_X_OFFSET && px < GAME_X_OFFSET + GAME_WIDTH &&
          py >= GAME_Y_OFFSET && py < GAME_Y_OFFSET + GAME_HEIGHT) {
        // Don't erase stars
        bool is_star = false;
        for (int i = 0; i < NUM_STARS; i++) {
          if (stars[i][0] == px && stars[i][1] == py) {
            is_star = true;
            break;
          }
        }
        if (!is_star) {
          display.drawPixel(px, py, BLACK);
        }
      }
    }
  }
}