// plasma.h — Standalone plasma effect for Fruit Jam RP2350
// 8-bit indexed plasma rendered through DVHSTX16 via a software
// palette LUT (256 x RGB565), rebuilt each frame — palette rotation and
// fades cost one small loop instead of hardware registers.
//
// Buttons:
//   Button1 (GPIO0) — cycle palette (5 options)
//   Button2 (GPIO4) — toggle palette-only / full-animate mode
//   Button3 (GPIO5) — randomize frequencies, drift speeds, rotation speed
//
// Palette options (PLASMA_PALETTE define sets startup default):
//   0=Fire  1=Ice  2=Toxic  3=Lava  4=Rainbow
//
// Animation modes (PLASMA_FULL_ANIMATE sets startup default):
//   0 = Palette-only: index map fixed, palette rotates (fast)
//   1 = Full animate: wave maps recomputed each frame via LUT (richer)


// ── Startup defaults (all become runtime variables) ───────────────────────────
#define PLASMA_PALETTE        0     // 0=Fire 1=Ice 2=Toxic 3=Lava 4=Rainbow
#define PLASMA_FULL_ANIMATE   0     // 0=palette-only 1=full animate

// These are starting values — Button3 randomizes them at runtime
#define PLASMA_ROT_SPEED_DEF  1     // palette steps per frame (1-4)
#define PLASMA_ANIM_SPEED_DEF 2     // wave drift steps per frame (1-4)
#define PLASMA_F1_DEF   3.0f        // horizontal frequency
#define PLASMA_F2_DEF   2.5f        // vertical frequency
#define PLASMA_F3_DEF   1.8f        // diagonal frequency
#define PLASMA_F4_DEF   1.2f        // radial frequency
#define PLASMA_T1_DEF   4           // horizontal drift speed
#define PLASMA_T2_DEF   3           // vertical drift speed
#define PLASMA_T3_DEF   5           // diagonal drift speed
#define PLASMA_T4_DEF   2           // radial drift speed

// ── Randomization ranges ──────────────────────────────────────────────────────
#define PLASMA_F_MIN    0.15f       // minimum frequency (HUGE cells)
#define PLASMA_F_MAX    8.0f        // maximum frequency (tighter pattern)
#define PLASMA_T_MIN    1           // minimum drift speed
#define PLASMA_T_MAX    9           // maximum drift speed
#define PLASMA_ROT_MIN  1           // minimum rotation speed
#define PLASMA_ROT_MAX  4           // maximum rotation speed

// ── Fade tuning ───────────────────────────────────────────────────────────────
#define FADE_FRAMES  25    // frames for fade out or fade in (try 15-40)

// ── LUT + pre-baked wave maps ─────────────────────────────────────────────────
#define PLASMA_LUT_SIZE  256

static uint8_t _plasmaLUT[PLASMA_LUT_SIZE];
static uint8_t _waveX[320];
static uint8_t _waveY[240];
/* diag wave is separable: (x+y)*f3 = x*f3 + y*f3 — two 1-D tables
   replace the old 76.8K 2-D map */
static uint8_t _waveDiagX[320];
static uint8_t _waveDiagY[240];
static uint8_t (*_waveRadial)[320];     // 240x320, PSRAM arena offset 0
static uint8_t _tOff1 = 0, _tOff2 = 0, _tOff3 = 0, _tOff4 = 0;

// ── Index map + palette ───────────────────────────────────────────────────────
/* Plasma map: rewritten every frame in full-animate -> SRAM arena.
   Radial wave table: read-only after init -> PSRAM arena.            */
static uint8_t (*_plasmaMap)[320];
static uint8_t _palR[256], _palG[256], _palB[256];
static int     _palOffset  = 0;
static int     _curPalette = PLASMA_PALETTE;

// ── Runtime tuning variables ──────────────────────────────────────────────────
static float _f1, _f2, _f3, _f4;       // wave frequencies
static int   _t1, _t2, _t3, _t4;       // drift speeds
static int   _rotSpeed;                 // palette rotation speed
static int   _animSpeed;                // wave rebuild steps per tick
static bool  _fullAnimate = (PLASMA_FULL_ANIMATE == 1);

static void _plLeds() {
  int n = _fullAnimate ? 5 : 3;
  switch (_curPalette) {
    case 0: ledBar(n, 255, 90, 0);   break;  // fire  orange
    case 1: ledBar(n, 0, 200, 255);  break;  // ice   cyan
    case 2: ledBar(n, 60, 255, 0);   break;  // toxic green
    case 3: ledBar(n, 255, 30, 0);   break;  // lava  red
    case 4: ledSpread();             break;  // rainbow spread (ignores n)
    default: ledBar(n, 200,200,200); break;
  }
}

