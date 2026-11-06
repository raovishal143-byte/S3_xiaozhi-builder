#!/usr/bin/env python3
"""Generate a small local English Ogg/Opus greeting and C++ byte header."""
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
build = root / "xiaozhi-esp32" / "build"
build.mkdir(parents=True, exist_ok=True)
wav = build / "jarvis-greeting.wav"
ogg = build / "jarvis-greeting.ogg"
header = root / "xiaozhi-esp32" / "main" / "jarvis_greeting.h"

subprocess.run(["espeak-ng", "-v", "en-us", "-s", "145", "-w", str(wav), "Hi there."], check=True)
subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(wav),
                "-ac", "1", "-ar", "24000", "-c:a", "libopus", "-b:a", "32k", str(ogg)], check=True)
data = ogg.read_bytes()
lines = []
for i in range(0, len(data), 12):
    lines.append("    " + ", ".join(f"0x{b:02x}" for b in data[i:i+12]) + ",")
header.write_text(
    "#pragma once\n#include <cstddef>\n"
    "static const unsigned char kJarvisGreetingOgg[] = {\n" +
    "\n".join(lines) + "\n};\n",
    encoding="utf-8")
print(f"Generated local greeting: {len(data)} bytes")
