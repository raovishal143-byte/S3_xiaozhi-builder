#!/usr/bin/env python3
"""Add an optional bounded-consumer PCM tap to the pinned XiaoZhi audio input path.

The callback is deliberately passive: when unset, the original audio path is
unchanged. A provider must copy frames into its own bounded queue and return
quickly; it must never block the audio input task or retain the vector reference.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
XIAOZHI = ROOT / "xiaozhi-esp32"


def replace_once(path: Path, old: str, new: str):
    source = path.read_text(encoding="utf-8")
    if new in source:
        return
    if old not in source:
        raise SystemExit(f"Gemini PCM hook anchor not found in {path}: {old[:120]!r}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")


def main():
    header = XIAOZHI / "main" / "audio" / "audio_service.h"
    source = XIAOZHI / "main" / "audio" / "audio_service.cc"

    replace_once(
        header,
        "struct AudioServiceCallbacks {\n",
        "struct AudioServiceCallbacks {\n"
        "    // Optional 16 kHz PCM input tap (10 ms frames); consumer must be non-blocking.\n"
        "    std::function<void(const std::vector<int16_t>&)> on_pcm_frame;\n",
    )

    replace_once(
        source,
        """            if (ReadAudioData(data, 16000, samples)) {
                audio_engine_->Feed(std::move(data));
                continue;
            }""",
        """            if (ReadAudioData(data, 16000, samples)) {
                // Gemini can observe the same microphone frames without opening
                // a second I2S reader or disturbing the offline wake-word engine.
                // The callback must be non-blocking and copy into bounded storage.
                if (callbacks_.on_pcm_frame) {
                    callbacks_.on_pcm_frame(data);
                }
                audio_engine_->Feed(std::move(data));
                continue;
            }""",
    )

    print("Optional 16 kHz / 10 ms PCM capture hook installed.")


if __name__ == "__main__":
    main()
