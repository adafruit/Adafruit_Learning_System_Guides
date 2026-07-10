// rotozoom.h — Tiling rotozoom + moving sphere lens distortion
// for Fruit Jam RP2350 / HSTX DVI
//
// Core split:
//   Core0 — buttons, animation state, blit pixel buffer to display, swap
//   Core1 — render loop: reads volatile state, writes to _rzBuf continuously
//
// This eliminates vsync hitching — core1 renders as fast as possible,
// core0 blits and swaps whenever core1 finishes a frame. Both cores
// are always doing useful work.


// ── Tuning ────────────────────────────────────────────────────────────────────
// Target framerate — set to 30 or 60
#define RZ_TARGET_FPS     60
#define RZ_FRAME_US       (1000000 / RZ_TARGET_FPS)

#define RZ_ANGLE_SPD      0.007f
#define RZ_ZOOM_MIN       0.5f
#define RZ_ZOOM_MAX       2.5f
#define RZ_ZOOM_SPD       0.004f

#define LENS_ENABLED      1
#define LENS_RADIUS       55
#define LENS_STRENGTH     0.55f
#define LENS_ORBIT_X      100.0f
#define LENS_ORBIT_Y      70.0f
#define LENS_SPD_X        0.00731f
#define LENS_SPD_Y        0.00513f

#define LENS_TINT_R       40
#define LENS_TINT_G       80
#define LENS_TINT_B       220
#define LENS_TINT_AMT     60

// ── Speed presets ─────────────────────────────────────────────────────────────
struct RZPreset { float angleSpdMul; float zoomSpdMul; const char *name; };
static const RZPreset _rzPresets[] = {
  {  1.0f,  1.0f, "Normal"      },
  {  2.5f,  1.5f, "Fast"        },
  { -1.0f,  1.0f, "Reverse"     },
  {  0.3f,  0.4f, "Slow drift"  },
  {  1.0f,  3.0f, "Zoom frenzy" },
};
#define RZ_PRESET_COUNT 5
static int _rzPresetIdx = 0;

// ── Lens table ────────────────────────────────────────────────────────────────
#define LENS_DIAM (LENS_RADIUS * 2)
static int8_t (*_lensU)[LENS_DIAM];     // arena
static int8_t (*_lensV)[LENS_DIAM];     // arena
static bool   (*_lensValid)[LENS_DIAM]; // arena

static void _buildLensTable() {
  Serial.println("rz: building lens table...");
  int r = LENS_RADIUS;
  for (int dy = -r; dy < r; dy++) {
    for (int dx = -r; dx < r; dx++) {
      float dist = sqrtf((float)(dx*dx + dy*dy));
      int lx = dx + r, ly = dy + r;
      if (dist >= r) { _lensValid[ly][lx]=false; _lensU[ly][lx]=0; _lensV[ly][lx]=0; continue; }
      _lensValid[ly][lx] = true;
      float t = dist / r;
      float bulge = sqrtf(1.0f - t*t);
      float displace = (1.0f - bulge) * LENS_STRENGTH;
      float nx = (dist > 0.001f) ? -dx/dist : 0.0f;
      float ny = (dist > 0.001f) ? -dy/dist : 0.0f;
      float du = nx * displace * LENS_RADIUS * 0.5f;
      float dv = ny * displace * LENS_RADIUS * 0.5f;
      _lensU[ly][lx] = (int8_t)constrain((int)du, -127, 127);
      _lensV[ly][lx] = (int8_t)constrain((int)dv, -127, 127);
    }
  }
  Serial.println("rz: lens table done");
}

// ── Pixel buffer — core1 writes here, core0 blits to display ──────────────────
static uint16_t     *_rzBuf;   // 320*240, SRAM arena (core1 rewrites every frame)
static volatile bool _rzFrameReady = false;

// ── Volatile animation params — core0 writes, core1 reads ─────────────────────
static volatile int32_t _vCosF    = 0;
static volatile int32_t _vSinF    = 0;
static volatile int32_t _vOffU    = 0;
static volatile int32_t _vOffV    = 0;
static volatile int      _vLensX  = 160;
static volatile int      _vLensY  = 120;
static volatile bool     _vLensOn = (LENS_ENABLED == 1);

static void _rzLeds() {
  int n = _rzPresetIdx + 1;
  if (_vLensOn) ledBar(n, 40, 120, 255);   // blue = lens on
  else          ledBar(n, 255, 255, 255);  // white = lens off
}

