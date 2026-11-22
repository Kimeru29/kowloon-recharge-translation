/* Freestanding MIPS II helpers for the eight owner-local KSF call bridges.
 * The bridge restores the EE caller's 128-bit registers around these o32 calls.
 */
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef unsigned long usize;

enum { MAX_BYTES = 100, MAX_LOGICAL = 56, MAX_SLOTS = 4, NAME_BYTES = 32 };
enum { STOCK, ENGLISH, PRISTINE, REJECTED_NAME };
enum { SPACE = 0xff0a, WIDE_SPACE = 0xff0b, LINE_BREAK = 0xff0e, END = 0xff0f };
enum { ROWS_OFFSET = 0x298, ROW_STRIDE = 108, FLAG_OFFSET = 0x90c };
enum { STYLE0 = 0x5d77d0, STYLE2 = 0x5d7830 };

struct File {
    u8 request[20];
    u32 size;
};

struct Row {
    u8 installed[30];
    u8 japanese[30];
    u8 english[];
};

struct Record {
    u32 offset;
    u16 file;
    u16 ordinal;
    u8 flags[MAX_SLOTS];
    u8 header[0x26];
    const struct Row *rows[MAX_SLOTS];
};

struct Display {
    u8 source[MAX_BYTES + 1];
    u8 wrapped[MAX_BYTES + 1];
};

struct Context {
    const struct Record *record;
    const u8 *state;
    const u8 *file;
    u32 mode;
    u32 copied;
    u32 cells;
    u32 failed;
    u8 family[NAME_BYTES];
    u8 given[NAME_BYTES];
    struct Display display[MAX_SLOTS];
    u32 generation;
};

struct Animator {
    u32 rate;
    u32 time;
    const u8 *font;
    u8 state;
    u8 padding1;
    u16 current;
    u16 count;
    u8 delay;
    u8 padding2;
    u32 child_mode;
    u32 children[MAX_LOGICAL];
    u32 second[MAX_LOGICAL];
    u8 physical[MAX_LOGICAL];
    u32 mode;
    u32 generation;
};

_Static_assert(sizeof(struct File) == 24, "native file table layout");
_Static_assert(sizeof(struct Record) == 68, "native record table layout");
_Static_assert(sizeof(struct Context) == 0x388, "owned context layout");
_Static_assert(sizeof(struct Animator) == 0x218, "native animation allocation");
_Static_assert(__builtin_offsetof(struct Animator, children) == 0x18, "native child block");
_Static_assert(__builtin_offsetof(struct Animator, second) == 0xf8, "second child block");
_Static_assert(__builtin_offsetof(struct Animator, physical) == 0x1d8, "physical node map");

extern const struct File choice_files[];
extern const struct Record choice_records[];
extern struct Context choice_context;
extern const u8 choice_cp932[8192];

#define READ_U32(p, off) (*(const u32 *)((const u8 *)(p) + (off)))
#define READ_U16(p, off) (*(const u16 *)((const u8 *)(p) + (off)))

static u32 size_bounded(const u8 *text, u32 capacity)
{
    for (u32 i = 0; i < capacity; ++i)
        if (!text[i])
            return i;
    return capacity;
}

static int matches(const u8 *a, const u8 *b, u32 count)
{
    for (u32 i = 0; i < count; ++i)
        if (a[i] != b[i])
            return 0;
    return 1;
}

static void copy(u8 *out, const u8 *in, u32 count)
{
    for (u32 i = 0; i < count; ++i)
        out[i] = in[i];
}

static u32 code(u8 lead, u8 trail)
{
    return ((u32)lead << 8) | trail;
}

static int double_byte(u8 lead, u8 trail)
{
    return ((lead >= 0x81 && lead <= 0x9f) || (lead >= 0xe0 && lead <= 0xfc))
        && trail >= 0x40 && trail <= 0xfc && trail != 0x7f;
}

static const u16 *font_table(u32 style)
{
    return ((const u16 *const *)0x5d7e20)[style];
}

static u32 glyph_index(u32 style, u32 unit)
{
    const u16 *table = font_table(style);
    u32 low = 0;
    u32 high = table[0];
    while (low < high) {
        u32 middle = low + (high - low) / 2;
        u32 glyph = table[middle + 1];
        if (glyph < unit)
            low = middle + 1;
        else if (glyph > unit)
            high = middle;
        else
            return middle;
    }
    return 0xffff;
}

