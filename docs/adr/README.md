<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# SemVer-Trust — Architecture Decision Records

One file per decision. Identifiers (ADR-NNN) are stable and are how decisions
are referenced from the specification's design record and elsewhere.

| ADR | Title | Status |
|---|---|---|
| ADR-001 | [Encode trust in SemVer pre-release identifiers, not build metadata](0001-encode-trust-in-semver-pre-release-identifiers-not-build-metadata.md) | Superseded by ADR-034 (2026-07-13) |
| ADR-002 | [Trust levels count independent accountable humans](0002-trust-levels-count-independent-accountable-humans.md) | Accepted (draft v0.1) |
| ADR-003 | [Scalar level in the tag; full provenance vector in the attestation](0003-scalar-level-in-the-tag-full-provenance-vector-in-the-attestation.md) | Accepted (draft v0.1) |
| ADR-004 | [Derivation proofs are the only exception to weakest-link flooring](0004-derivation-proofs-are-the-only-exception-to-weakest-link-flooring.md) | Superseded by ADR-033 (2026-07-13) |
| ADR-005 | [Bump policy: semantic floor + evidence ceiling, two strategies](0005-bump-policy-semantic-floor-evidence-ceiling-two-strategies.md) | Accepted (draft v0.1) |
| ADR-006 | [Path-scoped trust with transitive propagation is first-class](0006-path-scoped-trust-with-transitive-propagation-is-first-class.md) | Accepted (draft v0.1) |
| ADR-007 | [Configuration is the root of trust; meta-path violations hard-fail](0007-configuration-is-the-root-of-trust-meta-path-violations-hard-fail.md) | Superseded by ADR-028 (2026-07-12) |
| ADR-008 | [Unverifiable ≠ T0: verification failures abort](0008-unverifiable-t0-verification-failures-abort.md) | Accepted (draft v0.1) |
| ADR-009 | [Promotion: same SHA, new attestation; cascades; supersession over mutation](0009-promotion-same-sha-new-attestation-cascades-supersession-over-mutation.md) | Accepted (draft v0.1) |
| ADR-010 | [Trust channel generalizes (and should not mix with) rc](0010-trust-channel-generalizes-and-should-not-mix-with-rc.md) | Accepted (draft v0.1) |
| ADR-011 | [Language-agnostic core; ecosystem plugins; lossy registry projections](0011-language-agnostic-core-ecosystem-plugins-lossy-registry-projections.md) | Accepted (draft v0.1; registry-projection clause revised by ADR-034) |
| ADR-012 | [External dependencies out of scope for v0.1](0012-external-dependencies-out-of-scope-for-v0-1.md) | Accepted (draft v0.1) |
| ADR-013 | [Naming and repository topology](0013-naming-and-repository-topology.md) | Accepted (2026-07-04) |
| ADR-014 | [Licensing and control strategy](0014-licensing-and-control-strategy.md) | Accepted (2026-07-04) |
| ADR-015 | [Derivation inputs pinning via language-native mechanisms](0015-derivation-inputs-pin-via-language-native-mechanisms-not-environment-managers.md) | Superseded by ADR-033 (2026-07-13) |
| ADR-016 | [Development environments outcome-based convention](0016-development-environments-outcome-based-convention-devbox-as-maintainer-default.md) | Accepted (2026-07-04) |
| ADR-017 | [Roadmap reorders around demand side artifacts and keystone instrumentation](0017-roadmap-reorders-around-demand-side-artifacts-and-keystone-instrumentation.md) | Accepted (2026-07-04) |
| ADR-018 | [Verification interfaces accept injectable trust roots and clock from day one](0018-verification-interfaces-accept-injectable-trust-roots-and-clock-from-day-one.md) | Accepted (2026-07-04) |
| ADR-019 | [Trust levels order accountability not risk](0019-trust-levels-order-accountability-not-risk.md) | Accepted (2026-07-04) |
| ADR-020 | [Incorporate go-semver as reviewed re-commits](0020-incorporate-go-semver-as-reviewed-re-commits.md) | Accepted (2026-07-06) |
| ADR-021 | [Implementations consume conformance artifacts as vendored digest-pinned copies](0021-implementations-consume-conformance-artifacts-as-vendored-digest-pinned-copies.md) | Accepted (2026-07-06) |
| ADR-022 | [Attestation signatures are SSHSIG over the DSSE PAE with purpose-binding namespaces](0022-attestation-signatures-are-sshsig-over-the-dsse-pae-with-purpose-binding-namespaces.md) | Accepted (2026-07-11) |
| ADR-023 | [Merge commits are created locally, signed and trailered, never by web-flow](0023-merge-commits-are-created-locally-signed-and-trailered-never-by-web-flow.md) | Accepted (2026-07-11) |
| ADR-024 | [Adoption boundary: pre-scheme history is exempt, disclosed, and policy-pinned](0024-adoption-boundary-pre-scheme-history-is-exempt-disclosed-and-policy-pinned.md) | Superseded by ADR-026 (2026-07-12) |
| ADR-025 | [Self-review exclusion prevents double-counting, not first-counting](0025-self-review-exclusion-prevents-double-counting-not-first-counting.md) | Accepted (2026-07-12) |
| ADR-026 | [Adoption boundary reaffirmed: the motivating lost key was the GitHub web-flow signer](0026-adoption-boundary-reaffirmed-the-motivating-lost-key-was-the-github-web-flow-signer.md) | Superseded by ADR-027 (2026-07-12) |
| ADR-027 | [Release intervals are explicit and every recurring release chains to the accepted predecessor](0027-release-intervals-are-explicit-and-every-recurring-release-chains-to-the-accepted-predecessor.md) | Accepted (2026-07-12) |
| ADR-028 | [Bootstrap trust anchors and the previously accepted policy govern policy transitions](0028-bootstrap-trust-anchors-and-the-previously-accepted-policy-govern-policy-transitions.md) | Accepted (2026-07-12) |
| ADR-029 | [Version ancestry is authenticated independently from release intervals](0029-version-ancestry-is-authenticated-independently-from-release-intervals.md) | Accepted (2026-07-12) |
| ADR-030 | [Predicate v0.1 is historical and successor predicates carry explicit profile identity](0030-predicate-v0-1-is-historical-and-successor-predicates-carry-explicit-profile-identity.md) | Accepted (2026-07-12) |
| ADR-031 | [Qualified review requires final-revision approval and canonical actors](0031-qualified-review-requires-final-revision-approval-and-canonical-actors.md) | Accepted (2026-07-12) |
| ADR-032 | [Threshold is a hard clean-channel accountability gate](0032-threshold-is-a-hard-clean-channel-accountability-gate.md) | Accepted (2026-07-13) |
| ADR-033 | [Executable derivation proofs are out of the portable baseline](0033-executable-derivation-proofs-are-out-of-the-portable-baseline.md) | Accepted (2026-07-13) |
| ADR-034 | [Ecosystem publishing profiles constrain resolver-routing claims](0034-ecosystem-publishing-profiles-constrain-resolver-routing-claims.md) | Accepted (2026-07-13) |

## Adding an ADR

1. Copy the field structure of an existing ADR (Status / Date / Decision /
   Rationale / Rejected / Revisit trigger, plus Supersedes where applicable).
2. Filename is **derived from the title**: `NNNN-<slug>.md`, where the slug
   is the title lowercased with every run of non-alphanumeric characters
   replaced by a single hyphen, trimmed (e.g. "Unverifiable ≠ T0:
   verification failures abort" → `unverifiable-t0-verification-failures-abort`).
   Filename↔title alignment is checkable and checked.
3. Decisions change only by superseding: never edit an accepted ADR's
   Decision/Rationale/Rejected content. Set the superseded ADR's Status to
   `Superseded by ADR-NNN` — that status line is the only permitted edit.
4. Add a row to this index. Mirror material spec changes with a spec
   version bump (see `../design-record.md` §9 and the repository CLAUDE.md).
