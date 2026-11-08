#include "jarvis_led.h"
#include "application.h"
#include "device_state.h"
#include <esp_log.h>

#define TAG "JarvisLed"
static constexpr uint32_t kBlinkPeriodMs = 300;
static constexpr uint32_t kBreathPeriodMs = 35;

JarvisLed::JarvisLed(gpio_num_t rgb_gpio) {
    led_strip_config_t strip_cfg = {};
    strip_cfg.strip_gpio_num = rgb_gpio;
    strip_cfg.max_leds = 1;
    // Waveshare ESP32-S3-Zero onboard WS2812 uses RGB component order.
    strip_cfg.color_component_format = LED_STRIP_COLOR_COMPONENT_FMT_RGB;
    strip_cfg.led_model = LED_MODEL_WS2812;

    led_strip_rmt_config_t rmt_cfg = {};
    rmt_cfg.resolution_hz = 10 * 1000 * 1000;
    ESP_ERROR_CHECK(led_strip_new_rmt_device(&strip_cfg, &rmt_cfg, &strip_));
    ESP_ERROR_CHECK(led_strip_clear(strip_));

    esp_timer_create_args_t timer_args = {};
    timer_args.callback = &JarvisLed::TimerCallback;
    timer_args.arg = this;
    timer_args.dispatch_method = ESP_TIMER_TASK;
    timer_args.name = "jarvis_led";
    timer_args.skip_unhandled_events = true;
    ESP_ERROR_CHECK(esp_timer_create(&timer_args, &timer_));

    // Red blinking begins as soon as the board initializes and continues
    // until Application reports successful activation/internet initialization.
    SetMode(Mode::Startup);
}

JarvisLed::~JarvisLed() {
    if (timer_) {
        esp_timer_stop(timer_);
        esp_timer_delete(timer_);
    }
    if (strip_) {
        led_strip_del(strip_);
    }
}

void JarvisLed::Render(uint8_t brightness) {
    if (!strip_) return;

    uint8_t r = 0, g = 0, b = 0;
    switch (mode_) {
        case Mode::Startup:     r = brightness; g = 0;          b = 0;          break;
        case Mode::Greeting:    r = brightness; g = brightness; b = 0;          break;
        case Mode::Standby:     r = brightness; g = brightness; b = 0;          break;
        case Mode::Listening:
        case Mode::Processing:  r = 0;          g = 0;          b = brightness; break;
        case Mode::Speaking:    r = 0;          g = brightness; b = 0;          break;
        case Mode::Off:         break;
    }
    ESP_ERROR_CHECK(led_strip_set_pixel(strip_, 0, r, g, b));
    ESP_ERROR_CHECK(led_strip_refresh(strip_));
}

void JarvisLed::SetMode(Mode mode) {
    std::lock_guard<std::mutex> lock(mutex_);
    if (timer_) esp_timer_stop(timer_);
    mode_ = mode;
    phase_on_ = true;

    if (mode_ == Mode::Startup) {
        Render(28);
        ESP_ERROR_CHECK(esp_timer_start_periodic(timer_, kBlinkPeriodMs * 1000ULL));
        return;
    }
    if (mode_ == Mode::Greeting) {
        Render(28); // solid yellow throughout the local "Hi there" greeting
        return;
    }
    if (mode_ == Mode::Standby) {
        standby_brightness_ = 8;
        standby_direction_ = 1;
        Render(static_cast<uint8_t>(standby_brightness_));
        ESP_ERROR_CHECK(esp_timer_start_periodic(timer_, kBreathPeriodMs * 1000ULL));
        return;
    }
    if (mode_ == Mode::Listening || mode_ == Mode::Processing || mode_ == Mode::Speaking) {
        Render(30);
        ESP_ERROR_CHECK(esp_timer_start_periodic(timer_, kBlinkPeriodMs * 1000ULL));
        return;
    }
    Render(0);
}

void JarvisLed::OnTimer() {
    std::lock_guard<std::mutex> lock(mutex_);
    if (mode_ == Mode::Standby) {
        standby_brightness_ += standby_direction_ * 2;
        if (standby_brightness_ >= 54) {
            standby_brightness_ = 54;
            standby_direction_ = -1;
        } else if (standby_brightness_ <= 8) {
            standby_brightness_ = 8;
            standby_direction_ = 1;
        }
        Render(static_cast<uint8_t>(standby_brightness_));
        return;
    }

    phase_on_ = !phase_on_;
    if (mode_ == Mode::Startup) {
        Render(phase_on_ ? 28 : 0);
    } else if (mode_ == Mode::Listening || mode_ == Mode::Processing || mode_ == Mode::Speaking) {
        Render(phase_on_ ? 30 : 0);
    }
}

void JarvisLed::TimerCallback(void* arg) {
    static_cast<JarvisLed*>(arg)->OnTimer();
}

void JarvisLed::OnStateChanged() {
    {
        std::lock_guard<std::mutex> lock(mutex_);
        // The startup greeting has priority until its audio has fully drained.
        if (mode_ == Mode::Greeting) return;
    }
    switch (Application::GetInstance().GetDeviceState()) {
        case kDeviceStateStarting:
        case kDeviceStateConnecting:
            SetMode(Mode::Startup);
            break;
        case kDeviceStateIdle:
            voice_seen_ = false;
            SetMode(Mode::Standby);
            break;
        case kDeviceStateListening:
        case kDeviceStateAudioTesting:
            voice_seen_ = false;
            SetMode(Mode::Listening);
            break;
        case kDeviceStateSpeaking:
        case kDeviceStateNotifying:
            SetMode(Mode::Speaking);
            break;
        default:
            SetMode(Mode::Off);
            break;
    }
}

void JarvisLed::OnVoiceActivityChanged(bool active) {
    if (Application::GetInstance().GetDeviceState() != kDeviceStateListening) return;
    if (active) {
        voice_seen_ = true;
        SetMode(Mode::Listening);
    } else if (voice_seen_) {
        // Keep blue blinking while the recognized request is being processed.
        SetMode(Mode::Processing);
    }
}

void JarvisLed::OnStartupGreetingChanged(bool active) {
    if (active) {
        SetMode(Mode::Greeting);
    } else {
        SetMode(Mode::Standby);
    }
}
