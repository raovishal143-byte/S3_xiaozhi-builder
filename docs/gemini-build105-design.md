# JARVIS Gemini Build #105 — design plan

Status: design only; no firmware source, Build #105 files, wiring, or device state changed.

## Protected baseline

- Repository: raovishal143-byte/S3_xiaozhi-builder
- Reference branch: jarvis-rgb-status-led
- Reference commit: 3e24e80fe0d1f8da95af135516a010dcc3fa95b8
- Reference workflow run: https://github.com/raovishal143-byte/S3_xiaozhi-builder/actions/runs/42458677935
- Experimental branch: jarvis-gemini-build105 (created from the exact reference commit above)

Never commit experimental changes to the reference branch. Do not flash an experimental image until its build and test results are reported.

## User requirements

- Gemini is the conversational AI provider.
- Automatically handle Hindi, English, and natural Hindi-English code switching (Hinglish).
- Male-sounding voice.
- Free-tier use only; no paid fallback, no automatic billing upgrade.
- Half-duplex: capture user speech, stop microphone uplink, receive/play the complete response, then listen again.
- No laptop or always-on home PC.
- Preserve Build #105 board, pins, offline Jarvis wake-word, startup greeting, and LED state behaviour.

## Hardware contract (do not change)

- Board: Waveshare ESP32-S3-Zero, ESP32-S3FH4R2, 4 MB flash, 2 MB Quad PSRAM.
- INMP441: SCK GPIO4, WS GPIO5, DIN GPIO6.
- MAX98357A: LRCK GPIO7, BCLK GPIO8, DOUT GPIO9.
- Onboard RGB LED: GPIO21.
- External GPIO2 LED remains disabled.
- Offline wake word: Jarvis; model wn9_jarvis_tts.

## Proposed cloud service

- Gemini Live API over TLS WebSocket.
- Initial model candidate: gemini-3.8-live (confirm exact availability for the chosen API project before firmware integration).
- Audio input: 16-bit PCM, 16 kHz, little-endian per Live API WebSocket guide.
- Audio output: consume Gemini's returned audio chunks and convert/resample as needed for the existing I2S speaker path. Confirm the exact output sample rate/encoding from the selected model's session response; do not assume it is identical to the input.
- Voice candidate: Algieba (documented male, smooth) or Alnilam (documented male, firm); choose after listening to samples and verifying the selected model supports the voice.
- Language: use native-audio model automatic language detection; prompt it to reply in the language/code-switching style used by the user. Hindi and English are documented. Hinglish code-switching must be tested with real utterances; do not claim guaranteed recognition before testing.
- Conversation memory: retain session context only while the Live session remains active; define reconnect/session-resumption behaviour separately.

## Half-duplex state sequence

1. Device is in Build #105 standby state and local offline wake-word detection remains active.
2. On Jarvis detection, suspend wake-word detection and microphone uplink as required to avoid self-triggering.
3. Capture a bounded utterance using the existing I2S mic path and VAD/end-of-speech logic.
4. Convert/packetize PCM for Gemini Live API and send over WSS.
5. Stop uplink after the utterance; wait for response audio.
6. Decode/convert returned audio chunks and play through the existing I2S/MAX98357A path.
7. After playback drains, close or keep the Live session according to memory/timeout policy, re-arm local wake-word detection, and return to standby.
8. On Wi-Fi/API/quota failure, do not fall back to paid services; provide a local error indication and recover to standby.

## LED contract (preserve Build #105)

- Startup: red blink until internet.
- Greeting: yellow solid.
- Standby: yellow breathing.
- Listening: blue blink.
- Processing: blue blink.
- Speaking: green blink.

Map Gemini connection / capture / response / playback events onto these existing states. Do not rewrite the LED driver unless required by a verified integration issue.

## Security and free-only constraint

There is a design choice that must be resolved before shipping firmware:

A. Direct device-to-Gemini connection using a Gemini API key. This avoids any server, but the key embedded/stored on an ESP32 can be extracted. Keep the key out of GitHub and logs, restrict it to the Gemini API where possible, and use a project with billing disabled / no paid fallback. Treat this as a personal prototype trade-off, not production-grade key security.

B. Gemini ephemeral tokens. Google recommends short-lived tokens for client-to-server Live API connections. The device connects directly to Gemini using the short-lived token, but a small HTTPS token broker must mint it using the long-lived key. This is more secure and does not proxy audio, but it introduces a cloud function/service and may require account/billing configuration. It is not a zero-backend architecture.

No API key, token, Wi-Fi password, or other secret may be committed to this repository. Never enable paid billing or automatic paid fallback without explicit user approval.

## Engineering gates before a flashable build

1. Inspect the exact upstream XiaoZhi submodule revision and identify the current I2S capture, VAD, wake-word suspension, playback and state APIs.
2. Confirm selected Gemini Live model, free-tier access in the user's AI Studio project, voice compatibility, and WebSocket message schema.
3. Choose authentication path A or B.
4. Implement Gemini transport as a separate provider module; do not modify Build #105 baseline branch.
5. Add bounded audio buffers and PSRAM allocation checks; avoid large unbounded JSON/audio allocations.
6. Add sample-rate conversion only after inspecting the actual I2S configuration and Gemini response encoding.
7. Add explicit quota/rate-limit handling that never switches to paid models.
8. Build in GitHub Actions, inspect complete logs, verify binary size and board configuration.
9. Test boot, Wi-Fi reconnect, Jarvis wake, Hindi, English, Hinglish, male voice, playback quality, repeated turns, quota exhaustion, and recovery.
10. Only then publish an experimental artifact and ask before flashing.

## Current status

- Experimental branch created from the Build #105 commit.
- Design document added.
- No Gemini firmware transport implemented yet.
- No GitHub Actions firmware build triggered.
- No firmware flashed; Build #105 remains the known-good reference.
