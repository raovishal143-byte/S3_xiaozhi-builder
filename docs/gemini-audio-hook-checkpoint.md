# Gemini integration checkpoint — PCM capture hook

This checkpoint is intentionally limited to the first audio integration seam.

## Implemented on `jarvis-gemini-build105`

- Added `scripts/patch-gemini-audio-hook.py`.
- The normal firmware preparation step now applies that patch to the pinned XiaoZhi submodule.
- The patch adds an optional `AudioServiceCallbacks::on_pcm_frame` callback.
- The callback receives the existing 16 kHz microphone frames (10 ms / 160 samples per frame) from the same input task that feeds the offline audio engine.
- The callback is passive when unset; the original audio path still receives the same frame.
- A future Gemini consumer must copy frames into bounded storage and return immediately. It must not block the audio input task or retain the callback's vector reference.

## Not implemented yet

- No Gemini WebSocket client or session state machine.
- No ephemeral-token request implementation.
- No microphone utterance buffering / end-of-speech orchestration.
- No Gemini PCM response playback adapter.
- No Gemini API-key setup page or NVS key storage.
- No flashable Gemini firmware.

## Validation gate

The next firmware build must prove that the patch applies cleanly against the pinned XiaoZhi revision and that the existing JARVIS firmware still compiles with the new optional callback. Passing this build will validate only the capture hook, not Gemini connectivity or voice interaction.

Build #105's reference branch and commit remain unchanged.
