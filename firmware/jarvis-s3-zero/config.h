#pragma once

#include <driver/gpio.h>

// Waveshare ESP32-S3-Zero: 4 MB Flash, 2 MB Quad-SPI PSRAM.
#define AUDIO_INPUT_SAMPLE_RATE  16000
// Keep XiaoZhi's 24 kHz Opus playback rate, matching the known-good Build #97.
#define AUDIO_OUTPUT_SAMPLE_RATE 24000

// INMP441 microphone: SCK=4, WS=5, SD=6.
// MAX98357A amplifier: BCLK=7, LRCLK=8, DIN=9.
#define AUDIO_I2S_METHOD_SIMPLEX
#define AUDIO_I2S_MIC_GPIO_SCK  GPIO_NUM_4
#define AUDIO_I2S_MIC_GPIO_WS   GPIO_NUM_5
#define AUDIO_I2S_MIC_GPIO_DIN  GPIO_NUM_6
#define AUDIO_I2S_SPK_GPIO_BCLK GPIO_NUM_7
#define AUDIO_I2S_SPK_GPIO_LRCK GPIO_NUM_8
#define AUDIO_I2S_SPK_GPIO_DOUT GPIO_NUM_9

// Waveshare ESP32-S3-Zero onboard WS2812 RGB LED.
#define BUILTIN_LED_GPIO GPIO_NUM_21
