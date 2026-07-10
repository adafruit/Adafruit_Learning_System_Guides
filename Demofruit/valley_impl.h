// valley.h — Wireframe polygonal valley for Fruit Jam RP2350
// DVHSTX16, 320x240.
// Right half rendered, mirrored to left around screen center.
// Vertex projection cached per row.
//
// Buttons:
//   Button1 (GPIO0) — cycle wire color
//   Button2 (GPIO4) — cycle scroll speed
//   Button3 (GPIO5) — randomize wall height, noise amp, grid density
//
// Terrain animation:
//   ANIM_ENABLED 1 — walls breathe, floor undulates on independent timers
//   ANIM_ENABLED 0 — static geometry


// ── Tuning ────────────────────────────────────────────────────────────────────
#define GRID_W        10      // columns on right half (0=center, GRID_W=wall)
#define GRID_D        20      // rows visible ahead
#define GRID_STEP     1.0f    // world units between vertices
#define WALL_HEIGHT   5.0f    // valley wall height at outer edge
#define NOISE_AMP     0.4f    // height noise (try 0.2-1.2)
#define SCROLL_SPEED  0.18f   // forward speed (world units/frame)
#define CAM_HEIGHT    5.4f    // camera height above floor
#define CAM_TILT      0.20f   // downward look angle (radians)
#define FOCAL         200.0f  // perspective focal length
#define NEAR_CLIP     0.5f    // near clip distance
#define SCR_CX        160
#define SCR_CY        108

// ── Terrain animation ─────────────────────────────────────────────────────────
#define ANIM_ENABLED      1       // 0=static terrain, 1=animated
#define ANIM_WALL_AMP     2.5f    // wall height varies +/- this amount
#define ANIM_WALL_SPEED   0.012f  // wall breath speed (radians/frame)
#define ANIM_FLOOR_AMP    1.8f    // floor heave amplitude
#define ANIM_FLOOR_SPEED  0.007f  // floor undulation speed (radians/frame)
#define ANIM_PHASE_OFFSET 1.2f    // phase offset between wall and floor cycles
                                  // (radians — keeps them from syncing up)
// Floor heave tapers from center outward — inner columns move most,
// outer wall columns barely move, so floor and walls animate independently.
// ANIM_FLOOR_TAPER: 0.0=full taper (walls unaffected), 1.0=no taper (all moves)
#define ANIM_FLOOR_TAPER  0.15f

// ── Wire color ────────────────────────────────────────────────────────────────
// Each color is a {near, far} pair of RGB565 values.
// WIRE_NEAR: bright color for close edges
// WIRE_FAR:  dim color for far edges
// To add more colors, extend _wireColors and bump WIRE_COLOR_COUNT.

#define WIRE_COLOR_COUNT  5

struct WireColor { uint16_t near_c; uint16_t far_c; const char *name; };


static const WireColor _wireColors[WIRE_COLOR_COUNT] = {
  { C565(0,245,0),   C565(0,30,0),    "Green"   },
  { C565(0,220,220), C565(0,28,28),   "Cyan"    },
  { C565(245,140,0), C565(30,17,0),   "Orange"  },
  { C565(245,245,0), C565(30,30,0),   "Yellow"  },
  { C565(200,0,245), C565(25,0,30),   "Magenta" },
};

// ── Fade rows ─────────────────────────────────────────────────────────────────
#define FAR_FADE_ROW  18      // row where brightness reaches far color

// ── LED helper: strip in current wire color, n pixels lit ───────────────────

// ── Runtime variables (button-adjustable) ────────────────────────────────────
static int   _colorIdx   = 0;          // current wire color index

static void _vyLeds(int n) {
  const WireColor &wc = _wireColors[_colorIdx];
  uint8_t r = (uint8_t)(((wc.near_c >> 11) & 0x1F) * 255 / 31);
  uint8_t g = (uint8_t)(((wc.near_c >>  5) & 0x3F) * 255 / 63);
  uint8_t b = (uint8_t)(( wc.near_c        & 0x1F) * 255 / 31);
  ledBar(n, r, g, b);
}
static float _scrollSpeed = SCROLL_SPEED;
static float _wallHeight  = WALL_HEIGHT;
static float _noiseAmp    = NOISE_AMP;
static int   _gridW       = GRID_W;
static int   _gridD       = GRID_D;

// Speed steps for Button2
static const float _speedSteps[]  = { 0.06f, 0.12f, 0.18f, 0.28f, 0.40f };
static const int   _speedCount    = 5;
static int         _speedIdx      = 2;  // start at 0.18f

