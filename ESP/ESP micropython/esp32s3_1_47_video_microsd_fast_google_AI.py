import machine
import time
import st7789py as st7789
import os
import gc


# ==================== SD-КАРТА ====================
for pin_num in (14, 15, 16, 17, 18, 21):
    machine.Pin(pin_num, machine.Pin.IN, machine.Pin.PULL_UP)
time.sleep_ms(100)

try:
    sd = machine.SDCard(slot=1, width=4, sck=14, cmd=15, data=(16, 18, 17, 21))
    vfs = os.VfsFat(sd)
    try: 
        os.mount(vfs, "/sd")
    except Exception as e:
        pass
    print("SD Card OK")
except Exception as e:
    print(f"SD Error: {e}")

# ==================== ДИСПЛЕЙ ====================
rst_pin = machine.Pin(39, machine.Pin.OUT)
rst_pin.value(0); time.sleep_ms(50); rst_pin.value(1); time.sleep_ms(50)

backlight = machine.Pin(46, machine.Pin.OUT)
backlight.value(1)

spi = machine.SPI(1, baudrate=60000000, polarity=0, phase=0,
                  sck=machine.Pin(40), mosi=machine.Pin(45))

display = st7789.ST7789(spi, 240, 320, reset=None, 
                        cs=machine.Pin(42, machine.Pin.OUT), 
                        dc=machine.Pin(41, machine.Pin.OUT), rotation=1)

display.width = 320
display.height = 172
display.xstart = 0
display.ystart = 34

# ==================== ФУНКЦИЯ ВОСПРОИЗВЕДЕНИЯ RAW ВИДЕО ====================
# ==================== ИНИЦИАЛИЗАЦИЯ БУФЕРА КАДРА ====================

# Выносим создание буфера из функции на глобальный уровень.
# Перед созданием максимально жестко очищаем память от прошлых запусков.
gc.collect()
time.sleep_ms(50)
gc.threshold(gc.mem_free() // 4) # Заставляем GC работать агрессивнее

FRAME_SIZE = display.width * display.height * 2

try:
    # Создаем ОДИН постоянный буфер. При перезапуске скрипта 
    # MicroPython будет пытаться переиспользовать или перевыделить его чище.
    frame_buffer = bytearray(FRAME_SIZE)
    print("Буфер кадра успешно выделен в PSRAM")
except MemoryError:
    print("Критическая ошибка: Не удалось выделить память под буфер кадра!")
    # Если памяти совсем нет, пробуем аварийную очистку
    gc.collect()
    frame_buffer = bytearray(FRAME_SIZE)

def play_raw_video(filename, fps=24):
    # Размер одного кадра на экране: 320 * 172 * 2 байта = 110080 байт
    frame_size = display.width * display.height * 2
    
    # Создаем буфер кадра. Такой размер автоматически выделится в PSRAM
    gc.collect()
    frame_buffer = bytearray(frame_size)
    
    # Целевое время на один кадр в миллисекундах (для 24 fps это ~41 мс)
    frame_delay = int(1000 / fps)
    
    try:
        print(f"Открытие видео {filename}...")
        with open(filename, "rb") as f:
            while True:
                start_time = time.ticks_ms()
                
                # Читаем ровно один кадр из файла напрямую в буфер в PSRAM
                bytes_read = f.readinto(frame_buffer)
                
                # Если файл закончился (прочитано меньше, чем размер кадра) — выходим
                if bytes_read < frame_size:
                    print("Конец видеофайла")
                    break
                
                # Мгновенно выкидываем весь кадр на дисплей
                display.blit_buffer(frame_buffer, 0, 0, display.width, display.height)
                
                # Считаем, сколько заняло чтение с SD + вывод на экран
                elapsed = time.ticks_diff(time.ticks_ms(), start_time)
                
                # Удерживаем FPS. Если сработали быстрее 41 мс — спим остаток времени
                sleep_time = frame_delay - elapsed
                if sleep_time > 0:
                    time.sleep_ms(sleep_time)
                    
    except Exception as e:
        print(f"Ошибка воспроизведения: {e}")

# ==================== ОСНОВНОЙ ЦИКЛ ====================
time.sleep(2)

while True:
    # Запускаем видео по кругу
    play_raw_video("/sd/video2.raw", fps=60)
    time.sleep(1) # Пауза перед повтором