// ── Fade state ────────────────────────────────────────────────────────────────
enum FadeState { FADE_NONE, FADE_OUT, FADE_REBUILDING, FADE_IN };
static FadeState _fadeState = FADE_NONE;
static float     _fadeAlpha = 1.0f;   // 0.0 = black, 1.0 = full brightness

// ── Palette builders — all cyclic ─────────────────────────────────────────────
static inline float _tri(int i) {
  float t = i / 255.0f;
  return t < 0.5f ? t * 2.0f : (1.0f - t) * 2.0f;
}

static void _palFire() {
  for (int i = 0; i < 256; i++) {
    float t = _tri(i);
    _palR[i] = (uint8_t)(128 + t * 127);
    _palG[i] = (uint8_t)(t * t * 255);
    _palB[i] = (uint8_t)(t * t * t * 180);
  }
}
static void _palIce() {
  for (int i = 0; i < 256; i++) {
    float t = _tri(i), t2 = t * t;
    _palR[i] = (uint8_t)(20  + t2 * 235);
    _palG[i] = (uint8_t)(40  + t  * 215);
    _palB[i] = (uint8_t)(120 + t  * 135);
  }
}
static void _palToxic() {
  for (int i = 0; i < 256; i++) {
    float t = _tri(i), t2 = t * t;
    _palR[i] = (uint8_t)(t2 * t * 200);
    _palG[i] = (uint8_t)(60  + t  * 195);
    _palB[i] = (uint8_t)(t2  * 80);
  }
}
static void _palLava() {
  for (int i = 0; i < 256; i++) {
    float t = _tri(i), t2 = t * t;
    _palR[i] = (uint8_t)(80  + t  * 175);
    _palG[i] = (uint8_t)(t2  * t  * 160);
    _palB[i] = (uint8_t)(120 - t2 * 80);
  }
}
static void _palRainbow() {
  for (int i = 0; i < 256; i++) {
    float h=i/256.0f*6.0f; int s=(int)h; float f=h-s, q=1.0f-f;
    switch(s%6){
      case 0:_palR[i]=255;_palG[i]=(uint8_t)(f*255);_palB[i]=0;break;
      case 1:_palR[i]=(uint8_t)(q*255);_palG[i]=255;_palB[i]=0;break;
      case 2:_palR[i]=0;_palG[i]=255;_palB[i]=(uint8_t)(f*255);break;
      case 3:_palR[i]=0;_palG[i]=(uint8_t)(q*255);_palB[i]=255;break;
      case 4:_palR[i]=(uint8_t)(f*255);_palG[i]=0;_palB[i]=255;break;
      case 5:_palR[i]=255;_palG[i]=0;_palB[i]=(uint8_t)(q*255);break;
    }
  }
}

// ── Palette upload + load ──────────────────────────────────────────────────────
// alpha: 0.0=black, 1.0=full brightness
static uint16_t _pal16[256];   // software palette: index -> RGB565
static void _uploadPalette(DVHSTX16 &display, float alpha = 1.0f) {
  (void)display;
  for (int i = 0; i < 256; i++) {
    int src = (i + _palOffset) & 0xFF;
    _pal16[i] = C565((uint8_t)(_palR[src] * alpha),
                     (uint8_t)(_palG[src] * alpha),
                     (uint8_t)(_palB[src] * alpha));
  }
}

static void _loadPalette(int idx) {
  switch (idx) {
    case 1:  _palIce();     Serial.println("palette: Ice");     break;
    case 2:  _palToxic();   Serial.println("palette: Toxic");   break;
    case 3:  _palLava();    Serial.println("palette: Lava");    break;
    case 4:  _palRainbow(); Serial.println("palette: Rainbow"); break;
    default: _palFire();    Serial.println("palette: Fire");    break;
  }
  _palOffset = 0;
}

// ── Map builders ──────────────────────────────────────────────────────────────
static void _buildMapStatic() {
  Serial.println("plasma: building static map...");
  int cx = 160, cy = 120;
  for (int y = 0; y < 240; y++) {
    for (int x = 0; x < 320; x++) {
      float dx = x-cx, dy = y-cy;
      float v = sinf(x * _f1 * 2.0f * 3.14159f / PLASMA_LUT_SIZE)
              + sinf(y * _f2 * 2.0f * 3.14159f / PLASMA_LUT_SIZE)
              + sinf((x+y) * _f3 * 2.0f * 3.14159f / PLASMA_LUT_SIZE)
              + sinf(sqrtf(dx*dx+dy*dy) * _f4 * 2.0f * 3.14159f / PLASMA_LUT_SIZE);
      _plasmaMap[y][x] = (uint8_t)(v * 32.0f + 128.0f);
    }
    if (y % 60 == 0) { Serial.print("row "); Serial.println(y); }
  }
  Serial.println("plasma: static map done");
}

