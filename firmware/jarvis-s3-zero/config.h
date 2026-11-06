#pragma once

#include <driver/gpio.h>

// Waveshare ESP32-S3-Zero: 4 MB Flash, 2 MB PSRAM.
#define AUDIO_INPUT_SAMPLE_RATE  16000
#define AUDIO_OUTPUT_SAMPLE_RATE 48000

// Separate full-duplex I2S controllers are not required for these modules.
#define AUDIO_I2S_METHOD_SIMPLEX
#define AUDIO_I2S_MIC_GPIO_SCK  GPIO_NUM_4
#define AUDIO_I2S_MIC_GPIO_WS   GPIO_NUM_5
#define AUDIO_I2S_MIC_GPIO_DIN  GPIO_NUM_6
#define AUDIO_I2S_SPK_GPIO_BCLK GPIO_NUM_7
#define AUDIO_I2S_SPK_GPIO_LRCK GPIO_NUM_8
#define AUDIO_I2S_SPK_GPIO_DOUT GPIO_NUM_9

#define BUILTIN_LED_GPIO GPIO_NUM_21
#define JARVIS_EXTERNAL_LED_GPIO GPIO_NUM_2
