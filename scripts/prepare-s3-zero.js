#!/usr/bin/env node
// Adds a headless Waveshare ESP32-S3-Zero board to the pinned XiaoZhi submodule.
const fs = require('fs');
const path = require('path');
const root = path.resolve(__dirname, '..', 'xiaozhi-esp32');
const kconfigPath = path.join(root, 'main', 'Kconfig.projbuild');
const cmakePath = path.join(root, 'main', 'CMakeLists.txt');
const boardDir = path.join(root, 'main', 'boards', 's3-zero');

const configH = `#ifndef _BOARD_CONFIG_H_
#define _BOARD_CONFIG_H_

#include <driver/gpio.h>

#define AUDIO_INPUT_SAMPLE_RATE  16000
#define AUDIO_OUTPUT_SAMPLE_RATE 24000
#define AUDIO_I2S_METHOD_SIMPLEX

// INMP441 microphone
#define AUDIO_I2S_MIC_GPIO_SCK GPIO_NUM_4
#define AUDIO_I2S_MIC_GPIO_WS  GPIO_NUM_5
#define AUDIO_I2S_MIC_GPIO_DIN GPIO_NUM_6

// MAX98357A speaker amplifier
#define AUDIO_I2S_SPK_GPIO_BCLK GPIO_NUM_8
#define AUDIO_I2S_SPK_GPIO_LRCK GPIO_NUM_9
#define AUDIO_I2S_SPK_GPIO_DOUT GPIO_NUM_10

// External indicator LED(s) on GPIO2; onboard WS2812 is not used.
#define BUILTIN_LED_GPIO GPIO_NUM_2
#define BOOT_BUTTON_GPIO GPIO_NUM_0

#endif
`;

const boardCc = `#include "wifi_board.h"
#include "codecs/no_audio_codec.h"
#include "application.h"
#include "button.h"
#include "config.h"
#include "led/gpio_led.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <atomic>

class StartupAwareGpioLed : public GpioLed {
private:
    std::atomic<bool> startup_sequence_active_{true};
    std::atomic<bool> speaking_blink_active_{false};

    static void SpeakingBlinkTask(void* arg) {
        auto* self = static_cast<StartupAwareGpioLed*>(arg);
        auto& app = Application::GetInstance();
        while (self->speaking_blink_active_.load() &&
               app.GetDeviceState() == kDeviceStateSpeaking) {
            self->SetBrightness(100);
            self->TurnOn();
            vTaskDelay(pdMS_TO_TICKS(180));
            self->TurnOff();
            vTaskDelay(pdMS_TO_TICKS(180));
        }
        self->speaking_blink_active_.store(false);
        self->TurnOff();
        vTaskDelete(nullptr);
    }

public:
    explicit StartupAwareGpioLed(gpio_num_t gpio) : GpioLed(gpio) {}

    void OnStateChanged() override {
        if (startup_sequence_active_.load()) return;

        auto& app = Application::GetInstance();
        if (app.GetDeviceState() == kDeviceStateSpeaking) {
            bool expected = false;
            if (speaking_blink_active_.compare_exchange_strong(expected, true)) {
                if (xTaskCreate(SpeakingBlinkTask, "ai_led_blink", 2048, this, 1, nullptr) != pdPASS) {
                    speaking_blink_active_.store(false);
                    TurnOff();
                }
            }
        } else {
            speaking_blink_active_.store(false);
            TurnOff();
        }
    }

    void FinishStartupSequence() {
        startup_sequence_active_.store(false);
        speaking_blink_active_.store(false);
        TurnOff();
    }
};

class WaveshareS3ZeroBoard : public WifiBoard {
private:
    Button boot_button_;
    StartupAwareGpioLed* status_led_ = nullptr;

    static void StartupLedTask(void* arg) {
        auto* self = static_cast<WaveshareS3ZeroBoard*>(arg);
        for (int i = 0; i < 5; ++i) {
            self->status_led_->TurnOn();
            vTaskDelay(pdMS_TO_TICKS(180));
            self->status_led_->TurnOff();
            vTaskDelay(pdMS_TO_TICKS(180));
        }
        self->status_led_->FinishStartupSequence();
        vTaskDelete(nullptr);
    }

    void InitializeButtons() {
        boot_button_.OnClick([this]() {
            auto& app = Application::GetInstance();
            if (app.GetDeviceState() == kDeviceStateStarting) {
                EnterWifiConfigMode();
            } else {
                app.ToggleChatState();
            }
        });
        boot_button_.OnLongPress([this]() {
            EnterWifiConfigMode();
        });
    }

public:
    WaveshareS3ZeroBoard() : boot_button_(BOOT_BUTTON_GPIO) {
        status_led_ = new StartupAwareGpioLed(BUILTIN_LED_GPIO);
        status_led_->SetBrightness(100);
        InitializeButtons();
        xTaskCreate(StartupLedTask, "startup_led", 2048, this, 1, nullptr);
    }

    AudioCodec* GetAudioCodec() override {
        static NoAudioCodecSimplex audio_codec(
            AUDIO_INPUT_SAMPLE_RATE, AUDIO_OUTPUT_SAMPLE_RATE,
            AUDIO_I2S_SPK_GPIO_BCLK, AUDIO_I2S_SPK_GPIO_LRCK, AUDIO_I2S_SPK_GPIO_DOUT,
            AUDIO_I2S_MIC_GPIO_SCK, AUDIO_I2S_MIC_GPIO_WS, AUDIO_I2S_MIC_GPIO_DIN);
        return &audio_codec;
    }

    Led* GetLed() override {
        return status_led_;
    }
};

DECLARE_BOARD(WaveshareS3ZeroBoard);
`;

