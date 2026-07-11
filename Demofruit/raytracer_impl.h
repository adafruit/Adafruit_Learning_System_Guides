// SPDX-FileCopyrightText: 2026 John Park with Claude Opus 4.8 for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// raytracer.h — Chrome sphere raytracer for Fruit Jam RP2350
// DVHSTX16, 320x240 double-buffered.
// Core1 renders frames into a pixel buffer.
// Core0 handles display blit, swap, and button input.
//
// Buttons (GPIO0/4/5 = Button1/2/3 on Fruit Jam):
//   Button1 — randomize light angle (horizontal + elevation)
//   Button2 — randomize camera height
//   Button3 — randomize camera distance from sphere
//
// Optimizations:
//   1. Specular powf() -> 256-entry LUT
//   2. Shadow ray skipped outside sphere shadow footprint
//   3. Early-exit sky test
//   4. Per-row ray component precomputed
//   5. Half-res upscale via direct framebuffer writes
//   6. __attribute__((optimize("O3"))) on render function


// ── Tuning ────────────────────────────────────────────────────────────────────
#define RT_HALF_RES       1       // 1=render 160x120 upscaled 2x2, 0=320x240
#define RT_REFLECTIONS    1       // mirror bounce depth (1=fast, 2=richer)
#define RT_SPHERE_R       1.0f    // sphere radius
#define RT_SPHERE_BASE_Y  1.02f   // sphere center Y at rest
#define RT_SPHERE_BOB     0.18f   // vertical bob amplitude
#define RT_SPHERE_BOB_SPD 0.03f   // bob speed (radians/frame)
#define RT_CAM_SPD        0.008f  // camera orbit speed (radians/frame)
#define RT_CHECKER_SCALE  0.9f    // checker tile size
#define RT_FOV            0.85f   // field of view half-angle
#define RT_SKY_THRESHOLD  0.08f   // rd.y above this = pure sky early exit

// Starting values for button-randomizable parameters
#define RT_CAM_DIST_DEF   4.2f    // camera orbit radius
#define RT_CAM_HEIGHT_DEF 1.8f    // camera height above floor
#define RT_LIGHT_X_DEF    0.6f    // light direction x (horizontal)
#define RT_LIGHT_Y_DEF    0.8f    // light direction y (elevation)
#define RT_LIGHT_Z_DEF    0.4f    // light direction z (horizontal)

// Button randomization ranges
#define RT_LIGHT_ELEV_MIN 0.3f    // min light elevation (low raking light)
#define RT_LIGHT_ELEV_MAX 1.2f    // max light elevation (high overhead)
#define RT_CAM_HEIGHT_MIN 0.5f    // just above floor level
#define RT_CAM_HEIGHT_MAX 5.0f    // high aerial view
#define RT_CAM_DIST_MIN   2.0f    // close — sphere fills frame
#define RT_CAM_DIST_MAX   8.0f    // distant — sphere small in scene

// ── Colors (RGB float 0-1) ────────────────────────────────────────────────────
#define SKY_TOP_R  0.078f
#define SKY_TOP_G  0.235f
#define SKY_TOP_B  0.549f
#define SKY_HOR_R  0.706f
#define SKY_HOR_G  0.824f
#define SKY_HOR_B  0.922f
#define CHK_WARM_R 0.941f
#define CHK_WARM_G 0.863f
#define CHK_WARM_B 0.706f
#define CHK_COOL_R 0.7f
#define CHK_COOL_G 0.05f
#define CHK_COOL_B 0.05f
#define CHK_AMB    0.12f
#define SPH_DIFF_R 0.55f
#define SPH_DIFF_G 0.52f
#define SPH_DIFF_B 0.48f
#define SPH_DIFF_W 0.05f
#define SPEC_R     1.00f
#define SPEC_G     0.98f
#define SPEC_B     0.94f
#define SPEC_POW   80.0f

// ── Render dimensions ─────────────────────────────────────────────────────────
#if RT_HALF_RES
  #define RT_W  160
  #define RT_H  120
#else
  #define RT_W  320
  #define RT_H  240
#endif

// ── Vec3 ──────────────────────────────────────────────────────────────────────
struct V3 {
  float x, y, z;
  V3() : x(0), y(0), z(0) {}
  V3(float x, float y, float z) : x(x), y(y), z(z) {}
  V3  operator+(const V3 &b) const { return {x+b.x, y+b.y, z+b.z}; }
  V3  operator-(const V3 &b) const { return {x-b.x, y-b.y, z-b.z}; }
  V3  operator*(float t)     const { return {x*t,   y*t,   z*t};   }
  V3  operator*(const V3 &b) const { return {x*b.x, y*b.y, z*b.z}; }
  V3 &operator+=(const V3 &b) { x+=b.x; y+=b.y; z+=b.z; return *this; }
};

