# Garage reader: wiring, installation and card rights

## Hardware shown in your photos

The board is a LOLIN D1 mini V4.0.0 (ESP8266). The reader sticker lists:

| Reader wire | Label / use | Connection |
|---|---|---|
| Red | VCC +12 V | Regulated 12 V DC positive |
| Black | GND | Common DC ground |
| Green | D0 | Input Q1, collector to GPIO5 / board D1 / printed `5 SCL` |
| White | D1 | Input Q2, collector to GPIO4 / board D2 / printed `4 SDA` |
| Blue | LED | Insulate separately; unused |
| Yellow | BEEP | Insulate separately; unused |
| Brown | Ground to output WG34 | Black/common ground, connect with power off |

Confirm brown's instruction on your actual sticker before connecting: wire colors
are not universal. Use WG34 consistently; changing between WG26/WG34 changes tag
IDs and requires reassignment of rights. The firmware accepts both. The photos do
not establish RF frequency or idle data voltage. Test your fob; tags compatible
with the movie reader's PN532 are not necessarily compatible with this reader.

## Parts and wiring

![Wiring diagram](garage-reader-wiring.svg)

Add a regulated 12 V DC supply sized to the reader's specified current plus the
ESP8266, a 12 V-to-5 V buck converter rated for at least 500 mA output, and these
parts **for each data line**:

- One 2N3904 NPN transistor (Q1/Q2).
- One 47 kΩ resistor from reader data to base.
- One 100 kΩ resistor from base to ground.
- One 10 kΩ resistor from collector to board 3V3.
- One 10 kΩ reader-line pull-up fed from 5 V through a 1N4148 diode.

Use 1/4 W resistors. Check your transistor supplier's E/B/C lead order: BC547 and
other substitutions can have different physical pinouts. The diode's **stripe /
cathode faces the 10 kΩ resistor and reader data line**; its anode faces 5 V. This
provides an idle high for open-collector readers while blocking a higher reader
idle level from feeding back into 5 V.

Connect the emitter to ground and collector to the selected GPIO. The reader's
high turns the transistor on and makes the GPIO low; reader low makes GPIO high.
Both firmware inputs therefore require `inverted: true`. This proposed interface
handles ordinary 0–12 V logic, including open-collector or driven outputs. It is
not a certified outdoor lightning/surge isolator. Keep the GPIO wires short.

Power reader red from 12 V and board **VBUS** from the buck's regulated 5 V.
Connect black, both emitters, buck negative and board GND together. Board **3V3**
supplies only the collector pull-ups. Never feed 12 V to VBUS, 3V3 or GPIO.
For USB flashing, disconnect external 5 V from VBUS to avoid feeding two sources
together. Reader 12 V may remain powered with common ground.

No gate control wires connect to this reader. Home Assistant commands your
existing gate/door controller. If you need a new controller, use a separate
isolated dry-contact relay according to the gate manufacturer's control-input
instructions. Those terminals cannot be identified from these photos.

## Install and add the reader

1. Import `garage-reader.yaml` into ESPHome Device Builder and place
   `garage_reader.h` beside it. The PN532/movie YAML is for other hardware.
2. Merge `garage-secrets.example.yaml` into private `secrets.yaml`. Set Wi-Fi, a
   new 32-byte base64 API key and a unique OTA password. Generate a key with:
   ```sh
   python -c "import secrets,base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"
   ```
3. Compile and flash over USB. CLI: `esphome run garage-reader.yaml`. Future
   updates can use OTA. The reproducible toolchain is ESPHome 2026.8.2 / Arduino
   3.1.2; use ESPHome 2026.8.2 or newer.
4. Add discovered **Garage Card Reader** under **Settings > Devices & services >
   ESPHome**, supplying your key. If discovery fails, add it by IP address.
5. In the ESPHome integration entry's **Configure** options enable **Allow the
   device to perform Home Assistant actions**. This is required for tag reporting.
6. Ensure HA's Tags integration is loaded (`default_config:` normally loads it;
   otherwise add `tag:` to `configuration.yaml` and restart). Wait for the
   **Ready for Cards** diagnostic entity to turn on.

There is no open fallback hotspot or reader web server. Recovery uses USB or OTA
with your configured credentials. Never flash the automated dummy-credential build.

## Read a card, add it, assign rights

1. With access automations disabled, scan a card once.
2. Open **Settings > Tags**. HA automatically adds the scanned tag, such as
   `wg34-12345678`. Name it **Rendy garage card**. The ID is a decimal Wiegand
   payload, not necessarily a printed card number or phone/movie-reader UID.
