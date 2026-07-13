<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# ADR-004 — Derivation proofs are the only exception to weakest-link flooring

**Status:** Superseded by ADR-033 (2026-07-13)
**Date:** 2026-07-04
**Decision:** outputs byte-identical under a re-run of a pinned derivation command inherit the minimum trust of the declared inputs. Toolchain version is itself an input. Formatting-only commits are a degenerate derivation.
**Rationale:** generalizes the original OpenAPI/oapi-codegen insight (Brad's starter-repo philosophy: specs as human-reviewed contracts, generated code as constraint) to protoc, lockfiles, codemods, formatters — satisfying Requirement 1 without weakening P3, because the exception is *verified by reproduction*, not declared. Notably, this is a novel and defensible argument for spec-first architecture in the AI era: a reviewed contract *extends its trust* to everything provably generated from it.
**Rejected:** path-based exemptions for `gen/**` directories without regeneration (declared, not proven); size/type-based triviality exemptions (P3 corollary).
