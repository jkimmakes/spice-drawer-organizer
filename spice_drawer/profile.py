"""The physically tested Ball jar profile; dimensions are millimetres."""
from pathlib import Path
import hashlib
import json

PACKAGE = Path(__file__).resolve().parent
DATA = PACKAGE / "data" / "ball-4oz"
PITCH = (75.8, 62.5)
ORIGIN = (-37.9, -1.6619453570665357, 0.0)
GAP = 0.30
LOADED_HEIGHT = 76.154
MAX_MODULE = 3

def check_assets():
    manifest = json.loads((DATA / "assets.json").read_text())
    for name, sha in manifest["files"].items():
        if Path(name).name != name:
            raise ValueError("Invalid profile asset name")
        path = DATA / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            raise ValueError(f"Profile asset changed: {name}")
    return manifest
