<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# ADR-001 — Encode trust in SemVer pre-release identifiers, not build metadata

**Status:** Superseded by ADR-034 (2026-07-13)
**Date:** 2026-07-04
**Decision:** trust rides in pre-release position: `v1.4.0-t1.1 < v1.4.0`.
**Rationale:** pre-release semantics already do the job — Go modules, npm, and Cargo all exclude pre-releases from default range resolution, so low-trust releases are opt-in with zero consumer tooling. Build metadata is ignored for precedence and, decisively, **Go modules reject build-metadata suffixes** (only `+incompatible` exists) — a hard blocker for the first target ecosystem.
**Rejected:** `+ai.t0`-style build metadata (no precedence effect; Go-incompatible); a parallel tag namespace only (loses the in-band human-legible signal entirely).
**Revisit trigger:** none foreseen; this is load-bearing.
