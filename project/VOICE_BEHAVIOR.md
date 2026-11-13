# JARVIS Voice Behavior — Current Fixed Specification

- Assistant platform: XiaoZhi.
- Wake phrase: "Jarvis".
- Wake phrase detection: offline model `wn9_jarvis_tts`.
- Startup greeting: "Hi there", spoken locally once after successful startup and audio initialization.
- User interaction and spoken response language: English.
- Microphone: INMP441 on GPIO4/5/6, 16 kHz input.
- Speaker: MAX98357A on BCLK GPIO7, LRCLK GPIO8, DIN GPIO9.
- Speaker playback rate: 24 kHz, matching the known-good Build #97 baseline and XiaoZhi's 24 kHz Opus playback path.
- Speaker output format: mono, 32-bit I2S standard format, left slot, with the existing simplex TX/RX arrangement.
- Output volume: 100%, with linear PCM scaling; do not load an older lower volume from NVS.

## Expected sequence

1. Initialize the board, microphone, speaker, PSRAM, network, and XiaoZhi session.
2. Run the onboard red startup animation exactly five times.
3. Speak "Hi there!" once through the speaker.
4. Enter standby with a yellow breathing LED while waiting for the offline "Jarvis" wake phrase.
5. On wake phrase, enter listening state and capture the user's English speech.
6. While the request is handled, alternate green and blue LED flashes.
7. When XiaoZhi audio playback begins, blink the onboard LED green.
8. When playback finishes, return to yellow breathing standby.

## Audio integrity requirements

- Preserve the Build #97 I2S pin mapping: BCLK=7, LRCLK=8, DOUT=9.
- Preserve the 24 kHz speaker output rate until a measured codec-path test justifies changing it.
- Keep the upstream mono-left 32-bit I2S slot format and one-bit I2S alignment unless a captured logic trace proves it is wrong.
- Apply a linear 0–100 output scale and force 100% at startup so old NVS values cannot silently attenuate playback.
- Do not change microphone pins, sample rate, gain, or I2S format as part of the speaker-volume fix.
- Do not use GPIO2 or change any hardware wiring.
