import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
import json
import re
from pathlib import Path

FILE = Path("data/players.json")
REPORT = Path(PROJECT_ROOT) / "data" / "broken_players_report.txt"

text = FILE.read_text(encoding="utf-8", errors="replace")
lines = text.splitlines()

# Her oyuncu kaydının başlangıcını bul:
# players.json formatında oyuncular:
#
#   {
#     "id": ...
#
starts = []

for i, line in enumerate(lines):
    if re.match(r"^\s{2}\{\s*$", line):
        starts.append(i)

print(f"Toplam oyuncu bloğu bulundu: {len(starts)}")
print("Gerçekten bozuk kayıtlar kontrol ediliyor...\n")

broken = []
valid = 0

for index, start in enumerate(starts):

    if index + 1 < len(starts):
        end = starts[index + 1]
    else:
        end = len(lines)

    block_lines = lines[start:end]

    # Sonraki oyuncudan önceki virgülü temizle
    while block_lines and not block_lines[-1].strip():
        block_lines.pop()

    if block_lines and block_lines[-1].strip() == ",":
        block_lines.pop()

    block = "\n".join(block_lines).strip()

    # Son oyuncuda array kapanışı varsa çıkar
    if block.endswith("]"):
        block = block[:-1].rstrip()

    # Oyuncu objesinin sonundaki virgülü çıkar
    if block.endswith(","):
        block = block[:-1]

    try:
        json.loads(block)
        valid += 1

    except json.JSONDecodeError as e:

        start_line = start + 1

        # Oyuncu adı / id bulmaya çalış
        name_match = re.search(
            r'"name"\s*:\s*"([^"]*)"',
            block
        )

        id_match = re.search(
            r'"id"\s*:\s*"([^"]*)"',
            block
        )

        name = (
            name_match.group(1)
            if name_match
            else "ADI BULUNAMADI"
        )

        player_id = (
            id_match.group(1)
            if id_match
            else "ID BULUNAMADI"
        )

        actual_error_line = start_line + e.lineno - 1

        broken.append({
            "start": start_line,
            "error_line": actual_error_line,
            "name": name,
            "id": player_id,
            "error": e.msg,
            "block": block
        })


print("=" * 70)
print(f"Sağlam oyuncu: {valid}")
print(f"BOZUK oyuncu: {len(broken)}")
print("=" * 70)

with REPORT.open(
    "w",
    encoding="utf-8"
) as f:

    f.write(
        f"Sağlam oyuncu: {valid}\n"
        f"Bozuk oyuncu: {len(broken)}\n\n"
    )

    for number, item in enumerate(broken, 1):

        result = (
            f"{number}. BOZUK KAYIT\n"
            f"Oyuncu: {item['name']}\n"
            f"ID: {item['id']}\n"
            f"Kayıt başlangıç satırı: {item['start']}\n"
            f"Hata satırı: {item['error_line']}\n"
            f"Hata: {item['error']}\n"
            + "-" * 70
            + "\n"
        )

        print(result)

        f.write(result)
        f.write(item["block"])
        f.write("\n")
        f.write("=" * 70)
        f.write("\n\n")


print()
print(f"Detaylı rapor oluşturuldu: {REPORT}")
