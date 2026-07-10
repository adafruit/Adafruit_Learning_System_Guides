// starfield.h — Star rendering module for Fruit Jam Demoscene
// Include once from main .ino file


// ── Tuning ───────────────────────────────────────────────────────────────────
#define NUM_STARS           200
#define MAX_DEPTH           256     // Z range: 1..MAX_DEPTH
#define MIN_BRIGHTNESS      32      // Dimmest far star (0-255)

#define DRIFT_AMOUNT        0.0f    // pixels of max drift at cruise (try 10-60)
#define WARP_DRIFT_AMOUNT   0.0f    // pixels of drift at full warp (try 1-8)
#define DRIFT_SPEED_X       0.007f  // radians per frame, X axis (try 0.003-0.02)
#define DRIFT_SPEED_Y       0.005f  // radians per frame, Y axis (different = organic)

// ── Speed ramp ───────────────────────────────────────────────────────────────
#define SPEED_MIN           1.0f    // Z decrement at cruise (try 0.5-2.0)
#define SPEED_MAX           20.0f   // Z decrement at full warp (try 10.0-30.0)
#define CRUISE_MS           10000   // how long to idle at cruise speed (ms)
#define RAMP_MS             4000    // how long the exponential ramp takes (ms)
#define WARP_MS             2500    // how long to hold full warp (ms)
#define RAMP_EXPONENT       3.0f    // ramp curve: 2=gentle, 3=dramatic, 4=sudden

// ── Snap + recovery ──────────────────────────────────────────────────────────
#define SNAP_SPEED          0.1f    // speed during snap (try 0.1-0.5)
#define SNAP_MS             3000    // duration of snap halt (ms)
#define RECOVER_MS          3000    // ease back to cruise speed (ms)
#define RECOVER_EXPONENT    2.0f    // recovery curve: 2=gentle, 3=slower start

// ── Warp color tint ──────────────────────────────────────────────────────────
#define WARP_R              180
#define WARP_G              210
#define WARP_B              255

// ── Star struct ──────────────────────────────────────────────────────────────
struct Star {
  float x, y;
  float z;
  float pz;
};

// ── Module state ─────────────────────────────────────────────────────────────
static Star      _stars[NUM_STARS];
static int       _numStarsActive = NUM_STARS;   // Button3 randomizes
static float     _warpMax        = SPEED_MAX;   // Button2 steps
static float     _driftAngleX = 0.0f;
static float     _driftAngleY = 0.0f;
static RampPhase _rampPhase   = CRUISE;   // defined in main .ino
static uint32_t  _phaseStart  = 0;
static float     _speedCurrent = SPEED_MIN;

// ── Helpers ──────────────────────────────────────────────────────────────────

inline uint16_t rgb565(uint8_t r, uint8_t g, uint8_t b) {
  return ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3);
}

inline uint8_t lerpB(uint8_t a, uint8_t b, float t) {
  return (uint8_t)(a + t * (float)(b - a));
}

inline uint16_t starColor(float depthT, float speedN) {
  uint8_t bright = (uint8_t)(MIN_BRIGHTNESS + depthT * (255 - MIN_BRIGHTNESS));
  uint8_t r = lerpB(bright, (uint8_t)((WARP_R * bright) >> 8), speedN);
  uint8_t g = lerpB(bright, (uint8_t)((WARP_G * bright) >> 8), speedN);
  uint8_t b = lerpB(bright, (uint8_t)((WARP_B * bright) >> 8), speedN);
  return rgb565(r, g, b);
}

inline void project(float x, float y, float z, int cx, int cy, int &sx, int &sy) {
  float scale = (float)MAX_DEPTH / z;
  sx = (int)(x * scale) + cx;
  sy = (int)(y * scale) + cy;
}

void resetStar(Star &s, bool randomZ = false) {
  s.x  = random(-160, 160);
  s.y  = random(-120, 120);
  s.z  = randomZ ? random(1, MAX_DEPTH) : MAX_DEPTH;
  s.pz = s.z;
}

