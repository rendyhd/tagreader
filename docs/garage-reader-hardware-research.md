# Reader research and simpler hardware options

Research date: 2026-10-04.

## What the supplied evidence establishes

The order screenshot advertises **125 kHz + 13.56 MHz**, with **Wiegand 34 output**.
This establishes the ordered variant, not a measured electrical specification.
The actual reader's sticker is the authority for its wire colors: red +12 V,
black GND, green D0, white D1, blue LED, yellow BEEP, and brown grounded for WG34.

Neither the supplied label nor screenshot states the data-line high voltage,
output circuit, internal pull-up voltage/resistance, or a model number. A 12 V
power rating does **not** establish the D0/D1 signal voltage.

## Manufacturer documentation checked

- [SCIVAS KA-JS05](https://scivas.com/metal-housing-access-readers/dual-frequency-wiegand-switch.html):
  dual-frequency, WG26/34, IP68; specified metal housing, 112 x 76 x 20 mm.
  No data-line voltage specification in the page. This is a comparison product,
  not an identification of the photographed reader.
- [ICStation 7304D / item 12448](https://www.icstation.com/dual-frequency-rfid-reader-wireless-module-1356mhz-125khz-iso14443a-em4100-p-12448.html):
  dual-frequency, WG26/34; specifies idle-high data and 200 us low pulses.
  Its eight-wire mapping includes orange LED and green D1 / white D0,
  which differs from this reader. Its specifications must not be transferred
  to the photographed unit.
- [WEMOS D1 mini](https://www.wemos.cc/en/latest/d1/d1_mini.html):
  all GPIO operates at 3.3 V.
- [Espressif ESP32 datasheet](https://www.espressif.com/sites/default/files/documentation/esp32_datasheet_en.pdf):
  DC input-high range tops out at VDD + 0.3 V. Replacing the D1 mini with a
  standard ESP32 does not make a higher-voltage Wiegand output safe.
- [SparkFun BOB-12009 converter](https://www.sparkfun.com/sparkfun-logic-level-converter-bi-directional.html):
  assembled four-channel 5 V / 3.3 V converter, with components already fitted.

**Research conclusion:** no exact model or trustworthy output-voltage specification
has been established for this unit. There is no evidence supporting direct GPIO
connection. The original transistor interface remains the default for unknown
ordinary 0–12 V signal levels. Its component count is a conservative design
choice, not proof that every Wiegand reader needs eight external resistors.

## Mainboard recommendation

Keep the existing LOLIN D1 mini. The garage firmware already compiles for it and
reports cards to Home Assistant. More CPU power is not required for this job.
A generic ESP32 would still require a suitable electrical interface.

An assembled converter can reduce loose parts. A **5 V / 3.3 V BSS138 converter
such as BOB-12009 is an alternative only after establishing that both reader
data lines use ordinary 0–5 V signaling**. Do not treat this as approval to connect
an unspecified 12 V data output to that arrangement.

## Conditional simpler wiring: confirmed 0–5 V data only

This replaces both NPN input circuits. Power wiring remains as in the main guide.

| Connection | Destination |
|---|---|
| Converter HV | Regulated 5 V from the buck |
| Converter LV | D1 mini 3V3 |
| Converter GND | Common reader/buck/D1 mini ground |
| Reader green D0 | Converter HV1 |
| Converter LV1 | D1 mini D1 / GPIO5 / printed 5 SCL |
| Reader white D1 | Converter HV2 |
| Converter LV2 | D1 mini D2 / GPIO4 / printed 4 SDA |

Reader red still needs its labeled 12 V supply. Brown remains grounded for WG34.
Blue and yellow remain separately insulated.

The BSS138 converter preserves signal polarity. In `garage-reader.yaml`, change
**both Wiegand pins** from `inverted: true` to `inverted: false`. Keep GPIO5 and
GPIO4 and the other firmware settings. Recompile before using this wiring.
Do not make this polarity change when using the original NPN diagram.

This alternative has not been bench-tested with the user's reader. Check voltage
and pulses with the ESP disconnected, then test HA card registration and a harmless
action before enabling door/gate actions. All permissions remain assigned in HA
using Tags and the supplied blueprint; the interface choice does not change that.

