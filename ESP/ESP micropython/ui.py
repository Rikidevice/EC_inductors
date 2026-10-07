"""
ui.py — RAW-фон интерфейса + OR-наложение текста.

Использование:
    import ui
    bg = ui.load("/sd/interface.raw", display.width, display.height)
    frame = bytearray(display.width * display.height * 2)
    frame[:] = bg
    ui.text_or(frame, display.width, display.height, font, "X 1.23", 20, 20)
    display.blit_buffer(frame, 0, 0, display.width, display.height)
"""


def load(path, w, h):
    """Читает RAW RGB565 big-endian файл в bytearray."""
    size = w * h * 2
    buf = bytearray(size)
    try:
        with open(path, "rb") as f:
            n = f.readinto(buf)
            if n != size:
                print(f"UI: размер {n}, ожидалось {size}")
    except Exception as e:
        print("UI: ошибка чтения", path, e)
    return buf


def blit(display, buf):
    """Быстрый вывод готового буфера на экран."""
    display.blit_buffer(buf, 0, 0, display.width, display.height)


def text_or(target, target_w, target_h, font, text, x, y, color=0xFFFF):
    """
    OR-наложение текста на RGB565 big-endian буфер (in-place).
    Совместимо с шрифтами, у которых есть FONT, WIDTH, HEIGHT (vga2_16x16).
    """
    gw, gh = font.WIDTH, font.HEIGHT
    gb = gw * gh // 8
    hi = (color >> 8) & 0xFF
    lo = color & 0xFF
    px = x

    for ch in text:
        code = ord(ch)
        base = code * gb
        for gy in range(gh):
            yy = y + gy
            if yy < 0 or yy >= target_h:
                continue
            row_base = base + gy * (gw // 8)
            for gx in range(gw):
                xx = px + gx
                if xx < 0 or xx >= target_w:
                    continue
                b = font.FONT[row_base + (gx >> 3)]
                if b & (1 << (7 - (gx & 7))):
                    idx = (yy * target_w + xx) * 2
                    target[idx]     |= hi
                    target[idx + 1] |= lo
        px += gw