// ── Speed state machine ──────────────────────────────────────────────────────
// RampPhase enum must be declared before including this header.
float updateSpeed(float &speedN) {
  uint32_t now     = millis();
  uint32_t elapsed = now - _phaseStart;

  switch (_rampPhase) {
    case CRUISE:
      _speedCurrent = SPEED_MIN;
      if (elapsed >= CRUISE_MS) { _rampPhase = RAMP; _phaseStart = now; }
      break;

    case RAMP: {
      float t      = constrain((float)elapsed / (float)RAMP_MS, 0.0f, 1.0f);
      float curve  = powf(t, RAMP_EXPONENT);
      _speedCurrent = SPEED_MIN + curve * (_warpMax - SPEED_MIN);
      if (elapsed >= RAMP_MS) { _rampPhase = WARP; _phaseStart = now; }
      break;
    }

    case WARP:
      _speedCurrent = _warpMax;
      if (elapsed >= WARP_MS) { _rampPhase = SNAP; _phaseStart = now; }
      break;

    case SNAP:
      _speedCurrent = SNAP_SPEED;
      if (elapsed >= SNAP_MS) { _rampPhase = RECOVER; _phaseStart = now; }
      break;

    case RECOVER: {
      float t      = constrain((float)elapsed / (float)RECOVER_MS, 0.0f, 1.0f);
      float curve  = powf(t, RECOVER_EXPONENT);
      _speedCurrent = SNAP_SPEED + curve * (SPEED_MIN - SNAP_SPEED);
      if (elapsed >= RECOVER_MS) { _rampPhase = CRUISE; _phaseStart = now; }
      break;
    }
  }

  speedN = constrain((_speedCurrent - SPEED_MIN) / (_warpMax - SPEED_MIN),
                     0.0f, 1.0f);
  return _speedCurrent;
}

// ── Public API ───────────────────────────────────────────────────────────────

void initStars() {
  _phaseStart = millis();
  for (int i = 0; i < NUM_STARS; i++) resetStar(_stars[i], true);
}

void drawStars(DVHSTX16 &display, float speed, float speedN) {
  float driftNow = DRIFT_AMOUNT + speedN * (WARP_DRIFT_AMOUNT - DRIFT_AMOUNT);
  _driftAngleX += DRIFT_SPEED_X;
  _driftAngleY += DRIFT_SPEED_Y;
  int CX = 160 + (int)(sinf(_driftAngleX) * driftNow);
  int CY = 120 + (int)(sinf(_driftAngleY) * driftNow);

  for (int i = 0; i < _numStarsActive; i++) {
    Star &s = _stars[i];
    s.pz = s.z;
    s.z -= speed;

    if (s.z <= 0) { resetStar(s); continue; }

    int sx, sy, px, py;
    project(s.x, s.y, s.z,  CX, CY, sx, sy);
    project(s.x, s.y, s.pz, CX, CY, px, py);

    if (sx < 0 || sx >= 320 || sy < 0 || sy >= 240) { resetStar(s); continue; }

    float depthT   = 1.0f - (s.z / (float)MAX_DEPTH);
    uint16_t color = starColor(depthT, speedN);

    if (px != sx || py != sy) display.drawLine(px, py, sx, sy, color);
    else                       display.drawPixel(sx, sy, color);
  }
}

// bouncer.h — Per-letter temporal sine bounce with chrome text
// for Fruit Jam Demoscene
//
// Each character has an independent phase offset so it bobs up/down
// with a staggered wave rippling through the word.
// Alpha and sine amplitude fade out during warp (speedN -> 1).
//
// Rendering pipeline per frame:
//   1. Smooth alpha toward (1 - speedN)
//   2. Early-out if alpha ~0
//   3. For each character: compute Y offset from temporal sine + phase
//   4. Read each glyph bitmap directly from the flash font (no heap)
//   5. Walk scratch pixel by pixel, apply chrome gradient + alpha


// ── Tuning ───────────────────────────────────────────────────────────────────
#define BOUNCE_TEXT        "FRUIT JAM"
#define BOUNCE_CENTER_Y    130        // vertical center of bounce arc (pixels)
#define BOUNCE_AMP_MAX     28.0f      // max Y displacement (try 15-40)
#define BOUNCE_SPEED       0.07f      // radians per frame (try 0.04-0.12)
#define BOUNCE_PHASE_STEP  0.55f      // phase offset per character (try 0.3-0.9)
                                      //   small = lazy wave, large = rapid ripple
#define LETTER_SPACING     4          // extra pixels between characters
#define ALPHA_SMOOTH       0.06f      // alpha smoothing (try 0.03-0.15)