// Randomization ranges
#define RAND_WALL_MIN   2.0f
#define RAND_WALL_MAX   10.0f
#define RAND_NOISE_MIN  0.1f
#define RAND_NOISE_MAX  1.2f
#define RAND_GRIDW_MIN  6
#define RAND_GRIDW_MAX  14
#define RAND_GRIDD_MIN  14
#define RAND_GRIDD_MAX  26

static inline float _vRandf(float lo, float hi) {
  return lo + (hi - lo) * (random(1000) / 999.0f);
}

// ── State ─────────────────────────────────────────────────────────────────────
static float _camZ = 0.0f;
static float _ct   = 1.0f;
static float _st   = 0.0f;

// ── Animation state ───────────────────────────────────────────────────────────
static float _animWallAngle  = 0.0f;
static float _animFloorAngle = ANIM_PHASE_OFFSET;  // start offset from wall

// ── Height function ───────────────────────────────────────────────────────────
static inline float _wallProfile(int col, int gw, float wh) {
  float t = (float)col / (float)gw;
  return t * t * wh;
}

static inline float _hash(int ix, int iz) {
  uint32_t h = (uint32_t)(ix * 1619 + iz * 31337);
  h ^= (h >> 16); h *= 0x45d9f3b; h ^= (h >> 16);
  return (float)(h & 0xFFFF) / 65535.0f;
}

// animWallH: current animated wall height (replaces base _wallHeight)
// floorOffset: current floor heave offset, tapers toward walls
static inline float _vertexHeight(int col, int iz, int gw,
                                   float animWallH, float na,
                                   float floorOffset) {
  // Taper floor offset: full at col=0 (center), zero at col=gw (wall)
  float taper = 1.0f - ((float)col / (float)gw) * (1.0f - ANIM_FLOOR_TAPER);
  return _wallProfile(col, gw, animWallH)
       + _hash(col, iz) * na
       + floorOffset * taper;
}

// ── Projection ────────────────────────────────────────────────────────────────
struct PV { int16_t sx, sy; bool valid; };

static bool _projectRight(float wx, float wy, float wz,
                           float camY, float camZ, PV &pv) {
  float rx  = wx;
  float ry  = camY - wy;
  float rz  = wz - camZ;
  float ry2 = ry * _ct - rz * _st;
  float rz2 = ry * _st + rz * _ct;
  if (rz2 < NEAR_CLIP) { pv.valid = false; return false; }
  float invZ = FOCAL / rz2;
  pv.sx    = (int16_t)(rx  * invZ) + SCR_CX;
  pv.sy    = (int16_t)(ry2 * invZ) + SCR_CY;
  pv.valid = true;
  return true;
}

static inline int16_t _mirrorX(int16_t sx) {
  return (int16_t)(2 * SCR_CX - sx);
}

// ── Wire shade — lerp between near and far color by row depth ─────────────────
static inline uint16_t _wireShade(int row, int gd) {
  float t  = fminf(1.0f, (float)row / (float)FAR_FADE_ROW);
  // Lerp each channel separately
  const WireColor &wc = _wireColors[_colorIdx];
  uint8_t nr = (wc.near_c >> 11) & 0x1F;
  uint8_t ng = (wc.near_c >>  5) & 0x3F;
  uint8_t nb =  wc.near_c        & 0x1F;
  uint8_t fr = (wc.far_c  >> 11) & 0x1F;
  uint8_t fg = (wc.far_c  >>  5) & 0x3F;
  uint8_t fb =  wc.far_c         & 0x1F;
  uint8_t r  = (uint8_t)(nr + t * (fr - (int)nr));
  uint8_t g  = (uint8_t)(ng + t * (fg - (int)ng));
  uint8_t b  = (uint8_t)(nb + t * (fb - (int)nb));
  return (uint16_t)((r << 11) | (g << 5) | b);
}

// ── Draw mirrored line ────────────────────────────────────────────────────────
static inline void _drawMirrored(DVHSTX16 &display,
                                  int16_t x0, int16_t y0,
                                  int16_t x1, int16_t y1,
                                  uint16_t color) {
  display.drawLine(x0, y0, x1, y1, color);
  display.drawLine(_mirrorX(x0), y0, _mirrorX(x1), y1, color);
}

