/*  rt_graham.h — Faithful port of RT1.C to C++/float for RP2350
    
    Original:
        RT1.C    Ray tracing program
        Copyright 1987 Eric Graham
        Permission is granted to copy and modify this file, provided
        that this notice is retained.
    
    This file is a modified version of RT1.C. Changes from the original:
      1. K&R C -> C++ (prototypes, no implicit int)
      2. double -> float throughout (RP2350 FPU is single precision)
      3. reflect(): the published listing reads y[k]=xv*v[k]/(xn*n[k]),
         which divides by individual normal components (degenerate when
         any component is 0). Restored to the mathematically correct
         y[k]=xv*v[k]-xn*n[k] (flip the normal component of the incident
         vector) — almost certainly a '-' corrupted to '/(' in transcription.
      4. Added a recursion depth limit to mirror() (the three mirror balls
         can reflect each other indefinitely; MCU stack is finite).
      5. main()/initsc()/ham()/cleanup() (Amiga HAM display) removed —
         the caller drives rendering per-pixel via rtTracePixel().
      6. Lamp gained a noGlint flag: such lamps contribute diffuse light
         in pixbrite() but are skipped by glint(), so fill lights don't
         create extra specular highlights.
    
    Algorithm, structure, naming, and shading model are Eric Graham's,
    preserved as closely as practical.
*/


#define RT_BIG    1.0e10f
#define RT_SMALL  1.0e-3f
#define DULL      0
#define BRIGHT    1
#define MIRROR    2

#define RT_MAX_MIRROR_DEPTH 5   /* port addition: recursion guard */

/*  Ambient shading curve (pixbrite): diffuse = (n.zenith + F1) * F2.
    Eric's originals were F1=1.5, F2=0.4 — strongly zenith-weighted, which
    crushes downward-facing surfaces (chin, underside of limbs) to ~0.32x
    on top of whatever ambient level the scene sets. Flatter defaults here
    lift those surfaces while keeping upward-facing brightness ~equal:
       original: top (n.z=1) -> 1.00, chin (n.z=-0.7) -> 0.32
       below:    top         -> 0.96, chin            -> 0.45
    Restore 1.5f / 0.4f for museum-authentic shading.                     */
#define RT_AMB_F1  2.2f
#define RT_AMB_F2  0.30f

struct Lamp {
    float pos[3];
    float color[3];
    float radius;
    int   noGlint;   /* port addition: 1 = diffuse-only lamp, produces no
                        specular highlights in glint(). Lets a fill light
                        lift shadows without adding a second highlight.   */
};

struct Sphere {
    float pos[3];
    float color[3];
    float radius;
    int   type;       /* DULL, BRIGHT or MIRROR */
};

struct Patch {        /* a small bit of something visible */
    float pos[3];
    float normal[3];
    float color[3];
};

struct World {        /* everything in the universe, except observer */
    int     numsp;
    Sphere *sp;
    int     numlmp;
    Lamp   *lmp;
    Patch   horizon[2];   /* alternate squares on the ground */
    float   illum[3];     /* background diffuse illumination */
    float   skyhor[3];    /* sky color at horizon */
    float   skyzen[3];    /* sky color overhead */
};

struct Observer {
    float obspos[3];
    float viewdir[3];
    float uhat[3];        /* left to right in view plane */
    float vhat[3];        /* down to up in view plane */
    float fl, px, py;     /* focal length and pixel sizes */
    int   nx, ny;
};

/* ── small vector helpers (Eric's originals) ─────────────────────────────── */

static inline float rt_dot(const float *a, const float *b) {
    return a[0]*b[0] + a[1]*b[1] + a[2]*b[2];
}

static inline void rt_vecsub(float *a, const float *b, const float *c) {
    for (int k = 0; k < 3; ++k) a[k] = b[k] - c[k];
}

static inline void rt_veccopy(float *a, const float *b) {
    for (int k = 0; k < 3; ++k) a[k] = b[k];
}

static inline void rt_colorcpy(float *a, const float *b) {
    for (int k = 0; k < 3; ++k) a[k] = b[k];
}

static inline void rt_vecprod(float *a, const float *b, const float *c) {
    a[0] = b[1]*c[2] - b[2]*c[1];
    a[1] = b[2]*c[0] - b[0]*c[2];
    a[2] = b[0]*c[1] - b[1]*c[0];
}

static inline int rt_veczero(const float *v) {
    return v[0] == 0.0f && v[1] == 0.0f && v[2] == 0.0f;
}

/*  generate the equation of a line through points a and b.
    layout (interleaved, as in the original):
    line = { x0, dx, y0, dy, z0, dz }                                       */
static inline void rt_genline(float *l, const float *a, const float *b) {
    for (int k = 0; k < 3; ++k) { *l++ = a[k]; *l++ = b[k] - a[k]; }
}

/* position of a point on the line with parameter t */
static inline void rt_point(float *pos, float t, const float *line) {
    for (int k = 0; k < 3; ++k) {
        float a = *line++;
        pos[k] = a + (*line++) * t;
    }
}

/* ── intersections ───────────────────────────────────────────────────────── */

/* intersection of sphere and line; t returns line parameter of hit */
static int rt_intsplin(float *t, const float *line, const Sphere *sp) {
    float a = 0.0f, b = 0.0f, c = sp->radius;
    c = -c * c;
    for (int k = 0; k < 3; ++k) {
        float p = (*line++) - sp->pos[k];
        float q = *line++;
        a = q*q + a;
        float tt = q*p;
        b = tt + tt + b;
        c = p*p + c;
    }
    float d = b*b - 4.0f*a*c;
    if (d <= 0.0f) return 0;              /* line misses sphere */
    d = sqrtf(d);
    *t = -(b + d) / (a + a);
    if (*t < RT_SMALL) *t = (d - b) / (a + a);
    return *t > RT_SMALL;                 /* sphere in front of us? */
}

/* the Lamp struct shares pos/radius layout for intersection purposes */
static inline int rt_intlamp(float *t, const float *line, const Lamp *lm) {
    Sphere s;
    rt_veccopy(s.pos, lm->pos);
    s.radius = lm->radius;
    return rt_intsplin(t, line, &s);
}

/* intersection of line with ground (z = 0 plane) */
static inline int rt_inthor(float *t, const float *line) {
    if (line[5] == 0.0f) return 0;
    *t = -line[4] / line[5];
    return *t > RT_SMALL;
}

