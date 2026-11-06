#!/usr/bin/env python3
"""Install the JARVIS board profile and targeted XiaoZhi integration patches."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
XIAOZHI = ROOT / "xiaozhi-esp32"
BOARD_SRC = ROOT / "firmware" / "jarvis-s3-zero"
BOARD_DST = XIAOZHI / "main" / "boards" / "jarvis-s3-zero"


def replace_once(path: Path, old: str, new: str):
    source = path.read_text(encoding="utf-8")
    if new in source:
        return
    if old not in source:
        raise SystemExit(f"Patch anchor not found in {path}: {old[:100]!r}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")


def main():
    if not (XIAOZHI / "main" / "Kconfig.projbuild").exists():
        raise SystemExit("XiaoZhi submodule was not checked out")

    BOARD_DST.mkdir(parents=True, exist_ok=True)
    for name in ("config.h", "config.json", "jarvis_led.h", "jarvis_led.cc", "jarvis_s3_zero_board.cc"):
        shutil.copy2(BOARD_SRC / name, BOARD_DST / name)

    replace_once(
        XIAOZHI / "main" / "Kconfig.projbuild",
        """    config BOARD_TYPE_BREAD_COMPACT_WIFI
        bool "Bread Compact Wi-Fi (面包板)"
        depends on IDF_TARGET_ESP32S3
""",
        """    config BOARD_TYPE_JARVIS_S3_ZERO
        bool "JARVIS — Waveshare ESP32-S3-Zero"
        depends on IDF_TARGET_ESP32S3
    config BOARD_TYPE_BREAD_COMPACT_WIFI
        bool "Bread Compact Wi-Fi (面包板)"
        depends on IDF_TARGET_ESP32S3
""",
    )

    replace_once(
        XIAOZHI / "main" / "CMakeLists.txt",
        """if(CONFIG_BOARD_TYPE_BREAD_COMPACT_WIFI)
    set(BOARD_DIR "bread-compact-wifi")""",
        """if(CONFIG_BOARD_TYPE_JARVIS_S3_ZERO)
    set(BOARD_DIR "jarvis-s3-zero")
elseif(CONFIG_BOARD_TYPE_BREAD_COMPACT_WIFI)
    set(BOARD_DIR "bread-compact-wifi")""",
    )

    replace_once(
        XIAOZHI / "main" / "led" / "led.h",
        "    virtual void OnStateChanged() = 0;\n",
        "    virtual void OnStateChanged() = 0;\n"
        "    virtual void OnVoiceActivityChanged(bool active) { (void)active; }\n",
    )

    app = XIAOZHI / "main" / "application.cc"
    replace_once(
        app,
        '#include "application.h"\n',
        '#include "application.h"\n#include "jarvis_greeting.h"\n#include <string_view>\n',
    )
    replace_once(
        app,
        """            if (GetDeviceState() == kDeviceStateListening) {
                auto led = Board::GetInstance().GetLed();
                led->OnStateChanged();
            }""",
        """            if (GetDeviceState() == kDeviceStateListening) {
                auto led = Board::GetInstance().GetLed();
                led->OnVoiceActivityChanged(audio_service_.IsVoiceDetected());
            }""",
    )
    replace_once(
        app,
        """    if (!startup_completed_) {
        startup_completed_ = true;""",
        """    const bool first_startup_completion = !startup_completed_;
    if (first_startup_completion) {
        startup_completed_ = true;""",
    )
    replace_once(
        app,
        """    if (!has_error) {
        Schedule([this]() {
            // Play the success sound to indicate the device is ready
            audio_service_.PlaySound(Lang::Sounds::OGG_SUCCESS);
        });
    }""",
        """    if (!has_error && first_startup_completion) {
        Schedule([this]() {
            // Speak the locally generated greeting exactly once after first activation.
            audio_service_.PlaySound(std::string_view(
                reinterpret_cast<const char*>(kJarvisGreetingOgg), sizeof(kJarvisGreetingOgg)));
        });
    }""",
    )
    print("JARVIS board profile, VAD LED states and one-time startup greeting installed.")


if __name__ == "__main__":
    main()