static u32 english_token(const u8 *text, u32 remaining, u32 *token)
{
    if (text[0] == ' ' || text[0] == '"') {
        *token = text[0] == ' ' ? SPACE : glyph_index(0, 0x8168);
        return 1;
    }
    if (remaining < 2 || !double_byte(text[0], text[1]))
        return 0;
    u32 unit = code(text[0], text[1]);
    *token = unit == 0x8140 ? WIDE_SPACE : glyph_index(0, unit);
    return *token == 0xffff ? 0 : 2;
}

u32 choice_layout(const u8 *text, u8 *out, u32 *max_width)
{
    u8 offsets[MAX_LOGICAL + 1];
    u16 widths[MAX_LOGICAL + 1];
    u8 spaces[MAX_LOGICAL];
    u32 bytes = size_bounded(text, MAX_BYTES + 1);
    if (bytes > MAX_BYTES)
        return 0;
    u32 count = 0;
    offsets[0] = 0;
    widths[0] = 0;
    for (u32 pos = 0; pos < bytes;) {
        if (count == MAX_LOGICAL)
            return 0;
        u32 token;
        u32 n = english_token(text + pos, bytes - pos, &token);
        if (!n)
            return 0;
        spaces[count] = token == SPACE;
        widths[count + 1] = widths[count] + (token == SPACE ? 8 : 16);
        pos += n;
        offsets[++count] = pos;
    }
    if (!count)
        return 0;
    u32 limit = 448;
    u32 width = widths[count];
    if (width <= limit) {
        copy(out, text, bytes + 1);
        *max_width = width;
        return count;
    }
    if (bytes == MAX_BYTES)
        return 0;
    for (u32 split = count - 1; split > 0; --split) {
        u32 left = widths[split], right = width - left;
        if ((spaces[split - 1] || spaces[split]) && left <= limit && right <= limit) {
            u32 offset = offsets[split];
            copy(out, text, offset);
            out[offset] = '\n';
            copy(out + offset + 1, text + offset, bytes - offset + 1);
            *max_width = left > right ? left : right;
            return count;
        }
    }
    return 0;
}

static int name_value(const u8 *raw, u8 *out)
{
    u32 size = size_bounded(raw, NAME_BYTES);
    if (size >= NAME_BYTES || size % 2)
        return 0;
    for (u32 i = 0; i < size; i += 2) {
        u32 unit = code(raw[i], raw[i + 1]);
        if (!double_byte(raw[i], raw[i + 1])
            || !(choice_cp932[unit / 8] & (1u << (unit % 8))))
            return 0;
    }
    copy(out, raw, size + 1);
    return 1;
}

static int name_coverage(const u8 *text, u32 style)
{
    for (u32 i = 0; text[i]; i += 2) {
        u32 unit = code(text[i], text[i + 1]);
        /* 0x1952f0 reserves the full-width @ pair as an escape. */
        if (unit == 0x8197 || (unit != 0x8140 && glyph_index(style, unit) == 0xffff))
            return 0;
    }
    return 1;
}

static int expand(const u8 *template, u8 *out, int japanese, int use_names)
{
    u32 pos = 0;
    for (u32 i = 0; template[i];) {
        const u8 *input = template + i;
        const u8 *name = 0;
        u32 consume = 1;
        if (japanese) {
            if (double_byte(input[0], input[1]))
                consume = 2;
            else if (use_names && input[0] == 'p' && (input[1] == 'm' || input[1] == 'n')) {
                name = input[1] == 'm' ? choice_context.family : choice_context.given;
                consume = 2;
            }
        } else if (input[0] == 1 || input[0] == 2) {
            name = input[0] == 1 ? choice_context.family : choice_context.given;
        }
        const u8 *source = name ? name : input;
        u32 length = name ? size_bounded(name, NAME_BYTES) : consume;
        if (length > MAX_BYTES - pos)
            return 0;
        copy(out + pos, source, length);
        pos += length;
        i += consume;
    }
    out[pos] = 0;
    return 1;
}

static int compare_request(const u8 *a, const u8 *b)
{
    for (u32 i = 0; i < 20; ++i) {
        int difference = (int)a[i] - b[i];
        if (difference || !a[i])
            return difference;
    }
    return 1;
}

static u32 find_file(const u8 *request)
{
    u32 low = 0, high = CHOICE_FILE_COUNT;
    while (low < high) {
        u32 middle = low + (high - low) / 2;
        int order = compare_request(request, choice_files[middle].request);
        if (order < 0)
            high = middle;
        else if (order > 0)
            low = middle + 1;
        else
            return middle;
    }
    return CHOICE_FILE_COUNT;
}

