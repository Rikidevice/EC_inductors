import machine
import time
import os
import st7789py as st7789
import gc
import blue_font as font
import onewire, ds18x20
from machine import Pin
import ui
import struct
import dht
import network
import socket


time.sleep(5)


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

ow = onewire.OneWire(Pin(7, Pin.OPEN_DRAIN))
ds = ds18x20.DS18X20(ow)

# =========================================================================
# 1. АППАРАТНАЯ НАСТРОЙКА IPS-ДИСПЛЕЯ (ST7789)
# =========================================================================
# Ручной жесткий сброс чипа дисплея
rst_pin = machine.Pin(39, machine.Pin.OUT)
rst_pin.value(0)
time.sleep_ms(50)
rst_pin.value(1)
time.sleep_ms(50)

# Включение подсветки экрана (строго GPIO 46)
backlight = machine.Pin(46, machine.Pin.OUT)
backlight.value(1) 

# Конфигурация аппаратного SPI
spi = machine.SPI(1, 
                  baudrate=40000000, 
                  polarity=0, 
                  phase=0, 
                  sck=machine.Pin(40), 
                  mosi=machine.Pin(45))

# Инициализация объекта дисплея (обманываем валидацию встроенным размером 240)
display = st7789.ST7789(
    spi, 
    240, 
    320, 
    reset=None, 
    cs=machine.Pin(42, machine.Pin.OUT), 
    dc=machine.Pin(41, machine.Pin.OUT), 
    rotation=0  # Альбомная ориентация экрана
)

# Ручной возврат физических параметров матрицы Waveshare 1.47" (320x172)
display.width = 172
display.height = 320
display.xstart = 34
display.ystart = 0  # Смещение по вертикали для центрирования картинки

# Цветовая палитра интерфейса
BG_COLOR = st7789.color565(15, 15, 25)     # Глубокий темно-синий
TEXT_COLOR = st7789.YELLOW                 # Желтый текст для телеметрии
display.fill(BG_COLOR)

# =========================================================================
# 2. НАСТРОЙКА ШИНЫ I2C И АКСЕЛЕРОМЕТРА (QMI8658)
# =========================================================================
I2C_ADDR = 107  # Деситичный адрес чипа QMI8658 (0x6B)

# Инициализация шины I2C на подтвержденных пинах SCL=47, SDA=48
i2c = machine.I2C(0, sda=machine.Pin(48), scl=machine.Pin(47), freq=400000)

def init_qmi8658():
    """Последовательность активации датчика из официальной спецификации QST"""
    i2c.writeto_mem(I2C_ADDR, 0x02, b'\x60') # CTRL1: Инкремент адреса при пакетном чтении
    i2c.writeto_mem(I2C_ADDR, 0x03, b'\x20') # CTRL2: Настройка акселерометра (диапазон ±2g)
    i2c.writeto_mem(I2C_ADDR, 0x04, b'\x53') # CTRL3: Настройка гироскопа
    i2c.writeto_mem(I2C_ADDR, 0x05, b'\x00') # CTRL4: Без изменений
    i2c.writeto_mem(I2C_ADDR, 0x06, b'\x11') # CTRL5: Включение фильтра LPF
    i2c.writeto_mem(I2C_ADDR, 0x07, b'\x00') # CTRL6: Без изменений
    i2c.writeto_mem(I2C_ADDR, 0x08, b'\x03') # CTRL7: Пробуждение (активация акселя и гироскопа)
    time.sleep_ms(50)

def read_accel():
    """Чтение 6 байт осей ускорения и сборка Little Endian значений"""
    # Регистр 0x35 — это начало блока выходных данных акселерометра
    data = i2c.readfrom_mem(I2C_ADDR, 0x35, 6)
    
    # Побайтовая сборка (младший байт идет первым, старший — вторым)
    x = (data[1] << 8) | data[0]
    y = (data[3] << 8) | data[2]
    z = (data[5] << 8) | data[4]
    
    # Обработка знака для 16-битных чисел (двухпозиционный код)
    if x & 0x8000: x -= 65536
    if y & 0x8000: y -= 65536
    if z & 0x8000: z -= 65536
    
    # Коэффициент масштабирования для выбранного диапазона ±2g составляет 16384 LSB/g
    scale = 16384.0
    return x / scale, y / scale, z / scale

# Запуск акселерометра
try:
    init_qmi8658()
    display.text(font, "", 40, 70, st7789.GREEN, BG_COLOR)
    time.sleep(1)
    display.fill(BG_COLOR)
