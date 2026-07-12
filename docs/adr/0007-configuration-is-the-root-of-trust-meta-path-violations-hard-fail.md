<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# ADR-007 — Configuration is the root of trust; meta-path violations hard-fail

**Status:** Superseded by ADR-028 (2026-07-12)
**Date:** 2026-07-04
**Decision:** the policy file, scope map, derivation rules, identity map, and attestation-generating workflows are meta-paths requiring the maximum trust level; a release range containing a sub-level meta-path commit **fails verification** — no demotion.
**Rationale:** a T0 commit that edits scope boundaries can reclassify anything; demoting such a release still ships a compromised classifier. The config protects the system, so the system must protect the config.
**Rejected:** treating config as an ordinary scope.
