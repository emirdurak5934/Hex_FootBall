import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
import json
from pathlib import Path
from datetime import datetime

DATA_DIR = Path("data")
CURRENT_FILE = DATA_DIR / "players.json"

# players_before_ ile başlayan bütün yedekleri bul
backup_files = sorted(
    DATA_DIR.glob("players_before_*.json"),
    key=lambda p: p.stat().st_mtime,
    reverse=True
)

if not CURRENT_FILE.exists():
    raise FileNotFoundError("data/players.json bulunamadı.")

if not backup_files:
    raise FileNotFoundError(
        "data klasöründe players_before_*.json yedeği bulunamadı."
    )


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


print("Mevcut players.json yükleniyor...")
current_players = load_json(CURRENT_FILE)

print(f"Mevcut oyuncu sayısı: {len(current_players)}")

current_ids = {
    player.get("id")
    for player in current_players
    if player.get("id")
}

print()
print(f"Bulunan yedek sayısı: {len(backup_files)}")

missing_players = {}
backup_stats = []

for backup in backup_files:
    try:
        players = load_json(backup)
    except Exception as e:
        print(f"ATLANDI (okunamadı): {backup.name}")
        print(f"  Hata: {e}")
        continue

    found_here = 0

    for player in players:
        player_id = player.get("id")

        if not player_id:
            continue

        if player_id in current_ids:
            continue

        if player_id in missing_players:
            continue

        missing_players[player_id] = player
        found_here += 1

    backup_stats.append(
        (backup.name, len(players), found_here)
    )

    print(
        f"{backup.name}: "
        f"{len(players)} oyuncu | "
        f"{found_here} yeni eksik bulundu"
    )


print()
print("=" * 60)
print(f"Toplam eksik oyuncu bulundu: {len(missing_players)}")
print("=" * 60)

if not missing_players:
    print("Eklenecek eksik oyuncu yok.")
    raise SystemExit


# Önce kurtarılacak oyuncuların listesini rapora yaz
report_file = DATA_DIR / "missing_players_to_restore.txt"

with report_file.open("w", encoding="utf-8") as f:
    for player_id, player in missing_players.items():
        name = player.get("name", "İsim yok")
        f.write(f"{player_id} | {name}\n")

print(f"Liste oluşturuldu: {report_file}")

# Mevcut players.json için ekstra güvenlik yedeği
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

safety_backup = (
    DATA_DIR /
    f"players_before_missing_restore_{timestamp}.json"
)

with safety_backup.open("w", encoding="utf-8") as f:
    json.dump(
        current_players,
        f,
        ensure_ascii=False,
        indent=2
    )

print(f"Güvenlik yedeği oluşturuldu: {safety_backup}")

# Eksik oyuncuları mevcut listeye ekle
restored_players = current_players + list(
    missing_players.values()
)

# ID tekrar kontrolü
seen = set()
duplicates = []

for player in restored_players:
    player_id = player.get("id")

    if not player_id:
        continue

    if player_id in seen:
        duplicates.append(player_id)

    seen.add(player_id)

if duplicates:
    print()
    print("UYARI: Duplicate ID bulundu.")
    print(duplicates[:20])
    print("Dosya kaydedilmedi.")
    raise SystemExit


# Önce geçici dosyaya yaz
temp_file = DATA_DIR / "players_restored_temp.json"

with temp_file.open("w", encoding="utf-8") as f:
    json.dump(
        restored_players,
        f,
        ensure_ascii=False,
        indent=2
    )

# Tekrar JSON olarak açıp doğrula
test_players = load_json(temp_file)

if len(test_players) != len(restored_players):
    raise RuntimeError(
        "Geçici dosya doğrulaması başarısız."
    )

# Her şey sağlamsa players.json ile değiştir
temp_file.replace(CURRENT_FILE)

print()
print("=" * 60)
print("KURTARMA TAMAMLANDI")
print("=" * 60)
print(f"Eski oyuncu sayısı : {len(current_players)}")
print(f"Eklenen oyuncu     : {len(missing_players)}")
print(f"Yeni oyuncu sayısı : {len(restored_players)}")
print()
print("players.json başarıyla güncellendi.")