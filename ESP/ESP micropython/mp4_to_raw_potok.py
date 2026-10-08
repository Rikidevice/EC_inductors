import cv2
import numpy as np

# НАСТРОЙКИ
INPUT_VIDEO  = "logo_ec.mp4"
OUTPUT_RAW   = "logo_ec.raw"

# Размер, который реально показывает дисплей (портрет)
TARGET_WIDTH  = 172
TARGET_HEIGHT = 320

# Поворот исходного видео ДО ресайза:
#   0   — как есть (видео уже портретное)
#   90  — повернуть по часовой  (из альбомного сделать портретное)
#   270 — повернуть против часовой
#   180 — перевернуть
ROTATE_SOURCE = 0     # ← как у интерфейса


def rotate_frame(frame, deg):
    if deg == 90:
        return cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
    if deg == 270:
        return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
    if deg == 180:
        return cv2.rotate(frame, cv2.ROTATE_180)
    return frame


def convert_video_to_raw(video_path, raw_path):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Ошибка: Не удалось открыть видеофайл")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"Исходное видео: {total_frames} кадров, {fps:.2f} FPS")
    print(f"Поворот исходника: {ROTATE_SOURCE}°")
    print(f"Кадр на выходе: {TARGET_WIDTH}x{TARGET_HEIGHT}")
    print("Конвертация началась...")

    frame_count = 0
    with open(raw_path, "wb") as out_file:
        while True:
            ret, frame = cap.read()
            if not ret:
                break  # Конец видео

            # 1. Поворот исходника
            frame = rotate_frame(frame, ROTATE_SOURCE)

            # 2. Изменяем размер строго под геометрию экрана
            resized = cv2.resize(frame, (TARGET_WIDTH, TARGET_HEIGHT),
                                 interpolation=cv2.INTER_AREA)

            # 3. BGR -> RGB
            rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

            # 4. Разделяем каналы
            r = rgb[:, :, 0].astype(np.uint16)
            g = rgb[:, :, 1].astype(np.uint16)
            b = rgb[:, :, 2].astype(np.uint16)

            # 5. RGB565
            rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

            # 6. Big-endian (high, low)
            high_byte = (rgb565 >> 8) & 0xFF
            low_byte  = rgb565 & 0xFF

            raw_bytes = np.empty((TARGET_HEIGHT, TARGET_WIDTH, 2), dtype=np.uint8)
            raw_bytes[:, :, 0] = high_byte
            raw_bytes[:, :, 1] = low_byte

            out_file.write(raw_bytes.tobytes())

            frame_count += 1
            if frame_count % 30 == 0:
                print(f"Обработано кадров: {frame_count}/{total_frames}")

    cap.release()
    print(f"Успешно! Файл сохранен как: {raw_path}")
    print(f"Размер файла: {frame_count * TARGET_WIDTH * TARGET_HEIGHT * 2 / 1024 / 1024:.2f} МБ")


if __name__ == "__main__":
    convert_video_to_raw(INPUT_VIDEO, OUTPUT_RAW)