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


## User-approved implementation scope (2026-11-09)

The user explicitly approved a separate Gemini build with these constraints:

- Create/build only on `jarvis-gemini-build105`; never modify Build #105's reference branch.
- Half-duplex operation.
- User already has a Gemini API key and wants to enter it during device setup.
- Slightly robotic / synthetic voice response, still male-sounding.
- Absolutely no changes to microphone, speaker or LED GPIO pins.
- Absolutely no changes to the offline Jarvis wake word/model.
- Absolutely no changes to the existing local startup/welcome greeting ("Hi there"), its audio asset, or its startup timing/LED interaction.
- Preserve all other LED colours, blink/breathing patterns and state behaviour.
- No paid fallback; API quota or authentication errors must stop the request and recover safely.

### Voice style

Use a male prebuilt voice supported by the selected Live model (initial candidate: `Alnilam`, documented as firm; alternative `Algieba`, documented as smooth). Apply a restrained voice-direction instruction such as:

"Use a slightly synthetic, robotic assistant delivery: precise articulation, even pacing, controlled intonation, concise pauses, calm and formal. Keep it clearly understandable in Hindi and English. Do not sound harsh, distorted, or like a radio effect."

This is a voice-performance instruction, not a post-processing distortion effect. Do not alter the local startup greeting voice. Confirm actual voice availability for the selected Gemini API model before implementation.

### API key entry and security

The user will enter their own API key. Do not request it in chat, write it into source code, put it in GitHub Actions logs, or commit it to the repository. Preferred implementation is a first-boot local provisioning flow that accepts the key and stores it in device NVS; provide an explicit way to replace/erase it. Explain that device-local storage is not tamper-proof and an extracted key can be abused. The firmware must not contain a hard-coded key or a paid-service fallback. Do not build the key into the downloadable binary.

Before choosing the exact provisioning method, inspect the current board Wi-Fi provisioning UX and determine whether a captive portal/local setup page can be added without altering the existing welcome audio or LED behaviour. If that cannot be done safely, stop and ask for the preferred key-entry method rather than embedding secrets in GitHub.

### Do-not-touch verification checklist

Before publishing a Gemini artifact, compare the experimental branch against the protected baseline and verify:
- INMP441 pins remain SCK=4, WS=5, DIN=6.
- MAX98357A pins remain LRCK=7, BCLK=8, DOUT=9.
- Onboard RGB remains GPIO21; external GPIO2 remains disabled.
- Wake word remains offline `Jarvis`, model `wn9_jarvis_tts`.
- Local startup greeting remains the same existing "Hi there" audio and trigger; no voice/style prompt applies to it.
- LED behaviour remains startup red blink, greeting yellow solid, standby yellow breathing, listening/processing blue blink, speaking green blink.
- Half-duplex sequence is capture → upload → response playback → re-arm wake word.
- No API key is present in repository contents, build logs, or downloadable binary configuration.
- Free-tier/quota failure never triggers paid fallback.

### Implementation status correction

This repository branch currently contains the design plan only. A Gemini transport/provider implementation and a flashable firmware build have NOT yet been completed. Do not describe this as a working Gemini firmware until the engineering gates above pass and GitHub Actions produces a verified artifact.