// ── Animation state (core0 only) ──────────────────────────────────────────────
static uint32_t  _rzLastFrameUs = 0;
// Precomputed trig — updated every loop, used at blit time
static int32_t   _rzCosF_pre = 65536;
static int32_t   _rzSinF_pre = 0;
static int32_t   _rzOffU_pre = 0;
static int32_t   _rzOffV_pre = 0;
static int       _rzLensX_pre = 160;
static int       _rzLensY_pre = 120;
// Blit/swap state machine
enum RZState { RZ_WAIT_FRAME, RZ_BLIT, RZ_WAIT_SWAP };
static RZState _rzState = RZ_WAIT_FRAME;

static float _rzAngle     = 0.0f;
static float _rzZoomAngle = 0.0f;
static float _rzZoomMin   = RZ_ZOOM_MIN;
static float _rzZoomMax   = RZ_ZOOM_MAX;
static float _lensAngleX  = 0.0f;
static float _lensAngleY  = 1.3f;

static inline float _rzRandf(float lo, float hi) {
  return lo + (hi - lo) * (random(1000) / 999.0f);
}

// ── Lens tint blend ───────────────────────────────────────────────────────────
static inline uint16_t _lensBlend(uint16_t px) {
  uint8_t r = (px >> 11) & 0x1F;
  uint8_t g = (px >>  5) & 0x3F;
  uint8_t b =  px        & 0x1F;
  const uint8_t tr = LENS_TINT_R >> 3;
  const uint8_t tg = LENS_TINT_G >> 2;
  const uint8_t tb = LENS_TINT_B >> 3;
  r = (uint8_t)(r + (((int)(tr - r) * LENS_TINT_AMT) >> 8));
  g = (uint8_t)(g + (((int)(tg - g) * LENS_TINT_AMT) >> 8));
  b = (uint8_t)(b + (((int)(tb - b) * LENS_TINT_AMT) >> 8));
  return ((uint16_t)r << 11) | ((uint16_t)g << 5) | b;
}

// ── Core1: render loop ────────────────────────────────────────────────────────
__attribute__((optimize("O3")))
static void _rzRenderFrame() {
  // Snapshot volatile params once — consistent across the whole frame
  int32_t cosF  = _vCosF;
  int32_t sinF  = _vSinF;
  int32_t offU  = _vOffU;
  int32_t offV  = _vOffV;
  int     lensX = _vLensX;
  int     lensY = _vLensY;
  bool    lensOn= _vLensOn;

  int lx0 = lensX - LENS_RADIUS;
  int lx1 = lensX + LENS_RADIUS;
  int ly0 = lensY - LENS_RADIUS;
  int ly1 = lensY + LENS_RADIUS;

  uint16_t *buf = _rzBuf;

  for (int py = 0; py < 240; py++) {
    int dy = py - 120;
    int32_t u0 = offU + (int32_t)(-160) * cosF + (int32_t)dy * sinF;
    int32_t v0 = offV + (int32_t)( 160) * sinF + (int32_t)dy * cosF;

    bool inLensRow = lensOn && (py >= ly0 && py < ly1);
    uint16_t *row  = buf + py * 320;

    for (int px = 0; px < 320; px++) {
      int32_t u = u0 + px * cosF;
      int32_t v = v0 - px * sinF;

      if (inLensRow && px >= lx0 && px < lx1) {
        int ldx = px - lensX + LENS_RADIUS;
        int ldy = py - lensY + LENS_RADIUS;
        if ((unsigned)ldx < LENS_DIAM && (unsigned)ldy < LENS_DIAM
            && _lensValid[ldy][ldx]) {
          u += (int32_t)_lensU[ldy][ldx] << 16;
          v += (int32_t)_lensV[ldy][ldx] << 16;
          int tx = (u >> 16) & TEXTURE_MASK;
          int ty = (v >> 16) & TEXTURE_MASK;
          row[px] = _lensBlend(texture[ty][tx]);
          continue;
        }
      }

      int tx = (u >> 16) & TEXTURE_MASK;
      int ty = (v >> 16) & TEXTURE_MASK;
      row[px] = texture[ty][tx];
    }
  }
}

void rzCore1Entry() {
  while (true) {
    _rzRenderFrame();
    _rzFrameReady = true;
    // Wait for core0 to consume the frame
    while (_rzFrameReady) tight_loop_contents();
  }
}

// ── Public API ────────────────────────────────────────────────────────────────

void rzInit() {
  _rzBuf     = (uint16_t*)&g_sramArena[0];
  _lensU     = (int8_t(*)[LENS_DIAM])&g_arena[0];
  _lensV     = (int8_t(*)[LENS_DIAM])&g_arena[LENS_DIAM*LENS_DIAM];
  _lensValid = (bool  (*)[LENS_DIAM])&g_arena[2*LENS_DIAM*LENS_DIAM];
  _buildLensTable();
  _rzAngle      = 0.0f;
  _rzZoomAngle  = 0.0f;
  _lensAngleX   = 0.0f;
  _lensAngleY   = 1.3f;
  _rzZoomMin    = RZ_ZOOM_MIN;
  _rzZoomMax    = RZ_ZOOM_MAX;
  _rzFrameReady  = false;
  _rzLastFrameUs = time_us_32();
  _rzState       = RZ_WAIT_FRAME;
  _rzLeds();   // show starting preset + lens state
}

