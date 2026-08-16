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
| 0.1.0-alpha.2 | MacBook Pro M1 Pro, 16 GB | [JSON](../../benchmarks/results/v0.1.0-alpha.2-m1-pro.json) | DSH rc.6 release certification |
| 0.1.0-alpha.1 | MacBook Pro M1 Pro, 16 GB | [JSON](../../benchmarks/results/v0.1.0-alpha.1-m1-pro.json) | Alpha passed |

### 0.1.0-alpha.2 measured summary — reliability-alpha-v1

| Metric | p50 | p95 | p99 |
| --- | ---: | ---: | ---: |
| Capture → Muxiva Frame | 7.5 ms | 14.9 ms | 20.3 ms |
| Speech onset → ASR-confirmed barge-in | 886.6 ms | 1157.0 ms | 1256.0 ms |
| Speech end → ASR Final | 2112.4 ms | 2181.2 ms | 2239.8 ms |
| Agent text → first TTS PCM | 329.4 ms | 1175.3 ms | 1270.1 ms |
| Audio queue ahead | 219.7 ms | 227.2 ms | 231.5 ms |
| Stale audio after barge-in | 0.0 ms | 0.0 ms | 0.0 ms |

The run completed 130/130 turns and 30/30 interruptions, five minutes of idle
listening, and a 30-minute soak with zero failed turns, dropped frames, TTS
underruns, stale post-interruption audio, late results, or unbounded queues.
Mandarin CER was 12.62% and English WER was 6.32% on the deterministic synthetic
corpus. Peak process-tree RSS was 1111.3 MiB; active CPU averaged 19.1%, idle CPU
11.4%, and model storage was 2355.0 MiB. ASR p95 RTF was 0.062 and TTS p95 RTF
was 1.261.

This release intentionally selects `reliability-alpha-v1`. It requires
meaningful ASR text before interruption and two seconds of continuous silence
before Final, so those user-visible waits are included in the measured barge-in
and endpoint latency. It also favors complete-context Qwen prosody over the old
first-token gate. These numbers therefore must not be compared to alpha.1 as if
the event boundaries were unchanged.

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

## Versioned policy budgets

| Measurement | Latency Alpha v1 | Reliability Alpha v1 | Release v1 |
| --- | ---: | ---: | ---: |
| Browser capture → Muxiva Frame | p95 ≤ 45 ms | p95 ≤ 45 ms | p95 ≤ 35 ms |
| Speech onset → barge-in Signal | p95 ≤ 180 ms | p95 ≤ 1300 ms | p95 ≤ 140 ms |
| Speech end → ASR Final | p95 ≤ 750 ms | p95 ≤ 2400 ms | p95 ≤ 550 ms |
| First DSH text → first TTS PCM | p95 ≤ 900 ms | p95 ≤ 1400 ms | p95 ≤ 650 ms |
| Audio queue ahead | ≤ 240 ms | ≤ 240 ms | ≤ 160 ms |
| Stale audio after barge-in | ≤ 120 ms | ≤ 120 ms | ≤ 80 ms |

`latency-alpha-v1` is retained for the immutable alpha.1 report.
`reliability-alpha-v1` is narrowly scoped to alpha.2 and additionally requires
Mandarin CER ≤ 15%, English WER ≤ 8%, ASR p95 RTF ≤ 0.10 and TTS p95 RTF ≤
1.35. A future stable release cannot silently inherit these relaxed
user-visible latency limits: it must satisfy `release-v1` or introduce and
document a new pre-release policy before measurement.

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
node scripts/check-performance-report.mjs --require-version 0.1.0-alpha.2
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
  fixture to non-empty ASR partial or quality-gated multilingual Final
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
