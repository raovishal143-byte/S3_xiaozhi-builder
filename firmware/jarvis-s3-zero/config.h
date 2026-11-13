#pragma once

#include <driver/gpio.h>

// Waveshare ESP32-S3-Zero: 4 MB Flash, 2 MB Quad-SPI PSRAM.
#define AUDIO_INPUT_SAMPLE_RATE  16000
// MAX98357A does not support 24 kHz LRCLK. Use 32 kHz; XiaoZhi's
// AudioService resamples incoming 24 kHz Opus PCM to this codec rate.
#define AUDIO_OUTPUT_SAMPLE_RATE 32000

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
