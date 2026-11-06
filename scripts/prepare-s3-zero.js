#!/usr/bin/env node
// Generate the custom Waveshare ESP32-S3-Zero board for the fresh JARVIS build.
const fs = require("fs");
const path = require("path");
const root = path.resolve(__dirname, "..", "xiaozhi-esp32");
const kconfigPath = path.join(root, "main", "Kconfig.projbuild");
const cmakePath = path.join(root, "main", "CMakeLists.txt");
const boardDir = path.join(root, "main", "boards", "s3-zero");

const configH = `#ifndef _BOARD_CONFIG_H_
#define _BOARD_CONFIG_H_
#include <driver/gpio.h>
#define AUDIO_INPUT_SAMPLE_RATE  16000
#define AUDIO_OUTPUT_SAMPLE_RATE 24000
#define AUDIO_I2S_METHOD_SIMPLEX
// INMP441
#define AUDIO_I2S_MIC_GPIO_SCK GPIO_NUM_4
#define AUDIO_I2S_MIC_GPIO_WS  GPIO_NUM_5
#define AUDIO_I2S_MIC_GPIO_DIN GPIO_NUM_6
// MAX98357A (SD intentionally left unconnected; no SD GPIO is configured)
#define AUDIO_I2S_SPK_GPIO_BCLK GPIO_NUM_7
#define AUDIO_I2S_SPK_GPIO_LRCK GPIO_NUM_8
#define AUDIO_I2S_SPK_GPIO_DOUT GPIO_NUM_9
// External single-colour LED and onboard WS2812 RGB LED
#define JARVIS_EXTERNAL_LED_GPIO GPIO_NUM_2
#define JARVIS_RGB_LED_GPIO GPIO_NUM_21
#define BOOT_BUTTON_GPIO GPIO_NUM_0
#endif
`;

const boardCc = `#include "wifi_board.h"
#include "codecs/no_audio_codec.h"
#include "application.h"
#include "button.h"
#include "config.h"
#include "led/led.h"
#include "led/circular_strip.h"
#include "device_state.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <driver/gpio.h>
#include <atomic>

class JarvisStatusLed : public Led {
private:
    CircularStrip rgb_{JARVIS_RGB_LED_GPIO, 1};
    std::atomic<bool> startup_active_{true};

    static void ExternalLedTask(void* arg) {
        auto* self = static_cast<JarvisStatusLed*>(arg);
        bool phase = false;
        while (true) {
            auto state = Application::GetInstance().GetDeviceState();
            if (state == kDeviceStateIdle) {
                self->SetExternal(true); // standby: solid ON
                vTaskDelay(pdMS_TO_TICKS(100));
            } else if (state == kDeviceStateSpeaking || state == kDeviceStateNotifying) {
                phase = !phase;
                self->SetExternal(phase); // response: blink with the green external LED
                vTaskDelay(pdMS_TO_TICKS(350));
            } else {
                self->SetExternal(false);
                phase = false;
                vTaskDelay(pdMS_TO_TICKS(100));
            }
        }
    }

    static void StartupTask(void* arg) {
        auto* self = static_cast<JarvisStatusLed*>(arg);
        const StripColor green{0, 64, 0};
        for (int i = 0; i < 5; ++i) {
            self->rgb_.SetAllColor(green);
            vTaskDelay(pdMS_TO_TICKS(180));
            self->rgb_.SetAllColor({0, 0, 0});
            vTaskDelay(pdMS_TO_TICKS(180));
        }
        self->startup_active_.store(false);
        self->OnStateChanged();
        vTaskDelete(nullptr);
    }

    void SetExternal(bool on) {
        gpio_set_level(JARVIS_EXTERNAL_LED_GPIO, on ? 1 : 0);
    }

public:
    JarvisStatusLed() {
        gpio_config_t io = {};
        io.pin_bit_mask = 1ULL << JARVIS_EXTERNAL_LED_GPIO;
        io.mode = GPIO_MODE_OUTPUT;
        io.pull_up_en = GPIO_PULLUP_DISABLE;
        io.pull_down_en = GPIO_PULLDOWN_DISABLE;
        io.intr_type = GPIO_INTR_DISABLE;
        ESP_ERROR_CHECK(gpio_config(&io));
        SetExternal(false);
        xTaskCreate(ExternalLedTask, "jarvis_external_led", 2048, this, 2, nullptr);
        xTaskCreate(StartupTask, "jarvis_startup_led", 3072, this, 2, nullptr);
    }

    void OnStateChanged() override {
        if (startup_active_.load()) return;
        auto state = Application::GetInstance().GetDeviceState();
        SetExternal(false);
        switch (state) {
            case kDeviceStateIdle:
                rgb_.SetAllColor({0, 0, 0});
                SetExternal(true);
                break;
            case kDeviceStateConnecting:
                rgb_.Blink({64, 48, 0}, 350); // yellow: processing/thinking
                break;
            case kDeviceStateListening:
            case kDeviceStateAudioTesting:
                rgb_.Blink({0, 0, 64}, 350); // blue: listening
                break;
            case kDeviceStateSpeaking:
            case kDeviceStateNotifying:
                rgb_.Blink({0, 64, 0}, 350); // green: assistant speaking
                break;
            default:
                rgb_.SetAllColor({0, 0, 0});
                break;
        }
    }
};

class WaveshareS3ZeroBoard : public WifiBoard {
private:
    Button boot_button_;
    JarvisStatusLed status_led_;

    void InitializeButtons() {
        boot_button_.OnClick([this]() {
            auto& app = Application::GetInstance();
            if (app.GetDeviceState() == kDeviceStateStarting) {
                EnterWifiConfigMode();
            } else {
                app.ToggleChatState();
            }
        });
        boot_button_.OnLongPress([this]() { EnterWifiConfigMode(); });
    }

public:
    WaveshareS3ZeroBoard() : boot_button_(BOOT_BUTTON_GPIO) {
        InitializeButtons();
    }

    AudioCodec* GetAudioCodec() override {
        static NoAudioCodecSimplex codec(
            AUDIO_INPUT_SAMPLE_RATE, AUDIO_OUTPUT_SAMPLE_RATE,
            AUDIO_I2S_SPK_GPIO_BCLK, AUDIO_I2S_SPK_GPIO_LRCK, AUDIO_I2S_SPK_GPIO_DOUT,
            AUDIO_I2S_MIC_GPIO_SCK, AUDIO_I2S_MIC_GPIO_WS, AUDIO_I2S_MIC_GPIO_DIN);
        return &codec;
    }

    Led* GetLed() override { return &status_led_; }
};

DECLARE_BOARD(WaveshareS3ZeroBoard);
`;

