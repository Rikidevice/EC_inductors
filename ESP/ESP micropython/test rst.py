from machine import Pin
import time

# Настройка пина GPIO6 как вход с подтягивающим резистором
# Используй Pin.PULL_UP если кнопка соединяет пин с GND
# Используй Pin.PULL_DOWN если кнопка соединяет пин с 3.3V
button = Pin(6, Pin.IN, Pin.PULL_UP)

while True:
    if button.value() == 0:  # 0 = нажата (при PULL_UP), 1 = нажата (при PULL_DOWN)
        print("1")
    else:
        print("0")
    
    time.sleep(0.1)  # задержка 100 мс