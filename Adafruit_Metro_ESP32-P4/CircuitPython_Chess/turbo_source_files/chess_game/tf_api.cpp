// SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
// SPDX-License-Identifier: GPL-3.0-or-later
// Chess engine C API (see tf_api.h; tf = the TeensyFish engine it wraps). This file is the whole engine in one translation
// unit: it includes the engine sources from TeensyChess/src/engine and the game
// rules from TeensyChess/game.cpp, so the Teensy sketch and this module share one
// copy of the code. (One TU also avoids a native-module linker problem seen with
// const tables split over several objects.)

// Engine build options, see the engine's misc.h / tt.cpp / search.cpp
#define SF_NOW_HOOK   tf_now_ms
#define SF_YIELD_HOOK tf_yield_hook
#define SF_EXTERNAL_TT 1
#define SF_NO_STATIC_CONSTRUCTORS 1
#define SF_ARENA_TABLES 1
// Speed options for the P4's in-order core (see PLAN.md, "Speed option 2"); none
// changes the search: node counts match the Teensy build
#define SF_INCREMENTAL_PSQ 1
// Pawn hash entries (64 bytes each, in the arena); -DSF_PAWN_HASH=0 turns it off
#ifndef SF_PAWN_HASH
    #define SF_PAWN_HASH 128
#elif SF_PAWN_HASH == 0
    #undef SF_PAWN_HASH
#endif
#ifndef NDEBUG
    #define NDEBUG 1
#endif

#include "tf_api.h"

#include "TeensyChess/src/engine/attacks.cpp"
#include "TeensyChess/src/engine/engine.cpp"
#include "TeensyChess/src/engine/evaluate.cpp"
#include "TeensyChess/src/engine/misc.cpp"
#include "TeensyChess/src/engine/movegen.cpp"
#include "TeensyChess/src/engine/movepick.cpp"
#include "TeensyChess/src/engine/position.cpp"
#include "TeensyChess/src/engine/search.cpp"
#include "TeensyChess/src/engine/tt.cpp"
#include "TeensyChess/game.cpp"

using namespace Stockfish;

// ---------------------------------------------------------------------------
// Clock and context switching (board: RISC-V cycle counter + asm; host: POSIX)

#if defined(__riscv) && !defined(TF_HOST)

extern "C" {
// Saved callee-saved registers: ra, sp, s0..s11 (see tf_ctx_rv32.S)
struct tf_ctx {
    uint32_t regs[14];
};
void tf_ctx_switch(tf_ctx* save, const tf_ctx* load);
}

static inline uint32_t cycles32() {
    uint32_t c;
    __asm__ volatile("rdcycle %0" : "=r"(c));
    return c;
}

#else  // host

    #include <time.h>
    #include <ucontext.h>

struct tf_ctx {
    ucontext_t uc;
};
static void tf_ctx_switch(tf_ctx* save, const tf_ctx* load) {
    swapcontext(&save->uc, &load->uc);
}
// Host "cycles" are microseconds; tf_init() is told 1000 per ms
static inline uint32_t cycles32() {
    timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return uint32_t(uint64_t(ts.tv_sec) * 1000000u + uint64_t(ts.tv_nsec) / 1000u);
}

#endif

