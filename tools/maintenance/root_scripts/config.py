import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
# Bekleme süresi (saniye)
DELAY = 30

# Dosya yolları
PLAYERS_FILE = _path_os.path.join(PROJECT_ROOT, "data", "players.json")
PROCESSED_TEAMS_FILE = _path_os.path.join(
    PROJECT_ROOT,
    "data",
    "processed_teams.json",
)
LOG_FILE = _path_os.path.join(PROJECT_ROOT, "data", "logs.txt")
