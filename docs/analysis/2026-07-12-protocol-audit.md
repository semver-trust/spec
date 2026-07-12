<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Protocol Audit — SemVer-Trust Draft v0.3

**Date:** 2026-07-12  
**Status:** Findings recorded for issue disposition; non-normative  
**Specification target:** `semver-trust/spec@4449eb2`  
**Implementation target:** `semver-trust/semver-trust-go@f975d69`

## 1. Scope and method

This audit reconstructs the proposal in its strongest form, identifies the
decisions and assumptions on which it depends, and tests those decisions
against the normative draft, ADRs, schemas, conformance suite, cryptographic
fixtures, and reference Go implementation. It is a design and protocol audit,
not an accepted decision record. Findings change the scheme only through the
repository's issue, ADR-supersession, specification-versioning, and
conformance processes.

The review covered:

- the normative [draft v0.3 specification](../../spec/semver-trust.md);
- the [design record](../design-record.md) and ADR-001 through ADR-026;
- the v0.1 release and review predicate definitions and JSON Schemas;
- core and cryptographic conformance vectors and their Python oracle;
- the Go verifier, release evaluator, policy parser, review verifier, range
  walker, and derivation runner;
- current SemVer, Git, package-manager, in-toto, and SLSA behavior where it is
  load-bearing.

`task verify` completed with zero failures at the audited specification
revision. That establishes internal agreement for the cases represented by
the current vectors; it does not independently resolve the semantic and
coverage findings below.

## 2. Charitable reconstruction

SemVer-Trust's strongest claim is not that it detects AI authorship or predicts
code quality. Its defensible claim is:

> Derive release-scoped accountability facts from signed source and review
> evidence, aggregate them over affected scopes and internal dependencies, and
> use ordinary release channels to route releases whose evidence does not meet
> policy.

The intended pipeline is:

```text
signed commit and review evidence
                ↓
       per-commit own trust
                ↓
       floor by affected scope
                ↓
 internal-dependency propagation
                ↓
      effective trust vector
                ↓
 semantic floor + evidence policy
                ↓
 clean channel or -tN.iter channel
                ↓
      signed release attestation
```

This addresses a real calibration problem: automated systems can produce
plausible code and plausible development artifacts at high volume, while
traditional release signals do not state which identified humans accepted
responsibility for a change. The design intentionally treats a human
signature as an accountability assertion rather than claiming to recover
unobservable keystroke authorship.

## 3. Design strengths to preserve

The following elements survived the audit and should remain central:

1. **Accountability rather than authorship detection.** Principle 2 avoids an
   unwinnable inference problem and states the identity-laundering limit
   honestly.
2. **Unverifiable is not T0.** Verification failure aborts rather than turning
   unknown evidence into a low but apparently valid level.
3. **Scalar tag, full vector in the attestation.** The split keeps SemVer
   interoperable while preserving scope-level evidence for policy and audit.
4. **Scope flooring and dependency propagation.** These expose weak affected
   scopes that a repository-wide average or top-level badge would hide.
5. **Same-source promotion and immutable supersession.** New evidence can
   change a release's channel without rewriting the source history or mutating
   an old attestation.
6. **Conformance-first engineering.** Data vectors, digest-pinned vendoring,
   injectable clocks/trust roots, role-separated signer registries, and
   purpose-bound SSHSIG namespaces are strong implementation practices.
7. **Open acknowledgement of Goodhart and empirical uncertainty.** The design
   already records that accountability is not correctness and that the
   trust-to-outcome relationship remains unproven.

The project's most distinctive contribution is therefore **release-scoped
accountability aggregation and routing**, not a universal trust or risk score.

## 4. Findings summary

