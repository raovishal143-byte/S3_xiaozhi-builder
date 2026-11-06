#include "jarvis_led.h"
#include "application.h"
#include "device_state.h"
#include <esp_log.h>

#define TAG "JarvisLed"
static constexpr uint32_t kBlinkPeriodMs = 300;

JarvisLed::JarvisLed(gpio_num_t rgb_gpio, gpio_num_t external_gpio)
    : external_gpio_(external_gpio) {
    gpio_config_t gpio_cfg = {};
    gpio_cfg.pin_bit_mask = 1ULL << external_gpio_;
    gpio_cfg.mode = GPIO_MODE_OUTPUT;
    gpio_cfg.pull_up_en = GPIO_PULLUP_DISABLE;
    gpio_cfg.pull_down_en = GPIO_PULLDOWN_DISABLE;
    gpio_cfg.intr_type = GPIO_INTR_DISABLE;
    ESP_ERROR_CHECK(gpio_config(&gpio_cfg));
    ESP_ERROR_CHECK(gpio_set_level(external_gpio_, 0));

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

    // Start the red boot pattern immediately when the board creates this LED.
    // The board constructor forces LED creation before Application enters Starting.
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

void JarvisLed::Render(bool on) {
    phase_on_ = on;
    if (!strip_) return;

    uint8_t r = 0, g = 0, b = 0;
    if (on) {
        switch (mode_) {
            case Mode::Startup:     r = 24; g = 0;  b = 0;  break; // red
            case Mode::Speaking:    r = 0;  g = 24; b = 0;  break; // green
            case Mode::Listening:   r = 0;  g = 0;  b = 24; break; // blue
            case Mode::Processing:  r = 0;  g = 0;  b = 24; break; // blue
            default: break;
        }
    }
    ESP_ERROR_CHECK(led_strip_set_pixel(strip_, 0, r, g, b));
    ESP_ERROR_CHECK(led_strip_refresh(strip_));

    const bool external_on = on && mode_ == Mode::Speaking;
    ESP_ERROR_CHECK(gpio_set_level(external_gpio_, external_on ? 1 : 0));
}

void JarvisLed::SetMode(Mode mode) {
    std::lock_guard<std::mutex> lock(mutex_);
    if (timer_) ESP_ERROR_CHECK(esp_timer_stop(timer_));
    mode_ = mode;
    startup_edges_remaining_ = 0;

    if (mode_ == Mode::Startup) {
        // Start lit immediately; ten edges produce exactly five complete flashes.
        startup_edges_remaining_ = 10;
        Render(true);
        ESP_ERROR_CHECK(esp_timer_start_periodic(timer_, kBlinkPeriodMs * 1000ULL));
        return;
    }

    if (mode_ == Mode::Standby) {
        Render(false);
        ESP_ERROR_CHECK(gpio_set_level(external_gpio_, 1));
        return;
    }

    if (mode_ == Mode::Listening || mode_ == Mode::Processing || mode_ == Mode::Speaking) {
        Render(true);
        ESP_ERROR_CHECK(esp_timer_start_periodic(timer_, kBlinkPeriodMs * 1000ULL));
        return;
    }

    Render(false);
}

void JarvisLed::OnTimer() {
    std::lock_guard<std::mutex> lock(mutex_);
    if (mode_ == Mode::Startup) {
        --startup_edges_remaining_;
        if (startup_edges_remaining_ <= 0) {
            ESP_ERROR_CHECK(esp_timer_stop(timer_));
            mode_ = Mode::Off;
            Render(false);
            return;
        }
    }
    Render(!phase_on_);
}

void JarvisLed::TimerCallback(void* arg) {
    static_cast<JarvisLed*>(arg)->OnTimer();
}

void JarvisLed::OnStateChanged() {
    switch (Application::GetInstance().GetDeviceState()) {
        case kDeviceStateStarting:
            SetMode(Mode::Startup);
            break;
        case kDeviceStateIdle:
            voice_seen_ = false;
            SetMode(Mode::Standby);
            break;
        case kDeviceStateConnecting:
            SetMode(Mode::Processing);
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
        // While Jarvis processes the captured speech, retain the requested blue blink.
        SetMode(Mode::Processing);
    }
}
