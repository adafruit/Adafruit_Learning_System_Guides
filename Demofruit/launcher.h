// launcher.h — boot menu for the Fruit Jam Demoscene Sampler
// DVHSTX16 + GFX text over a slowly tumbling dim shaded cube.
// Button3 up, Button2 down, Button1 launch.

#pragma once
#include <Adafruit_dvhstx.h>
#include <math.h>
#include "common.h"
#include "audio.h"
#include "leds.h"

#define MENU_COUNT 6
static const char *menuNames[MENU_COUNT] = {
  "STARFIELD",
  "PLASMA",
  "CHROME SPHERE",
  "VALLEY RUN",
  "ROTOZOOM",
  "THE JUGGLER",
};

// signature RGB per demo (menu order) — used to tint the cube
static const uint8_t _menuTint[MENU_COUNT][3] = {
  {255,255,255}, {255,0,200}, {0,220,255}, {0,255,40}, {255,120,0}, {255,30,30}
};

// ── Tumbling cube ─────────────────────────────────────────────────────────────
static const float _cubeV[8][3] = {
  {-1,-1,-1},{ 1,-1,-1},{ 1, 1,-1},{-1, 1,-1},
  {-1,-1, 1},{ 1,-1, 1},{ 1, 1, 1},{-1, 1, 1},
};
// faces as quads (vertex indices), CCW when facing viewer
static const uint8_t _cubeF[6][4] = {
  {0,1,2,3}, {5,4,7,6}, {4,0,3,7}, {1,5,6,2}, {4,5,1,0}, {3,2,6,7},
};
static const uint8_t _cubeE[12][2] = {
  {0,1},{1,2},{2,3},{3,0},{4,5},{5,6},{6,7},{7,4},{0,4},{1,5},{2,6},{3,7},
};

static float _cubeAngle = 0.0f;

// project + draw the cube, dim, tinted toward (tr,tg,tb)
static void _drawCube(DVHSTX16 &d, uint8_t tr, uint8_t tg, uint8_t tb) {
  float a = _cubeAngle, b = _cubeAngle * 0.6f;
  float ca = cosf(a), sa = sinf(a), cb = cosf(b), sb = sinf(b);

  float px[8], py[8], pz[8];
  for (int i = 0; i < 8; i++) {
    float x = _cubeV[i][0], y = _cubeV[i][1], z = _cubeV[i][2];
    // rotate Y then X
    float x1 =  x*ca + z*sa;
    float z1 = -x*sa + z*ca;
    float y1 =  y*cb - z1*sb;
    float z2 =  y*sb + z1*cb;
    // perspective; cube sits centered, pushed back
    float zc = z2 + 4.5f;
    if (zc < 0.5f) zc = 0.5f;          // guard: never divide toward zero
    float s  = 150.0f / zc;
    float sx = 160 + x1 * s;
    float sy = 120 + y1 * s;
    // clamp well outside screen but finite, so GFX never sees wild values
    if (sx < -2000) sx = -2000; if (sx > 2000) sx = 2000;
    if (sy < -2000) sy = -2000; if (sy > 2000) sy = 2000;
    px[i] = sx;
    py[i] = sy;
    pz[i] = z2;
  }

  // face depth sort (painter's): draw far faces first
  int order[6]; float fz[6];
  for (int f = 0; f < 6; f++) {
    order[f] = f;
    fz[f] = pz[_cubeF[f][0]] + pz[_cubeF[f][1]]
          + pz[_cubeF[f][2]] + pz[_cubeF[f][3]];
  }
  for (int i = 0; i < 5; i++)            // tiny insertion sort, far->near
    for (int j = i + 1; j < 6; j++)
      if (fz[j] > fz[i]) { float t=fz[i];fz[i]=fz[j];fz[j]=t;
                           int o=order[i];order[i]=order[j];order[j]=o; }

  for (int k = 0; k < 6; k++) {
    int f = order[k];
    const uint8_t *q = _cubeF[f];
    // back-face cull via 2D winding (screen-space cross product)
    float ax = px[q[1]] - px[q[0]], ay = py[q[1]] - py[q[0]];
    float bx = px[q[2]] - px[q[0]], by = py[q[2]] - py[q[0]];
    float cross = ax * by - ay * bx;
    if (cross <= 0) continue;            // facing away

    // shade by face depth: nearer = a touch brighter, all dim
    float shade = 0.18f + 0.12f * (float)k / 5.0f;   // 0.18..0.30
    uint8_t r = (uint8_t)(tr * shade);
    uint8_t g = (uint8_t)(tg * shade);
    uint8_t bl= (uint8_t)(tb * shade);
    uint16_t col = C565(r, g, bl);
    // quad as two triangles
    d.fillTriangle(px[q[0]],py[q[0]], px[q[1]],py[q[1]], px[q[2]],py[q[2]], col);
    d.fillTriangle(px[q[0]],py[q[0]], px[q[2]],py[q[2]], px[q[3]],py[q[3]], col);
  }

  // faint wireframe over the fills for definition
  uint16_t wire = C565(tr/3, tg/3, tb/3);
  for (int e = 0; e < 12; e++)
    d.drawLine(px[_cubeE[e][0]], py[_cubeE[e][0]],
               px[_cubeE[e][1]], py[_cubeE[e][1]], wire);
}

static void _menuFrame(DVHSTX16 &d, int sel) {
  d.fillScreen(0x0000);

  // cube backdrop, tinted toward the highlighted demo
  _drawCube(d, _menuTint[sel][0], _menuTint[sel][1], _menuTint[sel][2]);

  // ── text on top ─────────────────────────────────────────────────────────
  d.setTextColor(C565(0, 230, 60));
  d.setTextSize(1);
  d.setCursor(34, 18);
  d.print("== FRUIT JAM DEMOSCENE SAMPLER ==");

  d.setTextSize(2);
  for (int i = 0; i < MENU_COUNT; i++) {
    int y = 52 + i * 24;
    if (i == sel) { d.setTextColor(C565(255,255,255)); d.setCursor(58, y); d.print("> "); }
    else          { d.setTextColor(C565(0,180,40));    d.setCursor(58, y); d.print("  "); }
    d.print(menuNames[i]);
  }

  d.setTextSize(1);
  d.setTextColor(C565(0, 140, 30));
  d.setCursor(30, 212);
  d.print("BTN3 UP   BTN2 DOWN   BTN1 LAUNCH");
  d.setCursor(48, 224);
  d.print("press RESET in demo for menu   music by kqvc");

  d.swap();
}

// never returns — launches via watchdog reboot
static void menuRun(DVHSTX16 &d) {
  Serial.println("menu: entry"); Serial.flush();
  // LED heartbeat: green flash = reached menu (visible without serial/display)
  ledAll(0, 255, 0); delay(200);
  int sel = 0;
  ledDemoColor(sel + 1);
  _menuFrame(d, sel);
  Serial.println("menu: first frame drawn"); Serial.flush();
  for (;;) {
    smpAudioPump();

    // physical layout: Button3 top, Button2 middle, Button1 bottom
    if (smpBtn(2)) { sel = (sel + MENU_COUNT - 1) % MENU_COUNT; ledDemoColor(sel + 1); }
    if (smpBtn(1)) { sel = (sel + 1) % MENU_COUNT;              ledDemoColor(sel + 1); }
    if (smpBtn(0)) smpLaunchDemo((uint32_t)sel);

    _cubeAngle += 0.012f;                // slow tumble
    _menuFrame(d, sel);
    smpAudioPump();
    delay(1);                            // yield for USB/background tasks
  }
}
