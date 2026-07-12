<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# ADR-028 — Bootstrap trust anchors and the previously accepted policy govern policy transitions

**Status:** Accepted (2026-07-12)
**Date:** 2026-07-12
**Supersedes:** ADR-007
**Decision:** the policy at `TO` is a **candidate policy** and never authorizes
its own transition. The **active policy** and verification roots for a release
interval come from one of two verifier-selected authorities:

1. At chain genesis — including migration from a predicate that cannot carry
   v0.4 continuity facts — an out-of-band **bootstrap descriptor** binds the repository
   and component, interval mode, adoption boundary if any, policy path and
   digest, non-removable paths for attestation-generating workflows,
   role-separated trust-material digests, verification profile, and
   injected-clock semantics. The descriptor itself MUST be authenticated by
   verifier-local configuration or by a signature under a verifier-pinned
   bootstrap authority; copying it from the candidate repository is not
   out-of-band trust. Repository files may supply the pinned bytes, but every
   byte source MUST match the descriptor; no command-line or ambient path
   overrides a pinned digest. The policy at `TO` MUST match the bootstrap policy
   exactly and governs the complete first interval.
2. For a recurring release, the accepted predecessor chain head binds the active
   policy path/digest, mandatory workflow paths, role-separated trust-material
   digests, and verification and clock profiles. Those active facts govern
   every commit in the new interval. The final policy found at `TO` is only a
   candidate. If the release succeeds, the attestation binds that candidate as
   the policy activated for the *next* interval. Intermediate policy versions
   committed within one interval never activate mid-interval.

Every verification MUST receive an explicit verifier-supplied verification
instant under the chain's bound clock profile, which defines the instant's
source and validity/freshness semantics; the release attestation MUST record
that instant. A candidate timestamp is evidence, not clock authority. Implicit
system time and ambient trust-root discovery are not authorities.

Policy activation is component-chain state. In a monorepo, one component's
accepted release does not activate its candidate for another component; shared
old roots remain necessary until every relevant component chain transitions.

Every commit is verified against active identities and rules. Candidate-only
keys cannot sign or review their own transition. The active required meta level
governs the interval, including every commit touching either the active or
candidate policy path, either policy's declared meta paths, the authority's
mandatory workflow paths, or repository-local trust material referenced by
either policy. The candidate policy MUST:

- retain the chain's policy path unless a new out-of-band bootstrap establishes
  a new chain;
- cover its own policy path, every authority-pinned workflow path, and every
  repository-local trust-material path in its meta paths;
- set a meta required level no lower than the active policy's level; and
- match the immutable chain-genesis adoption boundary when a legacy mirror is
  present.

Any unknown active signer, trust-material digest mismatch, under-level meta-path
commit, uncovered mandatory meta path, lowered meta level, moved boundary,
predecessor mismatch, or bootstrap mismatch aborts verification. A valid key or
workflow rotation is a two-stage operation: old roots authorize the transition;
new roots become usable only after the release attestation accepting the
candidate policy.

Release attestations for this model MUST distinguish the policy and trust
material that **evaluated** the current interval from the candidate policy and
trust material **activated** for the next interval, and MUST bind the bootstrap
descriptor or predecessor attestation that selected the active state, including
its mandatory workflow paths and verification/clock profiles, plus the
verifier-supplied verification instant. Predicate v0.1 cannot carry these facts
and remains unchanged; v0.4 release emission waits for the successor predicate.
A v0.1 attestation cannot select active policy for recurrence; migration uses an
authenticated bootstrap descriptor and MAY use the last trusted v0.1 `TO` as
the included adoption boundary (ADR-027).
**Rationale:** loading policy from `TO` and immediately using it to validate the
history leading to `TO` lets a candidate add an attacker key, lower meta
requirements, remove protected paths, move the boundary, or alter scopes and
then judge those changes under the weakened rules. A previous-policy model is
the standard safe transition shape: old authority approves new authority. A
release-boundary activation point is simpler and more reproducible than
mid-interval activation, and it creates an auditable key-rotation ceremony.
Out-of-band bootstrap is unavoidable at genesis; making its complete inputs
explicit is more honest than treating repository-controlled configuration as
its own root of trust.
**Rejected:** the `TO` policy governs its own interval (circular); candidate-only
keys may authorize the transition (self-enrollment); sequential policy
activation at each policy commit within one release (order-dependent,
multi-policy attestations and harder replay); ambient trust-root or path
overrides or implicit system time (non-reproducible and bypasses pinned
authority); forbidding all policy changes (prevents key rotation and legitimate
evolution); allowing a candidate to lower its own meta level or move the
adoption boundary in-band (removes its own guardrail).
**Revisit trigger:** an accepted policy-transition predicate/profile that can
represent safe mid-interval activation without ambiguity; or operational
evidence that release-boundary activation makes ordinary key rotation
unworkable.
