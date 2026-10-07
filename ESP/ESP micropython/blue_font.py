"""
vga2_16x16.py — 14-сегментный цифровой шрифт.
Автомасштабирование: меняешь WIDTH/HEIGHT — все сегменты пересчитываются.
WIDTH должна быть кратна 8 (8 / 16 / 24 / 32) — требование драйвера st7789py.
HEIGHT может быть любым от 8 до 32.
"""

# ═══════════════════════════════════════════════════════
#  РАЗМЕР ЗНАКА
# ═══════════════════════════════════════════════════════
WIDTH  = 8        # 8, 16, 24, 32  (кратно 8!)
HEIGHT = 8        # 8..32

# ═══════════════════════════════════════════════════════
#  ТОЛЩИНЫ / ЗАЗОРЫ / ДИАГОНАЛИ
#  None = авто (пропорционально размеру)
#  Число = фиксировано в пикселях
# ═══════════════════════════════════════════════════════
T_H      = None    # толщина горизонтальных сегментов
T_V      = None    # толщина вертикальных сегментов
T_D      = None    # толщина диагоналей
GAP_H    = None    # вертикальные зазоры
GAP_V    = None    # горизонтальные зазоры
DIAG_LEN = None    # длина диагоналей

ITALIC = False     # наклон вправо

# ═══════════════════════════════════════════════════════
FIRST = 0x00
LAST  = 0xff

_A  = 0x0001
_B  = 0x0002
_C  = 0x0004
_D  = 0x0008
_E  = 0x0010
_F  = 0x0020
_G1 = 0x0040
_G2 = 0x0080
_H  = 0x0100
_I  = 0x0200
_J  = 0x0400
_K  = 0x0800
_L  = 0x1000
_M  = 0x2000