/* are we on a 'black' or 'white' tile? tiles are 3 units wide */
static int rt_gingham(const float *pos) {
    int kx = 0, ky = 0;
    float x = pos[0], y = pos[1];
    if (x < 0.0f) { x = -x; ++kx; }
    if (y < 0.0f) { y = -y; ++ky; }
    return ((((int)x) + kx) / 3 + (((int)y) + ky) / 3) % 2;
}

/*  law of reflection: n is unit normal, x incoming, y outgoing.
    (See port note 3 in header — sign restored.)                            */
static void rt_reflect(float *y, const float *n, const float *x) {
    float u[3], v[3];
    rt_vecprod(u, x, n);          /* normal to the plane of n and x */
    if (rt_veczero(u)) {          /* bounce right back */
        y[0] = -x[0]; y[1] = -x[1]; y[2] = -x[2];
        return;
    }
    rt_vecprod(v, u, n);          /* u, v and n are orthogonal */
    float vv = rt_dot(v, v);
    float xv = rt_dot(x, v) / vv;
    float xn = rt_dot(x, n);
    for (int k = 0; k < 3; ++k) y[k] = xv*v[k] - xn*n[k];
}

/* normal (radial) direction of sphere at patch position */
static inline void rt_setnorm(Patch *p, const Sphere *s) {
    float *t = p->normal;
    rt_vecsub(t, p->pos, s->pos);
    float a = 1.0f / s->radius;
    for (int k = 0; k < 3; ++k) { *t = (*t) * a; ++t; }
}

/* ── shading ─────────────────────────────────────────────────────────────── */

/* how bright is the patch? (ambient + per-lamp diffuse with shadows) */
static void rt_pixbrite(float *brite, const Patch *p, const World *w,
                        const Sphere *spc) {
    static const float zenith[3] = { 0.0f, 0.0f, 1.0f };
    const float f1 = RT_AMB_F1, f2 = RT_AMB_F2;
    float diffuse = (rt_dot(zenith, p->normal) + f1) * f2;
    for (int k = 0; k < 3; ++k)
        brite[k] = diffuse * w->illum[k] * p->color[k];

    for (int l = 0; l < w->numlmp; ++l) {
        float line[6], lp[3], t;
        const float *ll = w->lmp[l].pos;
        const float *pp = p->pos;
        rt_vecsub(lp, ll, pp);
        float cosi = rt_dot(lp, p->normal);
        if (cosi <= 0.0f) continue;
        rt_genline(line, pp, ll);
        bool shadowed = false;
        for (int k = 0; k < w->numsp; ++k) {
            if (w->sp + k == spc) continue;
            if (rt_intsplin(&t, line, w->sp + k)) { shadowed = true; break; }
        }
        if (shadowed) continue;
        float r = sqrtf(rt_dot(lp, lp));
        cosi = cosi / (r * r * r);    /* unnormalized lp: = cos(theta)/r^2 */
        for (int k = 0; k < 3; ++k)
            brite[k] = brite[k] + cosi * p->color[k] * w->lmp[l].color[k];
    }
}

/* are we looking at a highlight? */
static int rt_glint(float *brite, const Patch *p, const World *w,
                    const Sphere *spc, const float *incident) {
    const float minglint = 0.95f;
    int firstlite = 1;
    float refvec[3] = {0,0,0}, ref2 = 0.0f;

    for (int l = 0; l < w->numlmp; ++l) {
        if (w->lmp[l].noGlint) continue;   /* diffuse-only lamp */
        float line[6], lp[3], t;
        const float *ll = w->lmp[l].pos;
        const float *pp = p->pos;
        rt_vecsub(lp, ll, pp);
        float cosi = rt_dot(lp, p->normal);
        if (cosi <= 0.0f) continue;     /* not with this lamp! */
        rt_genline(line, pp, ll);
        bool blocked = false;
        for (int k = 0; k < w->numsp; ++k) {
            if (w->sp + k == spc) continue;
            if (rt_intsplin(&t, line, w->sp + k)) { blocked = true; break; }
        }
        if (blocked) continue;
        if (firstlite) {
            float incvec[3] = { incident[1], incident[3], incident[5] };
            rt_reflect(refvec, p->normal, incvec);
            ref2 = rt_dot(refvec, refvec);
            firstlite = 0;
        }
        t = rt_dot(lp, refvec);
        t = t * t / (rt_dot(lp, lp) * ref2);
        if (t > minglint) {             /* it's a highlight */
            for (int k = 0; k < 3; ++k) brite[k] = 1.0f;
            return 1;
        }
    }
    return 0;
}

/* forward declaration for mirror recursion */
static void rt_raytrace(float *brite, const float *line, const World *w,
                        int depth);

/* bounce ray off mirror */
static int rt_mirror(float *brite, const Patch *p, const World *w,
                     const float *incident, int depth) {
    float incvec[3] = { incident[1], incident[3], incident[5] };
    float t = rt_dot(p->normal, incvec);
    if (t >= 0.0f || depth >= RT_MAX_MIRROR_DEPTH) {
        /* inside a sphere (dark), or recursion limit (port addition) */
        for (int k = 0; k < 3; ++k) brite[k] = 0.0f;
        return 0;
    }
    float refvec[3], line[6];
    rt_reflect(refvec, p->normal, incvec);
    line[0] = p->pos[0]; line[1] = refvec[0];
    line[2] = p->pos[1]; line[3] = refvec[1];
    line[4] = p->pos[2]; line[5] = refvec[2];
    rt_raytrace(brite, line, w, depth + 1);  /* recursion saves the day */
    for (int k = 0; k < 3; ++k) brite[k] = brite[k] * p->color[k];
    return 1;
}

/* calculate sky color: blend zenith to horizon */
static void rt_skybrite(float *brite, const float *line, const World *w) {
    float sin2 = line[5] * line[5];
    sin2 /= (line[1]*line[1] + line[3]*line[3] + sin2);
    float cos2 = 1.0f - sin2;
    for (int k = 0; k < 3; ++k)
        brite[k] = cos2 * w->skyhor[k] + sin2 * w->skyzen[k];
}

/* ── the raytracer ───────────────────────────────────────────────────────── */