// Core0: buttons, precompute trig, blit/swap state machine
void rzCore0Loop(DVHSTX16 &display) {
  // ── Buttons (always checked) ──────────────────────────────────────────────
  if (smpBtn(0)) {
    _rzPresetIdx = (_rzPresetIdx + 1) % RZ_PRESET_COUNT;
    _rzLeds();
    Serial.print("preset: "); Serial.println(_rzPresets[_rzPresetIdx].name);
  }
  if (smpBtn(1)) {
    _vLensOn = !_vLensOn;
    _rzLeds();
    Serial.print("lens: "); Serial.println(_vLensOn ? "ON" : "OFF");
  }
  if (smpBtn(2)) {
    ledBlink(255, 120, 0);    // orange action blink
    _rzLeds();
    _rzZoomMin = _rzRandf(0.2f, 1.2f);
    _rzZoomMax = _rzZoomMin + _rzRandf(0.5f, 3.0f);
    Serial.print("zoom: "); Serial.print(_rzZoomMin);
    Serial.print(" - "); Serial.println(_rzZoomMax);
  }

  // ── Precompute trig every loop — cheap, removes jitter at blit time ───────
  // Angles advance once per frame inside RZ_WAIT_FRAME, but trig is computed
  // continuously so by the time we blit the values are already ready.
  {
    float t    = (sinf(_rzZoomAngle) + 1.0f) * 0.5f;
    float zoom = _rzZoomMin + t * (_rzZoomMax - _rzZoomMin);
    if (zoom < 0.01f) zoom = 0.01f;
    float cosa = cosf(_rzAngle) / zoom;
    float sina = sinf(_rzAngle) / zoom;
    _rzCosF_pre = (int32_t)(cosa * 65536.0f);
    _rzSinF_pre = (int32_t)(sina * 65536.0f);
    _rzOffU_pre = (int32_t)(_rzAngle * 8.0f * 65536.0f / (2.0f * 3.14159f)) & 0x7FFFFF;
    _rzOffV_pre = (int32_t)(_rzAngle * 5.0f * 65536.0f / (2.0f * 3.14159f)) & 0x7FFFFF;
    _rzLensX_pre = 160 + (int)(sinf(_lensAngleX) * LENS_ORBIT_X);
    _rzLensY_pre = 120 + (int)(sinf(_lensAngleY) * LENS_ORBIT_Y);
  }

  // ── Blit/swap state machine ───────────────────────────────────────────────
  switch (_rzState) {

    case RZ_WAIT_FRAME: {
      // Wait for frame timer AND a rendered frame from core1
      if (!_rzFrameReady) return;
      uint32_t now = time_us_32();
      if ((now - _rzLastFrameUs) < RZ_FRAME_US) return;
      _rzLastFrameUs = now;

      // Advance animation angles exactly once per displayed frame
      const RZPreset &p = _rzPresets[_rzPresetIdx];
      _rzAngle     += RZ_ANGLE_SPD * p.angleSpdMul;
      _rzZoomAngle += RZ_ZOOM_SPD  * p.zoomSpdMul;
      _lensAngleX  += LENS_SPD_X;
      _lensAngleY  += LENS_SPD_Y;

      // Push precomputed params to core1
      _vCosF  = _rzCosF_pre;
      _vSinF  = _rzSinF_pre;
      _vOffU  = _rzOffU_pre;
      _vOffV  = _rzOffV_pre;
      _vLensX = _rzLensX_pre;
      _vLensY = _rzLensY_pre;

      _rzState = RZ_BLIT;
      break;
    }

    case RZ_BLIT: {
      // Blit pixel buffer to display framebuffer
      // Release core1 immediately after copy so it starts next frame
      // during the upcoming vsync wait — parallel work!
      uint16_t *fb = (uint16_t*)display.getBuffer();
      if (fb) {
        memcpy(fb, _rzBuf, 320 * 240 * 2);
      } else {
        for (int py = 0; py < 240; py++)
          for (int px = 0; px < 320; px++)
            display.drawPixel(px, py, _rzBuf[py*320+px]);
      }
      // Release core1 to start rendering next frame NOW
      // It will render during the vsync wait below
      _rzFrameReady = false;
      _rzState = RZ_WAIT_SWAP;
      break;
    }

    case RZ_WAIT_SWAP: {
      // swap() blocks until vsync — core1 renders next frame during this wait
      display.swap();
      _rzState = RZ_WAIT_FRAME;
      break;
    }
  }
}