static inline float dot(V3 a, V3 b)     { return a.x*b.x + a.y*b.y + a.z*b.z; }
static inline float len(V3 a)           { return sqrtf(dot(a,a)); }
static inline V3    norm(V3 a)          { return a*(1.0f/len(a)); }
static inline V3    reflect(V3 d, V3 n) { return d - n*(2.0f*dot(d,n)); }
static inline V3    clamp3(V3 c) {
  return {fmaxf(0,fminf(1,c.x)), fmaxf(0,fminf(1,c.y)), fmaxf(0,fminf(1,c.z))};
}
static inline V3 lerp3(V3 a, V3 b, float t) { return a*(1-t) + b*t; }

// ── Specular LUT ──────────────────────────────────────────────────────────────
#define SPEC_LUT_SIZE 256
static float _specLUT[SPEC_LUT_SIZE];

static void _buildSpecLUT() {
  for (int i = 0; i < SPEC_LUT_SIZE; i++) {
    float x = i / (float)(SPEC_LUT_SIZE - 1);
    _specLUT[i] = powf(x, SPEC_POW);
  }
}

static inline float specular(float cosA) {
  if (cosA <= 0.0f) return 0.0f;
  int idx = (int)(cosA * (SPEC_LUT_SIZE - 1));
  if (idx >= SPEC_LUT_SIZE) idx = SPEC_LUT_SIZE - 1;
  return _specLUT[idx];
}

// ── Scene state — volatile so core1 picks up core0 button changes ─────────────
static volatile bool  _rtFrameReady = false;
static volatile float _rtCamDist    = RT_CAM_DIST_DEF;
static volatile float _rtCamHeight  = RT_CAM_HEIGHT_DEF;
static volatile float _rtLightX     = RT_LIGHT_X_DEF;
static volatile float _rtLightY     = RT_LIGHT_Y_DEF;
static volatile float _rtLightZ     = RT_LIGHT_Z_DEF;

static uint16_t *_rtBuf;   // RT_W*RT_H, lives in g_arena
static float    _rtCamAngle = 0.0f;
static float    _rtBobAngle = 0.0f;

// Shadow footprint (updated each frame by core1)
static float _shadowCX = 0.0f, _shadowCZ = 0.0f, _shadowR2 = 0.0f;

// Random float in [lo, hi]
static inline float _rtRandf(float lo, float hi) {
  return lo + (hi - lo) * (random(1000) / 999.0f);
}

// ── Color helpers ─────────────────────────────────────────────────────────────
static inline uint16_t toRGB565(V3 c) {
  c = clamp3(c);
  uint8_t r = (uint8_t)(c.x * 255.0f);
  uint8_t g = (uint8_t)(c.y * 255.0f);
  uint8_t b = (uint8_t)(c.z * 255.0f);
  return ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3);
}

static V3 skyColor(V3 dir) {
  float t = fmaxf(0.0f, dir.y);
  return lerp3({SKY_HOR_R,SKY_HOR_G,SKY_HOR_B},{SKY_TOP_R,SKY_TOP_G,SKY_TOP_B}, t);
}

// ── Intersection ──────────────────────────────────────────────────────────────
static inline float hitSphere(V3 ro, V3 rd, V3 sc, float sr) {
  V3    oc = ro - sc;
  float b  = dot(oc, rd);
  float c  = dot(oc, oc) - sr*sr;
  float h  = b*b - c;
  if (h < 0.0f) return -1.0f;
  float sq = sqrtf(h);
  float t  = -b - sq;
  if (t > 0.001f) return t;
  t = -b + sq;
  return (t > 0.001f) ? t : -1.0f;
}

static inline float hitFloor(V3 ro, V3 rd) {
  if (fabsf(rd.y) < 0.0001f) return -1.0f;
  float t = -ro.y / rd.y;
  return (t > 0.001f) ? t : -1.0f;
}

// ── Checker floor color ───────────────────────────────────────────────────────
static inline V3 checkerColor(float wx, float wz, V3 lightDir, float shadow) {
  int ix = (int)floorf(wx * RT_CHECKER_SCALE);
  int iz = (int)floorf(wz * RT_CHECKER_SCALE);
  bool warm = ((ix + iz) & 1) == 0;
  V3 base = warm
    ? V3(CHK_WARM_R, CHK_WARM_G, CHK_WARM_B)
    : V3(CHK_COOL_R, CHK_COOL_G, CHK_COOL_B);
  float diff = fmaxf(0.0f, lightDir.y) * shadow;
  return base * (CHK_AMB + diff * (1.0f - CHK_AMB));
}

