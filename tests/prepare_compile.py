"""Create an isolated firmware build with public, non-working test credentials."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.test-build'
OUT.mkdir(exist_ok=True)
for name in ('movie-player.yaml', 'movie_reader.h'):
    shutil.copy2(ROOT / name, OUT / name)
(OUT / 'secrets.yaml').write_text(
    'wifi_ssid: compile-test-network\n'
    'wifi_password: compile-test-password-only\n'
    'movie_time_api_key: AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=\n'
    'movie_time_ota_password: compile-test-password-only\n'
)
print(OUT / 'movie-player.yaml')
