from machine import UART
import time
import struct

uart = UART(1, baudrate=115200, tx=9, rx=10)

def ONE_TDSEC(freq, duty, samples, cmd, timeout_ms=4000):
    frame = bytearray()
    frame.append(0x0F)
    frame.extend(struct.pack('<I', freq))
    frame.extend(struct.pack('<I', duty))
    frame.append(samples)
    frame.append(cmd)
    uart.write(frame)
    start = time.ticks_ms()
    response = bytearray()
    while time.ticks_diff(time.ticks_ms(), start) < timeout_ms:
        if uart.any():
            response.extend(uart.read())
            if len(response) >= 6 and response[0] == 0xF0:
                return struct.unpack('<I', response[1:5])[0]
        time.sleep_ms(10)
    return None

while True:
    freq = 10000
    freq = int(168000000 / freq)      # = 140
    dutypwm = int(freq / 2)           # = 70

    result = ONE_TDSEC(freq, dutypwm, 7, 1, timeout_ms=4000)   # ← ВЫЗОВ!
    print('TDS =', result)

    time.sleep_ms(100)