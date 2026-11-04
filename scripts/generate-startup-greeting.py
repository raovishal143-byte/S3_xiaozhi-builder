#!/usr/bin/env python3
"""Generate a self-contained Ogg/Opus startup greeting header for XiaoZhi."""
import pathlib
import subprocess
import tempfile

root = pathlib.Path(__file__).resolve().parents[1]
out = root / "xiaozhi-esp32" / "main" / "startup_greeting.h"

with tempfile.TemporaryDirectory() as tmp:
    wav = pathlib.Path(tmp) / "greeting.wav"
    ogg = pathlib.Path(tmp) / "greeting.ogg"
    subprocess.run([
        "espeak-ng", "-v", "en-us+m3", "-s", "145", "-p", "35",
        "-a", "170", "-w", str(wav), "Hey Buddy, how are you?"
    ], check=True)
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(wav), "-ac", "1", "-ar", "24000",
        "-c:a", "libopus", "-b:a", "24k", "-vbr", "on",
        "-application", "voip", "-f", "ogg", str(ogg)
    ], check=True)
    data = ogg.read_bytes()

if not data.startswith(b"OggS") or b"OpusHead" not in data[:128]:
    raise SystemExit("Generated greeting is not a valid Ogg/Opus stream")

lines = []
for i in range(0, len(data), 12):
    lines.append("    " + ", ".join(f"0x{x:02X}" for x in data[i:i+12]) + ",")
header = """// Generated at build time with eSpeak NG (English male voice) and FFmpeg.
// Exact offline startup phrase: Hey Buddy, how are you?
#pragma once
#include <cstddef>
#include <cstdint>
inline constexpr uint8_t STARTUP_GREETING_OGG[] = {
""" + "\n".join(lines) + """
};
inline constexpr size_t STARTUP_GREETING_OGG_LEN = sizeof(STARTUP_GREETING_OGG);
"""
out.write_text(header, encoding="utf-8")
print(f"Generated offline startup greeting: {len(data)} bytes -> {out}")
