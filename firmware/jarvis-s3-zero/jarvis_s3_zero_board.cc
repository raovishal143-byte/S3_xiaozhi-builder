#include "wifi_board.h"
#include "codecs/no_audio_codec.h"
#include "config.h"
#include "jarvis_led.h"

class JarvisS3ZeroBoard final : public WifiBoard {
public:
    JarvisS3ZeroBoard() {
        // Create the onboard RGB LED controller before Application starts.
        (void)GetLed();
    }

    AudioCodec* GetAudioCodec() override {
        static NoAudioCodecSimplex codec(
            AUDIO_INPUT_SAMPLE_RATE, AUDIO_OUTPUT_SAMPLE_RATE,
            AUDIO_I2S_SPK_GPIO_BCLK, AUDIO_I2S_SPK_GPIO_LRCK, AUDIO_I2S_SPK_GPIO_DOUT,
            AUDIO_I2S_MIC_GPIO_SCK, AUDIO_I2S_MIC_GPIO_WS, AUDIO_I2S_MIC_GPIO_DIN);
        return &codec;
    }

    Led* GetLed() override {
        static JarvisLed led(BUILTIN_LED_GPIO);
        return &led;
    }
};

DECLARE_BOARD(JarvisS3ZeroBoard);