def _resolve():
    global T_H, T_V, T_D, GAP_H, GAP_V, DIAG_LEN
    s = min(WIDTH, HEIGHT)
    if T_H is None: T_H = max(1, s // 8)
    if T_V is None: T_V = max(1, s // 8)
    if T_D is None: T_D = max(1, s // 14)
    if GAP_H is None: GAP_H = max(0, s // 16)
    if GAP_V is None: GAP_V = max(0, s // 16)
    if DIAG_LEN is None:
        mid_y = HEIGHT // 2
        DIAG_LEN = max(2, mid_y - T_H - T_H//2 - GAP_H)

_resolve()


def _pixels_for(bit):
    W, H = WIDTH, HEIGHT
    th, tv, td = T_H, T_V, T_D
    gh, gv = GAP_H, GAP_V
    dl = DIAG_LEN
    mid_y = H // 2

    xh0 = tv + gv
    xh1 = W - tv - gv

    yv_top0 = th + gh
    yv_top1 = mid_y - th//2 - gh
    yv_bot0 = mid_y - th//2 + th + gh
    yv_bot1 = H - th - gh

    ym0 = mid_y - th // 2
    ym1 = ym0 + th

    half = max(1, (xh1 - xh0 - gv) // 2)

    if bit == _A:
        return [(x, y) for y in range(0, th) for x in range(xh0, xh1)]
    if bit == _D:
        return [(x, y) for y in range(H - th, H) for x in range(xh0, xh1)]
    if bit == _G1:
        return [(x, y) for y in range(ym0, ym1) for x in range(xh0, xh0 + half)]
    if bit == _G2:
        return [(x, y) for y in range(ym0, ym1) for x in range(xh1 - half, xh1)]
    if bit == _F:
        return [(x, y) for x in range(0, tv) for y in range(yv_top0, yv_top1)]
    if bit == _B:
        return [(x, y) for x in range(W - tv, W) for y in range(yv_top0, yv_top1)]
    if bit == _E:
        return [(x, y) for x in range(0, tv) for y in range(yv_bot0, yv_bot1)]
    if bit == _C:
        return [(x, y) for x in range(W - tv, W) for y in range(yv_bot0, yv_bot1)]
    if bit == _L:
        xc = W // 2 - tv // 2
        return [(x, y) for x in range(xc, xc + tv) for y in range(yv_top0, yv_top1)]
    if bit == _M:
        xc = W // 2 - tv // 2
        return [(x, y) for x in range(xc, xc + tv) for y in range(yv_bot0, yv_bot1)]

    if bit == _H: return _diag(tv,               th + gh,                1,  1, dl, td)
    if bit == _I: return _diag(W - tv - 1,       th + gh,               -1,  1, dl, td)
    if bit == _J: return _diag(W - tv - 1,       H - th - gh - 1,       -1, -1, dl, td)
    if bit == _K: return _diag(tv,               H - th - gh - 1,        1, -1, dl, td)
    return []


def _diag(x0, y0, dx, dy, length, thick):
    px = set()
    for i in range(length):
        cx, cy = x0 + dx * i, y0 + dy * i
        for off in range(thick):
            xx, yy = cx, cy + (off if dy > 0 else -off)
            if 0 <= xx < WIDTH and 0 <= yy < HEIGHT:
                px.add((xx, yy))
    return list(px)


# ─── ТОЧКИ ───
def _dot_size():
    dw = max(2, WIDTH  // 5)
    dh = max(2, HEIGHT // 5)
    return dw, dh


def _dot_pixels():
    """Точка '.' — по центру, у самого низа."""
    dw, dh = _dot_size()
    x0 = (WIDTH - dw) // 2
    y0 = HEIGHT - dh
    return [(x, y) for y in range(y0, HEIGHT) for x in range(x0, x0 + dw)]


def _colon_pixels():
    """Двоеточие ':' — две точки: в верхней и нижней трети."""
    dw, dh = _dot_size()
    x0 = (WIDTH - dw) // 2
    y1 = HEIGHT // 3     - dh // 2      # верхняя точка
    y2 = 2 * HEIGHT // 3 - dh // 2      # нижняя точка
    px = []
    for y0 in (y1, y2):
        for y in range(max(0, y0), min(HEIGHT, y0 + dh)):
            for x in range(x0, x0 + dw):
                px.append((x, y))
    return px


# ─── цифры ───
_DIGITS = {
    '0': _A|_B|_C|_D|_E|_F,
    '1': _B|_C,
    '2': _A|_B|_G1|_G2|_E|_D,
    '3': _A|_B|_G1|_G2|_C|_D,
    '4': _F|_G1|_G2|_B|_C,
    '5': _A|_F|_G1|_G2|_C|_D,
    '6': _A|_F|_G1|_G2|_E|_C|_D,
    '7': _A|_B|_C,
    '8': _A|_B|_C|_D|_E|_F|_G1|_G2,
    '9': _A|_B|_C|_D|_F|_G1|_G2,
}

# ─── буквы ───
_LETTERS = {
    'A': _A|_B|_C|_E|_F|_G1|_G2,
    'B': _C|_D|_E|_F|_G1|_G2,
    'C': _A|_D|_E|_F,
    'D': _B|_C|_D|_E|_G1|_G2,
    'E': _A|_D|_E|_F|_G1|_G2,
    'F': _A|_E|_F|_G1|_G2,
    'G': _A|_C|_D|_E|_F,
    'H': _B|_C|_E|_F|_G1|_G2,
    'I': _B|_C,
    'J': _B|_C|_D|_E,
    'K': _B|_C|_E|_F|_I|_J,
    'L': _D|_E|_F,
    'M': _B|_C|_E|_F|_H|_I,
    'N': _B|_C|_E|_F|_H|_J,
    'O': _A|_B|_C|_D|_E|_F,
    'P': _A|_B|_E|_F|_G1|_G2,
    'Q': _A|_B|_C|_D|_E|_F|_J,
    'R': _A|_B|_E|_F|_G1|_G2|_J,
    'S': _A|_C|_D|_F|_G1|_G2,
    'T': _A|_L|_M,
    'U': _B|_C|_D|_E|_F,
    'V': _E|_C|_H|_I,
    'W': _B|_C|_E|_F|_J|_K,
    'X': _H|_I|_J|_K,
    'Y': _H|_I|_M,
    'Z': _A|_B|_G1|_G2|_E|_D,
}

_SYMBOLS = {
    ' ': 0,
    '-': _G1|_G2,
    '_': _D,
    '=': _D|_G1|_G2,
    '+': _G1|_G2|_L|_M,
    '/': _B|_G2|_E,
    '\\': _F|_G1|_C,
    '(': _A|_D|_E|_F,
    ')': _A|_B|_C|_D,
    '[': _A|_D|_E|_F,
    ']': _A|_B|_C|_D,
    '!': _B|_C,
    '*': _H|_I|_J|_K|_L|_M,
}

_PATTERNS = dict(_DIGITS)
for _ch, _pat in _LETTERS.items():
    _PATTERNS[_ch] = _pat
    _PATTERNS[_ch.lower()] = _pat
_PATTERNS.update(_SYMBOLS)

_BITS = (_A, _B, _C, _D, _E, _F, _G1, _G2, _H, _I, _J, _K, _L, _M)

# ═══════════════════════════════════════════════════════
#  СБОРКА ШРИФТА
# ═══════════════════════════════════════════════════════
_GLYPH_SIZE = WIDTH * HEIGHT // 8


def _set_pixel(buf, x, y):
    if ITALIC:
        x = x + (HEIGHT - 1 - y) // 4
    if 0 <= x < WIDTH and 0 <= y < HEIGHT:
        idx = y * (WIDTH // 8) + (x >> 3)
        if idx < _GLYPH_SIZE:
            buf[idx] |= 1 << (7 - (x & 7))


def _build_glyph(code):
    ch  = chr(code)
    pat = _PATTERNS.get(ch, 0)
    buf = bytearray(_GLYPH_SIZE)

    # сегментные символы
    for bit in _BITS:
        if not (pat & bit):
            continue
        for (x, y) in _pixels_for(bit):
            _set_pixel(buf, x, y)

    # точечные символы
    if ch == '.':
        for (x, y) in _dot_pixels():
            _set_pixel(buf, x, y)
    elif ch == ':':
        for (x, y) in _colon_pixels():
            _set_pixel(buf, x, y)

    return buf


_FONT = bytearray()
for _code in range(256):
    _FONT.extend(_build_glyph(_code))

_FONT = bytes(_FONT)
FONT = memoryview(_FONT)