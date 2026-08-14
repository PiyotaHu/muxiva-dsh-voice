# Contributing

Open an issue before changing the bridge protocol, DSH Session semantics, Graph ports, model set or latency budgets. Small UI, documentation and test improvements can go directly to a pull request.

Every pull request must:

1. keep Muxiva and DSH upstream repositories unmodified;
2. preserve bounded queues and cancellation propagation;
3. add tests for protocol/state-machine changes;
4. document model origin, immutable revision, SHA-256 and license;
5. pass `npm test`, `npm run pack:smoke` and Python compilation;
6. include M1 Pro latency evidence for changes on the audio hot path.

Use Conventional Commits and include a Developer Certificate of Origin sign-off.
