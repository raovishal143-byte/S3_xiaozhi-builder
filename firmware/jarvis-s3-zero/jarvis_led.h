#pragma once

#include "led/led.h"
#include <driver/gpio.h>
#include <led_strip.h>
#include <esp_timer.h>
#include <mutex>

class JarvisLed final : public Led {
public:
    explicit JarvisLed(gpio_num_t rgb_gpio);
    ~JarvisLed() override;

    void OnStateChanged() override;
    void OnVoiceActivityChanged(bool active) override;

private:
    enum class Mode { Off, Startup, Standby, Listening, Processing, Speaking };

    led_strip_handle_t strip_ = nullptr;
    esp_timer_handle_t timer_ = nullptr;
    std::mutex mutex_;
    Mode mode_ = Mode::Off;
    bool phase_on_ = false;
    bool voice_seen_ = false;
    bool startup_done_ = false;
    bool processing_blue_phase_ = false;
    int startup_edges_remaining_ = 0;
    uint8_t breath_step_ = 0;

    void SetMode(Mode mode);
    void Render(bool on);
    void OnTimer();
    static void TimerCallback(void* arg);
};
