"""Export and check the one-piece Ball jar label guide (requires OpenSCAD)."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from spice_drawer.mesh import read_mesh, verify
from spice_drawer.normalize import normalize

SOURCE = ROOT / "spice_drawer/cad/label_jig.scad"
OUTPUT = ROOT / "accessories/label-jig"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openscad", default=shutil.which("openscad") or "openscad")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    stl = OUTPUT / "ball_4oz_label_jig.stl"

    def cad(path, **settings):
        command = [args.openscad, "--hardwarnings", "--export-format", "binstl",
                   "-o", str(path)]
        for key, value in settings.items():
            command += ["-D", key + "=" + json.dumps(value)]
        result = subprocess.run(command + [str(SOURCE)], capture_output=True,
                                text=True, timeout=120)
        log = result.stdout + result.stderr
        if "WARNING:" in log or "ERROR:" in log:
            raise RuntimeError(log)
        return result, log

    if not args.verify_only:
        result, log = cad(stl, part="jig")
        if result.returncode or not stl.exists():
            raise RuntimeError(log)
        normalize(stl)
    mesh = verify(*read_mesh(stl))
    if mesh["size_mm"] != [76.0, 76.0, 32.5] or mesh["bounds_mm"][2][0] != 0:
        raise ValueError("Unexpected jig dimensions: " + str(mesh))

    checks = []
    with tempfile.TemporaryDirectory(prefix="label-jig-check-") as temp:
        for height in (58, 59, 60):
            for mode in ("jar", "insertion", "label_removal"):
                result, log = cad(Path(temp) / "intersection.stl", part="checks",
                                  check_mode=mode, jar_length=height)
                if result.returncode != 1 or "Current top level object is empty." not in log:
                    raise RuntimeError(f"{mode}, jar height {height}:\n{log}")
                checks.append(dict(check=mode, capped_height_mm=height,
                                   result="empty intersection"))
    report = dict(
        mesh=mesh,
        source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        stl_sha256=hashlib.sha256(stl.read_bytes()).hexdigest(),
        clearances=checks,
        label_size_mm=[35, 18],
        label_edges_above_jar_bottom_mm=[9.5, 27.5],
        label_center_above_jar_bottom_mm=18.5,
        physical_testing="Awaiting a fit test of the cleaned-up print",
        notes=[
            "Seating check lifts the jar 0.02 mm to exclude intended floor contact.",
            "Jar insertion samples lifts of 1, 5, 15, 30, 60 and 90 mm.",
            "A 0.25 mm thick label envelope is checked at lifts of 0, 1, 5, 10, 15, 30 and 60 mm.",
            "Reference omits quilting and the precise molded oval; align the jar visually and hold it during application.",
        ],
    )
    (OUTPUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"Verified one closed print part and {len(checks)} clearance cases: {stl}")


if __name__ == "__main__":
    main()