// ── Trace ─────────────────────────────────────────────────────────────────────
static V3 trace(V3 ro, V3 rd, V3 sphereCenter, V3 lightDir) {
  if (rd.y > RT_SKY_THRESHOLD) return skyColor(rd);

  float ts = hitSphere(ro, rd, sphereCenter, RT_SPHERE_R);
  float tf = hitFloor(ro, rd);

  if (ts < 0.0f && tf < 0.0f) return skyColor(norm(rd));

  if (ts > 0.0f && (tf < 0.0f || ts < tf)) {
    V3 hitPt  = ro + rd*ts;
    V3 normal = norm(hitPt - sphereCenter);
    V3 refDir = norm(reflect(rd, normal));
    V3 refCol;

#if RT_REFLECTIONS >= 2
    float ts2 = hitSphere(hitPt+refDir*0.01f, refDir, sphereCenter, RT_SPHERE_R);
    float tf2 = hitFloor(hitPt+refDir*0.01f, refDir);
    if (ts2 > 0.0f && (tf2 < 0.0f || ts2 < tf2)) {
      refCol = skyColor(norm(refDir));
    } else if (tf2 > 0.0f) {
      V3 fp2 = hitPt + refDir*tf2;
      float sh2 = (hitSphere(fp2+lightDir*0.01f, lightDir,
                              sphereCenter, RT_SPHERE_R) < 0.0f) ? 1.0f : 0.0f;
      refCol = checkerColor(fp2.x, fp2.z, lightDir, sh2);
    } else {
      refCol = skyColor(norm(refDir));
    }
#else
    float tf2 = hitFloor(hitPt+refDir*0.01f, refDir);
    if (tf2 > 0.0f) {
      V3 fp2 = hitPt + refDir*tf2;
      float ddx = fp2.x - _shadowCX, ddz = fp2.z - _shadowCZ;
      float sh2 = (ddx*ddx + ddz*ddz > _shadowR2) ? 1.0f
                : (hitSphere(fp2+lightDir*0.01f, lightDir,
                             sphereCenter, RT_SPHERE_R) < 0.0f) ? 1.0f : 0.0f;
      refCol = checkerColor(fp2.x, fp2.z, lightDir, sh2);
    } else {
      refCol = skyColor(norm(refDir));
    }
#endif

    V3    halfV = norm(lightDir - norm(rd));
    float spec  = specular(fmaxf(0.0f, dot(normal, halfV)));
    V3 specCol  = V3(SPEC_R, SPEC_G, SPEC_B) * spec;
    V3 diffCol  = V3(SPH_DIFF_R, SPH_DIFF_G, SPH_DIFF_B)
                  * fmaxf(0.0f, dot(normal, lightDir));
    return clamp3(refCol*(1.0f-SPH_DIFF_W) + diffCol*SPH_DIFF_W + specCol);
  }

  V3    floorPt = ro + rd*tf;
  float dx = floorPt.x - _shadowCX, dz = floorPt.z - _shadowCZ;
  float shadow = (dx*dx + dz*dz > _shadowR2) ? 1.0f
               : (hitSphere(floorPt+lightDir*0.01f, lightDir,
                            sphereCenter, RT_SPHERE_R) < 0.0f) ? 1.0f : 0.25f;
  return checkerColor(floorPt.x, floorPt.z, lightDir, shadow);
}

// ── Render one frame ──────────────────────────────────────────────────────────
__attribute__((optimize("O3")))
static void rtRenderFrame() {
  // Snapshot volatile camera/light params once per frame
  float camDist   = _rtCamDist;
  float camHeight = _rtCamHeight;
  V3    lightDir  = norm({(float)_rtLightX, (float)_rtLightY, (float)_rtLightZ});

  float sphereY = RT_SPHERE_BASE_Y + sinf(_rtBobAngle) * RT_SPHERE_BOB;
  V3    sphereCenter = {0.0f, sphereY, 0.0f};

  float camX = sinf(_rtCamAngle) * camDist;
  float camZ = cosf(_rtCamAngle) * camDist;
  V3    camPos = {camX, camHeight, camZ};

  V3 forward = norm(sphereCenter - camPos);
  V3 right   = norm({forward.z, 0, -forward.x});
  V3 up      = {right.y*forward.z - right.z*forward.y,
                right.z*forward.x - right.x*forward.z,
                right.x*forward.y - right.y*forward.x};

  _shadowCX = sphereCenter.x - lightDir.x * (sphereCenter.y / lightDir.y);
  _shadowCZ = sphereCenter.z - lightDir.z * (sphereCenter.y / lightDir.y);
  _shadowR2 = (RT_SPHERE_R * 2.5f) * (RT_SPHERE_R * 2.5f);

  float aspect = (float)RT_W / (float)RT_H;
  float invW   = 1.0f / RT_W;
  float invH   = 1.0f / RT_H;

  for (int py = 0; py < RT_H; py++) {
    float v      = (2.0f * (py + 0.5f) * invH - 1.0f) * RT_FOV;
    V3    rowBase = forward + up*v;
    uint16_t *row = &_rtBuf[py * RT_W];
    for (int px = 0; px < RT_W; px++) {
      float u = (2.0f * (px + 0.5f) * invW - 1.0f) * aspect * RT_FOV;
      V3 rd   = norm(rowBase + right*u);
      row[px] = toRGB565(trace(camPos, rd, sphereCenter, lightDir));
    }
  }

  _rtCamAngle += RT_CAM_SPD;
  _rtBobAngle += RT_SPHERE_BOB_SPD;
}

