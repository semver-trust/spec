<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# ADR-040 — The bootstrap family enforces two-key distinctness as a tool check without widening ADR-022

**Status:** Proposed (2026-07-21)
**Date:** 2026-07-21
**Related:** ADR-022
**Decision:** every bootstrap-family command that sees both a commit-signing key and an
attestation key checks that their fingerprints differ, and that an attestation key is an SSH key;
a key enrolled in both `allowed_signers` and `attestation_signers`, or offered as a signing key
while present in `attestation_signers`, is refused. This is a **tool-enforcement and convention**
decision. It does **not** widen ADR-022's normative scope: whether the specification itself makes
commit/attestation key distinctness a verification-time requirement is a separate decision this
ADR does not take.
**Rationale:** ADR-022 separates the commit and attestation registries and namespaces, but
nothing in the scheme checks today that the two keys are actually distinct, so the
two-keys-same-email confusion — one key doing both jobs — passes silently until it produces a
subtle downstream failure. The family already sees both keys during `enroll` and `setup`, so it
can surface the mistake at setup time, in the tool, for free, without asking the spec to grow a
new normative rule. Keeping the check tool-side preserves the option for the spec to decide the
harder question — whether verification must reject a shared key — on its own timeline.
**Rejected:** adding key-distinctness to the normative spec now (a larger decision with
verification-time consequences, deliberately left separate); doing nothing (the confusion stays
invisible until it bites); enforcing distinctness only in `enroll` (the check belongs in every
command that sees both keys, including `doctor` and `setup`).
**Revisit trigger:** the specification decides to make commit/attestation key distinctness a
normative verification requirement, at which point this tool check becomes enforcement of a spec
rule rather than a convention.
