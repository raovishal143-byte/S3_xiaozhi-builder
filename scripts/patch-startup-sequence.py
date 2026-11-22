#!/usr/bin/env python3
"""Apply isolated Waveshare startup LED/audio-start hooks; leave speech processing untouched."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "xiaozhi-esp32" / "main"

def replace(path, old, new):
    s = path.read_text(encoding="utf-8")
    if new in s:
        return
    if old not in s:
        raise SystemExit(f"Patch anchor missing in {path}: {old[:120]!r}")
    path.write_text(s.replace(old, new, 1), encoding="utf-8")

def main():
    # Board RGB status LED: remove constructor-time flashes, correct observed
    # red/green channel swap, and run the startup pattern only on first audio output.
    board = SRC / "boards" / "waveshare-esp32-s3-zero-xiaozhi" / "waveshare_s3_zero_board.cc"
    replace(board,
        "strip_config.color_component_format = LED_STRIP_COLOR_COMPONENT_FMT_GRB;",
        "strip_config.color_component_format = LED_STRIP_COLOR_COMPONENT_FMT_RGB;")
    replace(board,
        """        // Exactly five red startup flashes on the onboard addressable RGB LED.
        for (int i = 0; i < 5; ++i) {
            SetColor(255, 0, 0);
            vTaskDelay(pdMS_TO_TICKS(150));
            Clear();
            vTaskDelay(pdMS_TO_TICKS(150));
        }

""", "")
    replace(board,
        """    void OnStateChanged() override {
        const auto state = Application::GetInstance().GetDeviceState();""",
        """    void OnStartupGreetingChanged(bool active) override {
        startup_sequence_active_.store(active);
        mode_.store(active ? 3 : 0);
    }

    void OnStateChanged() override {
        if (startup_sequence_active_.load()) return;
        const auto state = Application::GetInstance().GetDeviceState();""")
    replace(board,
        """    std::atomic<int> mode_{0};

    void SetColor""",
        """    std::atomic<int> mode_{0};
    std::atomic<bool> startup_sequence_active_{false};

    void SetColor""")
    replace(board,
        """            const int mode = self->mode_.load();
            if (mode == 0) {""",
        """            const int mode = self->mode_.load();
            if (mode == 3) {
                for (int flash = 0; flash < 5 && self->startup_sequence_active_.load(); ++flash) {
                    self->SetColor(255, 0, 0);
                    vTaskDelay(pdMS_TO_TICKS(150));
                    self->Clear();
                    vTaskDelay(pdMS_TO_TICKS(150));
                }
                if (self->startup_sequence_active_.load()) self->mode_.store(4);
                continue;
            }
            if (mode == 0 || mode == 4) {""")
    replace(board,
        "self->SetColor(brightness, static_cast<uint8_t>((160 * brightness) / 255), 0);",
        "self->SetColor(brightness, brightness, 0);")
    replace(board,
        "if (state == kDeviceStateListening || state == kDeviceStateAudioTesting ||\n            state == kDeviceStateConnecting) {",
        "if (state == kDeviceStateListening || state == kDeviceStateAudioTesting ||\n            state == kDeviceStateConnecting || state == kDeviceStateActivating) {")

    # Add an output-start callback. It is fired at the first decoded frame only
    # when the app has explicitly armed the startup greeting; it does not alter PCM.
    led_h = SRC / "led" / "led.h"
    replace(led_h,
        "    virtual void OnStateChanged() = 0;\n",
        "    virtual void OnStateChanged() = 0;\n    virtual void OnStartupGreetingChanged(bool active) { (void)active; }\n")

    audio_h = SRC / "audio" / "audio_service.h"
    replace(audio_h,
        "    std::function<void(void)> on_playback_drained;\n",
        "    std::function<void(void)> on_playback_drained;\n    std::function<void(void)> on_audio_output_started;\n")
    audio_cc = SRC / "audio" / "audio_service.cc"
    replace(audio_cc,
        "        codec_->OutputData(task.pcm);",
        "        if (callbacks_.on_audio_output_started) callbacks_.on_audio_output_started();\n        codec_->OutputData(task.pcm);")

    app_h = SRC / "application.h"
    replace(app_h,
        "#include <cstdint>\n",
        "#include <cstdint>\n#include <atomic>\n")
    replace(app_h,
        "    bool pending_startup_wake_word_hint_ = false;\n",
        "    bool pending_startup_wake_word_hint_ = false;\n    std::atomic<bool> startup_greeting_pending_{false};\n    std::atomic<bool> startup_greeting_led_started_{false};\n")

    app = SRC / "application.cc"
    replace(app,
        """    callbacks.on_playback_drained = [this]() {
        xEventGroupSetBits(event_group_, MAIN_EVENT_PLAYBACK_DRAINED);
    };""",
        """    callbacks.on_playback_drained = [this]() {
        xEventGroupSetBits(event_group_, MAIN_EVENT_PLAYBACK_DRAINED);
    };
    callbacks.on_audio_output_started = [this]() {
        if (startup_greeting_pending_.load() && !startup_greeting_led_started_.exchange(true)) {
            Board::GetInstance().GetLed()->OnStartupGreetingChanged(true);
        }
    };""")
    replace(app,
        """            if (audio_service_.IsPlaybackIdle()) {
                notify_player_.OnPlaybackDrained();
            }
            // Deferred listening start""",
        """            if (audio_service_.IsPlaybackIdle()) {
                notify_player_.OnPlaybackDrained();
                if (startup_greeting_pending_.exchange(false)) {
                    startup_greeting_led_started_.store(false);
                    Board::GetInstance().GetLed()->OnStartupGreetingChanged(false);
                }
            }
            // Deferred listening start""")
    replace(app,
        """    if (!has_error) {
        Schedule([this]() {
            // Speak a short startup greeting after network activation succeeds.
            audio_service_.PlaySound(Lang::Sounds::OGG_HI_THERE);
        });
    }""",
        """    if (!has_error) {
        startup_greeting_pending_.store(true);
        startup_greeting_led_started_.store(false);
        Schedule([this]() {
            // LED pattern is triggered by the first decoded frame at audio output.
            audio_service_.PlaySound(Lang::Sounds::OGG_HI_THERE);
        });
    }""")

    print("Applied startup-only audio-frame LED trigger, five red flashes, true yellow breathing, blue listening/processing, green speaking, and RGB channel correction.")
    print("No microphone, I2S format, codec, speech streaming, speaker gain, or PSRAM code was changed.")

if __name__ == "__main__":
    main()