namespace {

// Everything mutable lives in this one struct
struct State {
    bool     initialized;
    void*    arenaMem;
    // Clock: milliseconds since tf_init, extended from the 32-bit cycle counter.
    // Correct as long as it is read at least once per counter wrap (about 12 s at
    // 360 MHz); the search reads it every 512 nodes.
    uint32_t cyclesPerMs;
    uint32_t lastCycles;
    uint32_t remCycles;
    int64_t  ms;
    // Search coroutine
    tf_ctx          callerCtx;
    tf_ctx          engineCtx;
    bool            thinking;     // started and not yet collected
    bool            done;         // the coroutine has finished its search
    bool            stopRequested;
    uint32_t        sliceEnd;     // cycle count at which the current slice ends
    bool            sliceActive;
    uint8_t*        stackLo;
    uint32_t        stackBytes;
    uint32_t        stackPeak;
    int             level;
    Search::LimitsType limits;
    Search::Result  result;
};

// Zeroed raw storage, not "State S;": Search::Result has default member
// initializers, which would make S need a static constructor, and the native
// module runs none. Every field is assigned before it is used.
alignas(State) unsigned char stateStorage[sizeof(State)];
#define S (*reinterpret_cast<State*>(stateStorage))
// The game likewise (ChessGame has a member initializer); tf_init() resets it
alignas(ChessGame) unsigned char gameStorage[sizeof(ChessGame)];
#define game (*reinterpret_cast<ChessGame*>(gameStorage))

constexpr uint8_t STACK_FILL = 0xA5;

int64_t clock_ms() {
    uint32_t now   = cycles32();
    uint32_t delta = now - S.lastCycles;
    S.lastCycles   = now;
    S.ms += delta / S.cyclesPerMs;
    S.remCycles += delta % S.cyclesPerMs;
    if (S.remCycles >= S.cyclesPerMs)
    {
        S.remCycles -= S.cyclesPerMs;
        S.ms++;
    }
    return S.ms;
}

// TF_ERR_INIT before tf_init(), TF_ERR_BUSY while a search runs, else 0
int blocked() { return !S.initialized ? TF_ERR_INIT : S.thinking ? TF_ERR_BUSY : 0; }

int copy_str(const char* s, char* out, int len) {
    int n = 0;
    while (s[n])
        n++;
    if (n + 1 > len)
        return TF_ERR_ARG;
    for (int i = 0; i <= n; i++)
        out[i] = s[i];
    return TF_OK;
}

bool str_eq(const char* a, const char* b) {
    while (*a && *a == *b)
        a++, b++;
    return *a == *b;
}

// Finds the legal move with this UCI text in the game position
Move parse_uci(const char* uci) {
    char buf[8];
    for (const Move& m : MoveList<ALL>(game.pos()))
    {
        Engine::move_to_uci(m, buf);
        if (str_eq(buf, uci))
            return m;
    }
    return Move::none();
}

// The coroutine body: runs one search on its own stack, then parks
void engine_entry() {
    S.result = Engine::think(game.pos(), S.limits, S.level);
    S.done   = true;
    for (;;)
        tf_ctx_switch(&S.engineCtx, &S.callerCtx);
}

uint32_t measure_stack_peak() {
    uint32_t untouched = 0;
    while (untouched < S.stackBytes && S.stackLo[untouched] == STACK_FILL)
        untouched++;
    return S.stackBytes - untouched;
}

}  // namespace

#ifdef SF_PROFILE
SfProfData sf_prof_data;
extern "C" unsigned sf_prof_now(void) {
    #if defined(__riscv) && !defined(TF_HOST)
    return cycles32();
    #else
    timespec ts;  // host: nanoseconds
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return unsigned(uint64_t(ts.tv_sec) * 1000000000u + uint64_t(ts.tv_nsec));
    #endif
}
extern "C" unsigned sf_prof_instret(void) {
    #if defined(__riscv) && !defined(TF_HOST)
    unsigned i;
    __asm__ volatile("rdinstret %0" : "=r"(i));
    return i;
    #else
    return 0;
    #endif
}
// Cycles and instructions inside tf_think_step's switches to the search
static uint64_t profThinkCycles, profThinkInstret;
// Profile counters (uint64 each): PROF_NB call counts, PROF_NB cycle counts,
// PROF_NB instruction counts, then the search's total cycles and instructions.
// reset clears them. Returns PROF_NB.
extern "C" int tf_prof_read(uint64_t* out, int reset) {
    for (int i = 0; i < PROF_NB; i++)
    {
        out[i]               = sf_prof_data.calls[i];
        out[PROF_NB + i]     = sf_prof_data.cycles[i];
        out[2 * PROF_NB + i] = sf_prof_data.instret[i];
        if (reset)
            sf_prof_data.calls[i] = sf_prof_data.cycles[i] = sf_prof_data.instret[i] = 0;
    }
    out[3 * PROF_NB]     = profThinkCycles;
    out[3 * PROF_NB + 1] = profThinkInstret;
    if (reset)
        profThinkCycles = profThinkInstret = 0;
    return PROF_NB;
}
#endif

// ---------------------------------------------------------------------------
// Engine hooks

extern "C" long long tf_now_ms(void) { return clock_ms(); }