static const struct Record *find_record(u32 file, u32 ordinal)
{
    u32 low = 0, high = CHOICE_RECORD_COUNT;
    u32 key = (file << 16) | ordinal;
    while (low < high) {
        u32 middle = low + (high - low) / 2;
        const struct Record *record = choice_records + middle;
        u32 other = ((u32)record->file << 16) | record->ordinal;
        if (key < other)
            high = middle;
        else if (key > other)
            low = middle + 1;
        else
            return record;
    }
    return 0;
}

static int ram_range(const void *pointer, u32 size)
{
    usize n = (usize)pointer;
    return n >= 0x100000 && n <= 0x2000000 - size;
}

static const struct Record *guard(const u8 *state, const u8 *first)
{
    u32 file = find_file(state + 0x3160);
    if (file == CHOICE_FILE_COUNT)
        return 0;
    u32 size = choice_files[file].size;
    const u8 *base = (const u8 *)READ_U32(state, 0x3158);
    if (!ram_range(base, size))
        return 0;
    u32 ordinal = READ_U16(state, 0x3150);
    const struct Record *record = find_record(file, ordinal);
    if (!record || ordinal >= READ_U16(base, 0) || record->offset + FLAG_OFFSET + 4 > size
        || !matches(base + record->offset, record->header, 0x26)
        || first != base + record->offset + FLAG_OFFSET + 1)
        return 0;
    u32 offset = record->offset + FLAG_OFFSET;
    for (u32 slot = 0; slot < MAX_SLOTS; ++slot) {
        if (offset >= size || base[offset++] != record->flags[slot])
            return 0;
        const struct Row *row = record->rows[slot];
        if ((record->flags[slot] == 1) != (row != 0))
            return 0;
        if (row) {
            if (offset + 30 > size || !matches(base + offset, row->installed, 30))
                return 0;
            offset += 30;
        }
    }
    return record;
}

static u32 prepare(const struct Record *record)
{
    int dynamic = 0;
    for (u32 slot = 0; slot < MAX_SLOTS && record->rows[slot]; ++slot) {
        const u8 *text = record->rows[slot]->english;
        for (u32 i = 0; text[i]; ++i)
            if (text[i] == 1 || text[i] == 2)
                dynamic = 1;
    }
    choice_context.family[0] = 0;
    choice_context.given[0] = 0;
    int names_valid = 1;
    if (dynamic) {
        int family_valid = name_value((const u8 *)0x7c4bc0, choice_context.family);
        int given_valid = name_value((const u8 *)0x7c4ba0, choice_context.given);
        names_valid = family_valid && given_valid;
    }
    u32 mode = names_valid ? ENGLISH : REJECTED_NAME;
    if (dynamic && names_valid
        && (!name_coverage(choice_context.family, 0) || !name_coverage(choice_context.given, 0)))
        mode = PRISTINE;
    u32 max_width = 0;
    if (mode == ENGLISH) {
        for (u32 i = 0; i < MAX_SLOTS && record->rows[i]; ++i) {
            struct Display *row = choice_context.display + i;
            u32 width;
            if (!expand(record->rows[i]->english, row->source, 0, 1)
                || !choice_layout(row->source, row->wrapped, &width)) {
                mode = PRISTINE;
                break;
            }
            if (max_width < width)
                max_width = width;
        }
    }
    if (mode != ENGLISH) {
        int use_names = mode == PRISTINE && name_coverage(choice_context.family, 2)
            && name_coverage(choice_context.given, 2);
        if (!use_names) {
            choice_context.family[0] = 0;
            choice_context.given[0] = 0;
        }
        for (u32 i = 0; i < MAX_SLOTS && record->rows[i]; ++i) {
            struct Display *row = choice_context.display + i;
            if (!expand(record->rows[i]->japanese, row->source, 1, use_names))
                return STOCK;
            copy(row->wrapped, row->source, size_bounded(row->source, MAX_BYTES + 1) + 1);
        }
    }
    choice_context.cells = (max_width + 25) / 26;
    return mode;
}

static int same_owner(const u8 *state)
{
    const struct Record *record = choice_context.record;
    if (!record || state != choice_context.state || READ_U16(state, 0x3150) != record->ordinal
        || (const u8 *)READ_U32(state, 0x3158) != choice_context.file || !state[0x32ea])
        return 0;
    return compare_request(state + 0x3160, choice_files[record->file].request) == 0;
}

