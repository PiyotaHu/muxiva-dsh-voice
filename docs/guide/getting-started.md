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

The downloader verifies every artifact before activation. An interrupted `curl` transfer resumes from its `.partial` file. The default footprint is about 460 MB compressed/downloaded plus the Python environment.

## 3. Install the DSH Bundle

```bash
dsh plugin --profile web add @muxiva/dsh-voice
dsh --profile web --dump-config
```

The dump must contain a `# == @muxiva/dsh-voice` layer and the `muxiva-dsh-voice` row.

## 4. Run and speak

Start `muxiva-dsh-voice start`, start `dsh --profile web`, open a session, and select the microphone button. Use headphones for the cleanest full-duplex certification run.

Before opening DSH, you can certify the complete local model path without a cloud model or microphone:

```bash
npm run test:e2e
```

The test synthesizes a Chinese sentence, routes the resulting browser PCM back as microphone audio, and requires VAD onset plus a final ASR transcript.

## 5. Tune

Edit `graph.json` in Muxiva Studio, or override the Node configuration:

- `vad_threshold`: lower hears quieter speech; `0.5` is the default.
- `min_silence_seconds`: lower commits faster but may split sentences; `0.45` is the default.
- `speaker_id`: `3–57` are Chinese female voices and `58–102` Chinese male voices in Kokoro v1.1.
- `speed`: `1.0` is natural rate.
