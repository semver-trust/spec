<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# ADR-029 — Version ancestry is authenticated independently from release intervals

**Status:** Accepted (2026-07-12)
**Date:** 2026-07-12
**Related:** ADR-009, ADR-027, ADR-028
**Decision:** release-interval ancestry, source-release continuity, and version
ancestry are distinct authenticated facts. Neither an adoption boundary, a
source predecessor's `TO`, nor a caller-selected `FROM` implicitly supplies the
SemVer baseline.

Every component chain binds one canonical tag prefix and authenticated
**version state**. At chain genesis, the bootstrap descriptor contains exactly
one of:

1. `version_predecessor: null`, which explicitly starts a new version line and
   establishes the synthetic clean baseline `v0.0.0` without claiming that a
   Git tag or commit exists for it, or that historical tags are absent; or
2. one version-predecessor descriptor binding a canonical clean §7.1 tag, its
   raw Git ref-target object ID, and its peeled commit object ID. The tag prefix
   MUST match the component chain. For an inception interval the predecessor
   commit MUST be reachable from `TO`; for an adoption interval it MUST be
   reachable from the included boundary `B` (equality allowed). Pinning a legacy
   version predecessor continues its version line but grants no provenance or
   trust claim to exempt history.

Bootstrap discovery is convenience only. A non-null selection with zero or
multiple candidate tags, a missing/malformed tag, prefix mismatch, moved raw
ref, changed peeled commit, or failed ancestry check aborts verification. Null
genesis MUST be explicit and authenticated; it is never inferred from failed
discovery. Tooling MAY propose a descriptor for maintainer approval but MUST NOT
silently choose the highest or nearest tag.

Every accepted release decision carries version state forward. That state binds
the tag prefix; the target baseline, represented by synthetic genesis or an
authenticated canonical tag plus its raw/peeled object IDs and source identity;
the target core version and bump class; whether its clean tag has been accepted;
the current accepted decision and immutable tag anchoring its lineage; the
accepted source-interval identities accumulated for the current trust claim;
and enough accepted decision-lineage state to derive trust-suffix iterations.
It also binds an explicit pending corrective bump greater than the target bump,
or its absence. An attestation-only decision retains the prior immutable tag
while becoming the current accepted decision. Applying the bound target bump to
the baseline core MUST produce the target core exactly.

The producer does not supply an aggregate target trust level. The verifier
derives it from the complete bound target lineage and authenticated evidence.

At adoption genesis, compatibility evidence may span from a legacy version
predecessor before `B`, but the target trust lineage starts with the verified
adoption interval. Exempt history remains disclosed and receives no trust level.

The verifier accepts one signed **version action**:

- **Advance:** apply the release decision's effective bump (the greater of the
  claimed bump, semantic floor, and any pending corrective bump) to the prior
  target core, or to the genesis baseline on the first release. The resulting
  target baseline is the bootstrap-pinned legacy predecessor or immutable
  lineage tag and source identity bound by the prior accepted decision, or
  synthetic genesis on the first release. At bootstrap, or when the predecessor
  target has an accepted clean tag, the new target lineage contains the current
  source interval only. When advancing from an unpromoted target, it appends the
  current interval to the predecessor's target lineage so skipped prereleases
  cannot launder trust. The resulting target bump is that effective bump.
  Advance clears the correction. A prerelease result starts at iteration one for
  its level.
- **Re-cut:** preserve an unpromoted target core while source changes are added.
  The target's clean tag MUST NOT already have been accepted, and compatibility
  evaluation from the target's bound baseline source through the new `TO` MUST
  remain within the target bump. The baseline may itself be a trust prerelease;
  for synthetic genesis, evaluation covers the complete inception history
  through the new `TO`. The current source interval is appended to the target
  lineage. Effective trust and blast are recomputed over every contributing
  interval, with each commit governed by the active authority bound to its
  original interval; a high-trust fix interval cannot erase an earlier low-trust
  contribution. For a prerelease result, iteration is one greater than the
  highest accepted iteration for that target and level in the selected
  version-decision lineage. A pending corrective bump prohibits re-cut.
- **Supersede:** preserve `TO`, source interval, target lineage, baseline, and
  target core while evidence changes. Promotion emits the target's clean tag if
  it is not already present. A same-level prerelease supersession derives the
  next iteration; demotion of an already published clean release is an
  attestation-only update and does not mutate or replace the clean tag (ADR-009).
  Compatibility evidence is recomputed from the bound target baseline; if its
  effective bump exceeds the bound target bump, the semantic invalidation is
  likewise attestation-only because no new tag can repair an immutable
  under-bumped release. When the invalidated decision is still the source head,
  resulting state binds that effective bump as a pending corrective floor. A
  later same-head supersession clears it only if recomputed evidence no longer
  exceeds the target bump. After a later source release has advanced continuity,
  every supersession of the older decision is attestation-only: it emits no tag,
  consumes no iteration, and cannot rewrite or become authority for the
  successor's already-bound version state.

The action and claimed bump are signed release-decision facts, analogous to
declared release intent; the prior version state is verifier-selected chain
authority. `current_version`, a version-predecessor flag, and trust-suffix
`iteration` are not protocol inputs. Any compatibility argument that supplies
them can only assert equality with authenticated/derived state; a mismatch
aborts.

Before emission, the exact tag is derived from the bound prefix, target core,
decision channel, effective trust level, and derived iteration. An existing tag
at that name aborts a new emission; tags are never moved or overwritten. The
successor release predicate MUST bind the version action, version predecessor
or genesis marker, prior and resulting version-state identities, exact emitted
tag or an explicit no-emission marker, immutable lineage tag raw/peeled object
IDs, and derived iteration where applicable.
**Rationale:** the same authenticated source interval can otherwise produce
different version lines solely because a producer supplied `FROM=""` or
`FROM=v0.9.4`. Using the adoption boundary as the version donor conflates
"history verified since here" with "version line continued from here"; ordinary
legacy adoption often places the last release tag before a later trustworthy
boundary. Binding only a predecessor tag is also insufficient: an accepted
predecessor may itself be `v1.4.0-t0.1`, promotions create multiple tags at one
commit, and a caller-selected `.1` versus `.2` still changes precedence.
Authenticated version state makes those choices reproducible without forbidding
legitimate re-cuts or evidence-only promotion.
Making late supersessions attestation-only prevents a delayed decision on an
old target from occupying the clean tag or trust iteration that an already
accepted re-cut lineage may still need.
Carrying an under-bump correction forward prevents the chain from acknowledging
a broken SemVer claim and then silently continuing it with an ordinary patch.
Accumulating unpromoted source intervals prevents a T0 prerelease from becoming
clean merely because a later re-cut or target advance contains only T3 fixes.
**Rejected:** derive version from the interval boundary or `FROM` spelling
(conflates independent facts); accept arbitrary `current_version` or iteration
(same chain state can emit different tags); infer the highest reachable SemVer
tag (ambiguous and repository-policy-dependent); require the legacy predecessor
to equal the adoption boundary (breaks normal migrations); bind only a tag name
or peeled commit (does not detect moved/recreated refs); require every recurring
predecessor to be clean (prevents fixes to trust prereleases); treat every
same-core cut as iteration one (tag collision and precedence ambiguity); let a
late supersession emit a tag after source continuity advances (can collide with
the active successor target without any legal state rewrite).
**Revisit trigger:** operational evidence that authenticated re-cut state is too
complex for ordinary prerelease workflows; or an accepted transparency/current-
state profile that supplies a stronger canonical version-decision lineage.