static void _buildAnimateMaps() {
  Serial.println("plasma: building LUT...");
  for (int i = 0; i < PLASMA_LUT_SIZE; i++) {
    float v = sinf(i * (2.0f * 3.14159265f / PLASMA_LUT_SIZE));
    _plasmaLUT[i] = (uint8_t)(v * 127.0f + 128.0f);
  }
  Serial.println("plasma: building wave maps...");
  for (int x = 0; x < 320; x++)
    _waveX[x] = (uint8_t)((int)(x * _f1) & 0xFF);
  for (int y = 0; y < 240; y++)
    _waveY[y] = (uint8_t)((int)(y * _f2) & 0xFF);
  for (int x = 0; x < 320; x++)
    _waveDiagX[x] = (uint8_t)((int)(x * _f3) & 0xFF);
  for (int y = 0; y < 240; y++)
    _waveDiagY[y] = (uint8_t)((int)(y * _f3) & 0xFF);
  int cx = 160, cy = 120;
  for (int y = 0; y < 240; y++) {
    for (int x = 0; x < 320; x++) {
      float dx = x-cx, dy = y-cy;
      _waveRadial[y][x] = (uint8_t)((int)(sqrtf(dx*dx+dy*dy) * _f4) & 0xFF);
    }
    if (y % 60 == 0) { Serial.print("radial row "); Serial.println(y); }
  }
  _tOff1 = _tOff2 = _tOff3 = _tOff4 = 0;
  Serial.println("plasma: wave maps done");
}

static void _rebuildMapAnimated() {
  for (int y = 0; y < 240; y++) {
    uint8_t        diagY  = _waveDiagY[y];
    const uint8_t *radial = _waveRadial[y];
    uint8_t       *out    = _plasmaMap[y];
    uint8_t        wy     = _waveY[y];
    for (int x = 0; x < 320; x++) {
      uint8_t i1 = _plasmaLUT[(_waveX[x] + _tOff1) & 0xFF];
      uint8_t i2 = _plasmaLUT[(wy        + _tOff2) & 0xFF];
      uint8_t i3 = _plasmaLUT[((uint8_t)(_waveDiagX[x] + diagY) + _tOff3) & 0xFF];
      uint8_t i4 = _plasmaLUT[(radial[x] + _tOff4) & 0xFF];
      out[x] = (uint8_t)(((uint16_t)i1 + i2 + i3 + i4) >> 2);
    }
  }
  _tOff1 += (uint8_t)_t1;
  _tOff2 += (uint8_t)_t2;
  _tOff3 += (uint8_t)_t3;
  _tOff4 += (uint8_t)_t4;
}

// ── Randomizer ────────────────────────────────────────────────────────────────
// Helper: random float in [lo, hi]
static inline float _randf(float lo, float hi) {
  return lo + (hi - lo) * (random(1000) / 999.0f);
}

static void _randomize() {
  Serial.println("plasma: randomizing...");

  // Pick four distinct frequencies — ensure no two are too similar
  // to avoid degenerate flat patterns
  _f1 = _randf(PLASMA_F_MIN, PLASMA_F_MAX);
  do { _f2 = _randf(PLASMA_F_MIN, PLASMA_F_MAX); } while (fabsf(_f2-_f1) < 0.3f);
  do { _f3 = _randf(PLASMA_F_MIN, PLASMA_F_MAX); } while (fabsf(_f3-_f1) < 0.3f || fabsf(_f3-_f2) < 0.3f);
  do { _f4 = _randf(PLASMA_F_MIN, PLASMA_F_MAX); } while (fabsf(_f4-_f1) < 0.3f || fabsf(_f4-_f2) < 0.3f || fabsf(_f4-_f3) < 0.3f);

  // Drift speeds — keep them distinct for organic motion
  _t1 = random(PLASMA_T_MIN, PLASMA_T_MAX + 1);
  do { _t2 = random(PLASMA_T_MIN, PLASMA_T_MAX + 1); } while (_t2 == _t1);
  do { _t3 = random(PLASMA_T_MIN, PLASMA_T_MAX + 1); } while (_t3 == _t1 || _t3 == _t2);
  do { _t4 = random(PLASMA_T_MIN, PLASMA_T_MAX + 1); } while (_t4 == _t1 || _t4 == _t2 || _t4 == _t3);

  _rotSpeed  = random(PLASMA_ROT_MIN, PLASMA_ROT_MAX + 1);
  _animSpeed = random(1, 4);

  Serial.print("f: "); Serial.print(_f1); Serial.print(" ");
  Serial.print(_f2); Serial.print(" "); Serial.print(_f3); Serial.print(" ");
  Serial.println(_f4);
  Serial.print("t: "); Serial.print(_t1); Serial.print(" ");
  Serial.print(_t2); Serial.print(" "); Serial.print(_t3); Serial.print(" ");
  Serial.println(_t4);
  Serial.print("rot: "); Serial.print(_rotSpeed);
  Serial.print("  anim: "); Serial.println(_animSpeed);

  // Rebuild both maps with new frequencies
  _buildMapStatic();
  _buildAnimateMaps();
}

