# Speech integration plan

## Status

Deferred for later consideration. No speech behavior is currently implemented.

## Goal

Offer optional provider-backed speech-to-text input and text-to-speech output
through the DARPS sidecar without making audio part of narrative state or
forcing speech dependencies on text-only hosts.

## Ownership boundary

DARPS may provide transcription and synthesis services. The host game remains
responsible for:

- microphone capture and permissions;
- choosing the addressed character or examination target;
- displaying, editing, or confirming a transcript;
- deciding when a final transcript becomes a `/talk` or `/examine` request;
- audio playback, queuing, interruption, volume, spatialization, and lip-sync;
- retaining or deleting recorded audio.

Speech calls are presentation/transport operations. They never change facts,
tracks, persona, canon, conversations, turns, pacing, or saves.

Partial STT results must never trigger a narrative turn. Only a host-submitted
final transcript enters an existing player-input endpoint.

## Preferred flow

```text
Microphone
  -> POST /transcribe
  -> final player transcript
  -> POST /talk or /examine
  -> validated DARPS prose and deltas
  -> POST /speak
  -> host audio playback
```

The endpoints remain independent so a host can mix native/platform speech
with DARPS services:

```text
native STT -> DARPS talk -> DARPS TTS
DARPS STT  -> DARPS talk -> native TTS
DARPS STT  -> DARPS talk -> DARPS TTS
text only
```

Avoid an initial `/talk/audio` endpoint. Combining binary audio, session
metadata, world JSON, target selection, transcription correction, narrative
execution, and synthesis into one request would obscure error handling and
make accidental turns more likely.

## Proposed HTTP API

### `POST /transcribe`

Accept raw audio with an audio content type:

```http
POST /transcribe?language=en&format=wav
Content-Type: audio/wav

<audio bytes>
```

Possible parameters:

| Parameter | Required | Purpose |
|---|---:|---|
| `language` | No | Language hint |
| `format` | No | Explicit format when content type is insufficient |
| `prompt` | No | Vocabulary hint for names, places, or specialized terms |

Return JSON:

```json
{
  "text": "What happened to Sir Edmund?",
  "language": "en",
  "duration": 2.7
}
```

The result is untrusted input text. It receives the ordinary guardrail,
attitude, persona, and knowledge processing only after the host submits it to
`/talk` or `/examine`.

### `POST /speak`

Accept display text and an optional voice selector:

```json
{
  "text": "I brought his cocoa at half past eleven.",
  "character": "butler",
  "voice": null,
  "format": "mp3"
}
```

Return raw audio:

```http
Content-Type: audio/mpeg
```

`character` selects a configured voice mapping. An explicit `voice`, if
supported, is host configuration vocabulary rather than an unrestricted
provider voice ID. General narration uses `narrator`.

The endpoint synthesizes exactly the supplied text. It does not assemble a
briefing, call a response model, interpret events, or update state.

## Proposed configuration

Speech remains host-owned runtime policy:

```yaml
speech:
  stt:
    enabled: false
    provider: ...
    model: ...
    base_url: null
    language: en
    max_audio_seconds: 60

  tts:
    enabled: false
    provider: ...
    model: ...
    base_url: null
    format: mp3
    voices:
      butler: halloway_voice
      widow: constance_voice
      narrator: manor_narrator
```

Provider-specific model and voice IDs belong in `config.yaml`, not pack
entity files. Packs describe voice performance in prose; the host deployment
chooses installed or cloud voices.

If portable pack-authored voice roles are later useful, introduce abstract
roles such as `voice_role: elderly_formal` and map those roles to provider IDs
in host configuration. Do not put provider credentials or deployment-specific
voice identifiers in packs.

## Provider architecture

Follow the existing optional-provider pattern:

- no new mandatory dependencies;
- standard-library HTTP adapters for compatible cloud services;
- API keys loaded from environment variables;
- provider errors translated into structured HTTP failures;
- full request metadata logged without recording binary audio or secrets;
- local/offline engines remain optional adapters or external processes.

Local models are a separate packaging problem. They may require native
libraries, model downloads, GPU runtimes, or large executables and must not
weaken DARPS's lightweight default installation.

## TTS caching

Synthesized audio is a good cache candidate because it is pure presentation.
Key cached audio by an exact hash of:

- normalized input text;
- provider and model;
- resolved voice;
- output format and synthesis settings;
- speech adapter/prompt version.

