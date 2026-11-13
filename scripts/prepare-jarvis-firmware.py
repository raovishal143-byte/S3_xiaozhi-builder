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

    # XiaoZhi upstream defaults ESP32-S3 to Octal PSRAM. The Waveshare
    # ESP32-S3-Zero uses 2 MB Quad-SPI PSRAM, so override the upstream default
    # before CMake/Kconfig generates sdkconfig. sdkconfig_append alone is not
    # sufficient when the upstream default has already selected Octal mode.
    replace_once(
        XIAOZHI / "sdkconfig.defaults.esp32s3",
        "CONFIG_SPIRAM_MODE_OCT=y",
        "CONFIG_SPIRAM_MODE_QUAD=y",
    )

    # JARVIS has no physical volume buttons. Use full output level and a
    # linear volume curve; the upstream squared curve attenuates 70% volume
    # to only 49% signal amplitude. Override any old NVS volume on startup.
    replace_once(
        XIAOZHI / "main" / "audio" / "codecs" / "no_audio_codec.cc",
        "int32_t volume_factor = pow(double(output_volume_) / 100.0, 2) * 65536;",
        "int32_t volume_factor = (int32_t(output_volume_) * 65536) / 100;",
    )
    replace_once(
        XIAOZHI / "main" / "audio" / "audio_codec.h",
        "    int output_volume_ = 70;",
        "    int output_volume_ = 100;",
    )
    replace_once(
        XIAOZHI / "main" / "audio" / "audio_codec.cc",
        '    Settings settings("audio", false);\n    output_volume_ = settings.GetInt("output_volume", output_volume_);',
        '    output_volume_ = 100;\n    ESP_LOGI(TAG, "JARVIS speaker output volume fixed at %d", output_volume_);',
    )

    # Instrument the real speaker write path. This distinguishes an empty/zero
    # decoded stream from an I2S transport failure without changing pin wiring.
    replace_once(
        XIAOZHI / "main" / "audio" / "codecs" / "no_audio_codec.cc",
        """    ESP_ERROR_CHECK(i2s_channel_init_std_mode(tx_handle_, &std_cfg));

    // Create a new channel for MIC""",
        """    ESP_ERROR_CHECK(i2s_channel_init_std_mode(tx_handle_, &std_cfg));
    ESP_LOGI(TAG, "JARVIS I2S speaker configured: rate=%d, BCLK=%d, WS=%d, DOUT=%d, 32-bit mono LEFT slot",
             output_sample_rate_, (int)spk_bclk, (int)spk_ws, (int)spk_dout);

    // Create a new channel for MIC""",
    )
    replace_once(
        XIAOZHI / "main" / "audio" / "codecs" / "no_audio_codec.cc",
        """int NoAudioCodec::Write(const int16_t* data, int samples) {
    std::lock_guard<std::mutex> lock(data_if_mutex_);
    std::vector<int32_t> buffer(samples);

    // output_volume_: 0-100
    // volume_factor_: 0-65536
    int32_t volume_factor = (int32_t(output_volume_) * 65536) / 100;
    for (int i = 0; i < samples; i++) {
        int64_t temp = int64_t(data[i]) * volume_factor; // 使用 int64_t 进行乘法运算
        if (temp > INT32_MAX) {
            buffer[i] = INT32_MAX;
        } else if (temp < INT32_MIN) {
            buffer[i] = INT32_MIN;
        } else {
            buffer[i] = static_cast<int32_t>(temp);
        }
    }

    size_t bytes_written;
    ESP_ERROR_CHECK(i2s_channel_write(tx_handle_, buffer.data(), samples * sizeof(int32_t), &bytes_written, portMAX_DELAY));
    return bytes_written / sizeof(int32_t);
}""",
        """int NoAudioCodec::Write(const int16_t* data, int samples) {
    std::lock_guard<std::mutex> lock(data_if_mutex_);
    std::vector<int32_t> buffer(samples);

    // output_volume_: 0-100
    // volume_factor_: 0-65536
    const int32_t volume_factor = (int32_t(output_volume_) * 65536) / 100;
    int32_t peak = 0;
    for (int i = 0; i < samples; i++) {
        int32_t sample = data[i];
        const int32_t magnitude = sample < 0 ? -sample : sample;
        if (magnitude > peak) peak = magnitude;
        const int64_t temp = int64_t(sample) * volume_factor;
        if (temp > INT32_MAX) {
            buffer[i] = INT32_MAX;
        } else if (temp < INT32_MIN) {
            buffer[i] = INT32_MIN;
        } else {
            buffer[i] = static_cast<int32_t>(temp);
        }
    }

    size_t bytes_written = 0;
    const esp_err_t err = i2s_channel_write(
        tx_handle_, buffer.data(), samples * sizeof(int32_t), &bytes_written, portMAX_DELAY);
    static uint32_t diagnostic_blocks = 0;
    const uint32_t block = ++diagnostic_blocks;
    if (block <= 12) {
        ESP_LOGI(TAG, "JARVIS I2S TX block=%u samples=%d peak_pcm=%ld volume=%d bytes=%u err=%s",
                 (unsigned)block, samples, (long)peak, output_volume_,
                 (unsigned)bytes_written, esp_err_to_name(err));
    }
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "JARVIS I2S TX write failed: %s", esp_err_to_name(err));
        return 0;
    }
    return bytes_written / sizeof(int32_t);
}""",
    )

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

    app_h = XIAOZHI / "main" / "application.h"
    replace_once(
        app_h,
        "    bool startup_completed_ = false;\n",
        "    bool startup_completed_ = false;\n    bool pending_startup_greeting_ = false;\n",
    )
    replace_once(
        app,
        """            if (audio_service_.IsPlaybackIdle()) {
                notify_player_.OnPlaybackDrained();
            }""",
        """            if (audio_service_.IsPlaybackIdle()) {
                notify_player_.OnPlaybackDrained();
                if (pending_startup_greeting_) {
                    pending_startup_greeting_ = false;
                    // Only enter standby after the local greeting has fully drained.
                    SetDeviceState(kDeviceStateIdle);
                }
            }""",
    )
    replace_once(
        app,
        """void Application::HandleActivationDoneEvent() {
    ESP_LOGI(TAG, "Activation done");

    SystemInfo::PrintHeapStats();
    SetDeviceState(kDeviceStateIdle);
""",
        """void Application::HandleActivationDoneEvent() {
    ESP_LOGI(TAG, "Activation done");

    SystemInfo::PrintHeapStats();
""",
    )
    replace_once(
        app,
        """    if (first_startup_completion) {
        startup_completed_ = true;
        pending_startup_wake_word_hint_ = !has_error;
    }
""",
        """    if (first_startup_completion) {
        startup_completed_ = true;
        pending_startup_wake_word_hint_ = !has_error;
    }
    if (has_error || !first_startup_completion) {
        SetDeviceState(kDeviceStateIdle);
    }
""",
    )
    replace_once(
        app,
        """    if (!has_error && first_startup_completion) {
        Schedule([this]() {
            // Speak the locally generated greeting exactly once after first activation.
            audio_service_.PlaySound(std::string_view(
                reinterpret_cast<const char*>(kJarvisGreetingOgg), sizeof(kJarvisGreetingOgg)));
        });
    }""",
        """    if (!has_error && first_startup_completion) {
        pending_startup_greeting_ = true;
        // Prevent the offline wake detector from hearing the device's own greeting.
        audio_service_.EnableWakeWordDetection(false);
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