static void rt_raytrace(float *brite, const float *line, const World *w,
                        int depth) {
    float t, tmin = RT_BIG, pos[3];
    Patch ptch;
    const Sphere *spnear = 0;
    const Lamp   *lmpnear = 0;

    for (int k = 0; k < w->numsp; ++k)          /* can we see some spheres */
        if (rt_intsplin(&t, line, w->sp + k)) {
            if (t < tmin) { tmin = t; spnear = w->sp + k; }
        }

    for (int k = 0; k < w->numlmp; ++k)         /* are we looking at a lamp */
        if (rt_intlamp(&t, line, w->lmp + k)) {
            if (t < tmin) { tmin = t; lmpnear = w->lmp + k; }
        }

    if (lmpnear) {                              /* we see a lamp! */
        for (int k = 0; k < 3; ++k)
            brite[k] = lmpnear->color[k] / (lmpnear->radius * lmpnear->radius);
        return;
    }

    if (rt_inthor(&t, line))                    /* do we see the ground? */
        if (t < tmin) {
            rt_point(pos, t, line);
            int k = rt_gingham(pos);            /* cheap vinyl */
            World *wm = (World *)w;             /* horizon patch pos is scratch */
            rt_veccopy(wm->horizon[k].pos, pos);
            rt_pixbrite(brite, &(w->horizon[k]), w, 0);
            return;
        }

    if (spnear) {                               /* we see a sphere */
        rt_point(ptch.pos, tmin, line);
        rt_setnorm(&ptch, spnear);
        rt_colorcpy(ptch.color, spnear->color);
        switch (spnear->type) {
            case BRIGHT:                        /* is it a highlight? */
                if (rt_glint(brite, &ptch, w, spnear, line)) return;
                /* fall through — original behavior */
            case DULL:
                rt_pixbrite(brite, &ptch, w, spnear); return;
            case MIRROR:
                rt_mirror(brite, &ptch, w, line, depth); return;
        }
        return;
    }

    rt_skybrite(brite, line, w);                /* nothing else, must be sky */
}

/* calculate ray for pixel i,j */
static void rt_pixline(float *line, const Observer *o, int i, int j) {
    float tp[3];
    float y = (0.5f * o->ny - j) * o->py;
    float x = (i - 0.5f * o->nx) * o->px;
    for (int k = 0; k < 3; ++k)
        tp[k] = o->viewdir[k] * o->fl + y * o->vhat[k]
              + x * o->uhat[k] + o->obspos[k];
    rt_genline(line, o->obspos, tp);
}

/* ── public entry: trace one pixel, return RGB 0..1 ─────────────────────── */
static inline void rtTracePixel(float *brite, const Observer *o,
                                const World *w, int i, int j) {
    float line[6];
    rt_pixline(line, o, i, j);
    rt_raytrace(brite, line, w, 0);
}

/*  scene_robot.h — The Juggler scene, from Eric Graham's robot.dat (1987)
    
    Scene data transcribed from robot.dat as distributed with the
    raytracer source. The figure is built from sphere "chains" — the
    original format specifies a start sphere, then counts of spheres
    interpolated toward successive endpoints (positions and radii
    both lerped). We expand those chains at init into a flat array.
    
    Coordinate system: X/Y horizontal ground plane, Z up.
    Ground: z=0, gingham tiles 3 units wide (yellow / green).
*/


#define MAX_SPHERES 80

/* Ambient illumination level. robot.dat specifies 0.25, which renders
   shadow sides quite dark on modern sRGB displays (the Amiga HAM pipeline
   and CRTs of the era were more forgiving). The lampfac auto-exposure
   rebalances direct light automatically, so raising this lifts shadows
   without clipping highlights. Try 0.25 (authentic) .. 0.45 (airy).      */
#define JG_AMBIENT 0.38f

/* Fill light: dim lamp behind/near the camera, placed LOW so its light
   travels slightly upward into downward-facing surfaces (chin, underside
   of arms) that the high key lamp and zenith-weighted ambient both miss.
   Intensity is relative to the key lamp (1.0); lampfac auto-exposure
   preserves the ratio. ~0.3 here lands at ~38% of key effectiveness given
   the distances. Set to 0.0f to disable (single-lamp authentic).         */
#define JG_FILL_INTENSITY  0.30f
#define JG_FILL_X        -150.0f
#define JG_FILL_Y         -60.0f
#define JG_FILL_Z          20.0f

static Sphere g_spheres[MAX_SPHERES];
static Lamp   g_lamps[2];
static World  g_world;
static Observer g_obs;

/* ── chain expander ──────────────────────────────────────────────────────── */
/* Append one sphere */
static int _scAdd(int n, float x, float y, float z, float r,
                  float cr, float cg, float cb, int type) {
    if (n >= MAX_SPHERES) return n;
    Sphere *s = &g_spheres[n];
    s->pos[0] = x; s->pos[1] = y; s->pos[2] = z;
    s->radius = r;
    s->color[0] = cr; s->color[1] = cg; s->color[2] = cb;
    s->type = type;
    return n + 1;
}

/*  Append `count` spheres interpolating from (x0,y0,z0,r0) toward
    (x1,y1,z1,r1), endpoint inclusive, start point NOT re-emitted.       */
static int _scChain(int n, float x0, float y0, float z0, float r0,
                    float x1, float y1, float z1, float r1,
                    int count, float cr, float cg, float cb, int type) {
    for (int i = 1; i <= count; i++) {
        float t = (float)i / (float)count;
        n = _scAdd(n,
                   x0 + (x1 - x0) * t,
                   y0 + (y1 - y0) * t,
                   z0 + (z1 - z0) * t,
                   r0 + (r1 - r0) * t,
                   cr, cg, cb, type);
    }
    return n;
}