// ── Chrome gradient ──────────────────────────────────────────────────────────
// 36-entry table covering FreeSansBold24pt7b glyph height (~33px)
// plus a few rows of padding. Index by pixel row within glyph bounding box.
// Profile: dark steel -> bright highlight -> mid silver -> dark base -> reflection
static const uint16_t BOUNCE_CHROME[36] = {
  rgb565( 50,  60,  72),   //  0 dark top
  rgb565( 70,  80,  95),   //  1
  rgb565( 95, 108, 122),   //  2
  rgb565(130, 144, 158),   //  3
  rgb565(170, 182, 194),   //  4 rising to highlight
  rgb565(210, 220, 230),   //  5
  rgb565(238, 244, 250),   //  6 highlight band
  rgb565(250, 253, 255),   //  7 peak — near white
  rgb565(248, 251, 255),   //  8
  rgb565(235, 242, 250),   //  9 falling
  rgb565(210, 220, 232),   // 10
  rgb565(182, 194, 208),   // 11
  rgb565(155, 168, 184),   // 12
  rgb565(130, 144, 160),   // 13 mid silver
  rgb565(115, 128, 145),   // 14
  rgb565(105, 118, 135),   // 15
  rgb565( 98, 112, 130),   // 16 darkest mid
  rgb565(102, 116, 133),   // 17 subtle turn
  rgb565(110, 124, 140),   // 18
  rgb565(122, 135, 150),   // 19
  rgb565(136, 148, 162),   // 20 lower silver
  rgb565(148, 160, 172),   // 21
  rgb565(158, 168, 180),   // 22
  rgb565(162, 172, 183),   // 23 lower highlight
  rgb565(155, 165, 177),   // 24
  rgb565(140, 150, 163),   // 25
  rgb565(120, 130, 144),   // 26
  rgb565( 96, 107, 122),   // 27
  rgb565( 72,  83,  98),   // 28 dark base
  rgb565( 54,  65,  80),   // 29
  rgb565( 42,  52,  68),   // 30
  rgb565( 36,  46,  62),   // 31
  rgb565( 32,  42,  58),   // 32
  rgb565( 30,  40,  56),   // 33
  rgb565( 30,  40,  56),   // 34 padding
  rgb565( 30,  40,  56),   // 35 padding
};

// ── Per-character metrics ─────────────────────────────────────────────────────
#define MAX_CHARS   16   // max characters in BOUNCE_TEXT

struct CharInfo {
  char     ch;
  int      screenX;    // left edge on screen
  int      glyphW;     // bitmap width from font
  int      glyphH;     // bitmap height from font
  int      xOffset;    // font xOffset
  int      yOffset;    // font yOffset (negative = above baseline)
  int      xAdvance;   // horizontal advance
  const GFXglyph *glyph;  // -> font glyph (flash); bitmap read directly
  const GFXfont  *font;   // owning font (for bitmap base)
};

// ── Module state ─────────────────────────────────────────────────────────────
static CharInfo  _chars[MAX_CHARS];
static int       _numChars   = 0;
static float     _alpha      = 0.0f;
static float     _bounceTime = 0.0f;

// ── Helpers ──────────────────────────────────────────────────────────────────

static inline uint16_t scaleColor16(uint16_t c, float a) {
  if (a >= 1.0f) return c;
  uint8_t r = (uint8_t)(((c >> 11) & 0x1F) * a) ;
  uint8_t g = (uint8_t)(((c >>  5) & 0x3F) * a);
  uint8_t b = (uint8_t)( (c        & 0x1F) * a);
  return (r << 11) | (g << 5) | b;
}

void freeBouncer() {
  _numChars = 0;   // no heap to free — glyphs live in flash font data
}

void initBouncer(const char *text) {
  const GFXfont *font = &FreeSansBold24pt7b;
  _numChars = 0;

  // First pass: measure total width to center on screen
  int totalW = 0;
  for (const char *p = text; *p && _numChars < MAX_CHARS; p++, _numChars++) {
    uint8_t idx = (uint8_t)*p;
    if (*p == ' ') { totalW += 18; continue; }  // space width
    if (idx < font->first || idx > font->last) continue;
    GFXglyph *g = &font->glyph[idx - font->first];
    totalW += g->xAdvance + LETTER_SPACING;
  }
  // Remove trailing spacing
  if (totalW > LETTER_SPACING) totalW -= LETTER_SPACING;

  // Second pass: assign positions and pre-render glyphs
  int x = (320 - totalW) / 2;
  _numChars = 0;
  for (const char *p = text; *p && _numChars < MAX_CHARS; p++) {
    CharInfo &ci = _chars[_numChars];
    ci.ch      = *p;
    ci.screenX = x;
    ci.glyph   = nullptr;
    ci.font    = font;

    uint8_t idx = (uint8_t)*p;
    if (*p == ' ') {
      ci.glyphW = 18; ci.glyphH = 0;
      ci.xOffset = 0; ci.yOffset = 0; ci.xAdvance = 18;
      x += 18;
    } else if (idx >= font->first && idx <= font->last) {
      GFXglyph *g = &font->glyph[idx - font->first];
      ci.glyph   = g;
      ci.glyphW  = g->width;
      ci.glyphH  = g->height;
      ci.xOffset = g->xOffset;
      ci.yOffset = g->yOffset;
      ci.xAdvance= g->xAdvance;
      x += ci.xAdvance + LETTER_SPACING;
    } else {
      ci.glyphW = 4; ci.glyphH = 0; ci.xAdvance = 4;
      ci.xOffset = ci.yOffset = 0;
      x += 4;
    }
    _numChars++;
  }
}