// ── Row cache — max grid width + 1 ───────────────────────────────────────────
#define MAX_GRID_W  (RAND_GRIDW_MAX + 1)
static PV _row0[MAX_GRID_W + 1];
static PV _row1[MAX_GRID_W + 1];

static void _projectRow(float wz, float camY, float camZ,
                         int gw, float animWallH, float na,
                         float floorOffset, PV *row) {
  int iz = (int)floorf(wz);
  for (int col = 0; col <= gw; col++) {
    float wx = col * GRID_STEP;
    float wy = _vertexHeight(col, iz, gw, animWallH, na, floorOffset);
    _projectRight(wx, wy, wz, camY, camZ, row[col]);
  }
}

// ════════════════════════════════════════════════════════════════════════════
// SHIP — flat-shaded wireframe fighter, complementary color, world-space
// ════════════════════════════════════════════════════════════════════════════

// ── Ship tuning ───────────────────────────────────────────────────────────────
#define SHIP_AHEAD        4.5f    // world units ahead of camera
#define SHIP_SCALE        1.1f    // overall size
#define SHIP_FLOOR_CLEAR  2.2f    // clearance above valley floor

// Motion — irrational speed ratios prevent periodic looping
#define SHIP_BOB_AMP      0.0f    // bob disabled
#define SHIP_BOB_SPD      0.00913f
#define SHIP_STRAFE_AMP   0.65f
#define SHIP_STRAFE_SPD   0.00617f
#define SHIP_SURGE_AMP    0.45f
#define SHIP_SURGE_SPD    0.00431f
#define SHIP_ROLL_AMP     0.18f

// Secondary slow amplitude modulators
#define SHIP_MOD_SPD1     0.00173f
#define SHIP_MOD_SPD2     0.00241f
#define SHIP_MOD_SPD3     0.00137f

#define SHIP_WALL_MARGIN  1.3f
#define SHIP_Y_SMOOTH     0.08f   // lerp factor for Y smoothing (0=frozen, 1=instant)
#define SHIP_MAX_SCR_Y    220     // max screen Y for ship center

// ── Ship state ────────────────────────────────────────────────────────────────
static float _shipBobA    = 0.0f;
static float _shipStrafeA = 1.5f;
static float _shipSurgeA  = 0.8f;
static float _shipModA1   = 0.0f;
static float _shipModA2   = 2.1f;
static float _shipModA3   = 4.3f;
static float _shipYSmooth = 3.0f;  // smoothed world Y — lerps toward target

// ── Complementary color ───────────────────────────────────────────────────────
static void _shipColors(uint16_t &wireCol, uint16_t &brightCol,
                        uint16_t &midCol,  uint16_t &darkCol) {
  const WireColor &wc = _wireColors[_colorIdx];
  float r = ((wc.near_c >> 11) & 0x1F) * (255.0f / 31.0f);
  float g = ((wc.near_c >>  5) & 0x3F) * (255.0f / 63.0f);
  float b =  (wc.near_c        & 0x1F) * (255.0f / 31.0f);
  float cr = 255.0f - r, cg = 255.0f - g, cb = 255.0f - b;
  if ((cr+cg+cb)/3.0f < 60.0f) { cr=200.0f; cg=80.0f; cb=255.0f; }
  uint8_t ri=(uint8_t)fminf(255,cr), gi=(uint8_t)fminf(255,cg), bi=(uint8_t)fminf(255,cb);
  wireCol   = C565(ri, gi, bi);
  brightCol = C565((uint8_t)(ri*0.85f), (uint8_t)(gi*0.85f), (uint8_t)(bi*0.85f));
  midCol    = C565((uint8_t)(ri*0.50f), (uint8_t)(gi*0.50f), (uint8_t)(bi*0.50f));
  darkCol   = C565((uint8_t)(ri*0.20f), (uint8_t)(gi*0.20f), (uint8_t)(bi*0.20f));
}

// ── Project a single world point ─────────────────────────────────────────────
static bool _projectWorld(float wx, float wy, float wz,
                           float camX, float camY, float camZ,
                           int16_t &sx, int16_t &sy) {
  float rx  = wx - camX;
  float ry  = camY - wy;
  float rz  = wz - camZ;
  float ry2 = ry * _ct - rz * _st;
  float rz2 = ry * _st + rz * _ct;
  if (rz2 < NEAR_CLIP) return false;
  float invZ = FOCAL / rz2;
  sx = (int16_t)(rx  * invZ) + SCR_CX;
  sy = (int16_t)(ry2 * invZ) + SCR_CY;
  return true;
}

