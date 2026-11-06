#!/usr/bin/env python3
"""Install the JARVIS board profile and targeted XiaoZhi integration patches."""
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
        raise SystemExit(f"Patch anchor not found in {path}: {old[:100]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")

def main():
    if not (XIAOZHI / "main" / "Kconfig.projbuild").exists():
        raise SystemExit("XiaoZhi submodule was not checked out")
    BOARD_DST.mkdir(parents=True, exist_ok=True)
    for name in ("config.h", "config.json", "jarvis_led.h", "jarvis_led.cc", "jarvis_s3_zero_board.cc"):
        shutil.copy2(BOARD_SRC / name, BOARD_DST / name)

    kconfig = XIAOZHI / "main" / "Kconfig.projbuild"
    replace_once(
        kconfig,
        '    config BOARD_TYPE_BREAD_COMPACT_WIFI\\n        bool "Bread Compact Wi-Fi (面包板)"\\n        depends on IDF_TARGET_ESP32S3\\n',
        '    config BOARD_TYPE_JARVIS_S3_ZERO\\n        bool "JARVIS — Waveshare ESP32-S3-Zero"\\n        depends on IDF_TARGET_ESP32S3\\n'
        '    config BOARD_TYPE_BREAD_COMPACT_WIFI\\n        bool "Bread Compact Wi-Fi (面包板)"\\n        depends on IDF_TARGET_ESP32S3\\n'
    )

    cmake = XIAOZHI / "main" / "CMakeLists.txt"
    replace_once(
        cmake,
        'if(CONFIG_BOARD_TYPE_BREAD_COMPACT_WIFI)\\n    set(BOARD_DIR "bread-compact-wifi")',
        'if(CONFIG_BOARD_TYPE_JARVIS_S3_ZERO)\\n    set(BOARD_DIR "jarvis-s3-zero")\\n'
        'elseif(CONFIG_BOARD_TYPE_BREAD_COMPACT_WIFI)\\n    set(BOARD_DIR "bread-compact-wifi")'
    )

    led_h = XIAOZHI / "main" / "led" / "led.h"
    replace_once(
        led_h,
        '    virtual void OnStateChanged() = 0;\\n',
        '    virtual void OnStateChanged() = 0;\\n'
        '    virtual void OnVoiceActivityChanged(bool active) { (void)active; }\\n'
    )

    app = XIAOZHI / "main" / "application.cc"
    replace_once(
        app,
        '#include "application.h"\\n',
        '#include "application.h"\\n#include "jarvis_greeting.h"\\n'
    )
    replace_once(
        app,
        '            if (GetDeviceState() == kDeviceStateListening) {\\n'
        '                auto led = Board::GetInstance().GetLed();\\n'
        '                led->OnStateChanged();\\n'
        '            }',
        '            if (GetDeviceState() == kDeviceStateListening) {\\n'
        '                auto led = Board::GetInstance().GetLed();\\n'
        '                led->OnVoiceActivityChanged(audio_service_.IsVoiceDetected());\\n'
        '            }'
    )
    replace_once(
        app,
        '    if (!startup_completed_) {\\n        startup_completed_ = true;',
        '    const bool first_startup_completion = !startup_completed_;\\n'
        '    if (first_startup_completion) {\\n        startup_completed_ = true;'
    )
    replace_once(
        app,
        '    if (!has_error) {\\n        Schedule([this]() {\\n'
        '            // Play the success sound to indicate the device is ready\\n'
        '            audio_service_.PlaySound(Lang::Sounds::OGG_SUCCESS);\\n'
        '        });\\n    }',
        '    if (!has_error && first_startup_completion) {\\n        Schedule([this]() {\\n'
        '            // Local greeting; no network TTS request is needed.\\n'
        '            audio_service_.PlaySound(std::string_view(\\n'
        '                reinterpret_cast<const char*>(kJarvisGreetingOgg), sizeof(kJarvisGreetingOgg)));\\n'
        '        });\\n    }'
    )
    print("JARVIS board profile, VAD LED states and one-time startup greeting installed.")

if __name__ == "__main__":
    main()