| ID | Priority | Finding | Proposed disposition |
|---|---|---|---|
| F-01 | P0 | Release intervals and predecessor continuity are ambiguous | Define exact intervals and chain releases |
| F-02 | P0 | The policy at `TO` authorizes its own transition | Previous policy governs; pin genesis roots |
| F-03 | P0 | Policy `threshold` is not part of the decision function | Formalize or remove it |
| F-04 | P0 | Non-approval review verdicts can increase trust | Count only qualified final-revision approval |
| F-05 | P0 | Distinct credentials do not establish distinct people | Add canonical actor identity or narrow the claim |
| F-06 | P0 | Executable derivation is unsound and unsafe downstream | Remove from baseline or redesign hermetically |
| F-07 | P0 | Predicate v0.1 changed after its freeze point | Preserve v0.1; mint a versioned successor |
| F-08 | P1 | Resolver and PyPI projections are conditional or lossy | Publish ecosystem profiles; defer unsafe projection |
| F-09 | P1 | Accountability is reused as a risk proxy | Separate accountability, compatibility, and risk |
| F-10 | P1 | Attestation binding, continuity, and freshness are incomplete | Bind repository/resources/profile and current state |
| F-11 | P1 | SLSA positioning omits the current Source Track | Consume or extend SLSA Source evidence |
| F-12 | P1 | Conformance is green but not adversarially complete | Add raw-evidence and negative end-to-end vectors |
| F-13 | P1 | Maintainer-facing state documentation drifted materially | Synchronize it and check future drift mechanically |

## 5. Protocol blockers

### F-01 — Release intervals and predecessor continuity

The specification uses `FROM..TO`, describes first-release traversal as
`root..TO`, and names `git rev-list FROM..TO` as the implementation mechanism.
Git's range notation means commits reachable from `TO` excluding `FROM` and
everything reachable from `FROM`; literal `root..TO` therefore excludes the
root. See the official [Git revision-range documentation][git-ranges].

The Go implementation compensates for an empty `from` by walking all commits,
but that special case is not equivalent to the normative notation. See the
[range walker][go-walk]. Adoption boundaries use a non-empty `from`, so the
boundary is excluded even though prose exempts history *before* the boundary.

More importantly, an arbitrary ancestor can currently serve as `FROM` without
being established as the immediately preceding accepted release. This permits
verified history to be skipped. The fixture builder illustrates the exposure
by placing policy setup outside the first verified range in
[`build-fixture-repos.sh`](../../conformance/crypto/build-fixture-repos.sh).

Proposed disposition:

- first release: `[ROOT, TO]`;
- recurring release: `(PREVIOUS_TO, TO]`;
- adoption release: `[BOUNDARY, TO]` if only pre-boundary history is exempt;
- bind `PREVIOUS_TO` to an accepted predecessor attestation;
- resolve refs to immutable objects, require ancestry, and define behavior for
  multiple reachable roots;
- reject skipped or conflicting predecessor chains.

### F-02 — Policy transitions are self-authorizing

The verification procedure loads the policy from `TO` and then applies it to
the history leading to `TO`. The implementation does the same before resolving
signer registries and attestation-verification configuration; see
[`verify.go`][go-verify].

A proposed policy can therefore authorize the credentials that validate its
own commit, lower meta-path requirements, remove protected paths, move the
adoption boundary, or alter scopes and derivations. The policy parser also
checks that `meta.paths` is nonempty but does not establish that the actual
policy and required workflow paths are present; see [`parse.go`][go-policy].

Proposed disposition:

1. An externally pinned or signed genesis policy establishes initial roots.
2. Accepted policy `P(n)` governs transition to `P(n+1)`.
3. `P(n+1)` activates only after the transition succeeds.
4. Minimum self-protection invariants are protocol requirements and cannot be
   removed by the policy being evaluated.

### F-03 — Policy threshold is not enforced

The policy example says `threshold = "T2"` is the minimum clean-channel level,
while the default table allows a T1/low-blast release with a differ into the
clean channel. The normative release procedure does not define which wins.

The conformance oracle's decision function does not accept a threshold; see
[`check-conformance.py`](../../scripts/check-conformance.py). The Go release
decision likewise does not apply the parsed value; see [`release.go`][go-release].

The field should either be removed or become an explicit gate before the
evidence-profile decision. Conformance vectors should vary only the threshold
and establish the required outcome.

### F-04 — Review qualification permits trust inflation

The [review schema](../../schemas/review-v0.1.json) permits `approved`,
`changes_requested`, and `commented`. The normative text does not explicitly
limit trust-bearing review to approval. The Go verifier's parsed subset omits
the verdict and accepts the first reviewer's class and identity; see
[`review.go`][go-review]. A signed comment or changes request can consequently
be treated as human review.