// ── Ship vertices ─────────────────────────────────────────────────────────────
// Local space: +Z=forward(nose), +X=right, +Y=up
//
//  Top view:
//        0(nose)
//       /  |  \
//     4/   8   \5     <- wing roots, cockpit front
//    1/    |    \2    <- wingtips
//    6\   3   //7     <- tail corners, cockpit rear
//       \___//
//
//  Side view: 8(ck-front) and 3(ck-rear) raised above wing plane

#define SHIP_NV 9
static const float _shipVX[SHIP_NV] = {
   0.00f, // 0 nose
  -1.00f, // 1 L wingtip
   1.00f, // 2 R wingtip
   0.00f, // 3 cockpit rear
  -0.45f, // 4 L wing root
   0.45f, // 5 R wing root
  -0.30f, // 6 tail L
   0.30f, // 7 tail R
   0.00f, // 8 cockpit front
};
static const float _shipVY[SHIP_NV] = {
   0.00f, // 0 nose
  -0.05f, // 1 L wingtip (slightly below)
  -0.05f, // 2 R wingtip
   0.20f, // 3 cockpit rear (raised)
   0.02f, // 4 L wing root
   0.02f, // 5 R wing root
  -0.02f, // 6 tail L
  -0.02f, // 7 tail R
   0.25f, // 8 cockpit front (most raised)
};
static const float _shipVZ[SHIP_NV] = {
   0.90f, // 0 nose (forward)
  -0.05f, // 1 L wingtip
  -0.05f, // 2 R wingtip
  -0.60f, // 3 cockpit rear
   0.35f, // 4 L wing root
   0.35f, // 5 R wing root
  -0.70f, // 6 tail L
  -0.70f, // 7 tail R
   0.25f, // 8 cockpit front
};

// ── Edges ─────────────────────────────────────────────────────────────────────
#define SHIP_NE 14
static const uint8_t _shipEdges[SHIP_NE][2] = {
  {0,1}, {0,2},          // nose to wingtips
  {1,6}, {2,7},          // wingtips to tail
  {6,7},                 // tail bar
  {1,4}, {2,5},          // wingtip to wing root
  {4,6}, {5,7},          // wing root to tail
  {0,8}, {8,3},          // nose to cockpit front, cockpit front to rear
  {3,6}, {3,7},          // cockpit rear to tail corners
  {4,5},                 // wing root bar
};

// ── Faces (triangles) with shade level 0=bright 1=mid 2=dark ─────────────────
// Tessellated to cover all visible surfaces without gaps.
// Winding: vertices listed so face is visible from above/front.
#define SHIP_NF 10
static const uint8_t _shipFaces[SHIP_NF][3] = {
  {0, 4, 1},   // L wing front triangle      bright
  {0, 2, 5},   // R wing front triangle      bright
  {4, 6, 1},   // L wing rear triangle       mid
  {5, 2, 7},   // R wing rear triangle       mid
  {4, 7, 6},   // centre rear quad tri 1     mid
  {4, 5, 7},   // centre rear quad tri 2     mid
  {0, 8, 4},   // L cockpit panel            bright
  {0, 5, 8},   // R cockpit panel            bright
  {8, 3, 6},   // L cockpit rear slope       mid
  {8, 7, 3},   // R cockpit rear slope       mid
};
static const uint8_t _shipFaceShade[SHIP_NF] = {0,0,1,1,1,1,0,0,1,1};

// ── Draw ship ─────────────────────────────────────────────────────────────────
static void _drawShip(DVHSTX16 &display,
                      float camX, float camY, float camZ,
                      float shipX, float shipY, float shipZ,
                      float roll) {
  uint16_t wireCol, brightCol, midCol, darkCol;
  _shipColors(wireCol, brightCol, midCol, darkCol);
  uint16_t shades[3] = { brightCol, midCol, darkCol };

  float cr = cosf(roll), sr = sinf(roll);

  int16_t pvx[SHIP_NV], pvy[SHIP_NV];
  bool    pvv[SHIP_NV];

  for (int i = 0; i < SHIP_NV; i++) {
    float lx = _shipVX[i] * SHIP_SCALE;
    float ly = _shipVY[i] * SHIP_SCALE;
    float lz = _shipVZ[i] * SHIP_SCALE;
    // Roll around local Z axis
    float rx2 = lx * cr - ly * sr;
    float ry2 = lx * sr + ly * cr;
    pvv[i] = _projectWorld(shipX+rx2, shipY+ry2, shipZ+lz,
                           camX, camY, camZ, pvx[i], pvy[i]);
  }

  // Fill faces (all valid)
  for (int f = 0; f < SHIP_NF; f++) {
    uint8_t a=_shipFaces[f][0], b=_shipFaces[f][1], c=_shipFaces[f][2];
    if (pvv[a] && pvv[b] && pvv[c])
      display.fillTriangle(pvx[a],pvy[a], pvx[b],pvy[b], pvx[c],pvy[c],
                           shades[_shipFaceShade[f]]);
  }

  // Wire edges on top
  for (int e = 0; e < SHIP_NE; e++) {
    uint8_t a=_shipEdges[e][0], b=_shipEdges[e][1];
    if (pvv[a] && pvv[b])
      display.drawLine(pvx[a],pvy[a], pvx[b],pvy[b], wireCol);
  }
}