/* ── build the juggler ───────────────────────────────────────────────────── */
static void sceneBuildJuggler() {
    int n = 0;

    /* the three juggled mirror balls */
    n = _scAdd(n, -0.9f, -2.1f, 5.3f, 0.6f,  0.9f, 0.9f, 0.9f, MIRROR);
    n = _scAdd(n, -1.1f,  1.9f, 5.9f, 0.6f,  0.9f, 0.9f, 0.9f, MIRROR);
    n = _scAdd(n, -0.4f, -1.2f, 6.8f, 0.6f,  0.9f, 0.9f, 0.9f, MIRROR);

    /* head (flesh), with dark sphere offset behind it = hair */
    n = _scAdd(n,  0.00f, 0.0f, 6.10f, 0.5f,  1.0f, 0.7f, 0.7f, BRIGHT);
    n = _scAdd(n,  0.02f, 0.0f, 6.12f, 0.5f,  0.2f, 0.1f, 0.1f, BRIGHT);

    /* eyes (blue) */
    n = _scAdd(n, -0.4f,  0.2f, 6.1f, 0.15f,  0.1f, 0.1f, 1.0f, BRIGHT);
    n = _scAdd(n, -0.4f, -0.2f, 6.1f, 0.15f,  0.1f, 0.1f, 1.0f, BRIGHT);

    /* neck */
    n = _scAdd(n,  0.0f,  0.0f, 5.5f, 0.2f,   1.0f, 0.7f, 0.7f, BRIGHT);

    /* torso (red): start at chest, chain of 5 down to waist */
    n = _scAdd  (n, 0.0f, 0.0f, 4.6f, 0.8f,   1.0f, 0.1f, 0.1f, BRIGHT);
    n = _scChain(n, 0.0f, 0.0f, 4.6f, 0.8f,
                    0.0f, 0.0f, 3.3f, 0.6f, 5, 1.0f, 0.1f, 0.1f, BRIGHT);

    /* left leg: hip -> 6 to knee -> 7 to foot */
    n = _scAdd  (n, 0.0f, 0.6f, 2.9f, 0.2f,   1.0f, 0.7f, 0.7f, BRIGHT);
    n = _scChain(n, 0.0f, 0.6f, 2.9f, 0.2f,
                   -0.6f, 0.6f, 1.6f, 0.2f, 6, 1.0f, 0.7f, 0.7f, BRIGHT);
    n = _scChain(n,-0.6f, 0.6f, 1.6f, 0.2f,
                   -0.4f, 0.6f, 0.0f, 0.1f, 7, 1.0f, 0.7f, 0.7f, BRIGHT);

    /* right leg */
    n = _scAdd  (n, 0.0f,-0.6f, 2.9f, 0.2f,   1.0f, 0.7f, 0.7f, BRIGHT);
    n = _scChain(n, 0.0f,-0.6f, 2.9f, 0.2f,
                    0.2f,-0.6f, 1.6f, 0.2f, 6, 1.0f, 0.7f, 0.7f, BRIGHT);
    n = _scChain(n, 0.2f,-0.6f, 1.6f, 0.2f,
                    0.4f,-0.6f, 0.0f, 0.1f, 7, 1.0f, 0.7f, 0.7f, BRIGHT);

    /* right arm: shoulder -> 6 to elbow -> 7 to hand */
    n = _scAdd  (n, 0.0f,-0.7f, 5.1f, 0.2f,   1.0f, 0.7f, 0.7f, BRIGHT);
    n = _scChain(n, 0.0f,-0.7f, 5.1f, 0.2f,
                   -0.2f,-1.2f, 4.2f, 0.2f, 6, 1.0f, 0.7f, 0.7f, BRIGHT);
    n = _scChain(n,-0.2f,-1.2f, 4.2f, 0.2f,
                   -1.1f,-2.0f, 4.1f, 0.1f, 7, 1.0f, 0.7f, 0.7f, BRIGHT);

    /* left arm (hand raised — mid-throw) */
    n = _scAdd  (n, 0.0f, 0.7f, 5.1f, 0.2f,   1.0f, 0.7f, 0.7f, BRIGHT);
    n = _scChain(n, 0.0f, 0.7f, 5.1f, 0.2f,
                   -0.2f, 1.2f, 4.2f, 0.2f, 6, 1.0f, 0.7f, 0.7f, BRIGHT);
    n = _scChain(n,-0.2f, 1.2f, 4.2f, 0.2f,
                   -1.0f, 1.9f, 4.8f, 0.1f, 7, 1.0f, 0.7f, 0.7f, BRIGHT);

    g_world.numsp = n;
    g_world.sp    = g_spheres;

    /* key lamp: (-100,50,150) r=15, white — Eric's original */
    g_lamps[0].pos[0] = -100.0f; g_lamps[0].pos[1] = 50.0f;
    g_lamps[0].pos[2] = 150.0f;  g_lamps[0].radius = 15.0f;
    g_lamps[0].color[0] = g_lamps[0].color[1] = g_lamps[0].color[2] = 1.0f;
    g_lamps[0].noGlint = 0;     /* key lamp: full specular highlights */
    g_world.numlmp = 1;

    /* fill lamp (port addition — see JG_FILL_* above) */
    if (JG_FILL_INTENSITY > 0.0f) {
        g_lamps[1].pos[0] = JG_FILL_X;
        g_lamps[1].pos[1] = JG_FILL_Y;
        g_lamps[1].pos[2] = JG_FILL_Z;
        g_lamps[1].radius = 15.0f;
        g_lamps[1].color[0] = g_lamps[1].color[1] = g_lamps[1].color[2]
                            = JG_FILL_INTENSITY;
        g_lamps[1].noGlint = 1;  /* fill: diffuse only, no highlights */
        g_world.numlmp = 2;
    }
    g_world.lmp = g_lamps;

    /* ground gingham: yellow / green, normals straight up */
    g_world.horizon[0].color[0] = 1.5f;
    g_world.horizon[0].color[1] = 1.5f;
    g_world.horizon[0].color[2] = 0.0f;
    g_world.horizon[1].color[0] = 0.0f;
    g_world.horizon[1].color[1] = 1.5f;
    g_world.horizon[1].color[2] = 0.0f;
    for (int k = 0; k < 2; k++) {
        g_world.horizon[k].normal[0] = 0.0f;
        g_world.horizon[k].normal[1] = 0.0f;
        g_world.horizon[k].normal[2] = 1.0f;
    }

    /* illumination and sky.
       robot.dat order follows rt2.c assignment order: zenith THEN horizon.
       zenith deep blue, horizon pale lavender — matches the original frames. */
    g_world.illum[0] = g_world.illum[1] = g_world.illum[2] = JG_AMBIENT;
    g_world.skyzen[0] = 0.1f; g_world.skyzen[1] = 0.1f; g_world.skyzen[2] = 1.0f;
    g_world.skyhor[0] = 0.7f; g_world.skyhor[1] = 0.7f; g_world.skyhor[2] = 1.0f;

    /* ── lamp auto-exposure, verbatim from rt2.c setup() ──────────────────
       "modify the lamp brightness so as to get the right exposure":
       find the factor that brings the brightest fully-lit sphere surface
       to exactly 1.0, and scale the lamp by it. Without this the distant
       lamp contributes ~nothing and the whole scene is ambient-only.    */
    {
        float lampfac = RT_BIG;
        for (int i = 0; i < g_world.numsp; ++i) {
            for (int j = 0; j < g_world.numlmp; ++j) {
                float tp[3];
                rt_vecsub(tp, g_world.sp[i].pos, g_world.lmp[j].pos);
                float r = sqrtf(rt_dot(tp, tp));
                r -= g_world.sp[i].radius;
                for (int k = 0; k < 3; ++k) {
                    float t = g_world.sp[i].color[k] * g_world.lmp[j].color[k]
                              / (r * r);
                    if (t == 0.0f) continue;
                    t = (1.0f - g_world.sp[i].color[k] * g_world.illum[k]) / t;
                    if (t < lampfac) lampfac = t;
                }
            }
        }
        for (int j = 0; j < g_world.numlmp; ++j)
            for (int k = 0; k < 3; ++k)
                g_world.lmp[j].color[k] *= lampfac;
    }
}