void drawBouncer(DVHSTX16 &display, float speedN) {
  // Alpha: target = 1 - speedN, smoothed
  float alphaTarget = 1.0f - speedN;
  _alpha += ALPHA_SMOOTH * (alphaTarget - _alpha);

  if (_alpha < 0.01f) {
    _bounceTime += BOUNCE_SPEED;
    return;
  }

  // Sine amplitude tracks alpha — materialises calm, gains bounce as alpha rises
  float amp = BOUNCE_AMP_MAX * _alpha;

  _bounceTime += BOUNCE_SPEED;

  for (int i = 0; i < _numChars; i++) {
    CharInfo &ci = _chars[i];
    if (!ci.glyph || ci.glyphW == 0 || ci.glyphH == 0) continue;

    // Per-character phase offset creates the staggered ripple
    float phase  = _bounceTime + i * BOUNCE_PHASE_STEP;
    int   yShift = (int)(sinf(phase) * amp);

    // Baseline for this character; yOffset is negative (above baseline)
    // We want the text centered around BOUNCE_CENTER_Y
    int baselineY = BOUNCE_CENTER_Y + yShift;

    for (int row = 0; row < ci.glyphH; row++) {
      int screenY = baselineY + ci.yOffset + row;
      if (screenY < 0 || screenY >= 240) continue;

      const uint8_t *bitmap = ci.font->bitmap;
      uint16_t bo = ci.glyph->bitmapOffset;
      for (int col = 0; col < ci.glyphW; col++) {
        // GFX font bitmaps are bit-packed, MSB-first, row-major
        uint32_t bit = (uint32_t)row * ci.glyphW + col;
        if (!(bitmap[bo + (bit >> 3)] & (0x80 >> (bit & 7)))) continue;

        int screenX = ci.screenX + ci.xOffset + col;
        if (screenX < 0 || screenX >= 320) continue;

        // Chrome: row index maps into 36-entry table
        int chromeIdx = (row * 36) / ci.glyphH;
        if (chromeIdx > 35) chromeIdx = 35;

        uint16_t color = scaleColor16(BOUNCE_CHROME[chromeIdx], _alpha);
        display.drawPixel(screenX, screenY, color);
      }
    }
  }
}

// ── Sampler integration: text list + buttons + run loop ──────────────────────
// Button1: cycle text  Button2: step warp intensity  Button3: randomize stars
static const char *_sfTexts[] = { "Adafruit", "Fruit Jam", "kqvc", "L  4  r  5" };
#define SF_TEXT_COUNT 4
static int _sfTextIdx = 0;
static const float _sfWarpSteps[] = { 8.0f, 14.0f, 20.0f, 28.0f };
static int _sfWarpIdx = 2;   // default 20 (= original SPEED_MAX)
// one signature color per message slot
static void _sfLeds() {
  static const uint8_t C[4][3] = {
    {255,255,255}, {0,220,255}, {255,120,0}, {255,0,200} };
  int m = _sfTextIdx & 3;
  ledBar(_sfWarpIdx + 1, C[m][0], C[m][1], C[m][2]);
}

void starfieldRun(DVHSTX16 &display) {
  Serial.println("sf: entry"); Serial.flush();
  Serial.printf("sf: free heap = %u\n", rp2040.getFreeHeap()); Serial.flush();
  initStars();
  Serial.println("sf: stars done"); Serial.flush();
  initBouncer(_sfTexts[_sfTextIdx]);
  Serial.printf("sf: bouncer done, free heap = %u\n", rp2040.getFreeHeap());
  Serial.flush();
  _sfLeds();
  for (;;) {
    smpAudioPump();
    if (smpBtn(0)) {                       // cycle message
      _sfTextIdx = (_sfTextIdx + 1) % SF_TEXT_COUNT;
      freeBouncer();
      initBouncer(_sfTexts[_sfTextIdx]);
      _sfLeds();
      Serial.printf("text: %s\n", _sfTexts[_sfTextIdx]);
    }
    if (smpBtn(1)) {                       // step warp intensity
      _sfWarpIdx = (_sfWarpIdx + 1) % 4;
      _warpMax = _sfWarpSteps[_sfWarpIdx];
      _sfLeds();
      Serial.printf("warp max: %.0f\n", _warpMax);
    }
    if (smpBtn(2)) {                       // randomize star density
      _numStarsActive = random(80, NUM_STARS + 1);
      for (int i = 0; i < _numStarsActive; i++) resetStar(_stars[i], true);
      ledBlink(255,255,255); _sfLeds();
      Serial.printf("stars: %d\n", _numStarsActive);
    }

    display.fillScreen(0x0000);
    float speedN;
    float speed = updateSpeed(speedN);
    drawStars(display, speed, speedN);
    drawBouncer(display, speedN);
    display.swap();
  }
}
