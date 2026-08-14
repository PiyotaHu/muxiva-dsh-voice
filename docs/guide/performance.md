# Performance and acceptance

The first certification machine is a MacBook Pro M1 Pro, 16 GB RAM, macOS, using the built-in microphone and speakers.

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
