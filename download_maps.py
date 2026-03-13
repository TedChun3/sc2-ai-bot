"""
Download SC2 ladder maps to the correct directory.
"""

import os
import platform
import urllib.request
import zipfile
from pathlib import Path


def get_sc2_maps_dir() -> Path:
    sc2path = os.environ.get("SC2PATH")
    if sc2path:
        return Path(sc2path) / "Maps"

    system = platform.system()
    if system == "Darwin":
        return Path("/Applications/StarCraft II/Maps")
    elif system == "Linux":
        return Path.home() / "StarCraftII" / "Maps"
    elif system == "Windows":
        return Path("C:/Program Files (x86)/StarCraft II/Maps")
    else:
        raise RuntimeError(f"Unsupported platform: {system}")


# Simple64 is included with SC2, but here are some ladder maps
MAPS = {
    "Simple64": None,  # Already included
}

LADDER_MAPS_URL = (
    "https://github.com/BurnySc2/python-sc2/releases/download/maps/maps.zip"
)


def main():
    maps_dir = get_sc2_maps_dir()
    print(f"SC2 Maps directory: {maps_dir}")

    if not maps_dir.parent.exists():
        print(f"⚠️  SC2 not found at {maps_dir.parent}")
        print("   Install StarCraft II first, then run this script.")
        print(f'   Or set SC2PATH: export SC2PATH="/path/to/StarCraft II"')
        return

    maps_dir.mkdir(exist_ok=True)

    if (maps_dir / "Simple64.SC2Map").exists():
        print("✅ Simple64 map already exists")
    else:
        print("⬇️  Downloading ladder maps...")
        zip_path = maps_dir / "maps.zip"
        try:
            urllib.request.urlretrieve(LADDER_MAPS_URL, zip_path)
            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(maps_dir)
            zip_path.unlink()
            print("✅ Maps downloaded and extracted!")
        except Exception as e:
            print(f"❌ Failed to download maps: {e}")
            print("   Download manually from: https://aiarena.net/wiki/maps/")

    print(f"\n📁 Available maps:")
    for f in sorted(maps_dir.glob("*.SC2Map")):
        print(f"   - {f.stem}")


if __name__ == "__main__":
    main()