/* ── observer per robot.dat: pos (-10,-4,5.5), alt -10°, az 20°, fl 35mm ── */
static void sceneSetupObserver(int nx, int ny) {
    const float degtorad = 0.0174533f;
    float alt = -10.0f * degtorad;
    float az  =  20.0f * degtorad;

    g_obs.obspos[0] = -10.0f;
    g_obs.obspos[1] =  -4.0f;
    g_obs.obspos[2] =   5.5f;

    g_obs.nx = nx;  g_obs.ny = ny;
    g_obs.px = 1.0f / nx;
    g_obs.py = 0.75f / ny;        /* original 4:3 frame */

    g_obs.fl = 0.028f * 35.0f;    /* '35' in robot.dat, rt2.c scaling */

    g_obs.viewdir[0] = cosf(az) * cosf(alt);
    g_obs.viewdir[1] = sinf(az) * cosf(alt);
    g_obs.viewdir[2] = sinf(alt);

    g_obs.uhat[0] = sinf(az);
    g_obs.uhat[1] = -cosf(az);
    g_obs.uhat[2] = 0.0f;

    g_obs.vhat[0] = -cosf(az) * sinf(alt);
    g_obs.vhat[1] = -sinf(az) * sinf(alt);
    g_obs.vhat[2] =  cosf(alt);
}

/*  kinematics.h — 3-ball cascade animation for the Juggler
    
    24-frame loop, beat = 4 frames (6 beats/loop), siteswap-3 cascade:
      - throws alternate hands every beat: R at frames 0/8/16, L at 4/12/20
      - each ball: 2 beats (8 frames) in flight, 1 beat (4 frames) carried
      - each hand: 8-frame inside<->outside oscillation; throws happen at
        the inside point, catches at the outside point
    
    The figure stands still except forearms (elbow->hand chains) and balls —
    faithful to the original animation's economy of motion.
    
    Geometry derives from the robot.dat pose: shoulders/elbows fixed at
    Eric's coordinates; the juggling plane sits at x ~= -0.9 in front of
    the body; ball apex ~6.8 matches the high ball in the .dat snapshot.
*/


#define JG_FRAMES      24
#define JG_BEAT         4
#define JG_FLIGHT       8     /* frames airborne (2 beats) */

/* hand path endpoints (y is mirrored for left hand) */
#define JG_HAND_X     -0.95f
#define JG_HAND_Y_IN   0.55f  /* inside (throw) |y| */
#define JG_HAND_Y_OUT  1.85f  /* outside (catch) |y| */
#define JG_HAND_Z      4.15f  /* base height */
#define JG_SCOOP       0.18f  /* scoop dip depth */
#define JG_BALL_LIFT   0.55f  /* carried ball center above hand center */

/* ── Body motion (knee bend + hip/torso bob and sway) ─────────────────────
   Matched to the original animation: ~one graceful dip-and-rise per loop
   with a lateral weight shift; feet planted, knees flex via 2-segment IK.
   Hands are NOT affected — ball pattern and timing stay exactly as-is.   */
#define JG_BOB_AMP    0.35f   /* vertical hip travel (world units) */
#define JG_SWAY_AMP   0.22f   /* lateral hip sway */
#define JG_BOB_PHASE  1.0f    /* radians; shifts where in the loop the dip lands */
#define JG_KNEE_FWD  -0.55f   /* knee bend bias: -x = toward camera (forward) */

/* parabola: flight from inside of one hand to outside of the other.
   rise to apex in JG_FLIGHT/2 frames; apex ~= (JG_HAND_Z+lift) + JG_RISE */
#define JG_RISE        2.1f
#define JG_GRAV        (2.0f * JG_RISE / ((JG_FLIGHT/2.0f)*(JG_FLIGHT/2.0f)))

/* sphere-array indices recorded at scene build time (scene_robot.h order) */
#define IDX_BALL0       0
#define IDX_BALL1       1
#define IDX_BALL2       2
#define IDX_RARM_HAND_CHAIN  /* set below in jugglerAnimInit */ 0

/* forearm chains: 7 spheres each, elbow->hand, radius 0.2 -> 0.1.
   scene_robot.h layout (verified by construction order):
     right arm: shoulder@idx, chain6 to elbow, chain7 to hand
     left arm follows.
   We re-derive the chain start indices at init by replaying the build
   counts rather than hardcoding magic numbers. */
static int _jgRForearm0 = -1;   /* index of first of 7 right forearm spheres */
static int _jgLForearm0 = -1;
static float _jgElbowR[3] = { -0.2f, -1.2f, 4.2f };   /* robot.dat elbows */
static float _jgElbowL[3] = { -0.2f,  1.2f, 4.2f };

/* Replay scene_robot.h build order to locate the forearm chains:
   3 balls + head + hair + 2 eyes + neck = 8
   torso 1+5 = 6                        -> 14
   left leg 1+6+7 = 14                  -> 28
   right leg 14                         -> 42
   right arm: shoulder(1) + upper(6)    -> 49, forearm 7 @ 49..55
   left arm:  shoulder(1) + upper(6)    -> 63, forearm 7 @ 63..69        */
