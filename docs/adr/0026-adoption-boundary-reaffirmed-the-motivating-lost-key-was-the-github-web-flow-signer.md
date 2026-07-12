<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# ADR-026 — Adoption boundary reaffirmed: the motivating lost key was the GitHub web-flow signer

**Status:** Accepted (2026-07-12)
**Date:** 2026-07-12
**Supersedes:** ADR-024
**Decision:** the adoption-boundary mechanism is reaffirmed **unchanged**: a repository MAY declare a single
policy-pinned boundary commit before which history is exempt (a first release verifies `boundary..TO`),
subject to the same three binding properties ADR-024 established — **policy-pinned** (the boundary lives only
in the policy file, protected by the §5.4 meta-path rule, frozen per decision by the §8.1 policy digest),
**disclosed** (`range.from_is_adoption_boundary` marks a boundary-anchored range; "verified since the
boundary" and "verified since inception" are never conflated), and **exempt, never laundered** (pre-boundary
history makes no claim at all; it is out-of-scope, never T0). What this ADR corrects is ADR-024's
project-specific decision text: the reference implementation is **not** an adoption-boundary user. The
"lost" key that motivated ADR-024 — `B5690EEEBB952194` — is GitHub's web-flow signing key (fingerprint
`968479A1AFF927E37D1A566BB5690EEEBB952194`, published at <https://github.com/web-flow.gpg>), which signs
web-UI merge commits. semver-trust-go vendors that key in its committed keyring
(`.semver-trust/gpg-keyring.asc`), declares no `adoption_boundary` in its policy, and verified its first
release (`v0.1.0`) from inception: the §10 walk covered `root..TO` including the root commit `6cacd9a7`,
which GitHub likewise reports as cryptographically verified.
**Rationale:** ADR-024 embedded a false factual premise inside its accepted Decision ("its earliest commits
are signed by a key whose public half is lost, which no key-family support can recover") and its Rationale
treated that premise as the triggering evidence. Issue-only annotation (spec issue #20) would leave the
correction outside the repository: anyone reading the vendored ADRs offline would find an accepted record
directing the reference repository toward a boundary it neither needs nor has — wrong first-release guidance
exactly where it is most likely to be consulted. Supersession keeps the correction as discoverable as the
mistake. The mistaken trigger does not invalidate the general adoption problem: repositories with genuinely
unverifiable pre-scheme history (adoption date, true key loss, platform migration) remain the mechanism's
real constituency, and the design record predicted that need before any trigger arrived. Implementations
keep their adoption-boundary support and tests; only this repository's need to exercise the option was
mistaken.
**Rejected:** deleting the adoption-boundary feature (the general problem stands; removing a sound mechanism
over a mistaken trigger repeats the error in the opposite direction); editing ADR-024's accepted
Decision/Rationale in place (the ADR change protocol forbids it — accepted records are immutable except for
the status line); issue-only annotation (poor repository-local discoverability: issues are not vendored with
the spec, ADRs are).
**Revisit trigger:** carried over from ADR-024 — evidence that boundary declarations are used to repeatedly
re-baseline history (multiple boundary moves in a repository's policy history), which would argue for
surfacing boundary-move counts in verification output.
