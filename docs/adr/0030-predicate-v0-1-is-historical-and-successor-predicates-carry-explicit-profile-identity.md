<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# ADR-030 — Predicate v0.1 is historical and successor predicates carry explicit profile identity

**Status:** Accepted (2026-07-12)
**Date:** 2026-07-12
**Related:** ADR-021, ADR-027, ADR-028, ADR-029
**Decision:** release and review predicate v0.1 are historical formats. They
remain verifiable under their frozen legacy semantics, but they MUST NOT be
extended or interpreted as carrying v0.4 continuity, policy-transition, or
authenticated version-state claims.

The successor predicate family starts at:

- `https://semver-trust.dev/release/v0.2`
- `https://semver-trust.dev/review/v0.2`

Each successor attestation MUST bind explicit profile identity: the
SemVer-Trust specification version, predicate contract version, evaluator
identity, graph/profile adapters, repository identity profile, verification
time profile, and the verification instant supplied to the verifier. The
release successor additionally binds the three v0.4 chain dimensions:
release interval/source predecessor, active/candidate policy state, and
authenticated version state. The review successor additionally binds canonical
actor identities, final-revision approval state, and the source identity and
target revisions the review covers.

Successor schemas are closed at their object boundaries except for explicitly
declared extension maps. Any change that alters validation behavior or
interpretation mints a new predicate URI and schema. Additive optional fields
inside a closed emitted schema are not a compatibility mechanism, because old
vendored validators reject fields they do not know.

Legacy v0.1 attestations MAY be used as historical evidence during migration,
but a v0.2 release chain begins with an authenticated bootstrap descriptor. A
v0.1 release attestation cannot serve as recurring predecessor authority
because it does not bind active/candidate policy state, trust roots, version
state, or the verifier profile that interpreted it.
**Rationale:** v0.1 bytes were emitted before the release-interval,
policy-transition, and version-ancestry contracts stabilized. The v0.1 schemas
are closed, so extending them in place would create two incompatible behaviors:
old validators reject the new bytes, while newer validators might assign
continuity meaning to fields historical attestations never carried. Assigning
a successor URI makes the interpretation explicit and digest-pinnable under
ADR-021.

Profile identity is load-bearing because the same repository facts can verify
differently under different draft rules, graph adapters, actor mappings, trust
roots, and verification times. If those choices remain ambient caller state,
two conforming tools can disagree on the same signed attestation without any
wire-level defect to point at.

The review predicate must evolve with the release predicate because release
trust depends on review facts. A release successor that binds final-revision
state is insufficient if the review attestation still cannot say which actor
was canonical, which revision was approved, and which profile interpreted the
approval.
**Rejected:** extend v0.1 with optional fields (closed vendored schemas reject
them); reinterpret existing v0.1 fields under v0.4 rules (historical bytes gain
claims they did not encode); rely on repository policy to supply profile
identity (the attestation is no longer portable); use one successor URI with
open-world unknown fields for normative semantics (unknown fields cannot be
required for verification).
**Revisit trigger:** implementation evidence that the v0.2 contract omits a
required binding for independent replay; or an adopted source-provenance
profile, such as a future SLSA Source integration, that should replace a
SemVer-Trust-native field with an external digest-pinned predicate.
