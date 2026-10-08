import machine
import time
import st7789py as st7789
import vga2_16x32 as font
import onewire, ds18x20
from machine import Pin
import os

test = 0

# ==================== SD-КАРТА ====================
try:
    sd = machine.SDCard(slot=1, width=4,
                        sck=14, cmd=15, data=(16, 18, 17, 21))
    vfs = os.VfsFat(sd)
    os.mount(vfs, "/sd")
    print("SD its OK")
except Exception as e:
    print(f"Err: {e}")

# ==================== ДИСПЛЕЙ ====================
# Сброс
rst_pin = machine.Pin(39, machine.Pin.OUT)
rst_pin.value(0)
time.sleep_ms(50)
rst_pin.value(1)
time.sleep_ms(50)

# Подсветка
backlight = machine.Pin(46, machine.Pin.OUT)
backlight.value(1)

# SPI
spi = machine.SPI(1, baudrate=40000000, polarity=0, phase=0,
                  sck=machine.Pin(40), mosi=machine.Pin(45))

# Пины CS и DC – сохраним их для прямого доступа
cs_pin = machine.Pin(42, machine.Pin.OUT)
dc_pin = machine.Pin(41, machine.Pin.OUT)

display = st7789.ST7789(
    spi,
    240,
    320,
    reset=None,
    cs=cs_pin,
    dc=dc_pin,
    rotation=1
)

# Физические параметры Waveshare 1.47"
display.width = 320
display.height = 172
display.xstart = 0
display.ystart = 34

BG_COLOR = st7789.color565(15, 15, 25)
TEXT_COLOR = st7789.YELLOW
display.fill(BG_COLOR)

# ==================== ФУНКЦИЯ ВЫВОДА BMP ====================

def load_bmp_to_ram(filename):
    """
    Считывает BMP с SD-карты, конвертирует в RGB565 и возвращает
    готовый bytearray, который MicroPython автоматически разместит в PSRAM.
    """
    start_time = time.ticks_ms()
    try:
        with open(filename, "rb") as f:
            if f.read(2) != b'BM':
                print("Файл не является BMP")
                return None

            f.seek(10)
            data_offset = int.from_bytes(f.read(4), "little")

            f.seek(18)
            bmp_width = int.from_bytes(f.read(4), "little")
            bmp_height = int.from_bytes(f.read(4), "little")

            f.seek(28)
            if int.from_bytes(f.read(2), "little") != 24:
                print("Поддерживается только 24-битный BMP")
                return None

            row_size = (bmp_width * 3 + 3) & ~3
            draw_w = min(bmp_width, display.width)
            draw_h = min(abs(bmp_height), display.height)

            # Выделяем один большой буфер под весь экран (~107.5 КБ).
            # Такой размер на ESP32-S3 автоматически уходит в SPIRAM (PSRAM).
            gc.collect() # Очищаем память перед выделением
            ram_buffer = bytearray(draw_w * draw_h * 2)
            
            print(f"Конвертация {filename} в RAM...")

            # Построчно читаем из файла и пишем в наш RAM-буфер
            for row in range(draw_h):
                if bmp_height > 0:
                    pos = data_offset + (bmp_height - 1 - row) * row_size
                else:
                    pos = data_offset + row * row_size
                
                f.seek(pos)
                bmp_row_data = f.read(draw_w * 3)

                # Вычисляем смещение текущей строки в результирующем буфере
                buf_idx = row * draw_w * 2

                # Оптимизированный цикл конвертации
                for i in range(0, len(bmp_row_data), 3):
                    b = bmp_row_data[i]
                    g = bmp_row_data[i+1]
                    r = bmp_row_data[i+2]
                    
                    color = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
                    
                    ram_buffer[buf_idx] = (color >> 8) & 0xFF
                    ram_buffer[buf_idx+1] = color & 0xFF
                    buf_idx += 2

            print(f"Готово за {time.ticks_diff(time.ticks_ms(), start_time)} мс. Буфер в ОЗУ создан.")
            return ram_buffer, draw_w, draw_h

    except Exception as e:
        print(f"Ошибка загрузки BMP в RAM: {e}")
        return None

# ==================== ОСНОВНОЙ ЦИКЛ ====================
time.sleep(2)

# Загружаем картинку в PSRAM один раз при старте программы
image_data = load_bmp_to_ram("/sd/bxna.bmp")

if image_data:
    buffer, w, h = image_data
        
    # Мгновенный вывод на экран всей картинки из PSRAM за один вызов!
    # Так как данные уже подготовлены, это отработает на максимальной скорости SPI.
    display.blit_buffer(buffer, 0, 0, w, h)