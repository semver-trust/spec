<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# ADR-032 — Threshold is a hard clean-channel accountability gate

**Status:** Accepted (2026-07-13)
**Date:** 2026-07-13
**Related:** ADR-005, ADR-019, ADR-031
**Decision:** Retain policy `threshold`, but define it as a hard
clean-channel accountability gate evaluated before the blast/differ decision
table. A release whose `effective_trust` is below the active policy threshold
MUST NOT enter the clean channel under the baseline decision profile regardless
of blast score, differ availability, or compatibility evidence.

The deterministic baseline decision order is:

1. derive the effective bump from claimed bump, semantic floor, and any
   authenticated corrective floor;
2. apply the accountability threshold;
3. if threshold is met, evaluate the baseline blast/differ table;
4. render with the selected strategy (`demote` or `inflate`).

The baseline threshold is `T2`. Before empirical validation of independent
agent review efficacy, T1 does not satisfy the portable baseline clean profile.
Policies may choose other thresholds, but conformance claims must bind the
threshold used.

Compatibility evidence, accountability evidence, and operational blast/risk
policy are separate inputs. Trust levels order accountability only; they are
not quality, security, safety, compatibility, or defect-probability scores.
Provider-specific blast scoring is portable only when a named, versioned
blast-scoring profile defines the mapping. Otherwise blast is local policy
input recorded in attestations but not a cross-implementation conformance
claim.

Release successor predicates must bind the threshold in the release decision so
replay does not depend on ambient policy interpretation.

**Rationale:** The prior draft described `threshold` as the minimum clean-channel
trust level while the decision table and oracle allowed a T1 clean release in
one cell. That made conforming implementations disagree about the same
evidence. Making threshold an explicit precedence step restores the meaning of
the policy vocabulary and keeps the clean-channel decision reproducible.

Separating the inputs preserves ADR-019. Effective trust may be used as an
accountability gate, but treating it as an inverse risk scalar would smuggle a
quality/security claim into a level system that intentionally does not make
one. Blast scoring remains useful, but only as policy evidence with explicit
profile identity or local scope.

Keeping `demote` and `inflate` as rendering strategies preserves ADR-005 while
making clear that both strategies consume the same deterministic baseline
decision about whether the clean claim is supported.

**Rejected:** remove `threshold` entirely (would leave existing policy
vocabulary misleading and force every clean-channel choice into the table);
allow the table to override threshold (recreates the mismatch); define a
portable numeric blast-risk formula now (false precision and provider gaming);
allow T1 into the baseline clean channel before evidence exists for T1 efficacy
(would imply a risk/quality claim the spec does not have); treat provider-local
blast scores as cross-implementation conformance facts (unportable without a
profile).

**Revisit trigger:** empirical validation supports a different portable
baseline threshold; a versioned blast-scoring profile is adopted; or
implementation experience shows `inflate` requires a pinned escalation target
rather than a policy-local choice.