The predicate also does not fully model final-revision approval after squash
or rebase, approval withdrawal, or agent independence. These facts are
necessary before review can increase own trust.

Proposed qualification rules:

- only `approved` counts;
- the approval binds the exact final revision or exact final diff;
- no later unreviewed changes are included;
- withdrawn or stale approvals do not count;
- repository and merge context are bound;
- reviewer credentials resolve to a canonical actor;
- squash/rebase is modeled explicitly or rejected;
- T1 requires evidence of independence from the authoring agent.

### F-05 — Credential distinction is not person distinction

T3 compares author and reviewer identities. Without a canonical actor mapping,
one person using two keys or platform accounts can satisfy that distinction.
A signature establishes that a credential made a statement; it does not by
itself create legal liability or prove a natural person's identity.

The scheme should map credentials and platform identities to stable,
organization-scoped actor IDs, including key rotation and aliases. If that
mapping is out of scope, the claim should narrow from “two distinct humans” to
“two distinct authorized human principals under the issuer's identity
policy.” T3 must also disclaim independence, diligence, non-collusion, and
review quality.

### F-06 — Executable derivation is unsound and unsafe

The derivation rule reruns a policy command over the proposed tree and compares
the resulting output bytes. A formatting command that leaves a malicious,
already-formatted file unchanged proves only that the file is a fixed point;
it does not prove derivation from trusted inputs. A generator can also read
existing outputs, undeclared paths, ambient environment, time, or network.

The Go implementation executes `sh -c` with ambient host capabilities in a
disposable checkout; see [`derive.go`][go-derive]. The checkout protects the
repository worktree, not the verifier's host, secrets, or network.

Proposed baseline disposition: remove executable derivation from the initial
interoperable profile. A future design would require a hermetic capability
sandbox, absent outputs, exact inputs/outputs, pinned generator and toolchain
digests, controlled environment/time, no network, and comparison against
outputs generated from trusted inputs. A signed reproducible-builder
attestation is preferable to downstream execution of repository code.

### F-07 — Predicate v0.1 did not remain frozen

The [schema policy](../../schemas/README.md) freezes a predicate version upon
first emission and permits additive optional fields. Both predicate schemas
use `additionalProperties: false`, so older vendored validators reject newly
added optional fields. `from_is_adoption_boundary` was added after the first
v0.1 DSSE fixture emission.

Draft v0.3 also changed classification interpretation without recording a
specification or evaluator version in the release predicate. Identical v0.1
fields can therefore produce different levels under different draft rules.

Proposed disposition:

- preserve v0.1 bytes and historical verification behavior;
- stop extending or making new interoperability claims for v0.1;
- mint a successor predicate with specification/profile identity, stable
  repository identity, predecessor linkage, immutable resource descriptors,
  trust-root identity, and verification-time semantics;
- either ignore unknown fields, consistent with [SLSA parsing guidance][slsa-parsing],
  or mint a new URI for every closed-schema change.

## 6. Additional material findings

### F-08 — Resolver behavior and registry projection

Prerelease routing is useful but not universal enforcement:

- npm publication uses the `latest` dist-tag by default unless the publisher
  selects another tag; default installation follows `latest` ([npm
  documentation][npm-tags]);
- Go's `@latest` can choose a prerelease when no release version exists
  ([Go module reference][go-latest]);
- PEP 440 can admit a prerelease when it is the only satisfying candidate
  ([PEP 440][pep440]);
- Cargo is closer to the intended default-exclusion behavior ([Cargo
  reference][cargo-pre]).

The accurate claim is that trust prereleases often reduce accidental default
selection when paired with an ecosystem-specific publishing profile. This is
routing friction, not verification. A clean tag has no T-level and is
indistinguishable from a non-adopter unless the attestation is verified.

The PyPI projection is also non-injective: `t0.1` and `t2.1` both project to
`rc1` when iteration restarts on a level change. Rebuilding a clean package
normally changes embedded version metadata, so reproducibility does not imply
artifact-digest equality across prerelease and clean versions. Defer this
projection or use a globally monotonic projection sequence with trust retained
only in the attestation.

