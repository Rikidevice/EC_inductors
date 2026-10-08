import cv2
import numpy as np

# НАСТРОЙКИ
INPUT_IMAGE  = "interface.jpg"
OUTPUT_RAW   = "interface.raw"

# Размер, который реально показывает дисплей
TARGET_WIDTH  = 172
TARGET_HEIGHT = 320

# Поворот исходной картинки ДО конвертации
#   0   — как есть (шаблон уже портретный 172×320)
#   90  — повернуть по часовой (из альбомного 320×172 сделать портретный)
#   270 — повернуть против часовой
#   180 — перевернуть
ROTATE_SOURCE = 90    # ← попробуй 90 или 270


def convert_image_to_raw(image_path, raw_path):
    img = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if img is None:
        print("Ошибка: не удалось открыть", image_path)
        return

    # Поворот исходника
    if ROTATE_SOURCE == 90:
        img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    elif ROTATE_SOURCE == 270:
        img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
    elif ROTATE_SOURCE == 180:
        img = cv2.rotate(img, cv2.ROTATE_180)

    src_h, src_w = img.shape[:2]
    print(f"Размер после поворота: {src_w}x{src_h}")

    # Приводим строго под дисплей
    resized = cv2.resize(img, (TARGET_WIDTH, TARGET_HEIGHT),
                         interpolation=cv2.INTER_AREA)

    # BGR -> RGB -> RGB565
    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
    r = rgb[:, :, 0].astype(np.uint16)
    g = rgb[:, :, 1].astype(np.uint16)
    b = rgb[:, :, 2].astype(np.uint16)
    rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

    hi = (rgb565 >> 8) & 0xFF
    lo = rgb565 & 0xFF

    raw_bytes = np.empty((TARGET_HEIGHT, TARGET_WIDTH, 2), dtype=np.uint8)
    raw_bytes[:, :, 0] = hi
    raw_bytes[:, :, 1] = lo

    with open(raw_path, "wb") as f:
        f.write(raw_bytes.tobytes())

    size = TARGET_WIDTH * TARGET_HEIGHT * 2
    print(f"Готово: {raw_path}, {size} байт")
    print(f"Ожидаемый размер в MicroPython: {172*320*2} байт")


if __name__ == "__main__":
    convert_image_to_raw(INPUT_IMAGE, OUTPUT_RAW)