fs.mkdirSync(boardDir, { recursive: true });
fs.writeFileSync(path.join(boardDir, 'config.h'), configH);
fs.writeFileSync(path.join(boardDir, 'waveshare_s3_zero.cc'), boardCc);

let kconfig = fs.readFileSync(kconfigPath, 'utf8');
if (!kconfig.includes('config BOARD_TYPE_S3_ZERO')) {
  const pos = kconfig.indexOf('endchoice', kconfig.indexOf('choice BOARD_TYPE'));
  if (pos < 0) throw new Error('Could not find endchoice in main/Kconfig.projbuild');
  kconfig = kconfig.slice(0, pos) +
    '    config BOARD_TYPE_S3_ZERO\n        bool "Waveshare ESP32-S3-Zero (custom, no display)"\n        depends on IDF_TARGET_ESP32S3\n' +
    kconfig.slice(pos);
  fs.writeFileSync(kconfigPath, kconfig);
}

let cmake = fs.readFileSync(cmakePath, 'utf8');
if (!cmake.includes('CONFIG_BOARD_TYPE_S3_ZERO')) {
  const marker = '\nendif()\n\nif(MANUFACTURER)';
  const pos = cmake.indexOf(marker);
  if (pos < 0) throw new Error('Could not find board-selection CMake insertion point');
  cmake = cmake.slice(0, pos) +
    '\nelseif(CONFIG_BOARD_TYPE_S3_ZERO)\n    set(BOARD_TYPE "s3-zero")\n    set(BOARD_NAME "waveshare-esp32-s3-zero")' +
    cmake.slice(pos);
  fs.writeFileSync(cmakePath, cmake);
}

