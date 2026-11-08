# JARVIS Gemini Build #105 — implementation plan

Status: experimental branch only. Build #105 remains the protected rollback image.

## Protected baseline

- Reference branch: `jarvis-rgb-status-led`
- Reference commit: `3e24e80fe0d1f8da95af135516a010dcc3fa95b8`
- Experimental branch: `jarvis-gemini-build105`
- Never commit experimental changes to the reference branch.
- Do not flash an experimental image until its build and test results are reported.

## User-approved behaviour

- Gemini Live is the conversational AI provider.
- Support Hindi, English, and natural Hindi-English code switching (Hinglish); validate with real tests.
- Use the selected deep male Algenib voice with a restrained synthetic/robotic delivery for spoken responses, provided the selected Live model accepts that voice.
- The startup greeting is the user's uploaded Algenib recording saying exactly "Hi there!". It is stored locally and played at the existing startup trigger. It must not call Gemini or require Wi-Fi at boot.
- The experimental branch replaces only its own greeting asset; Build #105's original greeting remains untouched.
- Half-duplex: capture one user utterance, stop microphone uplink, wait for the complete assistant response, play it, then re-arm offline wake detection.
- No laptop, always-on home PC, or user-operated server.
- User enters Wi-Fi credentials and their own Gemini API key during device setup. Never request the key in chat.
- Free-tier use only. No paid fallback, billing upgrade, or alternate paid provider.
- Preserve existing microphone/speaker pins, offline Jarvis wake word/model, and LED patterns.

## Hardware contract — do not change

- Board: Waveshare ESP32-S3-Zero, ESP32-S3FH4R2, 4 MB flash, 2 MB Quad PSRAM.
- INMP441: SCK GPIO4, WS GPIO5, DIN GPIO6.
- MAX98357A: LRCK GPIO7, BCLK GPIO8, DOUT GPIO9.
- Onboard RGB LED: GPIO21.
- External GPIO2 LED remains disabled.
- Offline wake word: Jarvis; model `wn9_jarvis_tts`.

## Local greeting asset

- Source recording supplied by the user: mono, 24 kHz, 16-bit PCM WAV.
- Converted for the existing playback path to mono 24 kHz Ogg/Opus.
- Experimental asset: `assets/jarvis-algenib-greeting.ogg`.
- `scripts/generate-greeting-header.py` embeds that Ogg asset into the firmware header.
- Preserve the current one-time greeting trigger, timing, wake-detector suppression during playback, and LED hand-off.
- Never run the old eSpeak greeting generator for this branch.

## Gemini Live transport

- Selected model: `gemini-3.8-live` (Gemini Developer API Live). Google's current pricing page lists it with free-tier input/output pricing; free-tier access remains subject to project-specific quotas and availability. Do not enable billing or paid fallback. Google's Live API voice documentation explicitly lists `Algenib` (Gravelly). The same documentation lists Hindi (`hi-IN`) and English India (`en-IN`); Hinglish code-switching will be prompt-guided and must be verified on-device. Confirm exact model access for the user's API key during first network test.
- Live API input: signed 16-bit little-endian PCM, 16 kHz mono.
- Live API output: signed 16-bit little-endian PCM, 24 kHz mono.
- WebSocket setup and server messages must follow the current Gemini Live API schema; do not assume older 2.5/3.1 message fields are unchanged.
- Use bounded buffers and PSRAM allocation checks. Avoid unbounded JSON/audio allocations.
- Add no paid fallback. Authentication, quota, or network errors must stop the turn and recover to standby.

## Half-duplex state sequence

1. Keep local offline Jarvis detection active in standby.
2. On Jarvis detection, suspend wake detection and the normal audio uplink.
3. Capture a bounded user utterance using the existing INMP441 path and existing VAD/end-of-speech behaviour.
4. Convert/packetize PCM as required by the Live API and send the utterance.
5. End the input turn and wait for Gemini's complete response.
6. Decode/convert response audio and play through the existing I2S/MAX98357A path.
7. After playback drains, re-arm local Jarvis detection and return to standby.
8. On failure, never silently switch to a paid model; show/log a clear error and safely recover.

## LED contract — preserve exactly

- Startup: red blink until internet.
- Greeting: yellow solid.
- Standby: yellow breathing.
- Listening: blue blink.
- Processing: blue blink.
- Speaking: green blink.
- Do not rewrite the LED driver unless a verified integration issue requires it.

## Wi-Fi and API-key provisioning

- Reuse the existing device Wi-Fi provisioning flow where possible.
- Add a local setup step for the Gemini API key; target a single device-hosted setup flow for Wi-Fi plus API key if it can be implemented without destabilizing the existing Wi-Fi portal.
- Store the key in device NVS only. Provide a way to replace/erase it.
- Never commit secrets, print them to logs, or embed them in the downloadable binary.
- Direct device-to-Gemini use avoids a server but a key stored on an ESP32 is extractable; explain this personal-prototype security trade-off.
- Verify the provisioning UX and NVS behaviour before claiming setup is complete.

## Engineering gates

1. Inspect the exact pinned XiaoZhi submodule revision and identify the current audio capture, VAD, wake-word suspension, playback, and network APIs.
2. Confirm the Live API model, Algenib voice support, free-tier availability/quota, authentication, and current WebSocket message schema.
3. Implement a separate Gemini transport/provider without changing the protected reference branch.
4. Implement local Wi-Fi/API-key provisioning without exposing credentials.
5. Verify all pins, wake-word model, greeting trigger, and LED behaviour against the protected baseline.
6. Build in GitHub Actions; inspect logs, binary size, partition/PSRAM configuration, and artifact contents.
7. Test boot, Wi-Fi reconnect, Jarvis wake, Hindi, English, Hinglish, Algenib voice, playback quality, repeated turns, quota exhaustion, and recovery.
8. Only then publish an experimental artifact and ask before flashing.

## Current implementation checkpoint

- Branch is based on the Build #105 reference commit.
- User's Algenib greeting has been converted and staged as a branch-specific Ogg/Opus asset.
- The greeting generator is being changed to embed that local asset.
- Gemini transport, API-key provisioning, and flashable firmware are not yet implemented.
- No experimental firmware has been flashed. Build #105 remains the rollback reference.