const u8 *choice_copy_source(const u8 *state, const u8 *source, u32 slot)
{
    if (!slot) {
        choice_context.record = 0;
        ++choice_context.generation;
        choice_context.mode = STOCK;
        choice_context.copied = 0;
        choice_context.failed = 0;
        const struct Record *record = guard(state, source);
        if (record && state[0x32ea]) {
            choice_context.state = state;
            choice_context.file = (const u8 *)READ_U32(state, 0x3158);
            choice_context.mode = prepare(record);
            if (choice_context.mode)
                choice_context.record = record;
        }
    }
    if (!same_owner(state) || slot >= MAX_SLOTS || slot != choice_context.copied)
        return source;
    const struct Record *record = choice_context.record;
    const struct Row *row = record->rows[slot];
    if (!row || source != choice_context.file + record->offset + FLAG_OFFSET + 1 + slot * 31)
        return source;
    ++choice_context.copied;
    return choice_context.display[slot].source;
}

u32 choice_initial_preprocess(const u8 *state, u32 slot, const u8 *source)
{
    if (!same_owner(state) || slot >= choice_context.copied)
        return 0;
    const u8 *owned = choice_context.display[slot].source;
    return (u32)matches(source, owned, size_bounded(owned, MAX_BYTES + 1) + 1);
}

u32 choice_mode(const u8 *state)
{
    if (!same_owner(state) || choice_context.copied != state[0x32e7])
        return STOCK;
    const struct Record *record = choice_context.record;
    for (u32 slot = 0; slot < MAX_SLOTS; ++slot) {
        if ((slot < choice_context.copied) != (record->rows[slot] != 0))
            return STOCK;
        if (slot < choice_context.copied) {
            const u8 *source = choice_context.display[slot].source;
            if (!matches(state + ROWS_OFFSET + slot * ROW_STRIDE, source,
                         size_bounded(source, MAX_BYTES + 1) + 1))
                return STOCK;
        }
    }
    return choice_context.mode;
}

u32 choice_view_mode(const u8 *state, u32 slot)
{
    return slot < choice_context.copied ? choice_mode(state) : STOCK;
}

const u8 *choice_set_source(const u8 *state, u32 slot, const u8 *source)
{
    if (!choice_view_mode(state, slot))
        return 0;
    const struct Display *row = choice_context.display + slot;
    return matches(source, row->source, size_bounded(row->source, MAX_BYTES + 1) + 1)
        ? row->wrapped : 0;
}

u32 choice_cursor_cells(const u8 *state)
{
    return choice_mode(state) == ENGLISH ? choice_context.cells : 0;
}

u32 choice_moving_row(const u8 *state)
{
    u32 slot = state[0x32e8];
    if (choice_mode(state) != ENGLISH)
        return 0;
    return slot < choice_context.copied ? slot + 1 : MAX_SLOTS + 1;
}

static int font_tag(const u8 *font, u32 physical)
{
    const u8 *source = font + 0x51 + physical * 2;
    u32 tag = 0;
    for (u32 family = 0; family < 2; ++family) {
        const u8 *name = family ? choice_context.given : choice_context.family;
        u32 n = size_bounded(name, NAME_BYTES) / 2;
        for (u32 glyph = 0; glyph < n; ++glyph, ++tag)
            if (matches(source, name + glyph * 2, 2))
                return (int)tag;
    }
    return -1;
}

int choice_bounded_name_tag(const u8 *task, u32 physical)
{
    return font_tag((const u8 *)READ_U32(task, 0x3c), physical);
}

static int node_address(const u8 *node)
{
    return ((usize)node & 3) == 0 && ram_range(node, 0x130);
}