static void jugglerAnimInit() {
    _jgRForearm0 = 49;
    _jgLForearm0 = 63;
}

/* ── Body rig ────────────────────────────────────────────────────────────────
   Sphere index map (from scene_robot.h build order, verified):
     3..13   head, hair, eyes, neck, torso(1+5)      — translate with body
     14..27  left leg: hip(14), upper 15..20, lower 21..27   — IK rebuilt
     28..41  right leg: hip(28), upper 29..34, lower 35..41  — IK rebuilt
     42..48  right shoulder + upper arm chain         — translate with body
     56..62  left shoulder + upper arm chain          — translate with body
   (forearms 49..55 / 63..69 are rebuilt from elbows every frame already) */
#define JG_BODY_FIRST   3
#define JG_BODY_LAST   13
#define JG_LHIP        14
#define JG_LUP0        15
#define JG_LLO0        21
#define JG_RHIP        28
#define JG_RUP0        29
#define JG_RLO0        35
#define JG_RSH_FIRST   42
#define JG_RSH_LAST    48
#define JG_LSH_FIRST   56
#define JG_LSH_LAST    62

/* rest pose captured at init (jugglerSetFrame mutates positions, so all
   per-frame motion must derive from these, never accumulate) */
static float _jgRestBody[ (JG_BODY_LAST-JG_BODY_FIRST+1) ][3];
static float _jgRestRSh [ (JG_RSH_LAST-JG_RSH_FIRST+1) ][3];
static float _jgRestLSh [ (JG_LSH_LAST-JG_LSH_FIRST+1) ][3];
static float _jgRestElbowR[3], _jgRestElbowL[3];
static float _jgHipRest[2][3];   /* [0]=left(y+) [1]=right(y-) */
static float _jgKneeRest[2][3];
static float _jgFootRest[2][3];
static float _jgLegL1[2], _jgLegL2[2];   /* segment lengths */

static void jugglerRigCapture(const Sphere *sp) {
    for (int i = JG_BODY_FIRST; i <= JG_BODY_LAST; i++)
        rt_veccopy(_jgRestBody[i-JG_BODY_FIRST], sp[i].pos);
    for (int i = JG_RSH_FIRST; i <= JG_RSH_LAST; i++)
        rt_veccopy(_jgRestRSh[i-JG_RSH_FIRST], sp[i].pos);
    for (int i = JG_LSH_FIRST; i <= JG_LSH_LAST; i++)
        rt_veccopy(_jgRestLSh[i-JG_LSH_FIRST], sp[i].pos);
    rt_veccopy(_jgRestElbowR, _jgElbowR);
    rt_veccopy(_jgRestElbowL, _jgElbowL);

    /* legs: rest joints from robot.dat geometry */
    rt_veccopy(_jgHipRest[0],  sp[JG_LHIP].pos);          /* (0, 0.6,2.9) */
    rt_veccopy(_jgHipRest[1],  sp[JG_RHIP].pos);          /* (0,-0.6,2.9) */
    _jgKneeRest[0][0]=-0.6f; _jgKneeRest[0][1]= 0.6f; _jgKneeRest[0][2]=1.6f;
    _jgKneeRest[1][0]= 0.2f; _jgKneeRest[1][1]=-0.6f; _jgKneeRest[1][2]=1.6f;
    _jgFootRest[0][0]=-0.4f; _jgFootRest[0][1]= 0.6f; _jgFootRest[0][2]=0.0f;
    _jgFootRest[1][0]= 0.4f; _jgFootRest[1][1]=-0.6f; _jgFootRest[1][2]=0.0f;
    for (int g = 0; g < 2; g++) {
        float d[3];
        rt_vecsub(d, _jgKneeRest[g], _jgHipRest[g]);
        _jgLegL1[g] = sqrtf(rt_dot(d,d));
        rt_vecsub(d, _jgFootRest[g], _jgKneeRest[g]);
        _jgLegL2[g] = sqrtf(rt_dot(d,d));
    }
}

/* body offset for frame f: one dip-and-rise + lateral sway per 24-frame loop */
static void _jgBodyOffset(float *off, int f) {
    float ph = 2.0f * 3.14159265f * (float)f / (float)JG_FRAMES;
    off[0] = 0.0f;
    off[1] = JG_SWAY_AMP * sinf(ph + JG_BOB_PHASE + 1.57f);
    off[2] = -JG_BOB_AMP * (0.5f + 0.5f * cosf(ph + JG_BOB_PHASE));
}

/* two-segment leg IK: hip h (moving) to planted foot p; knee on the
   circle-circle intersection, displaced toward the forward bend bias */
static void _jgSolveKnee(float *knee, const float *h, const float *p,
                         float L1, float L2) {
    float u[3];
    rt_vecsub(u, p, h);
    float d = sqrtf(rt_dot(u, u));
    float dmax = (L1 + L2) * 0.999f;
    if (d > dmax) d = dmax;            /* clamp: leg can't overextend */
    for (int k = 0; k < 3; k++) u[k] /= d;

    float a = (L1*L1 - L2*L2 + d*d) / (2.0f * d);
    float r2 = L1*L1 - a*a;
    float r  = (r2 > 0.0f) ? sqrtf(r2) : 0.0f;

    /* bend direction: forward (-x), made perpendicular to u */
    float b[3] = { JG_KNEE_FWD < 0 ? -1.0f : 1.0f, 0.0f, 0.0f };
    float bu = rt_dot(b, u);
    for (int k = 0; k < 3; k++) b[k] -= bu * u[k];
    float bl = sqrtf(rt_dot(b, b));
    if (bl < 1e-4f) { b[0] = -1; b[1] = 0; b[2] = 0; bl = 1; }
    for (int k = 0; k < 3; k++) b[k] /= bl;

    float fwd = (JG_KNEE_FWD < 0) ? -JG_KNEE_FWD : JG_KNEE_FWD;
    for (int k = 0; k < 3; k++)
        knee[k] = h[k] + u[k]*a + b[k]*r * (fwd > 0 ? 1.0f : 1.0f);
}

/* rebuild an N-sphere chain from `from` to `to`, radii r0->r1,
   start point NOT emitted (matches scene build convention) */
