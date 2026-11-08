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
    void OnStartupGreetingChanged(bool active);

private:
    enum class Mode { Off, Startup, Greeting, Standby, Listening, Processing, Speaking };

    led_strip_handle_t strip_ = nullptr;
    esp_timer_handle_t timer_ = nullptr;
    std::mutex mutex_;
    Mode mode_ = Mode::Off;
    bool phase_on_ = false;
    bool voice_seen_ = false;
    int standby_brightness_ = 8;
    int standby_direction_ = 1;

    void SetMode(Mode mode);
    void Render(uint8_t brightness);
    void OnTimer();
    static void TimerCallback(void* arg);
};
