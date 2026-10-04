"""Prepare an isolated build; the test binary must never be flashed."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.test-build' / 'garage'
OUT.mkdir(parents=True, exist_ok=True)
for name in ('garage-reader.yaml', 'garage_reader.h'):
    shutil.copy2(ROOT / name, OUT / name)
(OUT / 'secrets.yaml').write_text(
    'wifi_ssid: compile-test-network\n'
    'wifi_password: compile-test-password-only\n'
    'garage_reader_api_key: AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=\n'
    'garage_reader_ota_password: compile-test-password-only\n', encoding='utf-8'
)
print(OUT / 'garage-reader.yaml')