static void _jgChain(Sphere *sp, int n, const float *from, const float *to,
                     float r0, float r1) {
    for (int i = 1; i <= n; i++) {
        float t = (float)i / (float)n;
        sp[i-1].pos[0] = from[0] + (to[0]-from[0])*t;
        sp[i-1].pos[1] = from[1] + (to[1]-from[1])*t;
        sp[i-1].pos[2] = from[2] + (to[2]-from[2])*t;
        sp[i-1].radius = r0 + (r1-r0)*t;
    }
}

/* triangle wave 0..1..0 with period p, value 0 at t=0 */
static inline float _jgTri(int t, int p) {
    int m = t % p;
    float h = p * 0.5f;
    return (m < h) ? (m / h) : (2.0f - m / h);
}

/* hand position at frame f. side: -1 = right (y<0), +1 = left.
   Right hand: inside at frames ≡0 (mod 8), outside at ≡4.
   Left  hand: inside at frames ≡4, outside at ≡0.                       */
static void _jgHandPos(float *pos, int f, int side) {
    int phase = (side < 0) ? (f % 8) : ((f + 4) % 8);
    float t = _jgTri(phase, 8);            /* 0=inside, 1=outside */
    float ay = JG_HAND_Y_IN + (JG_HAND_Y_OUT - JG_HAND_Y_IN) * t;
    pos[0] = JG_HAND_X;
    pos[1] = side * ay;
    /* scoop: dip lowest mid-swing */
    pos[2] = JG_HAND_Z - JG_SCOOP * sinf(3.14159f * t);
}

/*  Ball schedule (period 24). Each entry: throw frame, throwing side.
    Ball is airborne [throw, throw+8), carried for 4 frames before its
    next throw by the catching hand.
      ball0: R@0   -> L, L@12 -> R   (carried R 20..24, L 8..12)
      ball1: L@4   -> R, R@16 -> L   (carried L 0..4,  R 12..16)
      ball2: R@8   -> L, L@20 -> R   (carried R 4..8,  L 16..20)        */
struct JgThrow { int frame; int side; };   /* side throws it */
static const JgThrow _jgSched[3][2] = {
    { {  0, -1 }, { 12, +1 } },
    { {  4, +1 }, { 16, -1 } },
    { {  8, -1 }, { 20, +1 } },
};

/* ball position at frame f for ball b */
static void _jgBallPos(float *pos, int f, int b) {
    /* find which segment of the ball's cycle f falls in */
    for (int s = 0; s < 2; s++) {
        int t0   = _jgSched[b][s].frame;
        int side = _jgSched[b][s].side;
        int rel  = ((f - t0) % JG_FRAMES + JG_FRAMES) % JG_FRAMES;
        if (rel < JG_FLIGHT) {
            /* airborne: thrown from `side` inside point toward the other
               hand's outside point */
            float from[3], to[3];
            /* throw: thrower's hand is at its inside position (phase 0) */
            from[0] = JG_HAND_X;
            from[1] = side * JG_HAND_Y_IN;
            from[2] = JG_HAND_Z + JG_BALL_LIFT;
            to[0]   = JG_HAND_X;
            to[1]   = -side * JG_HAND_Y_OUT;
            to[2]   = JG_HAND_Z + JG_BALL_LIFT;
            float t  = (float)rel;
            float T  = (float)JG_FLIGHT;
            float vz = JG_GRAV * T * 0.5f;
            pos[0] = from[0];
            pos[1] = from[1] + (to[1] - from[1]) * (t / T);
            pos[2] = from[2] + vz * t - 0.5f * JG_GRAV * t * t;
            return;
        }
    }
    /* not airborne: carried. The hand that holds it is the one that will
       throw it next; ball rides that hand. Determine next throw. */
    for (int s = 0; s < 2; s++) {
        int t0   = _jgSched[b][s].frame;
        int side = _jgSched[b][s].side;
        int rel  = ((t0 - f) % JG_FRAMES + JG_FRAMES) % JG_FRAMES;
        if (rel <= JG_BEAT) {     /* within the 4-frame dwell before throw */
            float hp[3];
            _jgHandPos(hp, f, side);
            pos[0] = hp[0];
            pos[1] = hp[1];
            pos[2] = hp[2] + JG_BALL_LIFT;
            return;
        }
    }
    /* shouldn't happen; park at origin-ish if it does */
    pos[0] = JG_HAND_X; pos[1] = 0.0f; pos[2] = JG_HAND_Z;
}

/* rebuild a 7-sphere forearm chain from fixed elbow to hand position */
static void _jgForearm(Sphere *sp, const float *elbow, const float *hand) {
    for (int i = 1; i <= 7; i++) {
        float t = (float)i / 7.0f;
        sp[i-1].pos[0] = elbow[0] + (hand[0] - elbow[0]) * t;
        sp[i-1].pos[1] = elbow[1] + (hand[1] - elbow[1]) * t;
        sp[i-1].pos[2] = elbow[2] + (hand[2] - elbow[2]) * t;
        sp[i-1].radius = 0.2f + (0.1f - 0.2f) * t;
    }
}

/*  Pose the scene for frame f (0..23). Mutates g_spheres: 3 ball
    positions + both forearm chains. Everything else stays put.        */
