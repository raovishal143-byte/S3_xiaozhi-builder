# JARVIS — English Voice Assistant

A clean project specification for a Waveshare ESP32-S3-Zero voice assistant using the XiaoZhi AI service.

## Confirmed user-facing behavior

- Startup spoken greeting: **"Hi there"**, once after successful initialization.
- Wake phrase: **"Jarvis"**.
- AI assistant/service: **XiaoZhi**.
- Conversation and spoken response language: **English**.
- Output audio: connected speaker through the I2S amplifier.

## LED state machine

The exact requested LED behavior is documented in [LED_BEHAVIOR.md](LED_BEHAVIOR.md).

| State | Onboard RGB (GPIO21) | External LED (GPIO2) |
|---|---|---|
| Power-on | Green, exactly 5 blinks | Off |
| Standby / waiting for Jarvis | Off | Solid on |
| Listening | Blue blinking | Off |
| Processing / thinking | Yellow blinking | Off |
| AI speaking / responding | Green blinking | Green blinking |

## Build policy

This repository branch starts from a clean baseline. Do not copy prior experimental firmware or generated binaries into this project.

Before producing a flashable image, verify:
1. Exact Waveshare ESP32-S3-Zero board target and flash/PSRAM configuration.
2. INMP441 microphone I2S pin mapping and channel/slot format.
3. MAX98357A I2S output pin mapping and amplifier enable/SD wiring.
4. GPIO21 onboard RGB LED type, pixel count, and color order.
5. GPIO2 external LED polarity and resistor/current limit.
6. XiaoZhi English language configuration and wake-word support.

A firmware artifact must only be called ready after a successful clean cloud build and a documented hardware test.