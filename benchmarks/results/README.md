# Certified benchmark results

One immutable JSON report is committed for every published version and
certification machine:

```text
v<package-version>-<machine-slug>.json
```

The first required report is
`v0.1.0-alpha.1-m1-pro.json`. It must validate against `../schema.json`; measured
values must never be copied from the latency budgets.

The certification run uses AC power, closes unrelated foreground applications,
records the exact macOS and dependency versions, hashes `models.lock.json`,
warms up the models, and then executes at least:

- 100 scripted turns;
- 30 mid-answer interruptions;
- Mandarin, English, numeric, Markdown, and code-oriented prompts;
- five minutes of continuous idle listening;
- a 30-minute soak.

Raw traces may be attached to the GitHub Release rather than committed when
they are large. The JSON report contains the reviewable aggregate and must not
contain microphone audio, transcripts, credentials, or workspace content.
