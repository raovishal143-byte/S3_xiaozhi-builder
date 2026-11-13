#include "jarvis_led.h"
#include "application.h"
#include "device_state.h"
#include <esp_log.h>
#include <cmath>

#define TAG "JarvisLed"
static constexpr uint32_t kBlinkPeriodMs = 300;
static constexpr uint64_t kBreathPeriodUs = 30000;
static constexpr float kPi = 3.14159265358979323846f;

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

    // Begin the one-time five-flash red startup pattern as soon as the board is created.
    SetMode(Mode::Startup);
}

JarvisLed::~JarvisLed() {
    if (timer_) {
        if (esp_timer_is_active(timer_)) {
            esp_timer_stop(timer_);
        }
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

    if (mode_ == Mode::Standby) {
        // Smooth yellow breathing, approximately a 3-second full cycle.
        const float phase = (2.0f * kPi * static_cast<float>(breath_step_)) / 100.0f;
        const float wave = 0.5f - 0.5f * std::cos(phase);
        const uint8_t level = static_cast<uint8_t>(2.0f + wave * 24.0f);
        r = level;
        g = level;
    } else if (on) {
        switch (mode_) {
            case Mode::Startup:
                r = 28; // red
                break;
            case Mode::Listening:
                b = 28; // blue
                break;
            case Mode::Processing:
                if (processing_blue_phase_) {
                    b = 28; // alternate blue and green on successive flashes
                } else {
                    g = 28;
                }
                break;
            case Mode::Speaking:
                g = 28; // green
                break;
            default:
                break;
        }
    }

    ESP_ERROR_CHECK(led_strip_set_pixel(strip_, 0, r, g, b));
    ESP_ERROR_CHECK(led_strip_refresh(strip_));
}

void JarvisLed::SetMode(Mode mode) {
    std::lock_guard<std::mutex> lock(mutex_);

    if (mode == Mode::Startup && startup_done_) return;
    // A newly created esp_timer is inactive; stopping it returns ESP_ERR_INVALID_STATE.
    // Only stop it when it is actually running, otherwise startup aborts before LEDs initialise.
    if (timer_ && esp_timer_is_active(timer_)) {
        ESP_ERROR_CHECK(esp_timer_stop(timer_));
    }

    mode_ = mode;
    startup_edges_remaining_ = 0;
    breath_step_ = 0;
    processing_blue_phase_ = false;

    if (mode_ == Mode::Startup) {
        startup_edges_remaining_ = 10; // ten edges = exactly five complete flashes
        Render(true);
        ESP_ERROR_CHECK(esp_timer_start_periodic(timer_, kBlinkPeriodMs * 1000ULL));
        return;
    }

    if (mode_ == Mode::Standby) {
        Render(true);
        ESP_ERROR_CHECK(esp_timer_start_periodic(timer_, kBreathPeriodUs));
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
    bool enter_standby = false;

    {
        std::lock_guard<std::mutex> lock(mutex_);

        if (mode_ == Mode::Startup) {
            --startup_edges_remaining_;
            if (startup_edges_remaining_ <= 0) {
                ESP_ERROR_CHECK(esp_timer_stop(timer_));
                startup_done_ = true;
                mode_ = Mode::Off;
                Render(false);
                enter_standby =
                    Application::GetInstance().GetDeviceState() == kDeviceStateIdle;
            } else {
                Render(!phase_on_);
            }
        } else if (mode_ == Mode::Standby) {
            breath_step_ = static_cast<uint8_t>((breath_step_ + 1) % 100);
            Render(true);
        } else {
            const bool next_on = !phase_on_;
            if (mode_ == Mode::Processing && next_on) {
                processing_blue_phase_ = !processing_blue_phase_;
            }
            Render(next_on);
        }
    }

    if (enter_standby) {
        SetMode(Mode::Standby);
    }
}

void JarvisLed::TimerCallback(void* arg) {
    static_cast<JarvisLed*>(arg)->OnTimer();
}

void JarvisLed::OnStateChanged() {
    {
        std::lock_guard<std::mutex> lock(mutex_);
        // Never let a quick network transition truncate the five startup flashes.
        if (mode_ == Mode::Startup && startup_edges_remaining_ > 0) return;
    }

    switch (Application::GetInstance().GetDeviceState()) {
        case kDeviceStateStarting: {
            bool startup_done;
            {
                std::lock_guard<std::mutex> lock(mutex_);
                startup_done = startup_done_;
            }
            if (!startup_done) SetMode(Mode::Startup);
            else SetMode(Mode::Off);
            break;
        }
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

    bool should_process = false;
    {
        std::lock_guard<std::mutex> lock(mutex_);
        if (active) {
            voice_seen_ = true;
        } else {
            should_process = voice_seen_;
        }
    }

    if (active) {
        SetMode(Mode::Listening);
    } else if (should_process) {
        SetMode(Mode::Processing);
    }
}
