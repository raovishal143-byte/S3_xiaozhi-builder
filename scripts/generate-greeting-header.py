#!/usr/bin/env python3
"""Embed the approved Algenib startup greeting as local Ogg/Opus bytes."""
from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[1]
asset = root / "assets" / "jarvis-algenib-greeting.ogg"
build = root / "xiaozhi-esp32" / "build"
header = root / "xiaozhi-esp32" / "main" / "jarvis_greeting.h"

if not asset.is_file():
    raise SystemExit(f"Required Algenib greeting asset is missing: {asset}")

build.mkdir(parents=True, exist_ok=True)
ogg = build / "jarvis-greeting.ogg"
shutil.copy2(asset, ogg)

data = ogg.read_bytes()
if not data.startswith(b"OggS"):
    raise SystemExit("Algenib greeting asset is not an Ogg container")

lines = []
for i in range(0, len(data), 12):
    lines.append("    " + ", ".join(f"0x{b:02x}" for b in data[i:i + 12]) + ",")
header.write_text(
    "#pragma once\n#include <cstddef>\n"
    "static const unsigned char kJarvisGreetingOgg[] = {\n" +
    "\n".join(lines) + "\n};\n",
    encoding="utf-8",
)
print(f"Embedded Algenib startup greeting: {len(data)} bytes")
