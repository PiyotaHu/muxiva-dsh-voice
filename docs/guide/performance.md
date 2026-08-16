# Performance, measured results, and acceptance

The first certification host is a MacBook Pro M1 Pro with 16 GB RAM. Automated
certification drives the real local WebSocket, Muxiva Graph, Silero, SenseVoice
and Qwen3-TTS path with deterministic, locally generated PCM; it does not claim
to measure room acoustics or a particular microphone.

## Published measured results

The complete immutable report contains p50/p95/p99 distributions, resource use,
quality, stability, exact versions and the model-lock digest.

Every npm release must add at least one immutable report under
[`benchmarks/results/`](../../benchmarks/results/), and this page must link that
exact JSON file. The release workflow rejects a tag when either the matching
report or the documentation link is missing.

| Release | Machine | Report | Status |
| --- | --- | --- | --- |
| 0.1.0-alpha.1 | MacBook Pro M1 Pro, 16 GB | [JSON](../../benchmarks/results/v0.1.0-alpha.1-m1-pro.json) | Alpha passed |

### 0.1.0-alpha.1 measured summary

| Metric | p50 | p95 | p99 |
| --- | ---: | ---: | ---: |
| Capture → Muxiva Frame | 8.0 ms | 15.4 ms | 16.5 ms |
| Speech onset → barge-in | 108.1 ms | 174.0 ms | 250.3 ms |
| Speech end → ASR Final | 567.6 ms | 597.8 ms | 616.9 ms |
| Agent text → first TTS PCM | 256.9 ms | 278.4 ms | 334.3 ms |
| Audio queue ahead | 216.4 ms | 223.9 ms | 224.6 ms |
| Stale audio after barge-in | 0.0 ms | 0.0 ms | 0.0 ms |

The run completed 130/130 turns and 30/30 interruptions, followed by five
minutes of idle listening and a 30-minute soak. It observed zero dropped audio
frames, zero TTS underruns and zero stale audio after interruption. Mandarin CER
was 9.43% and English WER was 2.74% on the synthetic `say` corpus. Those error
rates are repeatable regression signals, not estimates of real-human microphone
accuracy. Peak process-tree RSS was 2146.6 MiB and model storage was 2355.0 MiB;
see the JSON for CPU, startup and real-time-factor distributions.

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

## Reproduce the certification

After `npm run doctor -- --fix` and `npm run models`, run:

```bash
# Short local smoke run; its report is intentionally not releasable.
npm run benchmark:quick

# Release workload: 100 turns, 30 interruptions, 5-minute idle, 30-minute soak.
npm run benchmark:certify

# Validate every committed report and require this package version.
node scripts/check-performance-report.mjs --require-version 0.1.0-alpha.1
```

The harness synthesizes its Chinese and English fixtures locally with the macOS
Tingting and Samantha voices, streams 16 kHz PCM at real-time cadence, and sends
agent text through the actual Qwen3-TTS path. Generated fixtures and raw per-turn
traces are ignored by Git. A separate human acceptance pass with the built-in
microphone remains necessary for room noise, echo cancellation and perceived
voice quality.

## Measurement boundaries

- **Browser capture → Muxiva Frame:** `AudioWorklet` capture timestamp to the
  corresponding admitted audio Frame.
- **Speech onset → barge-in Signal:** first speech sample in the calibrated
  fixture to sustained high-confidence VAD or earlier non-empty ASR partial
  admission as `muxiva.voice.barge_in.confirmed`.
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
