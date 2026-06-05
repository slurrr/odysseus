# Voice / STT / TTS Notes

## What exists already

Odysseus already has a voice stack, but it is settings-driven rather than launched from Cookbook model cards.

Relevant files:
- `services/stt/stt_service.py`
- `routes/stt_routes.py`
- `static/js/voiceRecorder.js`
- `services/tts/tts_service.py`
- `routes/tts_routes.py`
- `static/js/tts-ai.js`
- `data/settings.json`

Current settings keys:

```json
{
  "tts_enabled": true,
  "tts_provider": "disabled",
  "tts_model": "tts-1",
  "tts_voice": "alloy",
  "tts_speed": "1",
  "stt_enabled": false,
  "stt_provider": "disabled",
  "stt_model": "base",
  "stt_language": ""
}
```

## STT providers

From `services/stt/stt_service.py`:

- `disabled` — no STT.
- `browser` — client-side Web Speech API.
- `local` — lazy-loads `faster-whisper` inside the Odysseus container.
- `endpoint:<id>` — calls a registered `ModelEndpoint` at:

```text
POST {base_url}/audio/transcriptions
```

with OpenAI-style multipart form:

```text
file=audio.webm
model=<stt_model or whisper-1>
language=<optional>
```

## TTS providers

From `services/tts/tts_service.py`:

- `disabled` — no TTS.
- `browser` — browser SpeechSynthesis.
- `local` — lazy-loads Kokoro-82M in-process.
- `endpoint:<id>` — calls a registered `ModelEndpoint` at:

```text
POST {base_url}/audio/speech
```

with OpenAI-style JSON:

```json
{
  "model": "tts-1",
  "input": "...",
  "voice": "alloy",
  "response_format": "mp3",
  "speed": 1.0
}
```

TTS audio is cached under `data/tts_cache`.

## Implication for existing external servers

Existing faster-whisper and Kokoro HTTP servers can likely be integrated without launching them from Cookbook if they expose OpenAI-compatible endpoints:

- STT: `/v1/audio/transcriptions` or equivalent base URL normalized to `/audio/transcriptions` by Odysseus.
- TTS: `/v1/audio/speech` or equivalent base URL normalized to `/audio/speech`.

The clean path is probably:
1. Add each voice server as a `ModelEndpoint`.
2. Set `stt_provider = "endpoint:<id>"` and/or `tts_provider = "endpoint:<id>"` in settings/UI.
3. Set model/voice names to whatever the external service expects.

## Open questions

- Where in Settings UI are STT/TTS providers exposed, and does it allow choosing arbitrary endpoint ids cleanly?
- Do the existing external faster-whisper/Kokoro servers implement OpenAI-compatible paths exactly, or do we need adapter routes?
- Should Cookbook grow first-class Voice serve cards, or should voice remain endpoint/settings-driven?
- If `agent-session-srv` owns voice long-term, should Odysseus call it as an endpoint provider rather than duplicating runtime management?

## Next test plan

1. List current model endpoints and settings.
2. Register existing faster-whisper server as an endpoint if not already present.
3. Set `stt_enabled=true`, `stt_provider=endpoint:<id>`, `stt_model=<server-model>`.
4. Use the mic button and confirm `/api/stt/transcribe` returns text.
5. Repeat for Kokoro via TTS endpoint mode.