// ── Public API ────────────────────────────────────────────────────────────────

void plasmaInit() {
  _plasmaMap  = (uint8_t(*)[320]) &g_sramArena[0];
  _waveRadial = (uint8_t(*)[320]) &g_arena[0];
  _plLeds();   // show starting palette + mode
  _palOffset  = 0;
  _curPalette = PLASMA_PALETTE;

  // Load startup defaults into runtime variables
  _f1 = PLASMA_F1_DEF; _f2 = PLASMA_F2_DEF;
  _f3 = PLASMA_F3_DEF; _f4 = PLASMA_F4_DEF;
  _t1 = PLASMA_T1_DEF; _t2 = PLASMA_T2_DEF;
  _t3 = PLASMA_T3_DEF; _t4 = PLASMA_T4_DEF;
  _rotSpeed  = PLASMA_ROT_SPEED_DEF;
  _animSpeed = PLASMA_ANIM_SPEED_DEF;

    _loadPalette(_curPalette);
  _buildMapStatic();
  _buildAnimateMaps();

  Serial.println("plasma: ready");
}

void plasmaTick(DVHSTX16 &display) {
  // Button1: cycle palette
  if (smpBtn(0)) {
    _curPalette = (_curPalette + 1) % 5;
    _loadPalette(_curPalette);
    _plLeds();
  }

  // Button2: toggle palette-only / full-animate mode
  if (smpBtn(1)) {
    _fullAnimate = !_fullAnimate;
    _plLeds();
    Serial.print("animate mode: ");
    Serial.println(_fullAnimate ? "FULL" : "PALETTE-ONLY");
  }

  // Button3: start fade-out -> randomize -> fade-in sequence
  if (smpBtn(2) && _fadeState == FADE_NONE) {
    _fadeState = FADE_OUT;
    _fadeAlpha = 1.0f;
    _plLeds();
    Serial.println("fade: starting");
  }

  // ── Fade state machine ──────────────────────────────────────────────────────
  if (_fadeState == FADE_OUT) {
    _fadeAlpha -= 1.0f / FADE_FRAMES;
    if (_fadeAlpha <= 0.0f) {
      _fadeAlpha = 0.0f;
      _fadeState = FADE_REBUILDING;
      Serial.println("fade: black — rebuilding");
    }
  } else if (_fadeState == FADE_REBUILDING) {
    _randomize();                  // blocks for ~2s while maps rebuild
    _fadeState = FADE_IN;
    _fadeAlpha = 0.0f;
    Serial.println("fade: fading in");
  } else if (_fadeState == FADE_IN) {
    _fadeAlpha += 1.0f / FADE_FRAMES;
    if (_fadeAlpha >= 1.0f) {
      _fadeAlpha = 1.0f;
      _fadeState = FADE_NONE;
      Serial.println("fade: done");
    }
  }

  _palOffset = (_palOffset + _rotSpeed) & 0xFF;

  if (_fullAnimate) {
    for (int s = 0; s < _animSpeed; s++) {
      _rebuildMapAnimated();
      smpAudioPump();          // keep music fed through the heavy rebuild
    }
  }

  _uploadPalette(display, _fadeAlpha);

  uint16_t *buf = (uint16_t *)display.getBuffer();
  if (buf) {
    for (int y = 0; y < 240; y++) {
      const uint8_t *src = _plasmaMap[y];
      uint16_t      *dst = buf + y * 320;
      for (int x = 0; x < 320; x++) dst[x] = _pal16[src[x]];
      if ((y & 63) == 63) smpAudioPump();
    }
  } else {
    for (int y = 0; y < 240; y++)
      for (int x = 0; x < 320; x++)
        display.drawPixel(x, y, _pal16[_plasmaMap[y][x]]);
  }

  display.swap();
}
