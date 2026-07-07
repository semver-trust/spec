<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# ADR-021 — Implementations consume conformance artifacts as vendored digest-pinned copies

**Status:** Accepted (2026-07-06)
**Date:** 2026-07-06
**Decision:** implementations (`semver-trust-go` first) consume this repository's conformance artifacts —
vectors, schemas, and crypto fixture material — as **vendored copies pinned by source commit SHA and per-file
content digest**. An explicit sync task refreshes the copy and records the pin in a manifest; implementation CI
verifies the vendored bytes match the manifest, and the manifest is the implementation's single
spec-version-pin location (surfaced by `--version`, per GO-026). Prose cross-references between repositories
use canonical URLs — `https://semver-trust.dev/...` for Pages-served artifacts, full GitHub URLs otherwise —
never filesystem-relative paths or symlinks across repository boundaries.
**Rationale:** ADR-015 extends P5 to verification portability: pinning must be self-contained and
language-native, so a fresh clone of an implementation builds and verifies with no ambient checkout, no
submodule ceremony, and no network. Vendoring is the consumption model this repository already anticipates —
`schemas/` and `conformance/` are Apache-2.0 licensed precisely "so implementations may vendor them freely."
The digest manifest preserves the cross-implementation identity of the vectors (ADR-018: everyone verifies the
same bytes) while making suite updates deliberate, reviewable diffs against a stated spec version rather than
silent drift.
**Rejected:** git submodules (clone and CI friction; a fresh clone without `--recursive` silently has no
vectors, defeating self-containment); test-time network fetch (breaks hermetic tests; ambient fetching is the
posture ADR-018 rejects in verification paths, and the conformance suite deserves the same); packaging
`conformance/` as a Go module (couples the language-agnostic contract to one ecosystem's tooling, against
ADR-011).
**Revisit trigger:** a second implementation whose ecosystem cannot vendor comfortably, or conformance
material that grows too large to vendor (for example, extensive crypto fixture sets) — revisit with a
digest-addressed artifact-registry distribution.