Cache eviction changes performance only. Audio cache contents never become
narrative state and do not belong in save files.

Decide separately whether the cache is memory-only, disk-backed, host-managed,
or disabled. A disk cache needs a size limit and documented privacy policy.

## Streaming design

### TTS streaming

Do not feed arbitrary LLM token chunks directly to TTS. Buffer complete
sentences:

```text
response token stream
  -> sentence boundary buffer
  -> synthesize complete sentence
  -> audio frames
```

Open decisions:

- sentence-boundary handling for abbreviations and dialogue punctuation;
- whether synthesis overlaps playback;
- audio framing and codec;
- cancellation when dialogue is skipped;
- reconciliation with the final validated prose;
- mid-stream synthesis failures;
- whether a sentence may play before the response's final events are
  validated.

The last point matters: current DARPS streaming permits prose to appear before
truth deltas are finalized. Spoken prose may follow the same boundary, but the
host must never infer narrative truth from audio.

### STT streaming

Streaming STT produces provisional and revised transcripts. Expose partials
for UI display only, followed by one explicit final transcript. Never connect
partials directly to `/talk`.

Streaming speech should be a later phase after whole-request endpoints are
stable.

## Implementation phases

### Phase 1: provider-neutral foundation

- Define speech provider interfaces and error types.
- Add disabled-by-default configuration parsing.
- Establish audio size, duration, format, and timeout limits.
- Ensure call logs never contain binary audio.

### Phase 2: non-streaming STT

- Add one cloud/HTTP transcription adapter.
- Add raw-audio request handling to the stdlib HTTP server.
- Return normalized transcript JSON.
- Document transcript confirmation and target selection.

### Phase 3: non-streaming TTS

- Add one cloud/HTTP synthesis adapter.
- Add raw-audio HTTP responses.
- Add character/narrator voice mapping.
- Add optional exact-hash audio caching.

### Phase 4: broader providers

- Add other cloud-compatible adapters where justified.
- Document host-native and external-sidecar integration.
- Evaluate local/offline adapters without making them required dependencies.

### Phase 5: streaming

- Add cancellation-aware sentence-streaming TTS.
- Add provisional/final streaming STT.
- Test interruption, disconnects, and partial provider failures.

## Testing obligations

All tests must use stub providers and synthetic bytes; never API keys,
microphones, speakers, or network calls.

Required coverage:

- disabled speech routes fail clearly or are absent by declared contract;
- supported content types and size limits;
- malformed, empty, oversized, and unsupported audio rejection;
- provider timeout and failure translation;
- transcript text never changes state by itself;
- partial STT never invokes a narrative call;
- TTS synthesizes exactly the supplied prose;
- character and narrator voice resolution;
- unknown voice selectors fail safely;
- audio cache key separation by text/model/voice/format;
- cached and uncached synthesis are byte-equivalent;
- binary audio never enters call logs or save state;
- streaming cancellation and error frames;
- existing text-only API and smoke tests remain unchanged.

## Documentation obligations

When implemented, update:

- `SPEC.md` runtime and HTTP sections;
- `docs/setup/configuration.md`;
- `docs/integration/providers.md`;
- `docs/integration/streaming-errors.md`;
- `docs/api/http-reference.md`;
- `docs/api/index.md`;
- `docs/api/clients.md`;
- architecture and information-flow diagrams;
- the C# reference client;
- `.agents/skills/ARCHITECTURE.md`, `GUIDE.md`, and `DECISIONS.md`.

## Open decisions

- Which first STT and TTS providers best fit the stdlib adapter model?
- Raw request bodies versus multipart input for transcription metadata.
- Supported codecs and whether DARPS ever performs transcoding.
- Whether `/speak` accepts arbitrary text or only text returned by DARPS.
- Whether voice mappings are character IDs, abstract roles, or both.
- Audio cache location, size, lifetime, and privacy policy.
- Maximum request duration and file size.
- Whether speech endpoints appear in `/pack` capabilities only when enabled.
- Whether speech belongs in the main sidecar or an optional companion process.

## Explicit non-goals

- DARPS does not capture microphones.
- DARPS does not choose the conversation target from audio.
- DARPS does not automatically execute a transcript.
- DARPS does not play audio or control speakers.
- DARPS does not perform lip-sync or facial animation.
- DARPS does not store audio in narrative saves.
- DARPS does not require speech dependencies for text-only use.
