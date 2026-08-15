# RFC-0001: ship Muxiva Python wheels with releases

Status: **shipped in Muxiva 0.1.1 on 2026-08-16**.

## Problem

Project-owned Python Node Packs load through Muxiva's native Python binding. Source checkouts can build that binding with Maturin, but a user installing only the Muxiva CLI has no matching wheel to put in the project venv. That prevents a true one-command plugin setup.

## Proposal

For every Muxiva release, publish an exact-version wheel set alongside the CLI artifacts:

- CPython 3.8–3.14 for macOS universal2, Linux x86_64/arm64, and Windows x86_64;
- SHA-256, GitHub build provenance, and automatic PyPI publish attestations;
- the release publishes SHA-256 manifests and exact artifact provenance;
- the voice plugin pins and verifies the exact Muxiva CLI/binding version.

This changes release packaging, not the Muxiva Runtime, Graph, Frame or Node contracts.

## Rejected alternatives

- Vendoring a private wheel in this plugin couples security fixes and hides Muxiva's release identity.
- Building Rust at every end-user install is slow, requires a toolchain and weakens the one-click promise.
- Reimplementing the Node Host outside Muxiva bypasses the product this showcase is meant to demonstrate.
