# Movie Time NFC player for Kodi

A fork of [adonno/tagreader](https://github.com/adonno/tagreader) for a child’s
DVD/Blu-ray case player. Insert a case to start its movie in Kodi through Home
Assistant. Play, Pause and Stop work as labelled; removing the case stops playback.

**Start with [the setup guide](docs/movie-time-setup.md).** It includes installation,
movie mapping, wiring, recovery and the checks to perform on your assembled player.

| File | Purpose |
|---|---|
| [movie-player.yaml](movie-player.yaml) | Firmware configuration for the original ESP8266 D1 mini |
| [movie_reader.h](movie_reader.h) | Required reader logic; put it beside the YAML |
| [secrets.example.yaml](secrets.example.yaml) | Copy/merge into your private ESPHome secrets file |
| [MovieTimeKodi blueprint](blueprints/MovieTimeKodi.yaml) | Select your reader, buttons and Kodi in Home Assistant |
| [Review and issue triage](docs/movie-time-review.md) | What was reviewed, addressed and still needs hardware testing |

The wiring is unchanged: PN532 on D1/D2, LED on D8, passive buzzer on D7,
Play on D5, Pause on D6, Stop on D0 with its external 10 kΩ pull-up to 3V3.

This version reads existing Home Assistant tag IDs and ordinary tag UIDs. It uses
persistent entity states, debounces case removal, preserves mute preferences and
avoids automatic playback on reconnect. Music-provider URL routing and tag writing
are absent from the movie firmware. The original `tagreader.yaml` remains for
reference and rollback; [its legacy instructions](docs/legacy-tagreader.md) do
not describe the movie player.

The tested firmware toolchain is **ESPHome 2026.8.2 / ESP8266 Arduino 3.1.2**.
Home Assistant tests execute the real blueprint with simulated Kodi responses.
Automated validation cannot certify your physical NFC reception, buzzer, wiring
or movie library: finish the bench checks in the setup guide before final assembly.

## Development checks

```sh
clang++ -std=c++17 -Wall -Wextra -Werror -fsanitize=address,undefined tests/test_reader.cpp -o /tmp/movie-reader-test
/tmp/movie-reader-test
python -m pytest -q tests/test_home_assistant.py
python tests/prepare_compile.py
esphome compile .test-build/movie-player.yaml
```

For the Home Assistant tests use Python 3.14.2+ and `requirements-test.txt`.
Install ESPHome 2026.8.2 in a separate Python 3.12 environment. The compile helper
creates an isolated build using dummy credentials; never flash that test binary.
Original project attribution and GPL licensing are retained in [LICENSE](LICENSE).