// ── Core1 entry ───────────────────────────────────────────────────────────────
void rtCore1Entry() {
  while (true) {
    rtRenderFrame();
    _rtFrameReady = true;
    while (_rtFrameReady) tight_loop_contents();
  }
}

// ── Core0: blit, swap, handle buttons ────────────────────────────────────────
void rtCore0Loop(DVHSTX16 &display) {
  // ── Button handling ─────────────────────────────────────────────────────────
  if (smpBtn(0)) {
    // Randomize light direction: random horizontal angle + random elevation
    float angle = _rtRandf(0.0f, 2.0f * 3.14159f);
    float elev  = _rtRandf(RT_LIGHT_ELEV_MIN, RT_LIGHT_ELEV_MAX);
    float horiz = sqrtf(1.0f - fminf(1.0f, (elev/1.5f)*(elev/1.5f))) * 0.8f;
    _rtLightX = cosf(angle) * horiz;
    _rtLightY = elev;
    _rtLightZ = sinf(angle) * horiz;
    Serial.print("light: "); Serial.print(_rtLightX);
    Serial.print(" "); Serial.print(_rtLightY);
    Serial.print(" "); Serial.println(_rtLightZ);
    ledBlink(0, 220, 255); ledAll(0, 220, 255);   // cyan action blink
  }

  if (smpBtn(1)) {
    _rtCamHeight = _rtRandf(RT_CAM_HEIGHT_MIN, RT_CAM_HEIGHT_MAX);
    Serial.print("cam height: "); Serial.println(_rtCamHeight);
    ledBlink(0, 220, 255); ledAll(0, 220, 255);
  }

  if (smpBtn(2)) {
    _rtCamDist = _rtRandf(RT_CAM_DIST_MIN, RT_CAM_DIST_MAX);
    Serial.print("cam dist: "); Serial.println(_rtCamDist);
    ledBlink(0, 220, 255); ledAll(0, 220, 255);
  }

  // ── Blit ────────────────────────────────────────────────────────────────────
  if (!_rtFrameReady) return;

#if RT_HALF_RES
  uint16_t *fb = (uint16_t*)display.getBuffer();
  if (fb) {
    for (int py = 0; py < RT_H; py++) {
      const uint16_t *src  = &_rtBuf[py * RT_W];
      uint16_t       *row0 = fb + (py*2)   * 320;
      uint16_t       *row1 = fb + (py*2+1) * 320;
      for (int px = 0; px < RT_W; px++) {
        uint16_t c = src[px];
        row0[px*2] = row0[px*2+1] = c;
        row1[px*2] = row1[px*2+1] = c;
      }
    }
  } else {
    for (int py = 0; py < RT_H; py++)
      for (int px = 0; px < RT_W; px++) {
        uint16_t c = _rtBuf[py * RT_W + px];
        int dx=px*2, dy=py*2;
        display.drawPixel(dx,dy,c); display.drawPixel(dx+1,dy,c);
        display.drawPixel(dx,dy+1,c); display.drawPixel(dx+1,dy+1,c);
      }
  }
#else
  uint16_t *buf = (uint16_t*)display.getBuffer();
  if (buf) memcpy(buf, _rtBuf, RT_W * RT_H * 2);
  else {
    for (int py = 0; py < RT_H; py++)
      for (int px = 0; px < RT_W; px++)
        display.drawPixel(px, py, _rtBuf[py * RT_W + px]);
  }
#endif

  display.swap();
  _rtFrameReady = false;
}

// ── Init ──────────────────────────────────────────────────────────────────────
void rtInit(DVHSTX16 &display) {
  _rtBuf = (uint16_t*)&g_sramArena[0];
  _buildSpecLUT();
  _rtCamDist   = RT_CAM_DIST_DEF;
  _rtCamHeight = RT_CAM_HEIGHT_DEF;
  _rtLightX    = RT_LIGHT_X_DEF;
  _rtLightY    = RT_LIGHT_Y_DEF;
  _rtLightZ    = RT_LIGHT_Z_DEF;
  display.fillScreen(0x0000);
  display.swap();
  _rtFrameReady = false;
  _rtCamAngle   = 0.0f;
  _rtBobAngle   = 0.0f;
  Serial.println("raytracer init OK");
}