extern "C" bool tf_yield_hook(void) {
    if (S.sliceActive && int32_t(cycles32() - S.sliceEnd) >= 0)
        tf_ctx_switch(&S.engineCtx, &S.callerCtx);
    return S.stopRequested;
}

// ---------------------------------------------------------------------------
// API

extern "C" {

}  // extern "C"

// The large tables, carved from the start of the memory given to tf_init()
namespace {

struct Arena {
    uintptr_t next, end;
    template<typename T>
    bool take(T*& ptr) {
        uintptr_t p = (next + 63) & ~uintptr_t(63);
        if (p + sizeof(T) > end)
            return false;
        ptr  = reinterpret_cast<T*>(p);
        next = p + sizeof(T);
        return true;
    }
};

// Sets the table pointers (one set of pointers: the engine's or, for sizing, copies)
struct TablePtrs {
    decltype(Attacks::LineBB_ptr)              line;
    decltype(Attacks::BetweenBB_ptr)           between;
    decltype(cuckoo_ptr)                       cuckooKeys;
    decltype(cuckooMove_ptr)                   cuckooMoves;
    decltype(pawnCorrectionHistory_ptr)        pawnCorr;
    decltype(minorPieceCorrectionHistory_ptr)  minorCorr;
    decltype(Engine::worker_ptr)               searchWorker;
    decltype(gameStates_ptr)                   states;
#ifdef SF_PAWN_HASH
    decltype(Eval::pawnTable_ptr)              pawnEntries;
#endif
};

bool carve_tables(Arena& a, TablePtrs& p) {
    return a.take(p.line) && a.take(p.between) && a.take(p.cuckooKeys) && a.take(p.cuckooMoves)
        && a.take(p.pawnCorr) && a.take(p.minorCorr) && a.take(p.searchWorker) && a.take(p.states)
#ifdef SF_PAWN_HASH
        && a.take(p.pawnEntries)
#endif
        ;
}

bool carve_engine_tables(Arena& a) {
    TablePtrs p;
    if (!carve_tables(a, p))
        return false;
    Attacks::LineBB_ptr             = p.line;
    Attacks::BetweenBB_ptr          = p.between;
    cuckoo_ptr                      = p.cuckooKeys;
    cuckooMove_ptr                  = p.cuckooMoves;
    pawnCorrectionHistory_ptr       = p.pawnCorr;
    minorPieceCorrectionHistory_ptr = p.minorCorr;
    Engine::worker_ptr              = p.searchWorker;
    gameStates_ptr                  = p.states;
#ifdef SF_PAWN_HASH
    Eval::pawnTable_ptr = p.pawnEntries;
#endif
    return true;
}

}  // namespace