const ledSourcePath = path.join(root, 'main', 'led', 'gpio_led.cc');
let ledSource = fs.readFileSync(ledSourcePath, 'utf8');
const idleLed = [
  "        case kDeviceStateIdle:",
  "            SetBrightness(IDLE_BRIGHTNESS);",
  "            TurnOn();",
  "            // TurnOff();",
  "            break;"
].join(String.fromCharCode(10));
const idleLedOff = [
  "        case kDeviceStateIdle:",
  "            TurnOff();",
  "            break;"
].join(String.fromCharCode(10));
const listeningLed = [
  "        case kDeviceStateListening:",
  "        case kDeviceStateAudioTesting:",
  "            if (app.IsVoiceDetected()) {",
  "                SetBrightness(HIGH_BRIGHTNESS);",
  "            } else {",
  "                SetBrightness(LOW_BRIGHTNESS);",
  "            }",
  "            // TurnOn();",
  "            StartFadeTask();",
  "            break;"
].join(String.fromCharCode(10));
const listeningLedOff = [
  "        case kDeviceStateListening:",
  "        case kDeviceStateAudioTesting:",
  "            TurnOff();",
  "            break;"
].join(String.fromCharCode(10));
const steadySpeaking = [
  "        case kDeviceStateSpeaking:",
  "            SetBrightness(SPEAKING_BRIGHTNESS);",
  "            TurnOn();",
  "            break;"
].join(String.fromCharCode(10));
const blinkingSpeaking = [
  "        case kDeviceStateSpeaking:",
  '            // GPIO2 stays steadily ON only while XiaoZhi is answering.',
  "            SetBrightness(SPEAKING_BRIGHTNESS);",
  "            TurnOn();",
  "            break;"
].join(String.fromCharCode(10));
if (ledSource.includes(idleLed)) ledSource = ledSource.replace(idleLed, idleLedOff);
else if (!ledSource.includes('case kDeviceStateIdle:' + String.fromCharCode(10) + '            TurnOff();')) throw new Error('Could not safely patch idle LED state');
if (ledSource.includes(listeningLed)) ledSource = ledSource.replace(listeningLed, listeningLedOff);
else if (!ledSource.includes('case kDeviceStateListening:' + String.fromCharCode(10) + '        case kDeviceStateAudioTesting:' + String.fromCharCode(10) + '            TurnOff();')) throw new Error('Could not safely patch listening LED state');
if (ledSource.includes(steadySpeaking)) ledSource = ledSource.replace(steadySpeaking, blinkingSpeaking);
else if (!ledSource.includes('GPIO2 stays steadily ON only while XiaoZhi is answering.')) throw new Error('Could not safely patch speaking LED state');

// Enforce the requested LED policy for every device state: only speaking is ON.
// The board-level StartupAwareGpioLed independently owns the five startup blinks.
const stateHandlerStart = ledSource.indexOf('void GpioLed::OnStateChanged() {');
const stateHandlerEnd = ledSource.indexOf('\nvoid GpioLed::EventTask', stateHandlerStart);
if (stateHandlerStart < 0 || stateHandlerEnd < 0) throw new Error('Could not locate complete GPIO LED state handler');
const stateHandler = [
  'void GpioLed::OnStateChanged() {',
  '    auto& app = Application::GetInstance();',
  '    if (app.GetDeviceState() == kDeviceStateSpeaking) {',
  '        SetBrightness(SPEAKING_BRIGHTNESS);',
  '        TurnOn();',
  '    } else {',
  '        TurnOff();',
  '    }',
  '}',
  ''
].join(String.fromCharCode(10));
ledSource = ledSource.slice(0, stateHandlerStart) + stateHandler + ledSource.slice(stateHandlerEnd + 1);
fs.writeFileSync(ledSourcePath, ledSource);

// Wake-word detections are local. When the network/protocol is unavailable,
// log the detection rather than silently discarding it.
const appSourcePath = path.join(root, "main", "application.cc");
let appSource = fs.readFileSync(appSourcePath, "utf8");
const noProtocol = 'void Application::HandleWakeWordDetectedEvent() {\n    if (!protocol_) {\n        return;\n    }';
const offlineWake = 'void Application::HandleWakeWordDetectedEvent() {\n    if (!protocol_) {\n        ESP_LOGI(TAG, "Offline wake word detected: %s (network unavailable)", audio_service_.GetLastWakeWord().c_str());\n        audio_service_.EnableWakeWordDetection(true);\n        return;\n    }';
if (appSource.includes(noProtocol)) appSource = appSource.replace(noProtocol, offlineWake);
else if (!appSource.includes('Offline wake word detected:')) throw new Error('Could not safely add offline wake-word logging');

fs.writeFileSync(appSourcePath, appSource);

// Startup greeting intentionally disabled by request.
console.log('Prepared custom Waveshare ESP32-S3-Zero board (no display, no startup greeting).');