### F-09 — Accountability is not a portable risk variable

Principle 6 correctly says levels order accountability, not risk. The risk
equation and default decision table nevertheless use level monotonically as a
risk proxy. The relationship between accountable-human count and defects,
vulnerabilities, or incidents is the project's keystone empirical hypothesis,
not an established invariant.

Keep three dimensions separate:

1. semantic compatibility evidence and floor;
2. accountability evidence;
3. operational risk or blast-radius policy.

A named policy profile may combine them for routing. T itself must not imply
quality, security, safety, or SemVer compatibility. Provider-specific blast
scoring should remain local policy until a deterministic profile and evidence
contract exist.

### F-10 — Attestation binding, continuity, and freshness

A signed attestation proves that an issuer made a statement. Consumers must
either replay the underlying facts or explicitly trust the issuer to establish
them. The current profile does not make that trust mode sufficiently explicit.

The wire contract should also bind:

- stable repository identity, not only a tag name and commit digest;
- digest algorithm names and immutable dependency/resource digests;
- specification, evaluator, graph adapter, policy profile, trust roots, and
  verification-time semantics;
- release-attester authorization separately from source-signer authorization;
- predecessor and supersession continuity;
- an authoritative current-state or transparency mechanism where demotion
  freshness matters.

A backward supersession pointer alone cannot prevent replay of an older clean
attestation while a later demotion is hidden. Subject matching should follow
the digest-oriented [in-toto Statement model][in-toto-statement], augmented by
stable source identity.

### F-11 — Position against current SLSA Source work

The README and founding analysis characterize SLSA primarily as build
provenance. Current SLSA Source requirements also cover stable repository
identity, source-history continuity, protected references, contemporaneous
source attestations, and two-party final-revision review at Source L4; see the
[SLSA Source Track][slsa-source].

This does not remove SemVer-Trust's novelty. SemVer-Trust should consume or
extend source-provenance evidence, then contribute accountable-agent
classification, scope aggregation, dependency propagation, and release-channel
routing. Reimplementing a weaker parallel source-review protocol would reduce
interoperability and increase capture burden.

### F-12 — Conformance coverage is not yet an independent oracle

The conformance suite is valuable and green, but important checks mirror
expected intermediate classifications rather than deriving all results from
raw evidence. Derivation vectors accept inherited levels without establishing
a derivation. Invalid grammar cases mainly establish trust-regex rejection.
The positive cryptographic path is SSH-based; other normative signature
families do not have equivalent positive fixtures.

Missing adversarial coverage includes:

- root and adoption-boundary inclusivity;
- predecessor-chain skipping and conflict;
- previous-policy transition and genesis roots;
- threshold-only decision changes;
- commented, changes-requested, withdrawn, stale, and wrong-revision review;
- two credentials mapped to one actor;
- squash/rebase review capture;
- predicate-version compatibility and unknown fields;
- ecosystem projection collisions and release freshness.

Until these exist, conformance claims should be capability-scoped rather than
interpreted as validation of the entire scheme.

### F-13 — Project-state documentation drift

At the audit target, README, CONTRIBUTING, AGENTS, and the design record
disagreed about the draft version, canonical spec path, implemented artifacts,
ADR range, and existence of the Go implementation. Existing checks did not
cover those facts. Maintainer-facing drift is especially risky because it
causes future human and agent work to begin from false premises.

Disposition: synchronize the state documentation and mechanically tie its
version, artifact status, canonical path, and ADR coverage to repository facts.

## 7. Assumption register

| Assumption | Audit assessment | Treatment |
|---|---|---|
| Automated contribution volume will grow | Plausible; design remains relevant without AI-specific forecasts | Frame as scalable accountability under automation |
| Higher T predicts fewer adverse outcomes | Untested and central | Keep out of normative risk equations pending evidence |
| Evidence capture has acceptable friction | Not established end to end | Reuse source-control/SLSA evidence and measure operator burden |
| Prereleases are default-excluded | Ecosystem-dependent | Require ecosystem publishing profiles |
| Consumers will act on the signal | Untested | Build demand-side verification before expanding protocol surface |
| Credential identity approximates a person | False generally | Canonical actor mapping or narrower claims |
| Weakest-link scope distributions are useful | Plausible but unmeasured | Profile real repositories |
| Internal dependency graphs are complete | Often false | Identify adapter/profile and fail closed on unresolved edges |
| Producers report honestly | Only when independently replayed or trusted | State the trust mode and anticipate selective adoption/Goodhart effects |

