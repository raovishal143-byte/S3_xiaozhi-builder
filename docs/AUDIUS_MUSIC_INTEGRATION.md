# Audius music integration plan — Waveshare ESP32-S3-Zero

## Goal

Add opt-in, on-demand music playback to the existing XiaoZhi/Jarvis firmware without replacing the XiaoZhi AI service, changing the board, changing the INMP441/MAX98357A wiring, or requiring a user-hosted server.

The first provider is the official Audius REST API. This is a provider choice for the first implementation, not a promise that every requested commercial song exists in the Audius catalogue.

## Hardware baseline (do not change)

- Board: Waveshare ESP32-S3-Zero, ESP32-S3, 4 MB flash, 2 MB Quad PSRAM
- Microphone: INMP441 — SCK GPIO4, WS GPIO5, SD GPIO6
- Amplifier: MAX98357A — BCLK GPIO8, LRC GPIO9, DIN GPIO10
- Status LED: GPIO2
- Existing offline wake word: Jarvis
- Existing XiaoZhi cloud/agent remains the conversational AI

## Audius API

Official API base: https://api.audius.co/v1

- Search: GET /tracks/search?query={encoded_query}&limit={n}
- Stream: GET /tracks/{track_id}/stream
- Read-only requests are documented as available without credentials; a free API key is available for higher rate limits.
- Official API docs: https://docs.audius.co/api/
- Free API plan details: https://docs.audius.co/sdk/

The client must use only the official Audius endpoints, respect track access restrictions and response redirects, and never scrape other music services or extract audio from YouTube/Spotify.

## Decoder feasibility audit (verified against the pinned XiaoZhi source)

The pinned XiaoZhi submodule already declares `espressif/esp_audio_codec: ~2.5.0`. Espressif's `esp_audio_codec` includes the MP3 decoder and a Simple Decoder API that accepts arbitrary-sized MP3 stream chunks, performs frame parsing, and returns PCM. Its Kconfig sets MP3 decoder support to enabled by default. Therefore, do not add ESP-ADF wholesale and do not add a second MP3 decoder library.

Relevant API family:
- `esp_audio_dec_register_default()`
- `esp_audio_simple_dec_register_default()`
- `esp_audio_simple_dec_open()` with `ESP_AUDIO_SIMPLE_DEC_TYPE_MP3`
- `esp_audio_simple_dec_process()`
- `esp_audio_simple_dec_get_info()`
- `esp_audio_simple_dec_close()`

The Simple Decoder is streaming-only (no seeking). A music seek/previous implementation must therefore restart a track or use provider-supported stream offsets; do not promise arbitrary seek.

**Critical output constraint:** XiaoZhi's existing `AudioService::AudioOutputTask()` is the single current writer that calls `AudioCodec::OutputData()` for decoded voice. Music must not write directly to the same I2S codec concurrently. The firmware implementation must add a shared output arbitration/queue so voice prompts and music PCM are serialized, with clear priority and cancellation rules. The existing Opus decode path must remain intact.

The upstream component's published MP3 resource figures are reference measurements, not a guarantee for this board or this build. The final 4 MB image, runtime heap, decoder stack, and PSRAM/internal-RAM allocations must be measured in the actual S3-Zero build.

## Device-side architecture

1. XiaoZhi remains responsible for speech recognition, understanding the request, and choosing the music action.
2. Add MCP tools to the device:
   - music.search_and_play(query)
   - music.pause()
   - music.resume()
   - music.stop()
   - music.next() (only if a queue exists)
   - music.set_volume(level)
3. Search results must be checked against the requested title/artist. Do not silently play a weak match; report when no reliable match is found.
4. Device downloads/streams the selected Audius MP3 over HTTPS and decodes it incrementally.
5. PCM is sent to the existing I2S output (MAX98357A). Do not route music through the XiaoZhi Opus conversation decoder.
6. Keep a dedicated playback task and bounded buffers. Do not buffer a whole song in RAM.
7. Pause or gate microphone/VAD processing during loud music playback to avoid speaker-to-microphone feedback; restore it on pause/stop/end.
8. Playback controls must not block the main application/MCP event loop.

## Memory and flash constraints

- Preserve the 4 MB flash partition layout and the existing Jarvis WakeNet model.
- Do not adopt another board's 16 MB / Octal-PSRAM sdkconfig or partition table.
- Prefer a small MP3 decoder already available in the resolved ESP-IDF/XiaoZhi dependency graph. Do not add ESP-ADF wholesale unless the final image and RAM use are measured and fit.
- Avoid large static buffers; use bounded streaming buffers and check internal RAM/PSRAM allocations.
- The current XiaoZhi AudioService receives/plays Opus conversation packets. The pinned dependency includes a streaming MP3 Simple Decoder, but AudioService has no music API; music must be integrated through a shared serialized PCM output path.

## Implementation gates (no flashing until all pass)

### Gate A — API validation
- [x] Confirm Audius search response and a streamable track ID for test queries (Tum Hi Ho and Shape of You; exact/original recording not guaranteed).
- [x] Confirm stream endpoint returns an MP3 response/redirect with audio bytes.
- [x] Confirm the pinned XiaoZhi dependency already includes Espressif's MP3 Simple Decoder; no extra decoder dependency is needed.
- Confirm missing/blocked tracks fail cleanly.
- Check Audius developer terms and track-level access/rights; do not imply that all catalogue content is cleared for every use.

### Gate B — firmware implementation
- Implement an Audius HTTPS client with bounded JSON parsing.
- Implement incremental MP3 decode and I2S PCM output.
- Add MCP control tools and explicit playback state.
- Keep existing Jarvis wake-word, GPIO2 LED, greeting, and board pins unchanged.

### Gate C — build and safety checks
- Build against the repository's pinned XiaoZhi submodule and ESP-IDF version.
- Verify 4 MB flash partition boundaries and firmware artifact sizes.
- Inspect linker/map and runtime heap use for the decoder and streaming buffers.
- Confirm no API key or bearer token is committed to source control.
- Produce a separate test artifact; do not overwrite or flash the existing Jarvis artifact.

### Gate D — hardware test
- Test search, play, pause, resume, stop, next/previous where supported, and volume.
- Test Wi-Fi loss, missing track, HTTP redirect, end-of-track, and repeated commands.
- Verify speech interaction resumes after playback and GPIO2 behavior remains correct.

## Current status

- A separate branch `feature/audius-music-player` has been created from the existing Jarvis build branch.
- This document records the safe integration plan.
- No firmware source has been changed for music yet, no new firmware has been built, and nothing has been flashed.
- Audius search and MP3 stream smoke tests passed for Tum Hi Ho and Shape of You queries. Returned matches included covers/remixes/instrumentals; original commercial recordings are not confirmed.
- Pinned XiaoZhi source already includes Espressif ESP Audio Codec ~2.5.0 with MP3 Simple Decoder support enabled by default.
- No music firmware source has been changed, no music firmware has been built, and nothing has been flashed. The next implementation task is shared audio-output arbitration plus the Audius streaming/decode task.
