/* Owner-local PS2 font layout. No allocation, text mutation, or renderer calls.
 * Addresses are EE RAM offsets so this exact kernel also runs in host tests. */
typedef unsigned int u32;
typedef unsigned char u8;
typedef struct {
    u32 fonts[4], count, flags;
    float left, top, width, height, space_ratio;
    float factor;
    u32 rows;
} Layout;
typedef struct { u32 field, node, steps; } Cursor;
typedef struct {
    u32 node, kind;
    float advance, width, height, pitch;
} Token;

#define INLINE static __attribute__((always_inline)) inline
#define LIMIT 1024u
#define END 0u
#define GLYPH 1u
#define SPACE 2u
#define BREAK 3u
#define BAD 4u

INLINE u32 word(u8 *ram, u32 p) { return *(u32 *)(ram + p); }
INLINE float real(u8 *ram, u32 p) { return *(float *)(ram + p); }
INLINE int address(u32 p, u32 size) {
    return p >= 0x1000u && p <= 0x02000000u - size && !(p & 3u);
}
INLINE int positive(float n) { return n > 0.f && n < 65536.f; }
INLINE float maximum(float a, float b) { return a > b ? a : b; }

/* Field boundaries are hard paragraph breaks; generated Details newlines can
 * be soft. The visited-node bound also rejects cycles before any writes. */
INLINE Token next(u8 *ram, Layout *c, Cursor *it, float factor) {
    Token t = {0, END, 0.f, 0.f, 0.f, 0.f};
    while (it->field < c->count) {
        u32 f = c->fonts[it->field];
        if (!address(f, 0x254u)) { t.kind = BAD; return t; }
        if (!it->node) {
            ++it->field;
            if (it->field == c->count) return t;
            f = c->fonts[it->field];
            if (!address(f, 0x254u)) { t.kind = BAD; return t; }
            it->node = word(ram, f + 4);
            t.kind = BREAK;
            return t;
        }
        u32 n = it->node;
        if (++it->steps > LIMIT || !address(n, 0x130u)) {
            t.kind = BAD; return t;
        }
        it->node = word(ram, n + 0x120);
        u32 code = word(ram, n), d = word(ram, f + 0x10);
        if (!address(d, 8)) { t.kind = BAD; return t; }
        float sx = real(ram, f + 0x48), sy = real(ram, f + 0x4c);
        float w = ram[d + 4] * sx, h = ram[d + 5] * sy;
        float advance = w + real(ram, f + 0x28);
        float pitch = maximum(h, h + real(ram, f + 0x2c));
        if (!positive(w) || !positive(h) || !positive(advance) ||
            !positive(pitch)) { t.kind = BAD; return t; }
        t.node = n;
        t.advance = advance * factor;
        t.width = maximum(w * factor - 1.f, 0.f);
        t.height = maximum(h * factor - 1.f, 0.f);
        t.pitch = pitch * factor;
        if (code < 0xffffff00u) { t.kind = GLYPH; return t; }
        if (code == 0xffffff0au || code == 0xffffff0bu) {
            t.kind = SPACE;
            t.advance = w * c->space_ratio * factor;
            if (code == 0xffffff0au) t.advance *= .5f;
            return t;
        }
        if (code == 0xffffff0eu) {
            t.kind = (c->flags & 1u) ? SPACE : BREAK;
            t.advance = w * c->space_ratio * factor;
            return t;
        }
        if (code == 0xffffff0fu) { it->node = 0; continue; }
        if (code == 0xffffff10u) continue; /* native zero-width marker */
        /* Unknown control operands must not be mistaken for visible glyphs. */
        t.kind = BAD;
        return t;
    }
    return t;
}

INLINE void vertices(u8 *ram, Token t, float x, float y) {
    *(float *)(ram + t.node + 0x10) = x;
    *(float *)(ram + t.node + 0x14) = y;
    *(float *)(ram + t.node + 0x50) = x + t.width;
    *(float *)(ram + t.node + 0x54) = y;
    *(float *)(ram + t.node + 0x90) = x;
    *(float *)(ram + t.node + 0x94) = y + t.height;
    *(float *)(ram + t.node + 0xd0) = x + t.width;
    *(float *)(ram + t.node + 0xd4) = y + t.height;
}

/* Each pass is bounded and read-only unless emit is set after a successful
 * measurement. Lookahead visits each word once, not once per character. */
INLINE int pass(u8 *ram, Layout *c, float factor, int emit, u32 *rows) {
    Cursor it = {0, word(ram, c->fonts[0] + 4), 0};
    float x = 0.f, y = 0.f, pitch = 0.f, pending = 0.f;
    int line = 0, boundary = 1;
    *rows = 0;
    for (;;) {
        Cursor before = it;
        Token t = next(ram, c, &it, factor);
        if (t.kind == BAD) return -1;
        if (t.kind == END) return 1;
        if (t.kind == BREAK) {
            if (line) { y += pitch; x = 0.f; pitch = 0.f; line = 0; }
            pending = 0.f; boundary = 1;
            continue;
        }
        if (t.kind == SPACE) {
            if (line) pending += t.advance;
            boundary = 1;
            continue;
        }
        if (boundary) {
            Cursor look = before;
            float advance = 0.f, extent = 0.f;
            for (;;) {
                Token part = next(ram, c, &look, factor);
                if (part.kind == BAD) return -1;
                if (part.kind != GLYPH) break;
                extent = maximum(extent, advance + part.width);
                advance += part.advance;
            }
            if (line && x + pending + extent > c->width) {
                y += pitch; x = 0.f; pitch = 0.f; line = 0;
                pending = 0.f;
            }
        }
        x += pending; pending = 0.f; boundary = 0;
        /* A single word wider than a row uses glyph boundaries, never elision. */
        if (line && x + t.width > c->width) {
            y += pitch; x = 0.f; pitch = 0.f; line = 0;
        }
        if (x + t.width > c->width || y + t.height > c->height) return 0;
        if (!line) { ++*rows; line = 1; }
        if (emit) vertices(ram, t, c->left + x, c->top + y);
        pitch = maximum(pitch, t.pitch);
        x += t.advance;
    }
}

/* Return 1 for a complete layout, 0 for invalid input. Private scales and
 * source/control nodes are never changed, so later rebuilds cannot compound
 * the exceptional vertical fit factor. */
int r67_description_wrap(u8 *ram, Layout *c) {
    u32 rows = 0;
    if (!c->count || c->count > 4 || !positive(c->width) ||
        !positive(c->height) || !positive(c->space_ratio)) return 0;
    for (u32 i = 0; i < c->count; ++i)
        if (!address(c->fonts[i], 0x254)) return 0;
    float fit = 1.f;
    int result = pass(ram, c, fit, 0, &rows);
    if (result < 0) return 0;
    if (!result) {
        float high = 1.f;
        for (u32 i = 0; i < 16 && !result; ++i) {
            fit *= .5f;
            result = pass(ram, c, fit, 0, &rows);
            if (result < 0) return 0;
        }
        if (!result) return 0;
        for (u32 i = 0; i < 16; ++i) {
            float mid = (fit + high) * .5f;
            result = pass(ram, c, mid, 0, &rows);
            if (result < 0) return 0;
            if (result) fit = mid; else high = mid;
        }
    }
    if (pass(ram, c, fit, 0, &rows) != 1) return 0;
    pass(ram, c, fit, 1, &rows);
    c->factor = fit;
    c->rows = rows;
    return 1;
}
