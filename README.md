# PWR_MOD — контроллер индуктивного измерения проводимости солей с регулировкой pH
# PWR_MOD — Inductive Salt Conductivity Meter with pH Control

[Русский](#русская-версия) · [English](#english-version)

---

## Русская версия

Плата управления для системы индуктивного (бесконтактного) измерения
проводимости солей трендового типа с автоматической коррекцией pH.
Поддерживает два варианта управляющего модуля: **ESP32 / ESP32-S3-1.47**
и **STM32F407VET6**. Связь по **Modbus (RTU/ASCII)**.

### Возможности

- **Индуктивный метод измерения проводимости солей**
  - Приём сигнала с катушки детекции (Rx) через **полноценный АЦП**
    с **гальванической развязкой**.
  - Отдельный канал измерения **pH** (также через развязанный АЦП).
- **Температурный контроль**
  - **DS18B20** — температура жидкости (1-Wire).
  - **DHT22 (AM2302)** — температура и влажность воздуха в помещении.
- **Управляющие модули (на выбор / распайка под оба):**
  - `ESP32` (WROOM-32 и совместимые);
  - `ESP32-S3-1.47` (дисплейный модуль);
  - `STM32F407VET6`.
- **Два шаговых двигателя** для дозирования:
  - `pH Up` — драйвер A4988;
  - `pH Down` — драйвер A4988.
- **Modbus**
- **Питание и защита** — 12В от 1А

### Аппаратная часть

| Узел | Реализация | Примечание |
|---|---|---|
| MCU | ESP32 / ESP32-S3-1.47 / STM32F407VET6 | выбор при сборке |
| АЦП (Rx катушки) | MCP3551 | гальваническая развязка |
| АЦП (pH) | ADS1232 | гальваническая развязка |
| Датчик температуры жидкости | DS18B20 | 1-Wire |
| Датчик температуры/влажности воздуха | DHT22 (AM2302) | 1-Wire-подобный |
| Драйвер ШД №1 (pH Up) | A4988 | полноценная обвязка |
| Драйвер ШД №2 (pH Down) | A4988 | полноценная обвязка |
| Интерфейс связи | Modbus RTU / ASCII | RS-485 - SN65HVD72DR |

**Плата:** 4 слоя, 111,1-91,3 мм.

### Прошивка и протокол

- **Modbus:** [RTU / ASCII], адрес по умолчанию — `[1]`,
  скорость — `[9600 8N1 / 19200 8N1]`.
- **Карта регистров:** [ссылка на docs/modbus_registers.md или таблицу ниже].

#### Карта регистров (черновик)

| Адрес | R/W | Описание | Ед. |
|---|---|---|---|
| 0x0000 | R | Проводимость солей | мкСм/см |
| 0x0001 | R | pH | pH |
| 0x0002 | R | Температура жидкости (DS18B20) | °C |
| 0x0003 | R | Температура воздуха (DHT22) | °C |
| 0x0004 | R | Влажность воздуха (DHT22) | % |
| 0x0010 | W | Уставка pH | pH |
| 0x0011 | W | Команда насоса pH Up | — |
| 0x0012 | W | Команда насоса pH Down | — |
| 0x00FF | R/W | Служебный / версия ПО | — |

### Сборка и запуск

1. Подать питание 12В (есть защита от полярности).
2. Проверить индикацию [PWR, RUN].
3. Подключить сборку из катушек Tx_Rx к разъёму [L3].
4. Подключить pH-электрод к разъёму [J5].
5. Подключить DS18B20 к разъёму [18b20].
6. Подключить DHT22 к разъёму [DHT22].
7. Подключить RS-485 (A/B/GND) [J11]  к верхнему уровню.
8. Подать команду по Modbus и убедиться в отклике.

### Безопасность

- Измерительная и цифровая части разделены по земле и питанию.
- Шаговые двигатели питаются от входного напряжения 12В

### Лицензия

Проект распространяется под лицензией **MIT**. Полный текст — в файле [`LICENSE`](LICENSE).

### Автор

[Talgat / RikiDevice] — [rikimtfree@gmail.com]

---

## English version

Control board for an inductive (non-contact) salt conductivity measurement
system of trending type with automatic pH correction.
Supports two control module options: **ESP32 / ESP32-S3-1.47**
and **STM32F407VET6**. Communication over **Modbus (RTU/ASCII)**.

### Features

- **Inductive salt conductivity measurement**
  - Detection coil (Rx) signal acquisition via a **full-featured ADC**
    with **galvanic isolation**.
  - Dedicated **pH** measurement channel (also via isolated ADC).
- **Temperature monitoring**
  - **DS18B20** — liquid temperature (1-Wire).
  - **DHT22 (AM2302)** — ambient air temperature and humidity.
- **Control modules (selectable / footprint for both):**
  - `ESP32` (WROOM-32 and compatible);
  - `ESP32-S3-1.47` (display module);
  - `STM32F407VET6`.
- **Two stepper motors** for dosing:
  - `pH Up` — A4988 driver;
  - `pH Down` — A4988 driver.
- **Modbus** — communication with upper layer (PLC / SCADA / PC).
- **Power and protection** — [specify: input voltage, regulators,
  overcurrent protection, TVS, etc.].

### Hardware

| Block | Implementation | Notes |
|---|---|---|
| MCU | ESP32 / ESP32-S3-1.47 / STM32F407VET6 | selected at build time |
| ADC (Rx coil) | [part] | galvanically isolated |
| ADC (pH) | [part] | galvanically isolated |
| Liquid temperature sensor | DS18B20 | 1-Wire, [parasitic/external power] |
| Ambient temp/humidity sensor | DHT22 (AM2302) | 1-Wire-like, [4.7–10 kΩ pull-up] |
| Stepper driver #1 (pH Up) | A4988 | full support circuitry |
| Stepper driver #2 (pH Down) | A4988 | full support circuitry |
| Communication | Modbus RTU / ASCII | RS-485 [transceiver] |
| Power | [voltage] | [regulators / protections] |

**PCB:** 4 layers, [size, mm], [thickness, mm], [accuracy class].

### Repository layout
PWR_MOD/
├─ PWR_MOD.kicad_pro # KiCad project
├─ PWR_MOD.kicad_sch # schematic
├─ PWR_MOD.kicad_pcb # PCB layout
├─ gerbers/ # Gerber + drill files
├─ docs/ # datasheets, PDFs, notes
│ ├─ schematic.pdf
│ ├─ pcb_top.pdf
│ └─ pcb_bottom.pdf
├─ firmware/ # firmware sources (if any)
├─ .gitignore
└─ README.md
text

### Fabrication

1. Open the project in **KiCad [version]**.
2. Run ERC (schematic) and DRC (PCB) — report saved to `docs/`.
3. Generate Gerber + Excellon (drill) into `gerbers/`.
4. Send `gerbers/*.zip` to the PCB house.
   - Layers: 4 (Top, Inner1, Inner2, Bottom).
   - [Optional] controlled impedance if required for the detection coil.

### Firmware and protocol

- **Modbus:** [RTU / ASCII], default address — `[1]`,
  default baud — `[9600 8N1 / 19200 8N1]`.
- **Register map:** [link to docs/modbus_registers.md or table below].

#### Register map (draft)

| Address | R/W | Description | Unit |
|---|---|---|---|
| 0x0000 | R | Salt conductivity | µS/cm |
| 0x0001 | R | pH | pH |
| 0x0002 | R | Liquid temperature (DS18B20) | °C |
| 0x0003 | R | Ambient temperature (DHT22) | °C |
| 0x0004 | R | Ambient humidity (DHT22) | % |
| 0x0010 | W | pH setpoint | pH |
| 0x0011 | W | pH Up pump command | — |
| 0x0012 | W | pH Down pump command | — |
| 0x00FF | R/W | Service / firmware version | — |

### Assembly and startup

1. Apply power [voltage, polarity].
2. Check indicators [PWR, RUN, ERR].
3. Connect the Rx coil to connector [J?].
4. Connect the pH electrode to connector [J?].
5. Connect DS18B20 to connector [J?].
6. Connect DHT22 to connector [J?].
7. Connect RS-485 (A/B/GND) to the upper layer.
8. Send a Modbus command and verify the response.

### Safety

- Galvanic isolation of the ADC is mandatory: measurement and digital
  sections are separated by ground and power.
- Stepper motors are powered from a separate [voltage] rail and **must not**
  share ground with the isolated ADC.
- When handling pH reagents (Up/Down), observe [safety precautions].

### License

The project is distributed under the MIT license. The full text is in the [`LICENSE`](LICENSE).

### Author

[Talgat / RikiDevice] — [rikimtfree@gmail.com]