extern "C" {

uint32_t tf_tables_bytes(void) {
    // Worst-case alignment padding included
    Arena     a{0, ~uintptr_t(0) >> 1};
    TablePtrs p;
    carve_tables(a, p);
    return uint32_t(a.next) + 64 * 8;
}

int tf_init(void* mem, uint32_t mem_bytes, uint32_t cycles_per_ms, uint32_t tt_max_bytes) {
    if (S.thinking)
        return TF_ERR_BUSY;
#if defined(__riscv) && !defined(TF_HOST)
    if (cycles_per_ms == 0)
        return TF_ERR_ARG;
    S.cyclesPerMs = cycles_per_ms;
#else
    (void) cycles_per_ms;
    S.cyclesPerMs = 1000;
#endif
    S.lastCycles = cycles32();
    // Pointers must stay put once the engine is set up (the worker is constructed
    // in place), so the memory can only be given once per module load
    if (S.initialized && mem != S.arenaMem)
        return TF_ERR_ARG;
    Arena a{uintptr_t(mem), uintptr_t(mem) + mem_bytes};
    if (!carve_engine_tables(a))
        return TF_ERR_ARG;
    S.arenaMem    = mem;
    usize ttBytes = usize(a.end - a.next);
    if (tt_max_bytes && ttBytes > tt_max_bytes + 31)
        ttBytes = tt_max_bytes + 31;  // + alignment slack, so it gets all of tt_max_bytes
    u32 clusters = TT.set_memory(reinterpret_cast<void*>(a.next), ttBytes);
    if (!clusters)
        return TF_ERR_ARG;
    if (!S.initialized)
        Engine::init();
    else
        Engine::new_game();
    S.initialized = true;
    game.reset();
    return int(clusters);
}

void tf_new_game(void) {
    if (!blocked())
        Engine::new_game();
}

int tf_reset(void) {
    if (int e = blocked())
        return e;
    game.reset();
    return TF_OK;
}

int tf_set_fen(const char* fen) {
    if (int e = blocked())
        return e;
    char old[128];
    game.pos().fen(old);
    if (!game.setFen(fen))
    {
        game.setFen(old);
        return TF_ERR_ARG;
    }
    return TF_OK;
}

int tf_fen(char* out, int len) {
    if (int e = blocked())
        return e;
    char buf[128];
    game.pos().fen(buf);
    return copy_str(buf, out, len);
}

int tf_board(uint8_t* out64) {
    if (int e = blocked())
        return e;
    for (int s = 0; s < 64; s++)
        out64[s] = uint8_t(game.pos().piece_on(Square(s)));
    return TF_OK;
}

int tf_side_to_move(void) {
    if (int e = blocked())
        return e;
    return int(game.sideToMove());
}

int tf_ply(void) {
    if (int e = blocked())
        return e;
    return game.plyCount();
}

int tf_push(const char* uci) {
    if (int e = blocked())
        return e;
    Move m = parse_uci(uci);
    if (m == Move::none() || !game.makeMove(m))
        return TF_ERR_ILLEGAL;
    return TF_OK;
}

int tf_pop(void) {
    if (int e = blocked())
        return e;
    return game.undoMove() ? TF_OK : TF_ERR_ILLEGAL;
}

int tf_last_move(char* out, int len) {
    if (int e = blocked())
        return e;
    char buf[8];
    Engine::move_to_uci(game.lastMove(), buf);
    return copy_str(buf, out, len);
}

int tf_targets(int from, uint32_t* lo, uint32_t* hi) {
    if (int e = blocked())
        return e;
    if (from < 0 || from > 63)
        return TF_ERR_ARG;
    Bitboard b = game.targets(Square(from));
    *lo        = uint32_t(b);
    *hi        = uint32_t(b >> 32);
    return TF_OK;
}

int tf_find_move(int from, int to, char promo, char* out, int len) {
    if (int e = blocked())
        return e;
    if (from < 0 || from > 63 || to < 0 || to > 63)
        return TF_ERR_ARG;
    PieceType pt = promo == 'n' ? KNIGHT
                 : promo == 'b' ? BISHOP
                 : promo == 'r' ? ROOK
                 : promo == 'q' ? QUEEN
                                : NO_PIECE_TYPE;
    bool isPromotion;
    Move m = game.findMove(Square(from), Square(to), pt, isPromotion);
    if (m == Move::none())
        return isPromotion && pt == NO_PIECE_TYPE ? 1 : TF_ERR_ILLEGAL;
    char buf[8];
    Engine::move_to_uci(m, buf);
    return copy_str(buf, out, len);
}

int tf_san(const char* uci, char* out, int len) {
    if (int e = blocked())
        return e;
    Move m = parse_uci(uci);
    if (m == Move::none())
        return TF_ERR_ILLEGAL;
    char buf[16];
    game.san(m, buf);
    return copy_str(buf, out, len);
}

int tf_result(void) {
    if (int e = blocked())
        return e;
    return int(game.result());
}

int tf_material(int color) {
    if (int e = blocked())
        return e;
    if (color != 0 && color != 1)
        return TF_ERR_ARG;
    return game.materialPoints(Color(color));
}

int tf_check_square(void) {
    if (int e = blocked())
        return e;
    const Position& pos = game.pos();
    return pos.checkers() ? int(pos.square<KING>(pos.side_to_move())) : -1;
}

uint32_t tf_perft(int depth) {
    if (blocked() || depth < 1)
        return 0;
    return uint32_t(Engine::perft(game.pos(), Depth(depth)));
}

int tf_think_start(void* stack_mem, uint32_t stack_bytes, int level, int movetime_ms, int depth,
                   uint32_t nodes) {
    if (int e = blocked())
        return e;
    if (stack_bytes < 16 * 1024 || level < 0 || level > 20 || movetime_ms < 0 || depth < 0)
        return TF_ERR_ARG;

    S.stackLo    = static_cast<uint8_t*>(stack_mem);
    S.stackBytes = stack_bytes;
    for (uint32_t i = 0; i < stack_bytes; i++)
        S.stackLo[i] = STACK_FILL;

    S.limits          = Search::LimitsType{};
    S.limits.movetime = movetime_ms;
    S.limits.depth    = depth;
    S.limits.nodes    = nodes;
    S.level           = level;
    S.done            = false;
    S.stopRequested   = false;
    S.sliceActive     = false;
    S.thinking        = true;

#if defined(__riscv) && !defined(TF_HOST)
    // First switch "returns" into engine_entry on the new stack
    uintptr_t top = (uintptr_t(stack_mem) + stack_bytes) & ~uintptr_t(15);
    S.engineCtx   = tf_ctx{};
    S.engineCtx.regs[0] = uint32_t(uintptr_t(&engine_entry));
    S.engineCtx.regs[1] = uint32_t(top);
#else
    getcontext(&S.engineCtx.uc);
    S.engineCtx.uc.uc_stack.ss_sp   = stack_mem;
    S.engineCtx.uc.uc_stack.ss_size = stack_bytes;
    S.engineCtx.uc.uc_link          = nullptr;
    makecontext(&S.engineCtx.uc, engine_entry, 0);
#endif
    return TF_OK;
}

int tf_think_step(int budget_ms) {
    if (!S.thinking)
        return TF_ERR_BUSY;
    if (S.done)
        return 1;
    // The slice end must stay within half the 32-bit counter range (about 6 s at
    // 360 MHz); a longer budget just returns 0 sooner and is called again.
    const uint32_t maxMs = 0x7fffffffu / S.cyclesPerMs;
    if (budget_ms < 1)
        budget_ms = 1;
    if (uint32_t(budget_ms) > maxMs)
        budget_ms = int(maxMs);
    S.sliceEnd    = cycles32() + uint32_t(budget_ms) * S.cyclesPerMs;
    S.sliceActive = true;
#ifdef SF_PROFILE
    uint32_t pc0 = sf_prof_now(), pi0 = sf_prof_instret();
#endif
    tf_ctx_switch(&S.callerCtx, &S.engineCtx);
#ifdef SF_PROFILE
    profThinkInstret += sf_prof_instret() - pi0;
    profThinkCycles += sf_prof_now() - pc0;
#endif
    S.sliceActive = false;
    clock_ms();  // keep the clock extension current between slices
    if (S.done)
    {
        S.stackPeak = measure_stack_peak();
        return 1;
    }
    return 0;
}

void tf_think_stop(void) { S.stopRequested = true; }

int tf_thinking(void) { return S.thinking; }

int tf_think_result(tf_result_t* r) {
    if (!S.thinking || !S.done)
        return TF_ERR_BUSY;
    S.thinking = false;
    Engine::move_to_uci(S.result.best, r->best);
    Engine::move_to_uci(S.result.ponder, r->ponder);
    r->score   = S.result.score;
    r->depth   = S.result.depth;
    r->nodes   = uint32_t(S.result.nodes);
    r->time_ms = uint32_t(S.result.time);
    return TF_OK;
}

uint32_t tf_stack_peak(void) { return S.stackPeak; }

#ifdef TF_DEBUG_STEPS
// Bring-up aid: runs one stage of tf_init() at a time (build with make DEBUG=1)
static volatile uint32_t debugWord;
int tf_debug_step(int step, void* mem, uint32_t mem_bytes) {
    switch (step)
    {
    case 0 : return int(cycles32() & 0x7fffffff);
    case 1 : debugWord = 0x12345678; return debugWord == 0x12345678;
    case 2 : S.cyclesPerMs = 360000; return int(S.cyclesPerMs);
    case 3 : {
        Arena a{uintptr_t(mem), uintptr_t(mem) + mem_bytes};
        return carve_engine_tables(a) ? int(a.next - uintptr_t(mem)) : -1;
    }
    case 4 : {
        uintptr_t start = uintptr_t(mem) + tf_tables_bytes();
        return int(TT.set_memory(reinterpret_cast<void*>(start), uintptr_t(mem) + mem_bytes - start));
    }
    case 5 : Attacks::init(); return 5;
    case 6 : Position::init(); return 6;
    case 7 : Eval::init(); return 7;
    case 8 : Search::init(); return 8;
    case 9 : new (Engine::worker_ptr) Search::Worker(); return 9;
    case 10 : Engine::new_game(); return 10;
    case 11 : game.reset(); return 11;
    case 12 : return int(uintptr_t(&debugWord));
    case 13 : return int(uintptr_t(&tf_debug_step));
    case 14 : return int(uintptr_t(&S));
    case 15 : return int(uintptr_t(&TT));
    case 17 : {  // ALU: 1M xorshift32 steps; returns cycles
        uint32_t x = 2463534242u, t0 = cycles32();
        for (int i = 0; i < 1000000; i++)
        {
            x ^= x << 13;
            x ^= x >> 17;
            x ^= x << 5;
        }
        debugWord = x;
        return int(cycles32() - t0);
    }
    case 18 :    // 256K dependent random reads over mem (power-of-two bytes); returns cycles
    case 19 : {  // the same over this module's code block (internal L2MEM, ~64 KB)
        const uint32_t* base = step == 18 ? static_cast<const uint32_t*>(mem)
                                          : reinterpret_cast<const uint32_t*>(&tf_debug_step);
        uint32_t        mask = (step == 18 ? mem_bytes : 65536) / 4 - 1;
        uint32_t        x = 2463534242u, acc = 0, t0 = cycles32();
        for (int i = 0; i < 262144; i++)
        {
            x ^= x << 13;
            x ^= x >> 17;
            x ^= x << 5;
            acc += base[(x ^ acc) & mask];
        }
        debugWord = acc;
        return int(cycles32() - t0);
    }
    case 20 :    // 64K slider/primitive calls on pseudo-random occupancies; returns cycles
    case 21 :    // 20 bishop, 21 rook, 22 queen, 23 popcount, 24 pop_lsb (all bits), 25 loop only
    case 22 :
    case 23 :
    case 24 :
    case 25 : {
        u64      x = 0x9E3779B97F4A7C15ull, acc = 0;
        uint32_t t0 = cycles32();
        for (int i = 0; i < 65536; i++)
        {
            x ^= x << 13;
            x ^= x >> 7;
            x ^= x << 17;
            Bitboard occ = x & (x >> 11) & (x >> 23);  // ~1/8 density
            Square   sq  = Square(i & 63);
            switch (step)
            {
            case 20 : acc ^= attacks_bb(BISHOP, sq, occ); break;
            case 21 : acc ^= attacks_bb(ROOK, sq, occ); break;
            case 22 : acc ^= attacks_bb(QUEEN, sq, occ); break;
            case 23 : acc += popcount(occ); break;
            case 24 :
                for (Bitboard b = occ; b;)
                    acc += pop_lsb(b);
                break;
            default : acc ^= occ;
            }
        }
        debugWord = uint32_t(acc ^ (acc >> 32));
        return int(cycles32() - t0);
    }
    case 26 : {  // instructions retired (instret CSR) over the step-17 ALU loop
    #if defined(__riscv) && !defined(TF_HOST)
        uint32_t i0, i1, x = 2463534242u;
        __asm__ volatile("rdinstret %0" : "=r"(i0));
        for (int i = 0; i < 1000000; i++)
        {
            x ^= x << 13;
            x ^= x >> 17;
            x ^= x << 5;
        }
        __asm__ volatile("rdinstret %0" : "=r"(i1));
        debugWord = x;
        return int(i1 - i0);
    #else
        return -1;
    #endif
    }
    case 16 : {  // copy mem_bytes bytes from the address in the first word of mem into mem
        const uint32_t* src = reinterpret_cast<const uint32_t*>(*static_cast<uint32_t*>(mem));
        uint32_t*       dst = static_cast<uint32_t*>(mem);
        for (uint32_t i = 0; i < mem_bytes / 4; i++)
            dst[i] = src[i];
        return 16;
    }
    }
    return -1;
}
#endif

}  // extern "C"