except Exception as e:
    display.text(font, "IMU ERROR", 40, 70, st7789.RED, BG_COLOR)
    print("Ошибка инициализации I2C:", e)
    while True: time.sleep(1)

# =========================================================================
# 3. ОСНОВНОЙ ЦИКЛ ОБНОВЛЕНИЯ ДАННЫХ
# =========================================================================
# ─── один раз после инициализации display ───
FRAME_W = display.width
FRAME_H = display.height
FRAME_SIZE = FRAME_W * FRAME_H * 2

bg_buf      = ui.load("/sd/interface.raw", FRAME_W, FRAME_H)
frame_buffer = bytearray(FRAME_SIZE)

TEXT_YELLOW = st7789.color565(255, 220, 0)
TEXT_GREEN  = st7789.color565(0, 255, 120)
TEXT_RED    = st7789.color565(255, 60, 60)
TEXT_CYAN   = st7789.color565(80, 220, 255)

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

play_raw_video("/sd/logo_ec.raw", fps=60)
# ==================== ОСНОВНОЙ ЦИКЛ ====================
time.sleep(2)

# ========== ПОДКЛЮЧЕНИЕ К WI-FI ==========
def connect_wifi(ssid, password, timeout=60):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('Connecting to WiFi...')
        wlan.connect(ssid, password)
        start_time = time.time()
        while not wlan.isconnected():
            if time.time() - start_time > timeout:
                print("WiFi connection timeout!")
                return None
            time.sleep(0.5)
    print('Network config:', wlan.ifconfig())
    return wlan

# ========== ПОДКЛЮЧЕНИЕ WI-FI ==========
wlan = connect_wifi("my", "220319840", 60)
if wlan is not None:
    ip_address = wlan.ifconfig()[0]
else:
    ip_address = None

# ========== ВЕБ-СЕРВЕР ==========
addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
server_socket = socket.socket()
server_socket.bind(addr)
server_socket.listen(1)
server_socket.setblocking(False)

# ========== ФУНКЦИЯ ДЛЯ ВЕБ-СТРАНИЦЫ (с формой калибровки) ==========
def web_page(temp, tempDHT22, humDHT22, TDS, EC, adc_raw, freq, table):
    # Формируем строки с текущими значениями для отображения в форме
    rows_html = ""
    for i, (adc, ec) in enumerate(table):
        rows_html += f"""
        <tr>
            <td><input type="number" name="adc{i+1}" value="{adc}" step="1" style="width:120px;"></td>
            <td><input type="number" name="ec{i+1}" value="{ec}" step="0.01" style="width:80px;"></td>
        </tr>
        """
    
    html = """<html><head><meta charset="UTF-8"><title>TDS Monitor</title>
    <meta http-equiv="refresh" content="1">
    <style>body{font-family:Arial;background:#1e1e2f;color:#fff;padding:20px;}
    h1{color:#4fc3f7;} table{width:100%%;max-width:600px;border-collapse:collapse;}
    td{padding:10px;border-bottom:1px solid #444;}
    .label{font-weight:bold;color:#aaa;} .value{color:#4fc3f7;}
    input{background:#333;color:#fff;border:1px solid #555;padding:4px;border-radius:4px;}
    .btn{background:#4fc3f7;color:#000;padding:8px 16px;border:none;border-radius:4px;cursor:pointer;}
    .btn:hover{background:#29b6f6;}
    </style></head><body>
    <h1>📊 TDS Trends – Induction Method</h1>
    <h3>Текущие показания</h3>
    <table>
    <tr><td class="label">Частота</td><td class="value">%s Гц</td></tr>
    <tr><td class="label">ADC сырой</td><td class="value">%s</td></tr>
    <tr><td class="label">18B20 температура</td><td class="value">%.2f °C</td></tr>
    <tr><td class="label">DHT22 температура</td><td class="value">%.2f °C</td></tr>
    <tr><td class="label">DHT22 влажность</td><td class="value">%.2f %%</td></tr>
    <tr><td class="label">TDS (отфильтрованный)</td><td class="value">%.0f ppm</td></tr>
    <tr><td class="label">EC (отфильтрованный)</td><td class="value">%.0f µS/cm</td></tr>
    </table>
    <hr>
    <h3>Калибровка (АЦП → EC при 20°C)</h3>
    <form method="POST" action="/">
        <table>
        <tr><th>АЦП</th><th>EC (µS/cm)</th></tr>
        %s
        </table>
        <br>
        <input type="submit" value="Сохранить калибровку" class="btn">
    </form>
    <p style="color:#888;font-size:12px;">Обновлено при загрузке</p>
    </body></html>""" % (freq, adc_raw, temp, tempDHT22, humDHT22, TDS, EC, rows_html)
    return html


