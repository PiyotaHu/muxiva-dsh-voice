# Performance, measured results, and acceptance

The first certification machine is a MacBook Pro M1 Pro, 16 GB RAM, macOS, using the built-in microphone and speakers.

## Published measured results

No certified release report has been published yet. The numbers in the budget
table below are acceptance targets, not measurements.

Every npm release must add at least one immutable report under
[`benchmarks/results/`](../../benchmarks/results/), and this page must link that
exact JSON file. The release workflow rejects a tag when either the matching
report or the documentation link is missing.

| Release | Machine | Report | Status |
| --- | --- | --- | --- |
| — | MacBook Pro M1 Pro, 16 GB | — | Certification pending |

Do not publish a hand-selected “best run.” The report contains p50/p95/p99 over
the complete accepted workload and is tied to the exact Muxiva, DSH, plugin, OS,
and model-lock versions.

## Latency budgets

| Measurement | Alpha budget | Release gate |
| --- | ---: | ---: |
| Browser capture → Muxiva Frame | p95 ≤ 45 ms | p95 ≤ 35 ms |
| Speech onset → barge-in Signal | p95 ≤ 180 ms | p95 ≤ 140 ms |
| Speech end → ASR Final | p95 ≤ 750 ms | p95 ≤ 550 ms |
| First DSH text → first TTS PCM | p95 ≤ 900 ms | p95 ≤ 650 ms |
| Audio queue ahead | ≤ 240 ms | ≤ 160 ms |
| Stale audio after barge-in | ≤ 120 ms | ≤ 80 ms |

Certification includes 100 scripted turns, 30 mid-answer interruptions, Chinese, English and code-oriented prompts, five minutes of continuous idle listening, and a 30-minute soak. Report median/p95/p99 plus the exact model lock and DSH/Muxiva versions.

The Graph uses bounded queues throughout. A latency win that relies on unbounded buffering fails certification.

## Required report contents

The versioned JSON report validates against
[`benchmarks/schema.json`](../../benchmarks/schema.json) and contains:

- system identity: machine, chip, memory, exact macOS version, and AC/battery;
- exact Muxiva, DSH Voice, DeepSeek Harness, Node, Python, and model-lock versions;
- latency distributions for all six budgets above;
- final-ASR and TTS real-time factors;
- cold/warm startup, idle/active CPU, peak RSS, and model disk usage;
- Mandarin CER, English WER, and TTS underruns;
- completed/failed turns, dropped audio frames, discarded late results, and
  confirmation that no queue is unbounded.

Large raw traces belong on the matching GitHub Release. The repository report
contains aggregate statistics only and must not contain audio, transcripts,
credentials, or workspace data.

## Measurement boundaries

- **Browser capture → Muxiva Frame:** `AudioWorklet` capture timestamp to the
  corresponding admitted audio Frame.
- **Speech onset → barge-in Signal:** first speech sample in the calibrated
  fixture to `muxiva.voice.speech.started` admission.
- **Speech end → ASR Final:** last speech sample to the Final accepted for the
  DSH turn; preview text does not count.
- **First DSH text → first TTS PCM:** first complete Agent sentence admitted to
  the speech path until the first PCM frame reaches the browser sink.
- **Audio queue ahead:** playable PCM already scheduled beyond the browser audio
  clock.
- **Stale audio after barge-in:** old-generation audio audible or scheduled
  after the barge-in boundary.

Model loading is reported separately as cold and warm startup and must not be
silently excluded from the published resource section.