## 8. Recommended disposition sequence

1. Freeze predicate v0.1 as experimental legacy; do not extend it.
2. Record an explicit threat/trust architecture covering malicious maintainers,
   compromised CI, credential compromise, repository rewrites, replay,
   equivocation, collusion, and honest implementation error.
3. Supersede release-range and policy-transition decisions with exact
   intervals, predecessor chaining, previous-policy governance, and genesis
   roots.
4. Define qualified review and canonical actor semantics.
5. Remove executable derivation from the baseline or redesign it around
   hermetic builder attestations.
6. Define one deterministic baseline decision profile, including threshold
   semantics and a strict separation between accountability and risk.
7. Consume SLSA Source or equivalent evidence for repository identity,
   continuity, and final-revision review.
8. Correct ecosystem routing claims and defer unsafe projections.
9. Mint the successor predicates after the semantic decisions stabilize.
10. Add adversarial conformance cases, then update the Go implementation and
    its vendored conformance digest.
11. Test whether accountability facts correlate with outcomes and whether
    consumers act on them before broadening policy claims.

## 9. Recommended baseline scope

Keep:

- signed source/review evidence from a defined source-provenance profile;
- canonical actor mapping;
- T0/T2/T3 accountability facts;
- T1 as an experimental corroboration fact;
- scope flooring and dependency propagation;
- one fixed demote-only decision profile;
- signed release attestations and native SemVer prerelease routing;
- same-source promotion.

Defer:

- standardized arbitrary blast scoring;
- inflation as a baseline strategy;
- executable derivation;
- PyPI projection;
- promotion evidence types without schemas;
- broad signature-family conformance claims;
- T1 as sufficient for a default clean release;
- claims that T-levels predict quality or security.

## 10. Audit verdict

The project should continue. Its core is a credible accountability-aware
release-routing design with unusually strong honesty and conformance instincts.
Draft v0.3 should not yet be frozen as a broadly interoperable,
security-relevant protocol. The path to credibility is to narrow the claim,
establish continuity and identity semantics, eliminate unsafe downstream
execution, version the wire contract honestly, and build on current source
provenance standards.

[cargo-pre]: https://doc.rust-lang.org/cargo/reference/specifying-dependencies.html
[git-ranges]: https://git-scm.com/docs/gitrevisions
[go-derive]: https://github.com/semver-trust/semver-trust-go/blob/f975d696a15d9d80f9b790ad76090515b189af85/internal/derive/derive.go#L49-L83
[go-latest]: https://go.dev/ref/mod#version-queries
[go-policy]: https://github.com/semver-trust/semver-trust-go/blob/f975d696a15d9d80f9b790ad76090515b189af85/internal/policy/parse.go#L256-L277
[go-release]: https://github.com/semver-trust/semver-trust-go/blob/f975d696a15d9d80f9b790ad76090515b189af85/cmd/semver-trust/release.go#L253-L287
[go-review]: https://github.com/semver-trust/semver-trust-go/blob/f975d696a15d9d80f9b790ad76090515b189af85/internal/verify/review.go#L13-L134
[go-verify]: https://github.com/semver-trust/semver-trust-go/blob/f975d696a15d9d80f9b790ad76090515b189af85/internal/verify/verify.go#L92-L151
[go-walk]: https://github.com/semver-trust/semver-trust-go/blob/f975d696a15d9d80f9b790ad76090515b189af85/internal/vcs/walk.go#L28-L75
[in-toto-statement]: https://github.com/in-toto/attestation/blob/main/spec/v1/statement.md
[npm-tags]: https://docs.npmjs.com/adding-dist-tags-to-packages/
[pep440]: https://peps.python.org/pep-0440/#handling-of-pre-releases
[slsa-parsing]: https://slsa.dev/spec/v1.0/provenance
[slsa-source]: https://slsa.dev/spec/v1.2/source-requirements