u32 choice_inspect_nodes(struct Animator *animator)
{
    const u8 *task = animator->font;
    u32 mode = animator->mode;
    if (!ram_range(task, 0x40) || !mode)
        return 0;
    const u8 *font = (const u8 *)READ_U32(task, 0x3c);
    if (!ram_range(font, 0x254))
        return 0;
    u32 descriptor = READ_U32(font, 0x10);
    u32 style = mode == ENGLISH ? 0 : 2;
    if (READ_U32(font, 0xc) != style || descriptor != (style == 0 ? STYLE0 : STYLE2)
        || font[0x24] != 0)
        return 0;
    if (style == 0 && READ_U16((const u8 *)descriptor, 4) != 0x1210)
        return 0;
    u32 count = READ_U16(font, 0x250);
    if (!count || count > MAX_LOGICAL + (style == 0))
        return 0;
    const u8 *node = (const u8 *)READ_U32(font, 4);
    const u32 *glyphs = (const u32 *)READ_U32((const u8 *)descriptor, 0x2c);
    const u8 *source = font + 0x51;
    u32 bytes = size_bounded(source, MAX_BYTES + 1);
    if (!bytes || bytes > MAX_BYTES)
        return 0;
    const u8 *previous = 0;
    u32 pos = 0, logical = 0, breaks = 0;
    for (u32 physical = 0; physical < count; ++physical) {
        if (!node_address(node) || READ_U32(node, 0x124) != (u32)previous)
            return 0;
        u32 actual = READ_U32(node, 0);
        if (style == 0) {
            if (pos >= bytes)
                return 0;
            u32 token;
            if (source[pos] == '\n') {
                if (++breaks > 1 || physical == 0 || physical + 1 == count)
                    return 0;
                token = LINE_BREAK;
                ++pos;
            } else {
                u32 units = english_token(source + pos, bytes - pos, &token);
                if (!units)
                    return 0;
                pos += units;
            }
            if (token >= 0xff00) {
                if (actual != (0xffff0000 | token))
                    return 0;
            } else if (!ram_range(glyphs, (token + 1) * 4)
                       || !glyphs[token] || actual != glyphs[token]) {
                return 0;
            }
            if (token != LINE_BREAK) {
                if (logical == MAX_LOGICAL)
                    return 0;
                animator->physical[logical++] = physical;
            }
        } else {
            if ((actual & 0xffffff00) == 0xffffff00 && actual != 0xffffff0b && actual != 0xffffff0a)
                return 0;
            if (logical == MAX_LOGICAL)
                return 0;
            animator->physical[logical++] = physical;
        }
        previous = node;
        node = (const u8 *)READ_U32(node, 0x120);
    }
    if ((style == 0 && pos != bytes) || !logical || !node_address(node)
        || READ_U32(node, 0) != 0xffffff0f || READ_U32(node, 0x120)
        || READ_U32(node, 0x124) != (u32)previous || (u32)node != READ_U32(font, 8))
        return 0;
    return logical;
}

void choice_init_animator(struct Animator *animator)
{
    animator->mode = choice_context.mode;
    animator->generation = choice_context.generation;
    animator->count = choice_inspect_nodes(animator);
    if (!animator->count)
        choice_context.failed = 1;
}

u32 choice_animation_count(struct Animator *animator)
{
    if (choice_context.failed || !animator->count || animator->count > MAX_LOGICAL
        || animator->generation != choice_context.generation)
        return 0;
    u32 count = choice_inspect_nodes(animator);
    if (count != animator->count) {
        choice_context.failed = 1;
        return 0;
    }
    return count;
}


static u8 *owned_sprite(const u8 *cursor, u32 slot, u16 identity)
{
    u8 *sprite = (u8 *)READ_U32(cursor, 0x24 + slot * 4);
    if (!ram_range(sprite, 0x94) || ((usize)sprite & 3)
        || READ_U16(sprite, 0x82) != 1 || READ_U16(sprite, 0x84) != identity || !sprite[0x93])
        return 0;
    return sprite;
}

static void move_sprite(u8 *sprite, float x, float y, float scale_x, float scale_y)
{
    *(float *)(sprite + 0x3c) = x;
    *(float *)(sprite + 0x40) = y;
    *(float *)(sprite + 0x60) = scale_x;
    *(float *)(sprite + 0x64) = scale_y;
}

void choice_fit_cursor(const u8 *task)
{
    const u8 *cursor = (const u8 *)READ_U32(task, 0x3c);
    if (!ram_range(cursor, 0x34))
        return;
    u16 stage = READ_U16(cursor, 0);
    float y = *(const float *)(cursor + 0x0c);
    if (stage == 2) {
        u8 *flash = owned_sprite(cursor, 0, 0x91);
        if (flash)
            move_sprite(flash, 12.25f, y + 8.5f, 0.140625f, 0.126953125f);
    } else if (stage == 3 || stage == 4) {
        u8 *left = owned_sprite(cursor, 0, 0x8d);
        u8 *right = owned_sprite(cursor, 1, 0x90);
        u8 *bottom = owned_sprite(cursor, 2, 0x8e);
        u8 *top = owned_sprite(cursor, 3, 0x8f);
        if (!left || !right || !bottom || !top)
            return;
        /* Native -90-degree frames rotate source X scale to screen Y.
         * Keep the first-line indicator in the margin, away from both rows.
         */
        move_sprite(left, 7.25f, y + 11.5f, 1.0f / 3.0f, 0.25f);
        move_sprite(right, 10.75f, y + 11.5f, 1.0f / 3.0f, 0.25f);
        move_sprite(bottom, 4.5f, y + 16.0f, 0.25f, 0.5f);
        move_sprite(top, 4.5f, y + 2.0f, 0.25f, 0.5f);
    }
}
