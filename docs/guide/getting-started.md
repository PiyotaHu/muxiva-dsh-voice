# Getting started

## 1. Verify the machine

```bash
npx @muxiva/dsh-voice doctor
```

Every row must pass. `doctor --fix` creates only this project's `.muxiva/venv`; it does not alter system Python.

## 2. Install local inference

```bash
npx @muxiva/dsh-voice setup
```

The downloader verifies every artifact before activation. An interrupted `curl` transfer resumes from its `.partial` file. The default download is about 590 MB; extracted models use about 1.2 GB plus the Python environment.

## 3. Install the DSH Bundle

```bash
dsh plugin --profile web add @muxiva/dsh-voice
dsh --profile web --dump-config
```

The dump must contain a `# == @muxiva/dsh-voice` layer and the `muxiva-dsh-voice` row.

## 4. Run and speak

Start `muxiva-dsh-voice start`, start `dsh --profile web`, open a session, and select the large voice orb above the composer. Use headphones for the cleanest full-duplex certification run.

Before opening DSH, you can certify the complete local model path without a cloud model or microphone:

```bash
npm run test:e2e
```

The test synthesizes a Chinese sentence, routes all resulting browser PCM back as microphone audio, and requires an exact SenseVoice final. It then sends the upstream English fixture and requires a valid English final.

## 5. Tune

Edit `graph.json` in Muxiva Studio, or override the Node configuration:

- `vad_threshold`: lower hears quieter speech; `0.5` is the default.
- `min_silence_seconds`: lower commits faster but may split sentences; `0.45` is the default.
- `final_language`: `auto` detects Chinese or English; pin `zh` or `en` only for a language-specific deployment.
- `speaker_id`: `3–57` are Chinese female voices and `58–102` Chinese male voices in Kokoro v1.1.
- `speaker_id: 21` (`zf_032`) and `speed: 0.95` are the conversational defaults.

`muxiva.speech_text_normalizer` is a project Node Pack between the built-in streaming Markdown formatter and TTS. It removes emoji and residual display syntax, preserves link labels, and speaks Chinese years, integers, decimals and percentages deterministically. It uses the public Node Pack mechanism and requires no Muxiva Runtime change.
