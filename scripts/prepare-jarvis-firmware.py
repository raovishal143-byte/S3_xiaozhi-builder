#!/usr/bin/env python3
"""Install the JARVIS board profile and small upstream integration patches."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
XIAOZHI = ROOT / "xiaozhi-esp32"
BOARD_SRC = ROOT / "firmware" / "jarvis-s3-zero"
BOARD_DST = XIAOZHI / "main" / "boards" / "jarvis-s3-zero"

def replace_once(path: Path, old: str, new: str):
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise SystemExit(f"Patch anchor not found in {path}: {old[:90]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")

def main():
    if not (XIAOZHI / "main" / "Kconfig.projbuild").exists():
        raise SystemExit("XiaoZhi submodule was not checked out")
    BOARD_DST.mkdir(parents=True, exist_ok=True)
    for name in ("config.h", "config.json", "jarvis_led.h", "jarvis_led.cc", "jarvis_s3_zero_board.cc"):
        source = BOARD_SRC / name
        if source.exists():
            shutil.copy2(source, BOARD_DST / name)

    kconfig = XIAOZHI / "main" / "Kconfig.projbuild"
    replace_once(
        kconfig,
        '    config BOARD_TYPE_BREAD_COMPACT_WIFI\n        bool "Bread Compact Wi-Fi (面包板)"\n        depends on IDF_TARGET_ESP32S3\n',
        '    config BOARD_TYPE_JARVIS_S3_ZERO\n        bool "JARVIS — Waveshare ESP32-S3-Zero"\n        depends on IDF_TARGET_ESP32S3\n'
        '    config BOARD_TYPE_BREAD_COMPACT_WIFI\n        bool "Bread Compact Wi-Fi (面包板)"\n        depends on IDF_TARGET_ESP32S3\n'
    )

    cmake = XIAOZHI / "main" / "CMakeLists.txt"
    replace_once(
        cmake,
        'if(CONFIG_BOARD_TYPE_BREAD_COMPACT_WIFI)\n    set(BOARD_DIR "bread-compact-wifi")',
        'if(CONFIG_BOARD_TYPE_JARVIS_S3_ZERO)\n    set(BOARD_DIR "jarvis-s3-zero")\n'
        'elseif(CONFIG_BOARD_TYPE_BREAD_COMPACT_WIFI)\n    set(BOARD_DIR "bread-compact-wifi")'
    )

    led_h = XIAOZHI / "main" / "led" / "led.h"
    replace_once(
        led_h,
        '    virtual void OnStateChanged() = 0;\n',
        '    virtual void OnStateChanged() = 0;\n'
        '    virtual void OnVoiceActivityChanged(bool active) { (void)active; }\n'
    )

    app = XIAOZHI / "main" / "application.cc"
    replace_once(
        app,
        '            if (GetDeviceState() == kDeviceStateListening) {\n'
        '                auto led = Board::GetInstance().GetLed();\n'
        '                led->OnStateChanged();\n'
        '            }',
        '            if (GetDeviceState() == kDeviceStateListening) {\n'
        '                auto led = Board::GetInstance().GetLed();\n'
        '                led->OnVoiceActivityChanged(audio_service_.IsVoiceDetected());\n'
        '            }'
    )
    print("JARVIS board profile and LED/VAD integration installed.")

if __name__ == "__main__":
    main()
