"""
Generate PNG figures from Mermaid .mmd files using the mermaid.ink public API.
Run from the docs/ directory: python generate_figures.py
"""

import base64
import sys
import urllib.request
import urllib.error
from pathlib import Path

FIGURES_DIR = Path(__file__).parent / "figures"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "image/png,image/*,*/*",
}


def generate(mmd_file: Path) -> bool:
    out = mmd_file.with_suffix(".png")
    source = mmd_file.read_text(encoding="utf-8").strip()
    encoded = base64.urlsafe_b64encode(source.encode("utf-8")).decode("ascii")
    url = f"https://mermaid.ink/img/{encoded}?bgColor=white"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            out.write_bytes(resp.read())
        print(f"  OK  {out.name}")
        return True
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:200]
        print(f"  FAIL {mmd_file.name}: HTTP {e.code} — {body}")
        return False
    except Exception as e:
        print(f"  FAIL {mmd_file.name}: {e}")
        return False


def main():
    mmd_files = sorted(FIGURES_DIR.glob("*.mmd"))
    if not mmd_files:
        print("No .mmd files found in figures/")
        sys.exit(1)

    print(f"Generating {len(mmd_files)} figures via mermaid.ink...\n")
    ok = sum(generate(f) for f in mmd_files)
    print(f"\n{ok}/{len(mmd_files)} figures generated successfully.")
    if ok < len(mmd_files):
        sys.exit(1)


if __name__ == "__main__":
    main()