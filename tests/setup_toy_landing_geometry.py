#!/usr/bin/env python3
"""Copy geometry files for ToyLandingModel."""

import shutil
from pathlib import Path

SOURCE_DIR = Path(
    "F:/dev/projects/osim_render/opensim-core/Bindings/Java/Matlab/OpenSenseExample/Geometry"
)
TARGET_DIR = Path("F:/dev/projects/osim_render/models/toys/ToyDropLanding/Geometry")

# Create target directory
TARGET_DIR.mkdir(parents=True, exist_ok=True)
print(f"Target directory: {TARGET_DIR}\n")

# Define file mappings (source -> target)
file_mappings = {
    "sacrum.vtp": "sacrum.vtp",
    "r_pelvis.vtp": "pelvis.vtp",
    "l_pelvis.vtp": "l_pelvis.vtp",
    "femur_r.vtp": "femur_r.vtp",
    "femur_l.vtp": "femur_l.vtp",
    "tibia_r.vtp": "tibia_r.vtp",
    "tibia_l.vtp": "tibia_l.vtp",
    "r_fibula.vtp": "fibula.vtp",
    "l_fibula.vtp": "l_fibula.vtp",
    "r_talus.vtp": "talus.vtp",
    "l_talus.vtp": "l_talus.vtp",
    "r_foot.vtp": "foot.vtp",
    "l_foot.vtp": "l_foot.vtp",
    "r_bofoot.vtp": "bofoot.vtp",
    "l_bofoot.vtp": "l_bofoot.vtp",
    "hat_spine.vtp": "hat_spine.vtp",
    "hat_jaw.vtp": "hat_jaw.vtp",
    "hat_skull.vtp": "hat_skull.vtp",
    "hat_ribs_scap.vtp": "hat_ribs.vtp",
}

copied = 0
failed = 0

for source_file, target_file in file_mappings.items():
    source_path = SOURCE_DIR / source_file
    target_path = TARGET_DIR / target_file

    if source_path.exists():
        try:
            shutil.copy2(source_path, target_path)
            print(f"[OK] {source_file:20} -> {target_file}")
            copied += 1
        except Exception as e:
            print(f"[FAIL] Failed to copy {source_file}: {e}")
            failed += 1
    else:
        print(f"[FAIL] Source not found: {source_file}")
        failed += 1

print(f"\n{'='*50}")
print(f"Summary: Copied {copied}, Failed {failed}")
print(f"{'='*50}")

if failed == 0:
    print("\n[SUCCESS] All geometry files copied successfully!")
    print(f"Location: {TARGET_DIR}")

    # List files in target
    print(f"\nFiles in {TARGET_DIR.name}:")
    for f in sorted(TARGET_DIR.glob("*.vtp")):
        print(f"  - {f.name}")
else:
    print("\n[WARNING] Some files could not be copied.")