// ── Ship tick ─────────────────────────────────────────────────────────────────
static void _shipTick(DVHSTX16 &display,
                      float camX, float camY, float camZ,
                      float animWallH, float floorOffset) {
  _shipBobA    += SHIP_BOB_SPD;
  _shipStrafeA += SHIP_STRAFE_SPD;
  _shipSurgeA  += SHIP_SURGE_SPD;
  _shipModA1   += SHIP_MOD_SPD1;
  _shipModA2   += SHIP_MOD_SPD2;
  _shipModA3   += SHIP_MOD_SPD3;

  float bobAmp    = SHIP_BOB_AMP    * (0.6f + 0.4f * sinf(_shipModA1));
  float strafeAmp = SHIP_STRAFE_AMP * (0.6f + 0.4f * sinf(_shipModA2));
  float surgeAmp  = SHIP_SURGE_AMP  * (0.6f + 0.4f * sinf(_shipModA3));

  // Strafe with wall clamp
  float rawStrafe = sinf(_shipStrafeA) * strafeAmp;
  float maxStrafe = (_gridW * GRID_STEP) - SHIP_WALL_MARGIN;
  if (maxStrafe < 0.1f) maxStrafe = 0.1f;
  float shipX = fmaxf(-maxStrafe, fminf(maxStrafe, rawStrafe));

  float roll = -(rawStrafe / (strafeAmp > 0.01f ? strafeAmp : 0.01f)) * SHIP_ROLL_AMP;

  float shipZ  = camZ + SHIP_AHEAD + sinf(_shipSurgeA) * surgeAmp;
  int   shipIZ = (int)floorf(shipZ);
  float floorH = _vertexHeight(0, shipIZ, _gridW, animWallH, _noiseAmp, floorOffset);

  // Target Y: fixed clearance above floor — no bob
  float targetY = floorH + SHIP_FLOOR_CLEAR;

  // Screen bottom constraint: project target, nudge up if needed
  {
    int16_t cx, cy;
    if (_projectWorld(shipX, targetY, shipZ, camX, camY, camZ, cx, cy)) {
      if (cy > SHIP_MAX_SCR_Y) {
        // Convert pixel overshoot to world Y nudge
        float rz  = (shipZ - camZ) * _ct + (camY - targetY) * _st;
        if (rz > 0.01f) {
          float invZ = FOCAL / rz;
          targetY += (cy - SHIP_MAX_SCR_Y) / invZ;
        }
      }
    }
  }

  // Smooth Y — lerp toward target, eliminates sudden jumps
  _shipYSmooth += (targetY - _shipYSmooth) * SHIP_Y_SMOOTH;

  _drawShip(display, camX, camY, camZ, shipX, _shipYSmooth, shipZ, roll);
}

// ── Public API ────────────────────────────────────────────────────────────────

void valleyInit() {
  _camZ        = 0.0f;
  _ct          = cosf(CAM_TILT);
  _st          = sinf(CAM_TILT);
  _colorIdx    = 0;
  _speedIdx    = 2;
  _scrollSpeed = _speedSteps[_speedIdx];
  _vyLeds(_speedIdx + 1);   // show starting speed
  _wallHeight  = WALL_HEIGHT;
  _noiseAmp    = NOISE_AMP;
  _gridW       = GRID_W;
  _gridD       = GRID_D;
  _animWallAngle  = 0.0f;
  _animFloorAngle = ANIM_PHASE_OFFSET;
  _shipBobA    = 0.0f;
  _shipStrafeA = 1.5f;
  _shipSurgeA  = 0.8f;
  _shipModA1   = 0.0f;
  _shipModA2   = 2.1f;
  _shipModA3   = 4.3f;
}

