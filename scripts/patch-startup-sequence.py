#!/usr/bin/env python3
"""Patch the Waveshare startup LED so five red flashes begin with startup audio."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "xiaozhi-esp32" / "main"

def replace(path, old, new):
    s = path.read_text(encoding="utf-8")
    if new in s:
        return
    if old not in s:
        raise SystemExit(f"Patch anchor missing in {path}: {old[:100]!r}")
    path.write_text(s.replace(old, new, 1), encoding="utf-8")

def main():
    led_h = SRC / "led" / "led.h"
    replace(led_h,
        "    virtual void OnStateChanged() = 0;\n",
        "    virtual void OnStateChanged() = 0;\n"
        "    virtual void OnStartupGreetingChanged(bool active) { (void)active; }\n")

    board = SRC / "boards" / "waveshare-esp32-s3-zero-xiaozhi" / "waveshare_s3_zero_board.cc"
    replace(board,
        """        // Exactly five red startup flashes on the onboard addressable RGB LED.
        for (int i = 0; i < 5; ++i) {
            SetColor(255, 0, 0);
            vTaskDelay(pdMS_TO_TICKS(150));
            Clear();
            vTaskDelay(pdMS_TO_TICKS(150));
        }

""",
        "")
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
                if (self->startup_sequence_active_.load()) {
                    self->mode_.store(4);  // Hold yellow while the combined startup audio continues.
                }
                continue;
            }
            if (mode == 4) {
                self->SetColor(255, 160, 0);
                vTaskDelay(pdMS_TO_TICKS(50));
                continue;
            }
            if (mode == 0) {""")

    app_h = SRC / "application.h"
    replace(app_h,
        "    bool startup_completed_ = false;\n",
        "    bool startup_completed_ = false;\n    bool pending_startup_greeting_ = false;\n")

    app = SRC / "application.cc"
    replace(app,
        """        if (bits & MAIN_EVENT_PLAYBACK_DRAINED) {
            if (audio_service_.IsPlaybackIdle()) {
                notify_player_.OnPlaybackDrained();
            }""",
        """        if (bits & MAIN_EVENT_PLAYBACK_DRAINED) {
            if (audio_service_.IsPlaybackIdle()) {
                notify_player_.OnPlaybackDrained();
                if (pending_startup_greeting_) {
                    pending_startup_greeting_ = false;
                    Board::GetInstance().GetLed()->OnStartupGreetingChanged(false);
                    SetDeviceState(kDeviceStateIdle);
                }
            }""")
    replace(app,
        """    if (!has_error) {
        Schedule([this]() {
            // Speak a short startup greeting after network activation succeeds.
            audio_service_.PlaySound(Lang::Sounds::OGG_HI_THERE);
        });
    }""",
        """    if (!has_error) {
        pending_startup_greeting_ = true;
        board.GetLed()->OnStartupGreetingChanged(true);
        Schedule([this]() {
            // Combined asset: Camaro starts now, then 2 seconds silence, then "Hi there".
            audio_service_.PlaySound(Lang::Sounds::OGG_HI_THERE);
        });
    }""")
    print("Patched: GPIO21 performs five red flashes from the first startup-audio frame, holds yellow through the car/2s/greeting sequence, then returns to standby breathing.")

if __name__ == "__main__":
    main()