while True:
    roms = ds.scan()
    # Чтение температуры
    try:
        ds.convert_temp()
        temp = ds.read_temp(roms[0])
    except Exception as e:
        temp = 200

    # 1) восстановить фон (быстрая C-копия)
    frame_buffer[:] = bg_buf

    try:
        # Считываем реальные физические перегрузки в g
        ax, ay, az = read_accel()
        f=60
        ui.text_or(frame_buffer, FRAME_W, FRAME_H, font,f"Freq: {az:+.2f} Hz", 20, f+20, TEXT_CYAN)
        ui.text_or(frame_buffer, FRAME_W, FRAME_H, font,f"ADC: {az:+.2f}", 20, f+40, TEXT_CYAN)
        ui.text_or(frame_buffer, FRAME_W, FRAME_H, font,f"T: {az:+.2f} °C", 20, f+60, TEXT_CYAN)
        ui.text_or(frame_buffer, FRAME_W, FRAME_H, font,f"DHT22 t: {az:+.2f} °C", 20, f+80, TEXT_CYAN)
        ui.text_or(frame_buffer, FRAME_W, FRAME_H, font,f"DHT22 h: {az:+.2f} %", 20, f+100, TEXT_CYAN)
        ui.text_or(frame_buffer, FRAME_W, FRAME_H, font,f"TDS: {az:+.2f} ppm", 20, f+120, TEXT_CYAN)
        ui.text_or(frame_buffer, FRAME_W, FRAME_H, font,f"EC: {az:+.2f} uS", 20, f+140, TEXT_CYAN)
        ui.text_or(frame_buffer, FRAME_W, FRAME_H, font,f"pH_adc: {az:+.2f}", 20, f+160, TEXT_CYAN)
        ui.text_or(frame_buffer, FRAME_W, FRAME_H, font,f"pH: {az:+.2f}", 20, f+180, TEXT_CYAN)
        # 3) вывести одним куском
        display.blit_buffer(frame_buffer, 0, 0, FRAME_W, FRAME_H)       
    
    except Exception as e:
        #display.text(font, "READ ERROR  ", 20, 70, st7789.RED, BG_COLOR)
        print("Ошибка чтения осей:", e)

    # ---- ОБРАБОТКА ВЕБ-ЗАПРОСОВ (GET и POST) ----
    try:
        conn, addr = server_socket.accept()
        if conn:
            request = conn.recv(1024)
            print("Request from", addr)
            
            # Проверяем метод
            if request.startswith(b'POST'):
                # Ищем тело (после двух \r\n)
                parts = request.split(b'\r\n\r\n', 1)
                if len(parts) > 1:
                    body = parts[1].decode()
                    # Парсим параметры (application/x-www-form-urlencoded)
                    params = {}
                    for pair in body.split('&'):
                        if '=' in pair:
                            key, val = pair.split('=', 1)
                            params[key] = val
                    # Собираем новые пары
                    new_table = []
                    for i in range(1, 5):
                        adc_key = f'adc{i}'
                        ec_key = f'ec{i}'
                        if adc_key in params and ec_key in params:
                            try:
                                adc = int(params[adc_key])
                                ec = float(params[ec_key])
                                new_table.append((adc, ec))
                            except:
                                pass
                    if len(new_table) == 4:
                        CAL_TABLE = new_table          # <-- убрали global
                        save_calibration(CAL_TABLE)
                        # Ответ с подтверждением
                        response = b'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n<html><body><h2>Калибровка сохранена!</h2><a href="/">Назад</a></body></html>'
                        conn.send(response)
                        conn.close()
                        continue  # переходим к следующей итерации цикла
            # GET-запрос: отдаём страницу
            response = web_page(temp, tempDHT22, humDHT22, TDS, EC_filtered, result, freq_ind, CAL_TABLE)
            conn.send('HTTP/1.1 200 OK\r\n')
            conn.send('Content-Type: text/html\r\n')
            conn.send('Connection: close\r\n\r\n')
            conn.sendall(response)
            conn.close()
            print("Response sent")
    except Exception as e:
        # Если нет соединения – просто игнорируем
        pass

    time.sleep_ms(1) # Периодичность обновления экрана (10 раз в секунду)