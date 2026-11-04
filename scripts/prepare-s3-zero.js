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

class WaveshareS3ZeroBoard : public WifiBoard {
private:
    Button boot_button_;
    GpioLed* status_led_ = nullptr;

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
        status_led_ = new GpioLed(BUILTIN_LED_GPIO);
        InitializeButtons();
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
  '            // Blink GPIO2 only while the assistant is speaking.',
  "            SetBrightness(SPEAKING_BRIGHTNESS);",
  "            StartContinuousBlink(180);",
  "            break;"
].join(String.fromCharCode(10));
if (ledSource.includes(idleLed)) ledSource = ledSource.replace(idleLed, idleLedOff);
else if (!ledSource.includes('case kDeviceStateIdle:' + String.fromCharCode(10) + '            TurnOff();')) throw new Error('Could not safely patch idle LED state');
if (ledSource.includes(listeningLed)) ledSource = ledSource.replace(listeningLed, listeningLedOff);
else if (!ledSource.includes('case kDeviceStateListening:' + String.fromCharCode(10) + '        case kDeviceStateAudioTesting:' + String.fromCharCode(10) + '            TurnOff();')) throw new Error('Could not safely patch listening LED state');
if (ledSource.includes(steadySpeaking)) ledSource = ledSource.replace(steadySpeaking, blinkingSpeaking);
else if (!ledSource.includes('Blink GPIO2 only while the assistant is speaking')) throw new Error('Could not safely patch speaking LED state');
fs.writeFileSync(ledSourcePath, ledSource);

// Automatically open a first conversation after Wi-Fi and cloud activation.
// The XiaoZhi server's greeting setting and the agent role provide the spoken text.
const appSourcePath = path.join(root, 'main', 'application.cc');
let appSource = fs.readFileSync(appSourcePath, 'utf8');
const readySoundBlock = [
  '    Schedule([this]() {',
  '        // Play the success sound to indicate the device is ready',
  '        audio_service_.PlaySound(Lang::Sounds::OGG_SUCCESS);',
  '    });'
].join(String.fromCharCode(10));
const startupGreetingBlock = [
  '    Schedule([this]() {',
  '        // Finish the ready sound before opening the automatic greeting session.',
  '        audio_service_.PlaySound(Lang::Sounds::OGG_SUCCESS);',
  '        while (!audio_service_.IsPlaybackIdle()) {',
  '            vTaskDelay(pdMS_TO_TICKS(50));',
  '        }',
  '        WakeWordInvoke("Hey Buddy");',
  '    });'
].join(String.fromCharCode(10));
if (appSource.includes(readySoundBlock)) {
  appSource = appSource.replace(readySoundBlock, startupGreetingBlock);
  fs.writeFileSync(appSourcePath, appSource);
} else if (!appSource.includes('WakeWordInvoke("Hey Buddy")')) {
  throw new Error('Could not safely add the startup greeting trigger');
}

console.log('Prepared custom Waveshare ESP32-S3-Zero board (no display).');
