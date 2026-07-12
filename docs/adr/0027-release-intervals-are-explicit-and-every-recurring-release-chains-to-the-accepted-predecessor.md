<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# ADR-027 — Release intervals are explicit and every recurring release chains to the accepted predecessor

**Status:** Accepted (2026-07-12)
**Date:** 2026-07-12
**Supersedes:** ADR-026
**Decision:** release history is a per-component authenticated chain, not a
producer-selected `FROM..TO` query. Every release resolves refs once to immutable
commit object IDs and uses exactly one of three interval modes:

1. **Inception:** a chain-genesis release with no adoption boundary covers
   every commit reachable from `TO`, including every reachable root. The Git
   operation is `git rev-list TO`; there is no `FROM` commit.
2. **Adoption:** a chain-genesis release with boundary `B` covers `B` and every
   in-range descendant reachable from `TO`, while excluding the history
   reachable from every parent of `B`. As a set this is
   `Reach(TO) − union(Reach(parent(B)))`; the Git operation is
   `git rev-list TO --not B^@`. `B` MUST be reachable from `TO`. The boundary is
   chain-genesis state pinned by the out-of-band bootstrap descriptor (ADR-028),
   not a mutable choice made by the candidate policy. A legacy
   `[policy] adoption_boundary` value may mirror it but MUST match it.
3. **Recurring:** a new source release covers `Reach(TO) − Reach(P)`, where `P`
   is the `TO` bound by the accepted predecessor attestation; the Git operation
   is `git rev-list P..TO`. The predecessor MUST be the verifier-selected current
   chain head for the same repository and component, its signature and complete
   chain MUST verify, `P` MUST be an ancestor of `TO`, and any tag naming `P`
   MUST still resolve to `P`. A caller-supplied alternate `FROM`, a missing or
   ambiguous chain head, a moved ref, or a non-ancestor aborts verification.

The commit *set* above is normative; implementations MAY choose an ordering for
processing so long as every member appears exactly once in the provenance
vector. Newly merged unrelated history is included whenever it becomes
reachable from `TO` and was not reachable from the predecessor.

A release attestation MUST bind its interval mode, resolved `TO`, resolved
boundary when applicable, and the cryptographic identity of its predecessor
attestation for a recurring release. Promotion, demotion, or another
superseding re-evaluation at the same `TO` preserves the prior decision's source
interval, source-predecessor link, original active authority, and candidate
state; it does not create an empty new source interval or let candidate-only
keys re-evaluate their enrollment. The next source release references the
accepted terminal attestation available for the current source head when
continuity advances. A later supersession of an older source release does not
rewrite an existing successor link. A history rewrite, skipped link, or
conflicting accepted source head is a verification failure.

Predicate v0.1 remains a historical format and cannot express these complete
continuity claims. A v0.4 release-conformance claim requires the successor
predicate selected by the predicate-versioning work; v0.1 bytes are not changed
by this decision. Migration from a v0.1 release therefore establishes a new
authenticated v0.4 chain genesis (ADR-028): it MAY pin the last trusted v0.1
`TO` as an adoption boundary, which is re-included and re-verified. The v0.1
attestation is historical evidence, not a continuity-capable predecessor.
**Rationale:** Git two-dot notation excludes its left endpoint. The former
`root..TO` wording therefore excluded the root it claimed to include, while the
implementation's empty-start special case did something different. More
importantly, allowing the producer to select any ancestor as `FROM` permits
policy or provenance history to be skipped. Explicit set definitions remove the
notation ambiguity; predecessor attestations make continuity an authenticated
property rather than a command-line convention. Including the adoption boundary
matches the promise that only history *before* it is exempt. Treating the
boundary as immutable chain genesis also prevents a candidate policy from moving
its own verification start.
**Rejected:** literal `root..TO` or `boundary..TO` (excludes the named commit);
arbitrary caller-selected `FROM` (permits history skipping); tag-only
predecessors without an accepted attestation (tags can move and do not prove
chain continuity); excluding the boundary (silently exempts one more commit than
the prose claims); requiring a single repository root (unnecessary — all newly
reachable roots can be included safely); allowing the active/candidate policy to
move the boundary after bootstrap (self-authorizing re-baselining); treating
promotion as a new empty interval (confuses evolving evidence with new source).
**Revisit trigger:** an accepted current-state/transparency profile that changes
how the canonical predecessor head is discovered; or a non-Git source system
whose reachability model cannot represent the three interval sets faithfully.
