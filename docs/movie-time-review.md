# Movie Time review — 8 September 2026

## Scope and result

The starting fork and upstream both point to `a8bb6fc43e5a687503d1b43edb32855d0de7050a`.
The review inventoried **179 issues**, triaged **all 42 open issues**, inspected
relevant closed reports and discussion threads (67 issue threads collected), and
reviewed **all six open pull-request diffs**. Issue reports are evidence of a
reported symptom, not proof that every device or current version has that fault.

The target is the original ESP8266 D1 mini + separate red PN532 + WS2812 + passive
buzzer, with Play/Pause/Stop buttons and the existing 10 kΩ D0 pull-up. The user
confirmed Kodi through Home Assistant, and **removal must stop the movie**.

`movie-player.yaml` is a separate, focused configuration. The original
`tagreader.yaml` remains intact for reference/rollback. The stock upstream YAML
also compiles on the tested ESPHome version; open issue count alone does not
establish that it is universally broken.

## Findings that matter for this player

| Finding | Evidence and consequence | Change / limit |
|---|---|---|
| Runtime memory pressure during tag actions | [#261](https://github.com/adonno/tagreader/issues/261) contains decoded OOM traces through NfcTag copies; [#238](https://github.com/adonno/tagreader/issues/238) reports Android NDEF crashes. The original action tree carries tag values through conditions/delays. | One synchronous parse action, no asynchronous NfcTag storage, first valid HA URI only, smaller feature set. This does not harden ESPHome’s entire NFC parser or prove runtime memory stability. |
| Held cases need different behaviour from tap cards | [#222](https://github.com/adonno/tagreader/issues/222), [#3](https://github.com/adonno/tagreader/issues/3), [#243](https://github.com/adonno/tagreader/issues/243). Current PN532 callbacks report transitions; repeated successful polls of one UID do not produce new on_tag callbacks. | Presence state waits for explicit removal/fault, with 300 ms insertion and 1500 ms absence debounce. No last-scan timeout that would eject a held case. |
| Brief absence, direct swaps and stale removal | PN532 can report a failed read as removal and can report B without a separate removal of A. | State helper ignores stale A removals after B, cancels brief dropouts and handles direct swaps. Tests include long holds and clock rollover. |
| Reader request failures can leave a stale case | The current PN532 `update()` warning path returns without calling on_tag_removed. | Persistent warning/failure for 1500 ms clears selection. Brief warnings do not. Reinsert after a sustained fault; a permanently failed setup still needs hardware recovery. |
| Event loss and reconnect replay | Reader events can be dropped before HA subscribes; transient events do not describe present state after reconnect. | Use ordinary selected-tag/button entities. No custom event subscription or device-to-HA action permission required. Initial/reconnected state never auto-starts playback. |
| Buttons need electrical and temporal care | D0 has no pull-up/interrupt support; fast presses can be coalesced by API batching. | D5/D6 internal pull-ups; D0 external 10 kΩ to 3V3 and polling; debounce and zero API batching delay. HA triggers only off→on edges from selected entities. |
| Existing HA tags must keep their IDs | [#231](https://github.com/adonno/tagreader/issues/231), [#40](https://github.com/adonno/tagreader/issues/40). Raw UID and stored HA ID are different. | Preserve first canonical `https://www.home-assistant.io/tag/…` URI ID, otherwise UID. Ignore Android/app and unrelated URI records. Show both selected ID and UID. |
| Buzzer preferences and startup noise | [#126](https://github.com/adonno/tagreader/issues/126), [#184](https://github.com/adonno/tagreader/issues/184); original boot actions force switches on. | No startup tune/forced enable; saved mute preferences. Valid RTTTL durations. [#305](https://github.com/adonno/tagreader/issues/305) has no confirmed universal fix; physical Test Buzzer remains required. |
| Kodi can silently reject commands | HA Kodi integration catches some protocol/transport exceptions and logs them. | Track a requested session, react to Player.Open error events, and confirm idle before clearing a stopped session. No claim that a scan beep confirms successful media playback. |
| Two automations/readers can interfere | [#218](https://github.com/adonno/tagreader/issues/218). Generic unfiltered event listeners can affect other players. | Blueprint chooses exact entities/player, keeps a dedicated session helper and serializes player calls. Remove old overlapping movie automations. |
| Unpinned builds and stale instructions | [#295](https://github.com/adonno/tagreader/issues/295), closed [#294](https://github.com/adonno/tagreader/issues/294), [#232](https://github.com/adonno/tagreader/issues/232). | Pinned ESPHome 2026.8.2 / Arduino 3.1.2 and actual compile CI; local files, current OTA/encryption setup and rollback guidance. |

## All open issues

“Addressed” here concerns this fork’s scope, not closing the upstream issue or
claiming its hardware symptoms were reproduced and cured.

| Issue | Assessment | Decision for Movie Time |
|---|---|---|
| [#305 — Buzzer No Longer Working?](https://github.com/adonno/tagreader/issues/305) | Unresolved hardware/runtime report | No proven general fix in the discussion. Valid RTTTL durations, isolated buzzer test and preserved mute setting; verify the actual passive buzzer. |
| [#304 — Tag reader not working as expected](https://github.com/adonno/tagreader/issues/304) | Setup and interpretation | Separate ESPHome dashboard discovery from HA integration availability. Selected Tag reports detection; the Kodi map decides what plays. |
| [#299 — Music Assistant library uri support](https://github.com/adonno/tagreader/issues/299) | Outside this build | Music Assistant URI formats are not needed for Kodi movie mapping. |
| [#295 — ESPHome 2025.7.2 has broken my tagreader](https://github.com/adonno/tagreader/issues/295) | Version regression risk | Pin and compile ESPHome 2026.8.2. Do not silently track stable/beta/dev; hardware reboot behaviour still needs testing. |
| [#293 — tagreader lite (low mem version)](https://github.com/adonno/tagreader/issues/293) | Relevant simplification | Follow the small-reader direction. Keep HA-ID reading, remove music routing and write/erase actions; add movie presence and buttons. |
| [#286 — Rejected RFIDs   -> Buzzer sound and LED red ?](https://github.com/adonno/tagreader/issues/286) | Handled at movie mapping | Unmapped tags do not start movies. A scan beep is not a claim that Kodi accepted the selection. |
| [#285 — wrong i2c address?](https://github.com/adonno/tagreader/issues/285) | Hardware/configuration | Explicit D1/SCL, D2/SDA, 0x24 and I2C mode. Do not change the address to hide wiring or board-mode faults. |
| [#276 — ESP32-H2 using zigbee connection?](https://github.com/adonno/tagreader/issues/276) | Outside this build | ESP32-H2 and Zigbee are different hardware and transport. |
| [#275 — How can I add a physical switch for trigger an action like "stop"](https://github.com/adonno/tagreader/issues/275) | Implemented | Play D5, Pause D6, Stop D0; correct pull-ups, polling on D0 and HA state triggers. |
| [#272 — unfortunate yaml shortening !](https://github.com/adonno/tagreader/issues/272) | Implemented setup change | Use local, explicit firmware files. No dashboard import that silently points back upstream. |
| [#270 — Reading JSON or URL](https://github.com/adonno/tagreader/issues/270) | Outside this build | Arbitrary JSON/URLs, phone emulation and Ethernet are not movie-case requirements. |
| [#267 — Sensor doesn't read tag](https://github.com/adonno/tagreader/issues/267) | Hardware verification required | Mode/wiring/power/tag reception must be checked with Reader Healthy, Selected Tag and the actual boards. |
| [#266 — Documentation on types of tags that work with the device.](https://github.com/adonno/tagreader/issues/266) | Documented | Use ordinary compatible 13.56 MHz NTAG tags or known-working cards; test stickers in both case formats. |
| [#261 — [WORKAROUND FOUND] ESPHome 2024.5.0 Breaks Tag Reader](https://github.com/adonno/tagreader/issues/261) | Mitigated, not claimed physically fixed | Remove delayed/deep action trees carrying NfcTag copies; parse synchronously and run feedback afterwards. Compile/heap figures are not runtime heap proof. |
| [#257 — Authentication failed](https://github.com/adonno/tagreader/issues/257) | Documented UID fallback | Protected MIFARE content may fail authentication; a readable UID can still select a mapped movie. |
| [#250 — Sandwich Version DIY Available?](https://github.com/adonno/tagreader/issues/250) | Outside this build | User has separate original boards and a custom printed enclosure, not a sandwich-board redesign. |
| [#248 — Compile of tagreader.yaml fails in ESPHome](https://github.com/adonno/tagreader/issues/248) | Build-host problem | Killed compiler process is not proof of an ESP runtime crash. Run the pinned build and retain its logs. |
| [#246 — Component pn532 took a long time for an operation](https://github.com/adonno/tagreader/issues/246) | Driver/hardware limit | PN532 operations can block. No cosmetic suppression of warnings; stable selection and bench testing cover the user-facing effect. |
| [#243 — remove tag](https://github.com/adonno/tagreader/issues/243) | Implemented | Explicit selected-case state becomes empty after absence debounce; HA stops its active movie session. |
| [#242 — custom code compatibility](https://github.com/adonno/tagreader/issues/242) | Implemented update boundary | Explicit local files and pinned CI; no uncontrolled upstream package changes. |
| [#241 — No more badge readers](https://github.com/adonno/tagreader/issues/241) | Needs hardware/runtime verification | Presence/fault diagnostics added. Sustained PN532 warnings clear selection, but failed hardware initialization still needs repair/restart. |
| [#238 — Scanned NTAG215 written by Home Assistant Android App caused post read crash](https://github.com/adonno/tagreader/issues/238) | Parser path simplified | Ignore non-URI Android records; accept first canonical HA tag URI or UID fallback. No delayed NfcTag copies in application actions. |
| [#236 — Error: Could not find one of 'package.json' manifest files in the package](https://github.com/adonno/tagreader/issues/236) | Build configuration | Specify d1_mini, current OTA syntax and exact tested toolchain; damaged PlatformIO installations are separate setup problems. |
| [#234 — web.esphome.io says "Failed to execute 'open' on 'SerialPort': Failed to open serial port.](https://github.com/adonno/tagreader/issues/234) | USB setup | Use a data-capable micro-USB cable and a free serial port; firmware cannot repair a cable/driver/port-access problem. |
| [#233 — image has dip switches in wrong position](https://github.com/adonno/tagreader/issues/233) | Corrected documentation | Switch 1 ON, switch 2 OFF for the original red PN532; printed labels take priority over old pictures. |
| [#232 — esphome version 1.16.0 ?](https://github.com/adonno/tagreader/issues/232) | Corrected documentation | Movie Time specifies tested ESPHome 2026.8.2 instead of the obsolete 1.16.0 instruction. |
| [#231 — Scanning a card from the HA app gives a different ID than from the tagreader](https://github.com/adonno/tagreader/issues/231) | Implemented ID compatibility | Read the stored HA URI ID before falling back to raw UID; show Selected UID separately. |
| [#228 — Connection encryption error (with api encryption key)](https://github.com/adonno/tagreader/issues/228) | Encryption retained | Encrypted API with user-specific key; reduced application complexity. Disabling encryption is not presented as a general fix. |
| [#227 — readopting D1 mini into ESPHome](https://github.com/adonno/tagreader/issues/227) | Avoided adoption loop | Explicit name, no automatic MAC suffix or dashboard-import back to upstream; migration preserves the existing name/key when desired. |
| [#225 — Add Option for the service write_music_tag to play local media.](https://github.com/adonno/tagreader/issues/225) | Outside this build | Kodi library IDs/file paths are mapped in HA; no music-writing service is needed. |
| [#223 — Missing documentation about Apple Music, Spotify and Sonos](https://github.com/adonno/tagreader/issues/223) | Outside this build | Music-provider routing removed from the movie configuration; legacy firmware remains separately documented. |
| [#222 — Wifi Disconnecting](https://github.com/adonno/tagreader/issues/222) | Relevant physical risk | Held-tag interference reported for closely stacked boards. The custom enclosure separates PN532 and ESP; verify a long held-case test. Firmware debounce cannot fix RF interference. |
| [#221 — disable automatic tag addition](https://github.com/adonno/tagreader/issues/221) | Avoided for movie firmware | Publish Selected Tag entity state, not automatic legacy tag_scanned events for every unknown tag. |
| [#220 — BUlk converter not enough power to run multiple devices](https://github.com/adonno/tagreader/issues/220) | Power hardware | Keep USB power and check actual supply/cable under load. No changes to unrelated bulk power installations. |
| [#217 — Upgrading to esp32](https://github.com/adonno/tagreader/issues/217) | Outside this build | No forced ESP32 migration. Target the original ESP8266 D1 mini and its existing pins. |
| [#215 — Requesting tag read failed! error](https://github.com/adonno/tagreader/issues/215) | Detection added | Persistent request warnings clear selection; wiring/PN532 failures still require physical investigation. |
| [#214 — Timed out waiting for readiness from PN532 error](https://github.com/adonno/tagreader/issues/214) | Driver/hardware diagnosis | Explicit mode, pins, speed and health diagnostics. A failed setup is not magically repaired by changing event code. |
| [#203 — Can't get tag read](https://github.com/adonno/tagreader/issues/203) | Hardware setup | Use the original wiring table and bench-test NFC independently of HA movie playback. |
| [#187 — tagreader not reading tags?](https://github.com/adonno/tagreader/issues/187) | Hardware setup | Reports include reversed wiring/mode errors; guide and tests separate these from movie automation problems. |
| [#175 — Unable to write config from ESPHome](https://github.com/adonno/tagreader/issues/175) | Outside this board variant | ESP32 configuration/LEDC changes do not apply to the user’s ESP8266; current firmware is compiled for the correct board. |
| [#82 — actually read contents of NFC tag](https://github.com/adonno/tagreader/issues/82) | Scoped read support | Retain canonical HA tag IDs, not arbitrary music/content dispatch or tag-writing functionality. |
| [#81 — Mqtt instead of homeassistant API](https://github.com/adonno/tagreader/issues/81) | Outside this build | Native ESPHome API fits the existing HA/Kodi installation; no MQTT broker is required. |

## Open pull requests

| PR | Review decision |
|---|---|
| [#296](https://github.com/adonno/tagreader/pull/296) — ESPHome 2025.8 | Adds `homeassistant_services: true`. Movie Time uses state entities and has no custom firmware-to-HA service/event calls; the flag is unnecessary here. |
| [#292](https://github.com/adonno/tagreader/pull/292) — lite | Good direction for an ESP8266, but retains old boot/mute and write-action behaviour in parts and does not implement a held movie case, its buttons or Kodi. Use a dedicated configuration, not a blind merge. |
| [#251](https://github.com/adonno/tagreader/pull/251) — I²C speed | A lower bus speed is plausible for longer hand-wired connections. Explicit 100 kHz is used, but no speed change can guarantee recovery from bad wiring or RF interference. |
| [#170](https://github.com/adonno/tagreader/pull/170) — sun brightness | Adds unnecessary web/time/sun features for this player; also uses latitude for longitude. Not adopted. |
| [#164](https://github.com/adonno/tagreader/pull/164) — MQTT | Different transport and old platform/OTA/light configuration. Not needed with existing HA/Kodi. |
| [#133](https://github.com/adonno/tagreader/pull/133) — documentation | Some useful explanatory ideas, but mixes old service syntax/hardware assumptions. Movie Time gets a current, hardware-specific guide. |

## Validation and remaining physical work

The checked-in tests exercise the same C++ parser/state helper used by firmware,
including 10,000 cycles under address/undefined-behaviour sanitizers. HA tests
validate the actual blueprint with HA’s schema/selector/trigger machinery and run
its real action sequences against simulated Kodi services. They also attach real
state/event triggers to check reader/player filtering.

See [validation results](movie-time-validation.json) and the branch’s **Movie Time
checks** workflow for exact build/test versions and results. Linker RAM/flash
figures are static allocations; they do not measure runtime free heap or prove
absence of hardware resets. The test firmware contains dummy credentials and is
not an installable personal image.

Still required on the user’s hardware: NFC range/alignment in both case formats,
a prolonged held-case test, actual buzzer/LED response, switch operation, correct
Kodi movie IDs/paths, HA entity selection and network-loss recovery. A failed
Wi-Fi/HA/Kodi connection cannot deliver an immediate Stop command; the blueprint
retains the session for cleanup when Kodi reconnects. After an unconfirmed stop
while Kodi remains connected, check the trace and press Stop again. The session
helper tracks this automation’s requested movie, not arbitrary later media
started with another remote.

No changes were flashed to a device or applied to a live HA/Kodi installation.

## Primary references

- [Upstream source at the reviewed commit](https://github.com/adonno/tagreader/tree/a8bb6fc43e5a687503d1b43edb32855d0de7050a)
- [ESPHome PN532 behaviour and wiring](https://esphome.io/components/binary_sensor/pn532/)
- [ESPHome 2026.8.2 PN532 implementation](https://github.com/esphome/esphome/blob/2026.8.2/esphome/components/pn532/pn532.cpp)
- [ESP8266 pin restrictions](https://esphome.io/components/esp8266/)
- [WEMOS D1 mini electrical documentation](https://www.wemos.cc/en/latest/d1/d1_mini.html)
- [ESPHome API state and action behaviour](https://esphome.io/components/api/)
- [Home Assistant Kodi integration](https://www.home-assistant.io/integrations/kodi/)
- [HA 2026.9.1 Kodi command handling](https://github.com/home-assistant/core/blob/2026.9.1/homeassistant/components/kodi/media_player.py)
- [Kodi JSON-RPC API](https://kodi.wiki/view/JSON-RPC_API/v13.5)
