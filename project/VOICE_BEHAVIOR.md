# JARVIS Voice Behavior — Fixed Specification

- Assistant platform: XiaoZhi.
- Wake phrase: "Jarvis".
- Startup greeting: "Hi there", spoken once after successful startup and audio initialization.
- User interaction language: English.
- AI spoken response language: English.
- Audio output: speaker driven by the connected I2S amplifier.

## Expected sequence

1. Power on and initialize the board, microphone, speaker, network, and XiaoZhi session.
2. Run the onboard green startup animation exactly five times.
3. Speak "Hi there" once.
4. Enter standby and wait for "Jarvis".
5. On wake phrase, enter listening state and capture the user's English speech.
6. While the request is being handled, enter processing state.
7. When XiaoZhi audio playback begins, enter speaking state.
8. When playback finishes, return to standby and wait for the next "Jarvis".

## Reliability requirements

- Do not announce startup success before audio output is initialized.
- If Wi-Fi or XiaoZhi connection fails, do not pretend the assistant is ready; expose a clear error state/log.
- Do not interrupt microphone capture or speaker playback with LED animation delays.
- English is the selected language for both recognition/conversation and spoken responses; verify the exact XiaoZhi firmware setting rather than assuming a UI-language option controls speech language.