3. Under **Settings > Automations & scenes > Blueprints > Import blueprint**, use:
   ```text
   https://github.com/rendyhd/tagreader/blob/codex/garage-gate-reader/blueprints/GarageCardAction.yaml
   ```
   Or copy the blueprint to
   `/config/blueprints/automation/rendyhd/GarageCardAction.yaml` and reload blueprints.
4. Create an automation from **Garage card - assign door or script rights**.
   Select this reader, paste the exact tag ID, and choose its permitted actions
   using HA's normal action editor. Optional conditions can limit access hours,
   require a guest-access helper, or check a door state.
5. Save as **Rendy card - open garage**. Create another automation for another
   card/reader or another set of rights. No firmware change is needed.

Choose your real entities in the UI. Examples:

```yaml
# Dedicated gate opening command
- action: cover.open_cover
  target:
    entity_id: cover.garage_gate

# Or a script, called directly so cooldown starts after it finishes
- action: script.open_side_door
```

`script.turn_on` also works but launches the script asynchronously. For toggle-only
gate buttons use a script or condition that checks a reliable closed-state sensor
so repeated scans cannot close a gate that is already opening.

You may skip the blueprint and create an automation from the card's Tags page.
Set **Tag scanned** to this card and restrict its **Device** to this reader.
Do not trigger access from **Last Card** sensor changes: that diagnostic state
can be resent on reconnect and is not a fresh scan.

To revoke a lost card, disable/delete **all automations granting it rights**.
Deleting or renaming its Tags entry does not revoke automations matching its ID;
another scan can recreate that entry. A card can have multiple rights automations.

## Bench checks before enabling door actions

1. Check soldering, ground continuity, transistor lead order and diode orientation
   with power off. Adjust the buck to 5.0 V before attaching VBUS.
2. With GPIOs disconnected, measure reader green/white against black. Idle levels
   must be ordinary 0–12 V logic. Powered interface collectors should idle low
   and never exceed 3.3 V. A scope/logic analyzer should show a rise toward 3.3 V
   for every reader low pulse.
3. Connect GPIOs. Strap brown to ground with power off, then reboot. A scan should
   show **Last Frame Bits = 34** and **Last Card = wg34-...**. If Bits updates
   but Last Card does not, check polarity/wiring/parity with temporary DEBUG logs.
   If nothing changes, check reader power and card compatibility. The interface
   requires `inverted: true` on both pins.
4. Verify the Tags entry appears. If Last Card changes but Tags does not, check
   readiness, API permission, Tags integration and logs.
5. Assign a harmless notification first. Verify the selected card triggers it,
   other cards do not, and another reader with the same ID does not. Assign a
   second card a different action and check each gets only its assigned rights.
6. Hold a card in the field and check for repeated actions. Re-present after at
   least 2.5 s with no frames from that card and after cooldown. Firmware limits
   all scan reports to one per 2 s; the blueprint discards invocations during its
   actions and the extra 5 s default cooldown.
7. Disconnect HA/Wi-Fi, scan, and reconnect. No stored scan should execute. Remove
   and re-present after Ready for Cards returns. Logger-only connections do not
   count as HA. Reboot with a held card and test startup suppression too.
8. Disable its rights automation and verify it no longer acts. Test conditions,
   then replace the harmless action with your actual door/gate/script action.

Wiegand has no reliable removal signal. The quiet period is a repeat filter, not
proof of removal. First frames emitted only after startup readiness or repeat
gaps longer than the quiet period may count as new presentations. Adjust
`card_quiet_ms` for your hardware. The blue/yellow inputs remain disconnected;
the reader's own beep/LED means a physical read, not access granted.

Keep the Wi-Fi controller and connections inside the secured area. Wiegand and
card IDs can be copied/replayed; this provides UID-based automation, not
cryptographic access control. Retain the gate's normal obstruction/safety controls.

## Sources

- [WEMOS D1 mini: board and 3.3 V GPIO](https://www.wemos.cc/en/latest/d1/d1_mini.html)
- [ESPHome Wiegand](https://esphome.io/components/wiegand/)
- [ESPHome native API and tag reporting permission](https://esphome.io/components/api/)
- [Home Assistant Tags](https://www.home-assistant.io/integrations/tag/)
- [Tag trigger and reader restriction](https://www.home-assistant.io/docs/automation/trigger/#tag-trigger)
- [2N3904 ratings and pinout](https://www.onsemi.com/pdf/datasheet/2n3903-d.pdf)

Your sticker supplies the wire colors. The input circuit is a proposed design
that still requires the physical checks above.