__attribute__((optimize("O3")))
void valleyTick(DVHSTX16 &display) {
  // ── Buttons ───────────────────────────────────────────────────────────────
  if (smpBtn(0)) {
    _colorIdx = (_colorIdx + 1) % WIRE_COLOR_COUNT;
    _vyLeds(_speedIdx + 1);                 // recolor strip to new wire color
    Serial.print("color: "); Serial.println(_wireColors[_colorIdx].name);
  }
  if (smpBtn(1)) {
    _speedIdx    = (_speedIdx + 1) % _speedCount;
    _scrollSpeed = _speedSteps[_speedIdx];
    _vyLeds(_speedIdx + 1);                 // N of 5 = speed preset
    Serial.print("speed: "); Serial.println(_scrollSpeed);
  }
  if (smpBtn(2)) {
    {
      const WireColor &wc = _wireColors[_colorIdx];
      ledBlink((uint8_t)(((wc.near_c>>11)&0x1F)*255/31),
               (uint8_t)(((wc.near_c>>5)&0x3F)*255/63),
               (uint8_t)((wc.near_c&0x1F)*255/31));
      _vyLeds(_speedIdx + 1);
    }
    _wallHeight = _vRandf(RAND_WALL_MIN,  RAND_WALL_MAX);
    _noiseAmp   = _vRandf(RAND_NOISE_MIN, RAND_NOISE_MAX);
    _gridW      = random(RAND_GRIDW_MIN,  RAND_GRIDW_MAX + 1);
    _gridD      = random(RAND_GRIDD_MIN,  RAND_GRIDD_MAX + 1);
    Serial.print("wall:"); Serial.print(_wallHeight);
    Serial.print(" noise:"); Serial.print(_noiseAmp);
    Serial.print(" gridW:"); Serial.print(_gridW);
    Serial.print(" gridD:"); Serial.println(_gridD);
  }

  display.fillScreen(0x0000);
  _camZ += _scrollSpeed;

  // ── Terrain animation ─────────────────────────────────────────────────────
#if ANIM_ENABLED
  _animWallAngle  += ANIM_WALL_SPEED;
  _animFloorAngle += ANIM_FLOOR_SPEED;
  float animWallH   = _wallHeight  + sinf(_animWallAngle)  * ANIM_WALL_AMP;
  float floorOffset = sinf(_animFloorAngle) * ANIM_FLOOR_AMP;
  // Clamp wall height so it never goes negative
  if (animWallH < 0.3f) animWallH = 0.3f;
#else
  float animWallH   = _wallHeight;
  float floorOffset = 0.0f;
#endif

  float camY   = CAM_HEIGHT;
  float startZ = _camZ + NEAR_CLIP + GRID_STEP;

  _projectRow(startZ, camY, _camZ, _gridW, animWallH, _noiseAmp, floorOffset, _row0);

  for (int row = 0; row < _gridD - 1; row++) {
    float    wz1   = startZ + (row + 1) * GRID_STEP;
    uint16_t color = _wireShade(row, _gridD);

    _projectRow(wz1, camY, _camZ, _gridW, animWallH, _noiseAmp, floorOffset, _row1);

    for (int c = 0; c < _gridW; c++) {
      PV &a = _row0[c];
      PV &b = _row0[c + 1];
      PV &d = _row1[c];
      if (a.valid && b.valid)
        _drawMirrored(display, a.sx, a.sy, b.sx, b.sy, color);
      if (a.valid && d.valid)
        _drawMirrored(display, a.sx, a.sy, d.sx, d.sy, color);
    }
    {
      PV &a = _row0[_gridW];
      PV &d = _row1[_gridW];
      if (a.valid && d.valid)
        _drawMirrored(display, a.sx, a.sy, d.sx, d.sy, color);
    }

    memcpy(_row0, _row1, (_gridW + 2) * sizeof(PV));
  }

  // Final row horizontal edges
  {
    uint16_t color = _wireShade(_gridD - 1, _gridD);
    for (int c = 0; c < _gridW; c++) {
      PV &a = _row0[c];
      PV &b = _row0[c + 1];
      if (a.valid && b.valid)
        _drawMirrored(display, a.sx, a.sy, b.sx, b.sy, color);
    }
  }

  // Draw ship over terrain
  _shipTick(display, 0.0f, CAM_HEIGHT, _camZ, animWallH, floorOffset);

  display.swap();
}