fs.mkdirSync(boardDir, { recursive: true });
fs.writeFileSync(path.join(boardDir, "config.h"), configH);
fs.writeFileSync(path.join(boardDir, "waveshare_s3_zero.cc"), boardCc);

let kconfig = fs.readFileSync(kconfigPath, "utf8");
if (!kconfig.includes("config BOARD_TYPE_S3_ZERO")) {
  const choice = kconfig.indexOf("choice BOARD_TYPE");
  const pos = kconfig.indexOf("endchoice", choice);
  if (choice < 0 || pos < 0) throw new Error("Could not locate BOARD_TYPE choice");
  kconfig = kconfig.slice(0, pos) +
    '    config BOARD_TYPE_S3_ZERO\n        bool "Waveshare ESP32-S3-Zero (JARVIS)"\n        depends on IDF_TARGET_ESP32S3\n' +
    kconfig.slice(pos);
  fs.writeFileSync(kconfigPath, kconfig);
}

let cmake = fs.readFileSync(cmakePath, "utf8");
if (!cmake.includes("CONFIG_BOARD_TYPE_S3_ZERO")) {
  const marker = "\nif(NOT BOARD_DIR AND NOT CMAKE_BUILD_EARLY_EXPANSION)";
  const pos = cmake.indexOf(marker);
  if (pos < 0) throw new Error("Could not locate BOARD_DIR validation insertion point");
  cmake = cmake.slice(0, pos) +
    '\nelseif(CONFIG_BOARD_TYPE_S3_ZERO)\n    set(BOARD_DIR "s3-zero")' +
    cmake.slice(pos);
}
if (!cmake.includes("list(APPEND MAIN_PRIV_REQUIRES_EXTRA espressif__led_strip)")) {
  const marker = 'set(MAIN_PRIV_REQUIRES_EXTRA "")';
  const pos = cmake.indexOf(marker);
  if (pos < 0) throw new Error("Could not locate component dependency insertion point");
  cmake = cmake.slice(0, pos) +
    marker + '\nlist(APPEND MAIN_PRIV_REQUIRES_EXTRA led_strip)' +
    cmake.slice(pos + marker.length);
}
fs.writeFileSync(cmakePath, cmake);

console.log("Prepared Waveshare ESP32-S3-Zero JARVIS board: mic 4/5/6, speaker 7/8/9, external LED 2, RGB LED 21; amplifier SD untouched.");