static void jugglerSetFrame(Sphere *spheres, int f) {
    /* balls: cascade pattern — untouched by body motion */
    for (int b = 0; b < 3; b++)
        _jgBallPos(spheres[b].pos, f, b);

    /* body offset for this frame */
    float off[3];
    _jgBodyOffset(off, f);

    /* translate torso/head/neck/eyes and shoulder+upper-arm chains */
    for (int i = JG_BODY_FIRST; i <= JG_BODY_LAST; i++)
        for (int k = 0; k < 3; k++)
            spheres[i].pos[k] = _jgRestBody[i-JG_BODY_FIRST][k] + off[k];
    for (int i = JG_RSH_FIRST; i <= JG_RSH_LAST; i++)
        for (int k = 0; k < 3; k++)
            spheres[i].pos[k] = _jgRestRSh[i-JG_RSH_FIRST][k] + off[k];
    for (int i = JG_LSH_FIRST; i <= JG_LSH_LAST; i++)
        for (int k = 0; k < 3; k++)
            spheres[i].pos[k] = _jgRestLSh[i-JG_LSH_FIRST][k] + off[k];

    /* elbows ride the body; hands stay on cascade paths */
    for (int k = 0; k < 3; k++) {
        _jgElbowR[k] = _jgRestElbowR[k] + off[k];
        _jgElbowL[k] = _jgRestElbowL[k] + off[k];
    }

    /* legs: hips ride the body, feet stay planted, knees solved by IK */
    for (int g = 0; g < 2; g++) {
        float hip[3], knee[3];
        for (int k = 0; k < 3; k++) hip[k] = _jgHipRest[g][k] + off[k];
        _jgSolveKnee(knee, hip, _jgFootRest[g], _jgLegL1[g], _jgLegL2[g]);

        int hipIdx = (g == 0) ? JG_LHIP : JG_RHIP;
        int up0    = (g == 0) ? JG_LUP0 : JG_RUP0;
        int lo0    = (g == 0) ? JG_LLO0 : JG_RLO0;
        rt_veccopy(spheres[hipIdx].pos, hip);
        _jgChain(&spheres[up0], 6, hip,  knee,          0.2f, 0.2f);
        _jgChain(&spheres[lo0], 7, knee, _jgFootRest[g], 0.2f, 0.1f);
    }

    /* forearms: from (bobbing) elbows to (cascade-fixed) hands */
    float handR[3], handL[3];
    _jgHandPos(handR, f, -1);
    _jgHandPos(handL, f, +1);
    _jgForearm(&spheres[_jgRForearm0], _jgElbowR, handR);
    _jgForearm(&spheres[_jgLForearm0], _jgElbowL, handL);
}

// ── Sampler integration: render-to-PSRAM + playback run loop ─────────────────
#define RT_SKIP 2
#define FRAME_W 320
#define FRAME_H 240
#define FRAME_PX (FRAME_W * FRAME_H)
static uint16_t psramFrames[JG_FRAMES * FRAME_PX] PSRAM;

static World g_worldCore1;
static volatile int  _jobFrame  = -1;
static volatile bool _core1Done = false;

static inline uint16_t briteToRGB565(const float *b) {
  float r=b[0],g=b[1],bl=b[2];
  if(r>1)r=1; if(r<0)r=0; if(g>1)g=1; if(g<0)g=0; if(bl>1)bl=1; if(bl<0)bl=0;
  return (((uint16_t)(r*31.0f))<<11)|(((uint16_t)(g*63.0f))<<5)|((uint16_t)(bl*31.0f));
}

static DVHSTX16 *_jgDisp = nullptr;

static inline void storePixel(uint16_t *frame,int i,int j,uint16_t c){
  for(int dy=0;dy<RT_SKIP;dy++){uint16_t*row=frame+(j+dy)*FRAME_W+i;
    for(int dx=0;dx<RT_SKIP;dx++)row[dx]=c;}
}

static void renderRows(const World*w,uint16_t*frame,int core,bool live){
  // live progress under double buffering: every few block-rows, blit the
  // in-progress PSRAM frame to the back buffer and swap — venetian reveal
  float brite[3];
  int rowsDone=0;
  for(int j=0;j<FRAME_H;j+=RT_SKIP){
    if(((j/RT_SKIP)&1)!=core)continue;
    for(int i=0;i<FRAME_W;i+=RT_SKIP){
      rtTracePixel(brite,&g_obs,w,i,j);
      uint16_t c=briteToRGB565(brite);
      storePixel(frame,i,j,c);
    }
    if(live){                       // live == core0 path only
      smpAudioPump();                // keep music fed during the render
      if(((++rowsDone)&7)==0){
        uint16_t*fb=(uint16_t*)_jgDisp->getBuffer();
        if(fb){memcpy(fb,frame,FRAME_PX*2);_jgDisp->swap();}
      }
    }
  }
}

static void _jgCore1Entry(){
  int last=-1;
  while(true){
    int f=_jobFrame;
    if(f!=last&&f>=0){
      renderRows(&g_worldCore1,&psramFrames[f*FRAME_PX],1,false);
      last=f;_core1Done=true;
    }
    tight_loop_contents();
  }
}

static const float _jgFps[] = {3,6,12,18,24,30};
void jugglerRun(DVHSTX16 &display){
  _jgDisp=&display;
  ledAll(255,255,255);          // white = rendering (also a liveness signal)
  sceneBuildJuggler();
  sceneSetupObserver(FRAME_W,FRAME_H);
  jugglerAnimInit();
  jugglerRigCapture(g_spheres);
  g_worldCore1=g_world;
  multicore_launch_core1(_jgCore1Entry);

  for(int f=0;f<JG_FRAMES;f++){
    jugglerSetFrame(g_spheres,f);
    _core1Done=false; _jobFrame=f;
    renderRows(&g_world,&psramFrames[f*FRAME_PX],0,true);
    while(!_core1Done){smpAudioPump();tight_loop_contents();}
    uint16_t*fb=(uint16_t*)display.getBuffer();
    if(fb){memcpy(fb,&psramFrames[f*FRAME_PX],FRAME_PX*2);display.swap();}
  }

  int fpsIdx=2; bool paused=false; int playFrame=0;
  uint32_t lastUs=time_us_32();
  auto jgFpsBar=[&](){int n=fpsIdx+1; if(n>5)n=5;
                      ledBar(n, 0,255,40);};   // green playback, N=fps step
  jgFpsBar();
  for(;;){
    smpAudioPump();
    if(smpBtn(0)&&fpsIdx>0){fpsIdx--;jgFpsBar();Serial.printf("fps: %.0f\n",_jgFps[fpsIdx]);}
    if(smpBtn(1)&&fpsIdx<5){fpsIdx++;jgFpsBar();Serial.printf("fps: %.0f\n",_jgFps[fpsIdx]);}
    if(smpBtn(2)){paused=!paused;
      if(paused)ledAll(255,30,30); else jgFpsBar();   // red pause / green play
      Serial.println(paused?"paused":"playing");}
    if(paused)continue;
    uint32_t frameUs=(uint32_t)(1000000.0f/_jgFps[fpsIdx]);
    uint32_t now=time_us_32();
    if(now-lastUs<frameUs)continue;
    lastUs=now;
    uint16_t*fb=(uint16_t*)display.getBuffer();
    if(fb){memcpy(fb,&psramFrames[playFrame*FRAME_PX],FRAME_PX*2);display.swap();}
    playFrame=(playFrame+1)%JG_FRAMES;
  }
}
