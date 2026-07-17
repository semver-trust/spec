<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# SemVer-Trust: Provenance-Scoped Trust Levels for Semantic Versioning

**Draft v0.10**
**Status:** Design draft for review
**Date:** 2026-07-13
**Canonical home:** https://semver-trust.dev · https://github.com/semver-trust/spec

---

## 1. Scope and goals

This specification defines a scheme for capturing the provenance of source code changes in a git repository, aggregating that provenance into a **trust level** for a release, encoding the trust level in a [SemVer 2.0.0](https://semver.org)–compatible version string, and publishing a verifiable **release attestation** that downstream consumers and policy engines can evaluate.

The scheme exists because AI agents now author a significant share of production code, and a version number's implicit claim — "this release is a safe drop-in replacement" — is only as strong as the evidence behind it. SemVer-Trust makes that evidence explicit, cryptographically verifiable, and machine-consumable, without breaking any existing SemVer tooling.

### 1.1 Design principles

1. **A version bump is a compatibility claim; a trust level is the strength of evidence behind the claim.** The scheme never asks "who is better, humans or AI" — it asks "what evidence supports this release's claims."
2. **Trust levels measure attested accountability, not keystrokes.** Cryptography cannot distinguish a human typing from an agent running in the human's terminal under the human's key. A human signature is an accountability assertion: *"I stand behind this change as mine, or I reviewed what was produced under my name."* The scheme is honest about this rather than pretending to measure authorship it cannot verify.
3. **Weakest link, objectively scoped.** Aggregation is a floor, never an average, and scoping is derived from git diff paths (objective) rather than declared intent (gameable).
4. **Degrade honestly.** Ecosystems with less verification tooling can *prove* less, so more of their releases stay in the opt-in channel. Missing evidence lowers provable trust; it never gets waived.
5. **The git tag is canonical; the attestation is portable.** Registry version strings are lossy projections. Trust also evolves after a version string is frozen, so the living record lives in attestations, and the tag records trust *at release time*.
6. **Levels order accountability, not risk.** Trust levels rank attested human accountability, not predicted defect rates. Empirical risk assessment belongs to policy, which consumes the full evidence vector. A high-evidence T1 release may be empirically safer than a rubber-stamped T3; the levels remain true because they claim only who stands behind the change.

### 1.2 Non-goals

- **Third-party dependency trust.** External dependencies are the domain of SLSA, sigstore, and SCA tooling. Policy MAY require minimum SLSA levels for externals; this spec governs first-party code only. (See §12, Open questions.)
- **Runtime behavior guarantees.** A T3 release can still be wrong. Trust levels bound *provenance and review evidence*, not correctness.
- **Judging AI code quality.** The scheme assigns no inherent quality penalty to agent-authored code; it tracks what has and has not been independently reviewed and evidenced.

## 2. Terminology

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are to be interpreted as described in RFC 2119.

| Term | Definition |
|---|---|
| **Accepted release attestation** | A release attestation whose signature, subject, predicate, predecessor chain, and policy/trust bindings verify under the verifier's trust context. |
| **Accountable human** | A natural person whose verified identity (via signature or platform-authenticated review) is bound to a change in the role of author or reviewer. |
| **Active policy** | The policy selected by the bootstrap descriptor or accepted predecessor attestation that governs the current release interval (§5.4). |
| **Agent** | An automated system (LLM-based or otherwise) that authors or reviews code under a machine identity or under a human's identity. |
| **Attestation** | A signed [in-toto Statement](https://in-toto.io) binding a subject (commit SHA, tag, artifact digest) to a predicate (facts about provenance, review, evidence, or a release decision). |
| **Bootstrap descriptor** | Out-of-band chain-genesis trust input binding the initial policy, trust material, release-interval state, and version-ancestry state (§5.4, §7.5). |
| **Candidate policy** | The policy present at `TO`; on a recurring release it activates only after the active policy has accepted the release (§5.4). |
| **Canonical actor** | The stable policy-bound identity for one accountable person or agent after mapping credentials, platform accounts, aliases, and key rotations (§4.2, §9). |
| **Component** | A releasable unit within a repository, identified by a scope and released under a (possibly path-prefixed) tag. |
| **Derivation** | A deterministic transformation from declared input paths to declared output paths via a pinned command. |
| **Effective trust** | A component's trust level after transitive propagation through its internal dependency graph (§5.3). |
| **Evidence provider** | A pluggable, ecosystem-specific analyzer supplying compatibility proofs, coverage, or blast-radius inputs (§6). |
| **Own trust** | The trust floor over commits touching a component's scope, before propagation. |
| **Predecessor attestation** | The verifier-selected accepted chain head for the same repository and component; its `TO` anchors the next recurring interval (§5.2). |
| **Release interval** | The exact set of commits whose provenance contributes to a release, selected by inception, adoption, or recurring mode (§5.2). |
| **Scope** | A named set of repository paths defined in the policy file (§9). |
| **Target lineage** | The accepted source intervals whose changes must support the current target's trust claim; it accumulates through re-cuts and advances from unpromoted targets, and resets only after an accepted clean target or at authenticated bootstrap (§7.5). |
| **Trust channel** | The release lane implied by trust: the *clean channel* (plain version) or the *pre-release channel* (version carrying a trust identifier). |
| **Version action** | Signed release intent selecting advance, re-cut, or supersede behavior under authenticated version state (§7.5). |
| **Version predecessor** | The bootstrap-pinned legacy clean tag, or accepted predecessor decision, that supplies authenticated version state; distinct from a release-interval boundary (§7.5). |
| **Version state** | Per-component authenticated state from which the target core, trust-suffix iteration, and exact emitted tag are derived (§7.5). |

## 3. Trust model

### 3.1 Levels

A trust level is a scalar `T0`–`T3` counting **independent accountable humans** bound to a change, with one intermediate rung for agent corroboration:

| Level | Definition | Intuition |
|---|---|---|
| **T0** | No accountable human. Agent-authored (or mixed/ambiguous authorship) with no independent review. | Fully autonomous. |
| **T1** | No accountable human, but independently agent-reviewed (§3.3). | Autonomous with machine corroboration. |
| **T2** | Exactly one accountable human, in either role. | One human stands behind it. |
| **T3** | Two distinct accountable humans: canonical human author actor ≠ canonical human reviewer actor. | Authored and independently reviewed by different humans. |

Levels are an accountability ordering, not a risk ordering (Principle 6, §1.1): policy maps levels plus evidence to risk; the levels themselves claim only the count of independent accountable humans.
For T3, "distinct" means distinct canonical human actors under the issuer's
active actor policy. The level does not prove natural-person uniqueness beyond
that policy, review diligence, non-collusion, or review quality.

### 3.2 Level assignment (normative)

Per-commit levels are assigned from the full authorship × review matrix. Authorship class is determined by the commit's verified signer identity class (§4.2) combined with provenance trailers (§4.1); review class by qualified merge-time attestations (§4.3).

| Authorship | Review | Level |
|---|---|---|
| agent | none | **T0** |
| mixed / ambiguous | none | **T0** |
| agent | agent (independent) | **T1** |
| mixed / ambiguous | agent (independent) | **T1** |
| human | none | **T2** |
| human | agent (independent) | **T2** |
| agent | human | **T2** |
| mixed / ambiguous | human | **T2** |
| human | human (distinct canonical actor) | **T3** |

Notes:

- *Ambiguous* means the signer identity class and the provenance trailers conflict, or required trailers are absent under a policy that mandates them. Ambiguity MUST floor to the agent-authored row — unverifiable claims of human authorship are treated as absent.
- The self-review exclusion prevents one human from counting twice, never from counting once: a human reviewing their own *human-authored* commit adds no second human (T3 requires distinct canonical human actors), but for agent-, mixed-, or ambiguous-authored commits — where no human author is counted — a qualified human review adds the first accountable human even when the reviewer maps to the commit signer's canonical actor (agent + human = T2; spec repository ADR-025). Anything else would punish the honest `Provenance: agent` trailer: omitting it would classify the commit human-authored and reach T2 directly.
- Multiple unverified co-authors (e.g., `Co-authored-by:` trailers without signatures) do not raise a commit above T2. Only signature-verified or platform-attested identities count.
- Distinctness is evaluated on canonical actors, not raw credentials. One person using two keys, two platform accounts, or a rotated credential still counts as one accountable human when those credentials map to the same canonical actor.
- The scalar is deliberately lossy: `human + none` and `agent + human` both map to T2. Policies that need the distinction MUST consume the full **provenance vector** in the attestation (§8.1), which preserves authorship and review classes separately. The scalar exists for tag encoding and precedence; the vector exists for policy.

### 3.3 Independent agent review (T1)

An agent review qualifies as *independent* only if all of the following hold:

1. The reviewing agent runs in a separate execution context with no shared conversational or working state with the authoring agent.
2. The reviewer's canonical agent actor (§4.2) differs from the author's canonical actor.
3. The review produces a signed qualified review attestation (§4.3) with verdict `approved`, bound to the final revision or final diff that was merged, naming the commit SHA(s), reviewing agent/model, and evidence of the separate execution context.

Implementations SHOULD prefer a different model family for the reviewer. This spec makes no empirical claim that T1 review approaches human review efficacy — self-preference bias in model-reviewing-model settings is an open research question. T1 exists as a distinct rung so that policy can price it separately from both T0 and T2.
The separate-execution evidence recorded for T1 is issuer-asserted unless a
source-control or workload profile gives it stronger, independently verifiable
semantics; consumers SHOULD weight T1 corroboration accordingly.

## 4. Commit-level provenance

### 4.1 Provenance trailers

Commits SHOULD carry git trailers declaring authorship class:

```
Provenance: agent | human | mixed
Provenance-Agent: <tool>/<version>        (required when Provenance != human)
Provenance-Model: <model-identifier>      (optional)
```

Example:

```
Add idempotency keys to payment intents

Provenance: agent
Provenance-Agent: claude-code/2.8
Provenance-Model: claude-fable-5
```

Rules:

- Trailers are **self-asserted and advisory**. They refine classification but never override the signer identity class: a trailer claiming `Provenance: human` on a commit signed by a machine identity is *ambiguous* (§3.2).
- Existing `Co-authored-by:` trailers from agent tooling (e.g., Claude Code's default trailer) MUST be recognized as corroborating evidence of agent involvement but MUST NOT substitute for `Provenance:` where policy requires it.
- Client-side hooks that add trailers are a convenience. Enforcement is server-side: a pre-receive hook or CI check MUST reject commits to protected branches that lack required trailers or a valid signature, per policy.

### 4.2 Identity classes and signatures

Every commit on a protected branch MUST be signed. The **identity class** of the verified signer is the primary authorship signal:

- **Human identities:** SSH or GPG keys enrolled in an allowed-signers registry, or sigstore *gitsign* certificates whose OIDC identity maps to a person in the identity map (§9).
- **Agent identities:** machine identities — CI workload identities (e.g., OIDC tokens issued to a pipeline), bot accounts, or dedicated agent service identities — verified via sigstore keyless signing or registered machine keys. Agents operating in CI MUST commit under agent identities, never under a human's credentials.

Credential identities are evidence, not the unit of accountability. The active
policy MUST map every credential identity and every platform review account that
can affect trust to exactly one canonical actor, and the actor's class (human or
agent) is the class used by §3.2. Key rotation and account aliases are represented
by multiple credentials mapping to the same canonical actor. A verifier MUST NOT
treat two raw credentials as two accountable humans unless the active actor map
binds them to two distinct canonical human actors. An unmapped credential or
ambiguous many-actor mapping is unverifiable for trust purposes and MUST abort
when the credential is needed to classify a protected-branch commit or counted
review.

**The identity-laundering limit (normative honesty clause).** When a human runs an agent locally and commits under their own key, the scheme cannot detect it. Such commits classify as human-authored *as an accountability assertion by the signer* (Principle 2, §1.1). Organizations SHOULD state this interpretation in contributor policy, SHOULD require agents to emit provenance trailers even in local use, and MAY audit via spot review. The residual risk is accepted and documented in the threat model (§11) rather than hidden.

### 4.3 Merge-time review attestation

Review facts live outside git (platform PR approvals), so they MUST be captured into the provenance record at merge time:

1. At merge, a trusted workflow (CI or merge queue) generates an in-toto attestation with predicate type `https://semver-trust.dev/review/v0.2` whose subjects are the merged commit SHAs, recording: reviewer canonical actors and their classes (human/agent), credential identities, approval verdicts, approval state, the PR/MR reference, covered revisions, final-revision or final-diff approval binding, repository and merge-context identity, merge strategy, and the verifier profiles used. Historical `review/v0.1` attestations remain verifiable under frozen legacy semantics, but they are not sufficient for v0.10 release-conformance claims.
2. The attestation MUST be signed by the workflow's workload identity and stored per §8.2.
3. A review is **qualified** for trust classification only if all of the following hold:
   - the verdict is `approved`;
   - the reviewer credential maps under the active actor profile to exactly one canonical actor with the recorded class;
   - the approval was active at merge: not withdrawn, dismissed, stale, superseded by a later `changes_requested` verdict from the same actor, or otherwise marked ineffective by the source-control platform;
   - the approval covers the final reviewed source revision set or an explicitly recorded final diff, and any post-approval change to the source, target, conflict-resolution content, or merge result either preserves that exact approved diff under the source-control profile or requires re-approval;
   - the review attestation binds the stable repository identity, change identity, target branch or equivalent merge context, source revisions, target revision, merge strategy, result revision, evaluator profile, actor-identity profile, source-control profile, and verification instant used to make the effective-at-merge decision; and
   - for agent review, the attestation includes evidence that the reviewing agent ran in a separate execution context with no shared conversational or working state with the authoring agent (§3.3).
4. Non-qualified reviews — including comments, `changes_requested`, stale approvals, withdrawn or dismissed approvals, wrong-revision approvals, and approvals by credentials that collapse to the same canonical actor when a distinct actor is required — MUST NOT raise a commit's trust level. If policy requires such a review for a protected merge or release claim, the unmet requirement is a verification failure, not a demotion.
5. **Merge strategies:** squash and rebase merges rewrite authorship and destroy per-commit provenance. Repositories MUST either (a) forbid squash/rebase merges on protected branches, or (b) ensure the merge-time attestation records the pre-rewrite source revisions and provenance plus the deterministic source-control binding from those revisions to the result revision, so the resulting commit can be classified from attested facts. A squash or rebase approval qualifies only when the approved pre-rewrite content is exactly the content that produced the recorded result revision under the source-control profile.
6. **Merge commits themselves:** a merge commit with a non-empty diff (conflict resolution) introduces authored changes. It MUST be classified like any other commit — the resolver is its author; the review attestation covering the PR does not automatically cover novel conflict-resolution hunks unless the reviewer re-approved after resolution.

### 4.4 Generated outputs and derivation claims

The portable baseline does not define executable derivation proofs. A verifier
MUST NOT execute repository-, policy-, or producer-supplied commands to raise the
trust level of generated outputs, formatted files, lockfile rewrites, or other
mechanically produced artifacts. Such paths contribute the trust level of the
commits that changed them unless a future accepted proof profile defines a
non-ambient, reproducible, capability-bounded evidence format.

A derivation claim MAY be recorded as non-authoritative evidence for local
policy or future proof profiles, but it supplies no portable trust elevation by
itself. Re-running a command and observing byte-identical outputs is
fixed-point evidence, not derivation evidence: it does not prove the committed
outputs came from trusted inputs, that the command read only declared inputs,
that it was independent of time, environment, or network state, or that the
toolchain was uncompromised.

An attempted derivation elevation that is absent, unsupported, unverifiable, or
outside an accepted proof profile is not a waiver and not a downgrade to T0; it
is ignored for re-leveling. Ordinary weakest-link flooring still applies. This
preserves the no-de-minimis rule (§5.1): generated or formatting-only commits
are classified by their accountable authorship/review evidence like any other
commit.

## 5. Aggregation

### 5.1 Scope partitioning

The policy file (§9) maps path globs to named scopes. A commit **touches** a scope if any path in its diff matches the scope's globs. Scoping keys off diff paths — objective ground truth from git — never off declared intent, commit messages, or size heuristics. A commit touching `services/auth/**` and `docs/**` contributes its trust level to both scopes. Paths matching no scope fall into an implicit `default` scope.

For a root commit included by an inception interval, diff paths are computed
against Git's empty tree. Merge-commit conflict-resolution changes follow
§4.3.4; adoption does not retroactively assign trust to exempt parent history.

There is no *de minimis* exception: a one-line T0 commit floors its scope
exactly like a thousand-line one. Any "trivial commits don't count" rule becomes
the hiding place for a payload. Generated outputs and formatting-only commits
are not exempt under the portable baseline (§4.4).

### 5.2 Own trust (per-scope floor)

Let `Reach(X)` be the set containing commit `X` and every commit reachable
through its parents. A release resolves every supplied ref once to an immutable
commit object ID and selects exactly one **release interval**:

1. **Inception interval:** a chain-genesis release with no adoption boundary covers
   `Reach(TO)`. The equivalent Git operation is `git rev-list TO`; every
   reachable root is included.
2. **Adoption interval:** a chain-genesis release with bootstrap-pinned boundary `B`
   covers `Reach(TO) − union(Reach(p) for p in parents(B))`. The equivalent Git
   operation is `git rev-list TO --not B^@`. `B` MUST be reachable from `TO` and
   is included; only history reachable through its parents is exempt.
3. **Recurring interval:** every later source release covers
   `Reach(TO) − Reach(P)`, equivalent to `git rev-list P..TO`, where `P` is the
   resolved `TO` from the accepted predecessor attestation. `P` MUST be an
   ancestor of `TO` and MUST be the verifier-selected current chain head for the
   same repository and component. A caller-supplied alternate `FROM`, a missing
   or ambiguous head, a moved predecessor tag, a skipped chain link, or a
   non-ancestor MUST abort verification.

The commit set is normative; implementations MAY process it in any order that
records every member exactly once. Newly merged unrelated history is included
when it becomes reachable from `TO` and was not reachable from the predecessor.
When `TO = P`, the operation is a promotion or other superseding re-evaluation
of the existing source release (§7.3), not a new empty source interval. A
superseding re-evaluation preserves the source release's exact interval,
source-predecessor link, active authority, candidate state, and version target
lineage. It cannot use newly activated candidate keys to re-evaluate the
transition that enrolled them, and it does not rewrite source-predecessor links
after a later source release has advanced the chain.

Release-interval selection does not select a version predecessor. `B`, `P`, and
a legacy version tag may name the same commit, but equality does not merge their
roles: interval state answers which commits contribute trust, source continuity
answers which attestation precedes this release, and version state answers which
SemVer line and iteration are continued (§7.5, ADR-029).

For every scope touched by the selected interval:

```
own_trust(scope) = min over commits c in range, c touches scope:
                     level(c)        # per §3.2; no portable derivation elevation
```

A commit that fails signature verification, or whose required attestations
cannot be located and verified, has no level: verification of the release MUST
fail (§10). Unverifiable is not T0 — T0 is a verified fact about a verified
commit.

**Adoption boundary (optional).** A repository whose earliest history predates
the scheme — or is otherwise unverifiable — MAY establish one boundary in its
out-of-band bootstrap descriptor (§5.4). The resolved boundary object ID is
immutable chain-genesis state. It is **included** in the verified interval,
**disclosed** in the release attestation, and **exempt, never laundered** only
for its parent history: pre-boundary commits contribute no trust level and are
reported as outside the verified region, never as T0. A legacy
`[policy] adoption_boundary` value MAY mirror the bootstrap value but MUST match
it and has no authority to move it. See ADR-027, superseding ADR-026.

### 5.3 Transitive propagation (effective trust)

Scopes are not independent: components consume other components inside the same workspace. Effective trust propagates as a floor over the internal dependency graph:

```
effective(C) = min( own_trust(C),
                    min over internal deps D of C: effective(D) )
```

- The graph comes from a **graph adapter** for the workspace tooling (Go module graph / `go list`, pnpm or npm workspaces, Cargo workspace metadata, Bazel query, etc.).
- Dependency **cycles** collapse to their strongly connected component: every member of an SCC shares the SCC's minimum own-trust.
- The dependency is evaluated **at the version/tree actually consumed** by the release being cut. A release attestation MUST pin which internal dependency versions (or tree states) its effective trust was computed against (§8.1).
- Propagation is what makes path scoping safe rather than cosmetic. Without it, risk launders into shared libraries while consumers' scopes stay pristine — the same failure mode dependency scanners had before transitive analysis. It also concentrates the incentive correctly: shared packages are where human review buys the most trust, because their level multiplies across every consumer.
- External (third-party) dependencies are out of scope for effective-trust computation (§1.2); policy MAY impose separate requirements on them.

### 5.4 Meta-paths and policy transitions

The policy file, scope map, derivation metadata, identity map, trust material, and
workflows that generate attestations can reclassify anything. A candidate policy
at `TO` therefore MUST NOT authorize its own transition.

The verifier selects the **active policy** and role-separated trust material
from one of two authorities:

- **Chain genesis:** an out-of-band bootstrap descriptor binds the repository
  and component; interval mode and boundary when applicable; canonical tag
  prefix and version predecessor or explicit version genesis (§7.5); policy
  path and digest; non-removable meta paths for attestation-generating
  workflows; trust-material digests; verification profile; and injected-clock
  semantics. The verifier MUST authenticate the descriptor from local
  configuration or a signature under a verifier-pinned bootstrap authority;
  repository-controlled bytes alone do not establish it. The policy at `TO`
  and all supplied trust bytes MUST match these pins exactly.
- **Recurring release:** the accepted predecessor attestation binds the active
  policy path/digest, mandatory workflow meta paths, trust-material digests,
  verification profile, and authenticated version state (§7.5). This active
  state governs every commit in the new interval. The final policy at `TO` is
  the **candidate policy** and activates only after the release succeeds;
  intermediate policy versions do not activate mid-interval.

The bootstrap descriptor also pins the chain's clock profile, which every
accepted attestation carries forward. The profile defines the instant's source
and its validity/freshness semantics. Each verification MUST receive an
explicit verifier-supplied instant under that profile and MUST record the
instant in its release attestation. A candidate-supplied timestamp is evidence,
not clock authority; implicit wall-clock reads and ambient trust roots are not
verification authority.

Release continuity, policy activation, and version state are component-chain
state. In a monorepo, accepting a candidate policy or version transition for
component `A` does not activate it for component `B`; `B` continues under its
own accepted predecessor until its chain crosses the transition. Shared-key
rotations therefore retain the old roots until every relevant component chain
has transitioned.

The active policy's identity registries and required meta level apply to every
commit touching either policy path, either policy's declared meta paths, the
authority's mandatory workflow paths, or repository-local trust material
referenced by either policy. Candidate-only keys cannot authorize their own
enrollment. A candidate policy MUST retain the chain policy path, cover its own
path, the authority's mandatory workflow paths, and repository-local trust
material in its meta paths, set a meta required level no lower than the active
level, and match the immutable adoption boundary when a legacy mirror is
present.

Therefore:

- The policy path and every repository-local trust-material path are implicit
  meta-paths even if a glob omits them. The candidate must also cover every
  workflow path pinned by chain authority; any omission makes it invalid.
- Commits touching the union of active and candidate meta-paths MUST meet the
  active required level, regardless of which scope they otherwise fall in, and
  SHOULD additionally require review by designated owners.
- An unknown active signer, mismatched trust digest, uncovered mandatory path,
  lowered meta level, moved boundary, or under-level meta-path commit MUST fail
  verification outright — not demote, fail.
- A valid key rotation is two-stage: old roots authorize the transition; new
  roots become usable only after an accepted release activates the candidate.

Repository paths supplied explicitly to a verifier are byte locators only; they
MUST match the bootstrap/predecessor digests and never override them. See
ADR-028, superseding ADR-007.

## 6. Release evaluation

A release decision consumes three separate input families and applies the active
policy:

- **Compatibility evidence** — determines the semantic floor, the *minimum*
  bump the change semantics permit (§6.1).
- **Accountability evidence** — supplies the effective trust level and is
  compared to the active policy's clean-channel threshold (§6.2). A trust level
  is not a quality, security, safety, or compatibility score.
- **Operational policy evidence** — supplies blast score and any supporting
  provider facts the active policy chooses to consider (§6.2).

The baseline decision function is deterministic:

1. Compute the effective bump as the maximum of the claimed bump, semantic
   floor, and any pending corrective bump from authenticated version state.
2. Apply the accountability threshold. If `effective_trust < threshold`, the
   clean channel is unavailable regardless of blast score or compatibility
   evidence.
3. If the threshold is met, evaluate the baseline blast/differ table (§6.4).
4. Render the result through the selected enforcement strategy (§6.3): `demote`
   uses the pre-release channel when the clean claim is unavailable; `inflate`
   escalates the bump instead.

The resulting effective bump and channel are applied to verifier-selected
version state (§7.5). The producer may propose a signed version action and
claimed bump, but it does not supply the prior version, tag prefix, or
trust-suffix iteration. For re-cuts, supersessions, and advances from
unpromoted targets, effective trust, blast, and compatibility evidence apply to
the complete target lineage (§7.5), not only the newest source interval.

### 6.1 Semantic floor

Determined by the strongest available compatibility evidence, in order of preference:

1. **Compatibility differ** (evidence provider): `apidiff` (Go), `cargo-semver-checks` (Rust), `japicmp` (Java), API Extractor (TypeScript), etc. A detected breaking change in the public surface forces MAJOR. No trust level overrides the semantic floor — T3 code that breaks the API is still a MAJOR release.
2. **Declared intent**: Conventional Commits (`feat:` → MINOR, `fix:` → PATCH, `!`/`BREAKING CHANGE:` → MAJOR) where no differ exists. Declared intent is weak evidence and interacts with §6.2 accordingly.

### 6.2 Accountability threshold and blast radius

The active policy's `threshold` is the minimum effective trust level eligible
for the clean channel. The draft v0.10 baseline threshold is `T2`: before
empirical validation of T1 efficacy (§12.1), independently agent-reviewed code
does not satisfy the portable baseline clean profile. Policies MAY choose a
different threshold, but any conformance claim MUST identify the threshold used.

To *claim* a bump is to claim what it implies (PATCH: drop-in safe; MINOR:
additive only). Once the accountability threshold is met, the claim must also be
supported by compatibility and operational-policy evidence appropriate to the
blast score.

**Blast-radius inputs** (pluggable; core inputs are language-agnostic, starred inputs come from evidence providers):

| Input | Source |
|---|---|
| Changed lines / files / churn concentration | git (universal) |
| Scope criticality weight | policy file (universal) |
| Dependency manifest changes (`go.mod`, `package.json`, `Cargo.toml`, lockfiles) | git (universal) |
| Public-surface delta * | compatibility differ |
| Import-graph fan-in of touched packages * | language adapter |
| Test coverage on changed lines * | coverage provider |

Implementations map these to a qualitative score (`low` / `moderate` / `high`).
This spec deliberately does not define a numeric formula; false precision here
invites gaming. A blast score is portable across implementations only when a
named, versioned blast-scoring profile defines the mapping. Otherwise the score
is local policy input: it may be recorded and consumed by that policy, but it is
not a cross-implementation conformance claim. The score, its inputs, provider
versions, and scoring profile identity (or an explicit local-policy marker) MUST
all appear in the release attestation.

### 6.3 Enforcement strategies

When the threshold gate or baseline blast/differ table does not support the
clean claim, policy selects one strategy:

- **`demote` (RECOMMENDED):** keep the semantically correct bump but confine the release to the pre-release channel (§7) until evidence accumulates — post-hoc human review, canary/soak results, audit. Preserves the API-compatibility meaning of MAJOR/MINOR/PATCH; consumers opt in explicitly.
- **`inflate`:** escalate the bump (PATCH→MINOR or →MAJOR) so default-range consumers do not auto-adopt. Supported because some organizations want risk expressed in the precedence-relevant part of the version; costs include diluting MAJOR's "your code must change" signal and forcing migration review where no API changed.

### 6.4 Baseline decision table

This table is the portable baseline decision profile after the threshold gate
in §6.2 has succeeded. It is deterministic for a supplied threshold, effective
trust, blast score, strategy, differ availability, claimed bump, and semantic
floor. Provider-specific blast scoring is outside baseline conformance unless a
versioned blast-scoring profile is named.

Channel for the *clean* (plain-version) release; anything else goes to the
pre-release channel under `demote`, or bumps under `inflate`:

| Effective trust | Blast: low | moderate | high |
|---|---|---|---|
| **T3** | clean | clean | clean, differ proof REQUIRED for PATCH claim |
| **T2** | clean | clean, differ proof required for PATCH claim | pre-release |
| **T1** | pre-release | pre-release | pre-release |
| **T0** | pre-release | pre-release | pre-release |

Where no compatibility differ exists for the ecosystem, cells reading "differ proof required" resolve to **pre-release** — the honest-degradation principle (§1.1): less verification tooling means lower provable trust, not equal trust with less backing.

## 7. Version encoding

### 7.1 Canonical tag grammar

```
trust-ident   = "t" level                      ; level = "0" / "1" / "2" / "3"
trust-suffix  = trust-ident "." iteration      ; iteration = SemVer numeric identifier, starts at 1
trust-version = core-version "-" trust-suffix  ; core-version = MAJOR.MINOR.PATCH
tag           = [component-path "/"] "v" (core-version / trust-version)
```

Examples: `v1.4.0-t1.1`, `auth/v2.0.0-t0.3`, `pkg/common/v0.9.0` (clean).

- The trust identifier occupies SemVer pre-release position, so
  `v1.4.0-t1.1 < v1.4.0` by SemVer precedence. This provides native ordering
  friction, not a complete verification or routing guarantee: dependency
  resolvers differ, registries expose additional tag/channel controls, and a
  clean version carries no visible trust level unless the consumer verifies the
  release attestation. Producers and consumers MUST apply an ecosystem
  publishing profile (§7.4) before claiming default-resolution behavior.
- Levels are a fixed single digit. (Lexical ASCII comparison of alphanumeric identifiers would order `t10 < t2`; capping at one digit forecloses the hazard.)
- Component paths follow the ecosystem's nested-tag convention where one exists (Go nested modules use exactly this `dir/vX.Y.Z` prefix form).
- **The trust-shaped namespace is reserved.** A pre-release whose first dot-separated identifier matches the trust shape — `t` immediately followed by a level digit — is reserved for this scheme. A well-formed trust suffix is a trust version; a trust-shaped identifier that does *not* satisfy the grammar (a two-digit level, a missing or zero iteration, or a level outside `0`–`3` — e.g. `t10.1`, `t1`, `t1.0`, `t4.1`) is **invalid and MUST be rejected**, never reinterpreted as an ordinary pre-release. Reinterpreting a malformed trust identifier as a plain pre-release would both silently discard intended trust information and open a spoofing surface — a tag that reads as a trust encoding to a human while carrying no verified meaning — so parsing fails closed, exactly as the conformance grammar vectors require. Non-trust pre-releases (`rc.1`, `alpha`, …) carry no trust information and are unaffected: they remain ordinary pre-releases with the trust suffix simply absent.

### 7.2 Precedence interactions and the rc question

SemVer compares dot-separated pre-release identifiers left to right, ASCII-lexically for alphanumerics; numerics sort below alphanumerics. Consequences worth pinning:

- `v1.4.0-rc.1 < v1.4.0-t1.1 < v1.4.0` (`"rc" < "t1"`). A trust-gated release outranks an rc among pre-releases.
- This spec's position: **the trust channel generalizes the rc pattern.** An rc's traditional job — publish, soak, gather evidence, promote — is precisely the trust-promotion lane. Projects adopting SemVer-Trust SHOULD NOT combine `rc`-style identifiers and trust identifiers on the same version; a below-threshold release *is* the release candidate, with the trust level stating *why* it is not yet clean.
- Iteration (`.2`, `.3`) is derived from the accepted version-decision lineage
  (§7.5): a re-cut at the same core version and level increments that level's
  prior maximum; the first cut at a different level starts at one (`-t0.1` →
  fixes reviewed → `-t2.1`). A producer never supplies the iteration.

### 7.3 Promotion

Promotion moves a release from the pre-release channel to the clean channel **without changing its source**:

1. New evidence is attested (human review attestation, soak/canary evidence, audit) against the same commit SHA.
2. The verifier recomputes effective trust across the preserved target lineage
   and applies the decision table while preserving the authenticated version
   target (§7.5); if the release now
   qualifies and source continuity has not advanced, the clean tag (`v1.4.0`)
   is created **on the identical SHA**, with a fresh release attestation citing
   the promotion evidence and superseding the prior decision. A later
   re-evaluation is attestation-only (§7.5).
3. **Immutable registries:** git and Go modules tolerate two tags on one
   commit, but package artifacts commonly bake the version string into package
   metadata, so promotion in immutable artifact registries means
   *republication from the identical source SHA*. A project MAY additionally
   promise byte-identical artifacts only when its build profile makes the
   version string external to the artifact or otherwise proves reproducibility
   across promotion. Otherwise each artifact carries its own attestation bound
   to the same source SHA, and the source binding — not artifact-digest
   equality — is the portable promotion guarantee.
4. **Cascade:** promotion of a dependency MAY trigger re-evaluation of downstream components whose effective trust was floored by it (their attestations pin the dependency, §5.3, making affected components discoverable). Downstream promotion follows the same rule: same SHA, new attestation. This resolves the "auth is stuck in pre-release because pkg/common was T0" case without rebuilding auth.
5. Demotion (evidence invalidated, e.g., a review attestation revoked) cannot un-publish a clean version; it is expressed by publishing a superseding attestation and, where warranted, a security advisory. This is the standing reason the attestation, not the tag, is the living record (§1.1, Principle 5).

### 7.4 Ecosystem publishing profiles

The git tag is canonical; registries receive ecosystem-specific publishing
profiles. A profile constrains only routing and publication behavior. It is not
trust verification: portable consumers verify the accepted release attestation,
predicate contract, source binding, predecessor chain, policy/trust bindings,
and any current-state/freshness mechanism their policy requires.

| Ecosystem | Profile | Notes |
|---|---|---|
| Go modules | native tag | Pre-release identifiers pass through and release versions are preferred for version queries. Caveat: `latest` selects the highest pre-release when no release version exists for the module path, so a trust pre-release is not universally hidden from default queries. Build metadata is not a portable trust carrier: the go command canonicalizes versions and removes build metadata except special suffixes such as `+incompatible`. Nested-module tags align with component paths. |
| npm | native version plus explicit dist-tags | `1.4.0-t1.1` is a valid npm version, and npm semver range matching excludes prereleases by default unless the comparator opts into the same core's prerelease set. Publication MUST NOT leave a trust pre-release on the `latest` dist-tag unless the producer intentionally wants ordinary `npm install <pkg>` consumers to receive it; `npm publish --tag <non-latest>` or an equivalent registry operation is required. A dedicated tag such as `trust-t1` MAY make explicit opt-in ergonomic. |
| Cargo | native version | Cargo dependency requirements and `cargo install` avoid pre-releases unless explicitly requested. Cargo may then upgrade a prerelease dependency to a semver-compatible released version, which matches the promotion path. |
| Python/PyPI | deferred baseline | PEP 440 cannot publish `1.4.0-t1.1`; it also allows prereleases when they are already installed, explicitly requested, or the only satisfying available candidate. The earlier `rc<iteration>` projection is not injective when trust level changes restart SemVer-Trust iterations, so the portable baseline defines no PyPI projection. A future Python profile MUST either use a globally monotonic projection sequence per core version with trust detail only in the attestation, or define another injective mapping before making publishing claims. |

The Python/PyPI row is the existence proof for Principle 5: any consumer logic
that depends on parsing trust out of a registry version string is non-portable;
portable consumers verify attestations.

### 7.5 Authenticated version ancestry

The exact release tag is derived from per-component authenticated **version
state**, never from a caller-selected `current_version`, `FROM`, or iteration.
The release interval (§5.2) and version ancestry are independent.

At chain genesis, the authenticated bootstrap descriptor binds a canonical tag
prefix and exactly one of:

1. `version_predecessor: null`, explicitly starting a new version line. The
   synthetic clean baseline is `v0.0.0`; it names no Git object and makes no
   claim that historical tags are absent.
2. One version-predecessor descriptor containing a canonical clean §7.1 tag,
   its raw Git ref-target object ID, and its peeled commit object ID. The prefix
   MUST equal the chain's tag prefix. For inception, the predecessor commit MUST
   be an ancestor of or equal to `TO`. For adoption, it MUST be an ancestor of
   or equal to `B`; it may therefore precede the first verified commit without
   laundering exempt history. Implementations use
   `git merge-base --is-ancestor V TO` or
   `git merge-base --is-ancestor V B`, respectively.

The descriptor, not repository tag discovery, selects the genesis predecessor.
For a non-null selection, a missing or malformed tag, zero or multiple
descriptors, prefix/component mismatch, changed raw ref target, changed peeled
commit, or failed ancestry check MUST abort. Null genesis MUST be explicit and
authenticated; it is never inferred from failed discovery. Tooling MAY propose
a descriptor for explicit maintainer approval but MUST NOT silently select the
highest or nearest tag.

A chain-genesis release MUST use the advance action.

Every accepted release decision carries forward the tag prefix; target baseline,
represented by synthetic genesis or an authenticated canonical tag with
raw/peeled object IDs and source identity; current target core and bump; whether
the clean target has been accepted; current accepted decision and immutable tag
anchoring its decision lineage; accepted source-interval identities accumulated
for the current trust claim; accepted per-level trust iterations; and an
explicit pending corrective bump greater than the target bump, or its absence.
An attestation-only decision retains the prior immutable tag while becoming the
current accepted decision. The accepted predecessor supplies this state for
recurrence. Applying the bound target bump to the baseline core MUST produce the
target core exactly.

The producer MUST NOT supply an aggregate target trust level. The verifier
derives it from the complete bound target lineage and authenticated evidence.

At adoption genesis, compatibility evidence may span from a legacy version
predecessor before `B`, but the target trust lineage starts with the verified
adoption interval. Exempt history remains disclosed and receives no trust level.

A release proposes one signed **version action**:

- **Advance:** apply the effective bump (the greater of claimed bump, semantic
  floor, and any pending corrective bump) to the predecessor target core, or to
  `0.0.0` at explicit genesis, establishing a new target. Its target baseline
  becomes the bootstrap-pinned legacy predecessor or immutable lineage tag and
  source identity bound by the prior accepted decision, or synthetic genesis on
  the first release. At bootstrap, or when the predecessor target has an accepted
  clean tag, the new target lineage contains the current source interval only.
  When advancing from an unpromoted target, it appends the current interval to
  the predecessor's target lineage so skipped prereleases cannot launder trust.
  The resulting target bump is that effective bump. Advance clears the
  correction. If the result is a trust prerelease, its iteration is one for that
  level.
- **Re-cut:** preserve an unpromoted target core while source changes are added.
  The clean target MUST NOT already have been accepted. Compatibility evidence
  from the target's bound baseline source through the new `TO` MUST be
  recomputed; the baseline may itself be a trust prerelease. For synthetic
  genesis, evidence covers the complete inception history through the new `TO`.
  The current source interval is appended to the target lineage. Effective trust
  and blast are recomputed across every contributing interval, with each commit
  governed by the active authority bound to its original interval; a high-trust
  fix interval cannot erase an earlier low-trust contribution. If the semantic
  floor exceeds the target's bound bump, verification aborts and the release
  must advance to a sufficient target. A trust result's iteration is one greater
  than the highest accepted iteration for that target and level in the selected
  version-decision lineage. A pending corrective bump prohibits re-cut.
- **Supersede:** preserve `TO`, interval, target lineage, baseline, and target
  core while evidence changes. Promotion emits the unoccupied clean target;
  another trust decision derives its iteration as above. Demotion of an accepted
  clean release is attestation-only and does not mutate its tag. Compatibility
  evidence is recomputed from the bound target baseline; if its effective bump
  exceeds the bound target bump, the semantic invalidation is also
  attestation-only because no new tag can repair an immutable under-bumped
  release. If that decision is still the source head, resulting state binds the
  effective bump as a pending corrective floor. A later same-head supersession
  clears it only if recomputed evidence no longer exceeds the target bump. After
  a later source release has advanced continuity, every supersession of the
  older decision is attestation-only: it emits no tag, consumes no iteration,
  and cannot rewrite or become authority for the successor's already-bound
  version state.

The version action and claimed bump are candidate decision facts and MUST be
bound by the accepted attestation. They do not authorize alternate prior state.
Any compatibility input asserting a version predecessor, current version, or
iteration MUST equal the authenticated/derived value or verification aborts.

Before emission, the verifier derives the exact tag from the bound prefix,
target core, decision channel, effective trust level, and derived iteration. If
that tag name already exists, new emission MUST abort; tags are never moved or
overwritten. The release attestation binds both prior and resulting version
state. See ADR-029.

## 8. Attestation

### 8.1 Release attestation predicate

Release attestations are in-toto Statements
(`https://in-toto.io/Statement/v1`). Subjects bind the tag name to the commit
SHA (and artifact digests where applicable). The following is a historical v0.1
example; its emitted schema and interpretation remain frozen:

```json
{
  "_type": "https://in-toto.io/Statement/v1",
  "subject": [
    { "name": "auth/v1.4.0-t1.1", "digest": { "gitCommit": "8c1f2e…" } }
  ],
  "predicateType": "https://semver-trust.dev/release/v0.1",
  "predicate": {
    "component": "auth",
    "range": { "from": "auth/v1.3.2", "to": "8c1f2e…", "from_is_adoption_boundary": false },
    "trust": {
      "effective": "T1",
      "own": "T3",
      "floor_source": { "component": "common", "version": "v0.9.0-t0.3" },
      "dependencies_pinned": [ { "component": "common", "version": "v0.9.0-t0.3" } ]
    },
    "commits": [
      {
        "sha": "…",
        "level": "T3",
        "authorship": { "class": "human", "identity": "alice@…", "trailers": { "Provenance": "human" } },
        "review": { "class": "human", "identity": "bob@…", "attestation": "<ref>" },
        "derivations": []
      }
    ],
    "evidence": {
      "compat": { "provider": "apidiff@v0.x", "result": "compatible" },
      "coverage_changed_lines": 0.82,
      "blast_radius": { "loc": 431, "files": 12, "fan_in": "high", "score": "moderate", "inputs": { } }
    },
    "decision": {
      "claimed_bump": "minor",
      "semantic_floor": "minor",
      "strategy": "demote",
      "channel": "prerelease",
      "policy": { "path": ".semver-trust/policy.toml", "digest": "sha256:…" },
      "supersedes": null
    },
    "timestamp": "2026-07-02T00:00:00Z"
  }
}
```

Across predicate versions, the **provenance vector** (per-commit authorship and
review classes) MUST be preserved even though the tag carries only the scalar
level (§3.2), and `supersedes` links promotion/demotion decisions.

The successor release predicate type is `https://semver-trust.dev/release/v0.2`.
It is the first release predicate allowed to claim v0.10/v0.9/v0.8/v0.7/v0.6/v0.5/v0.4 trust-chain
conformance. Its schema is `schemas/release-v0.2.json`; the matching review
successor is `https://semver-trust.dev/review/v0.2`.

A v0.10 release attestation MUST additionally bind the interval mode and resolved
`TO`; the resolved adoption boundary for adoption mode; the cryptographic
identity of the accepted predecessor attestation for recurring mode; the active
policy and role-separated trust-material digests that evaluated the interval;
the candidate policy and trust-material digests activated for the next interval;
the authority-pinned mandatory workflow paths; the verification and clock
profiles plus injected verification instant; the version action, genesis marker
or predecessor, prior and resulting version-state identities, exact emitted tag
or explicit no-emission marker, immutable lineage tag raw/peeled object IDs, and
derived iteration where applicable; the target lineage's accepted interval
identities and aggregate evidence; and the bootstrap descriptor or predecessor
that selected the active state. The release decision binding includes the
claimed bump, semantic floor, accountability threshold, strategy, channel,
ecosystem publishing profile when a registry projection is claimed, and
supersession identity.
When external source evidence is consumed, the predicate MUST also bind the
source evidence profile and evidence identities as described in §8.3.
Predicate v0.1 cannot express those continuity claims and MUST NOT be used to
claim v0.10/v0.9/v0.8/v0.7/v0.6/v0.5/v0.4 release conformance. This draft does not change existing v0.1 bytes
or fixture expectations and assigns them no v0.4 continuity meaning. Because
v0.1 did not encode its evaluator/specification profile, v0.2 successor
attestations MUST bind explicit specification, predicate, evaluator,
repository-identity, graph, policy, actor-identity where applicable, and
verification-time profiles. Successor schemas are closed except for declared
extension maps; any change that alters validation or interpretation requires a
new predicate URI and schema. Version-state identities in `release/v0.2` carry a digest plus a
canonicalization profile. That profile is `semver-trust-version-state-json`
(ADR-036): the accepted, carried-forward version state serialized with RFC 8785
(JSON Canonicalization Scheme) and hashed with SHA-256, each state binding its
predecessor's digest as a hash-chain link. Emitters MUST produce, and verifiers
MUST reproduce, this digest from the authenticated version state; a mismatch
aborts.

Migration from v0.1 establishes a new authenticated v0.10 chain genesis. The
bootstrap descriptor MAY independently pin a selected legacy `TO` as an included
adoption boundary and a canonical clean legacy tag as a version predecessor when
each satisfies §5.2 and §7.5. Neither binding implies the other: the version
predecessor may precede a later adoption boundary. A v0.1 attestation may be
retained as historical evidence but cannot serve as recurring authority because
it does not bind the active/candidate policy, trust, and version state.

### 8.2 Storage and verification of attestations

- Attestations MUST be signed (sigstore keyless with a transparency log entry, or organization-managed keys).
- Storage options: a git ref namespace (e.g., `refs/attestations/*`), an OCI registry (attestation-as-artifact), or a transparency-log-backed store (Rekor). Git notes are acceptable for convenience but are mutable and not fetched or protected by default — **storage integrity is never the trust anchor; the signature inside the attestation is.** Verifiers MUST validate signatures and subject digests regardless of where the attestation was fetched from.
- Review attestations (§4.3), non-authoritative derivation metadata (§4.4),
  promotion evidence (§7.3), and release attestations (§8.1) share the storage
  and signing requirements.

### 8.3 Source evidence profiles and SLSA Source integration

SemVer-Trust may consume source-control evidence produced by another profile,
including SLSA Source. SLSA Source v1.2 defines cross-system Source
Verification Summary Attestations (Source VSAs), while leaving detailed Source
Provenance formats to source-control systems because those systems differ in
their workflows and evidence. SemVer-Trust therefore consumes SLSA Source as a
profiled evidence input, not as a replacement for this specification's
accountability, policy, version-ancestry, or release-decision rules.

A **source evidence profile** MUST name:

1. the source-control system or VSA issuer identity trusted for the profile;
2. the accepted verification mode: `replay` or `trusted_issuer`;
3. the repository identity canonicalization and resource URI matching rules;
4. the source-revision digest algorithms and subject matching rules;
5. the protected-reference, history-continuity, and source-review facts the
   profile imports, and which SemVer-Trust fields consume them;
6. the issuer authorization roots and purpose binding for source-evidence
   attestations;
7. the clock profile, evidence freshness rule, and verification instant; and
8. the current-state or transparency mechanism used to detect hidden
   successors, demotions, or equivocation when the policy requires freshness.

In `replay` mode, the verifier validates the underlying source provenance and
derives the imported facts itself. In `trusted_issuer` mode, the verifier
validates a Source VSA or equivalent summary from an explicitly trusted issuer
and accepts only the claims that the source evidence profile authorizes that
issuer to summarize. A signature proves only that an issuer made a statement;
it does not prove the statement's underlying facts unless the verifier either
replays those facts or deliberately trusts that issuer for those facts.

Subject and resource matching fail closed. A source-evidence attestation applies
only when:

- its repository resource URI canonicalizes to the release attestation's
  repository identity under the bound repository-identity profile;
- its subject digest identifies the same immutable source revision as the
  release interval's resolved `TO` or an explicitly named source revision in the
  evaluated target lineage;
- its digest algorithm is permitted by the source evidence profile for that VCS;
- any named references used for policy decisions are fully qualified and bound
  to the matched revision at the verification instant; and
- the attestation issuer is authorized for the source-evidence purpose under
  injected trust material selected by bootstrap or accepted predecessor state.

SemVer-Trust treats the following as directly reusable source facts when the
profile supplies them with the bindings above: stable repository identity,
immutable source-revision identity, protected named-reference membership,
history continuity from a declared start revision, contemporaneous
source-provenance generation, and final-revision/final-diff review evidence.
SemVer-Trust remains responsible for canonical actor mapping, accountable-human
counting, agent-independence semantics, scope flooring, propagation,
compatibility and blast policy, threshold decisions, release intervals, policy
transition, authenticated version ancestry, and supersession continuity.

A v0.2 release predicate that uses external source evidence MUST bind the
source evidence profile and evidence identities through the declared
`predicate.extensions` map. Because `release/v0.2` has emitted bytes, changing
its closed schema to require new top-level fields would require a new predicate
URI. The extension binding is sufficient only when the profile identity,
evidence digests, issuer roots, verification mode, and freshness/current-state
mechanism are all present and covered by the signed predicate.

If freshness matters to the release policy — for example, when a hidden
superseding demotion would change an accepted release decision — the source
evidence profile MUST define an authoritative current-state check or
transparency proof. Absent that proof, verification is relative to the
verifier-supplied accepted evidence set and MUST NOT claim globally latest
state. Conflicting accepted source-evidence statements for the same repository,
revision, profile, and verification instant are equivocation and MUST abort
unless the profile defines a deterministic conflict-resolution rule.

## 9. Policy file

The policy file is TOML, lives in the repository, and is itself a meta-path (§5.4). Reference example:

```toml
[policy]
version   = "0.1"
threshold = "T2"        # minimum effective trust for the clean channel
strategy  = "demote"    # "demote" (recommended) | "inflate"
# adoption boundary is immutable bootstrap state (§5.2), not mutable policy

[scopes]
"services/auth/**"    = "auth"
"services/billing/**" = "billing"
"pkg/**"              = "common"
"docs/**"             = "docs"
# unmatched paths -> implicit "default" scope

[scopes.weights]      # blast-radius criticality (low|moderate|high|critical)
auth    = "critical"
common  = "critical"
billing = "high"
docs    = "low"

[meta]
paths          = [".semver-trust/**", ".github/workflows/**", "CODEOWNERS"]
required_level = "T3"

[derivation]
# Non-authoritative metadata only in the portable baseline (§4.4). A future
# proof profile may define executable or non-executable derivation evidence, but
# this policy cannot make verifier command execution part of baseline trust.
profile = "none"

[identity]
# registry of keys trusted to sign review/release attestations — SSHSIG over the
# DSSE PAE (§4.3, §8.2, ADR-022); ssh allowed-signers format. Optional.
attestation_signers = ".semver-trust/attestation_signers"

[identity.human]
allowed_signers = ".semver-trust/allowed_signers"   # ssh allowed-signers format
gpg_keyring     = ".semver-trust/gpg-keyring.asc"   # armored OpenPGP public keyring (optional)
oidc_issuers    = ["https://accounts.example.com"]  # gitsign identities mapped to people

[identity.agent]
oidc_issuers     = ["https://token.actions.githubusercontent.com"]
subject_patterns = ["repo:acme/platform:*"]
bot_accounts     = ["release-bot@acme.dev"]

[identity.actor.alice]
class       = "human"
credentials = ["ssh:SHA256:alice-old", "ssh:SHA256:alice-current"]
accounts    = ["github:alice", "github:alice-work"]

[identity.actor.review-bot]
class       = "agent"
credentials = ["oidc:repo:acme/platform:environment:review"]
accounts    = ["github:acme-review-bot"]

[trailers]
require = true          # commits on protected branches must carry Provenance:

[graph]
adapter = "gomod"       # gomod | pnpm | cargo | bazel | none

[evidence.go]
compat                      = "apidiff"
coverage_min_changed_lines  = 0.70

[registry.npm]
dist_tag_prefix = "trust-"
```

`[identity.actor.<id>]` entries define the canonical actor map used by §3.2 and
§4.3. A credential or platform account MAY appear in only one actor entry in the
active policy. Multiple credentials under one actor represent aliases or key
rotation, not multiple accountable humans.

`[identity.human] gpg_keyring` is optional and names an armored OpenPGP public
keyring for GPG-signed commits — the OpenPGP counterpart to the SSH
`allowed_signers` registry. `[identity] attestation_signers` is optional and
names the registry of keys trusted to sign review and release attestations
(SSHSIG over the DSSE PAE, §4.3, §8.2). These paths locate repository bytes;
their digests and roles come from the bootstrap descriptor or accepted
predecessor and MUST match (§5.4). An explicitly supplied path MAY locate the
same pinned bytes but MUST NOT override their digest or role.

The policy at `TO` is a candidate on recurring releases. The active predecessor
policy evaluates the complete interval; only an accepted release activates the
candidate for the next interval. A legacy `[policy] adoption_boundary` MAY be
parsed for backward compatibility but is not authoritative in v0.4 and MUST
match the bootstrap descriptor (§5.2).

## 10. Verification algorithm (normative)

Given a component `C`, proposed release commit `TO`, and exactly one
verifier-selected chain authority — a bootstrap descriptor for chain genesis,
an accepted predecessor attestation for a recurring release, or an accepted
decision selected for superseding re-evaluation:

1. **Resolve immutable inputs:** resolve `TO` and every named boundary/tag once.
   Record raw ref-target object IDs and peeled commit object IDs separately;
   later ref movement or recreation is a verification failure.
2. **Select active authority:** validate the bootstrap descriptor or the
   predecessor's signature and complete chain. For a predecessor, require the
   same repository and component, the unique accepted chain head, and an
   ancestor `P`. Load active policy/trust bytes and require every digest and role
   to match the authority. Require an explicit verifier-supplied verification
   instant under the authority's pinned clock profile (§5.4). Select the
   component's tag prefix and version state from the bootstrap descriptor or
   accepted predecessor, validate §7.5 ancestry/ref bindings, and reject any
   caller-selected version predecessor, `current_version`, or iteration.
3. **Enumerate the release interval** using the inception, adoption, or recurring
   reachability set in §5.2. No caller-selected alternate `FROM` is accepted.
4. **Load the candidate policy** from `TO`; record its digest and referenced
   trust-material digests. On bootstrap it MUST equal the pinned active policy.
   On recurrence, validate its mandatory policy/trust/workflow meta coverage,
   non-decreasing meta level, policy path, and immutable boundary under the
   active policy (§5.4).
5. **Per commit under active authority:** verify the signature and active signer
   class (§4.2); read trailers (§4.1); locate and verify the covering review
   attestation under active attestation roots (§4.3). Any unverifiable commit →
   **abort**. Assign the level per §3.2.
6. **Enforce meta paths:** apply the active required level to the union of active
   and candidate meta/policy/trust-material paths. Any violation → **abort**
   (§5.4).
7. **Handle derivation claims:** record any derivation metadata (§4.4), but do
   not execute repository/policy commands and do not raise path trust from
   unsupported derivation claims.
8. **Partition by scope** (§5.1) under the active policy and compute
   `own_trust` (§5.2). Candidate scope changes do not affect the current interval.
9. **Propagate:** resolve the internal dependency graph at consumed versions,
   collapse SCCs, compute `effective(C)` (§5.3), and record pinned dependencies
   and the floor source.
10. **Collect evidence** under the active policy: run configured providers and
    compute the semantic floor (§6.1) and blast score (§6.2).
11. **Decide and derive the tag:** evaluate the active policy threshold (§6.2),
    baseline table (§6.4), and strategy (§6.3), honoring the semantic floor
    unconditionally. Apply the signed advance/re-cut/supersede action to
    authenticated version state and for a re-cut, supersession, or advance from
    an unpromoted target reconstruct the complete target lineage under each
    interval's bound authority. Derive target-level trust, blast, semantic
    floor, exact target core, and iteration (§7.5). Any occupied output tag,
    incomplete target lineage, incompatible re-cut, or version-state mismatch →
    **abort**; a superseding semantic invalidation follows §7.5's
    attestation-only path instead.
12. **Emit and advance:** construct the signed annotated tag object and obtain
    its raw/peeled IDs without overwriting a ref; assemble, sign, and store the
    release attestation (§8), binding the interval, active authority, candidate
    state, profiles, injected verification instant, and prior/resulting version
    state; then publish the final tag ref only if absent and project to registries
    (§7.4). An orphan object or attestation alone is not accepted chain state,
    and retry MUST NOT move an occupied tag. Only acceptance of this new-source
    attestation advances source continuity and activates the candidate policy
    and resulting version state for the next interval.
13. **Superseding re-evaluations** — including promotion and demotion — first
    validate the superseded decision and its complete source/predecessor chain.
    They preserve its exact `TO`, interval, source-predecessor link, active
    policy/trust/profile state, candidate policy/trust state, and version
    baseline/target lineage. They re-execute the superseded source interval under
    its original active authority and each earlier target-lineage interval under
    the authority bound to that interval, using updated authenticated evidence
    (§7.3, §7.5). Such a re-evaluation cannot activate a different candidate or
    create a new source interval. After source continuity has advanced, it is
    attestation-only and cannot emit a tag, consume an iteration, or rewrite
    existing successor/version links.

## 11. Threat model

| Threat | Mitigation | Residual risk |
|---|---|---|
| Forged provenance trailers | Trailers advisory; identity class from verified signature governs; conflicts floor to agent (§3.2, §4.1) | Low |
| Identity laundering (agent under human key) | Accountability semantics stated normatively (§4.2); agent trailers required by policy; CI agents forced onto machine identities; spot audits | **Accepted & documented** — T2/T3 mean "human stands behind it," not "human typed it" |
| Actor-map laundering | Actor map is policy/trust material selected by bootstrap or accepted predecessor state; meta-path and policy-transition rules protect actor-map changes (§4.2, §5.4, §9) | T3 means two distinct canonical human actors under the issuer's identity policy, not independently proven natural-person distinctness or non-collusion |
| Review rubber-stamping | Compatibility evidence and blast policy still apply (differ proofs, coverage); distinct-actor requirement for T3; audit trails in attestations | Moderate — review *quality* is out of scope by design |
| Payload hidden in "trivial" or generated commit | No de-minimis exception (§5.1); no executable derivation bypass in the portable baseline (§4.4) | Low |
| Risk laundering via shared libs | Transitive propagation over the workspace graph (§5.3) | Low |
| Scope-map / policy tampering | Bootstrap/predecessor selects active policy; authority-pinned workflows and union meta-paths require the active level; candidate activates only after acceptance (§5.4) | Low |
| Candidate key self-enrollment | Candidate-only identities cannot verify their transition; old roots govern the interval (§5.4) | Low |
| Skipped release history | Recurring intervals anchor to the accepted predecessor chain head; arbitrary `FROM` is rejected (§5.2) | Low once the verifier has an authoritative current head; rollback/freeze remains (§12.9) |
| Adoption-boundary movement | Boundary is immutable bootstrap chain state and the boundary commit is included (§5.2) | Low |
| Version-line or iteration injection | Bootstrap/predecessor binds version state; exact tags and iterations are derived; moved, ambiguous, or caller-selected predecessors fail (§7.5) | Low once the verifier has an authoritative current version-decision head (§12.9) |
| Trust reset across skipped prereleases | Target lineage accumulates through re-cuts and advances from unpromoted targets; only complete authenticated reevaluation can raise it (§7.5) | Low once the complete accepted target lineage is available |
| Squash/rebase provenance destruction | Forbid, or capture pre-squash provenance in merge attestation (§4.3) | Low |
| Conflict-resolution smuggling in merge commits | Non-empty merge diffs classified as authored changes (§4.3.4) | Low |
| Attestation store tampering | Signatures detect forgery; an authoritative current-state or transparency profile is needed to detect hidden successors/demotions (§8.2, §8.3) | Moderate unless the active source/version profiles define freshness |
| Source-evidence replay or issuer overreach | Source evidence must bind repository resource URI, immutable revision subject, digest algorithm, issuer authorization, verification mode, and freshness semantics (§8.3) | Low for replayed evidence; moderate when policy trusts an issuer summary without replay |
| Source-evidence equivocation | Conflicting accepted source-evidence statements for the same repository/revision/profile/instant abort unless the profile defines deterministic conflict resolution (§8.3) | Low with transparency or authoritative current-state proofs; moderate otherwise |
| Generator/toolchain compromise | Portable baseline verifiers do not execute repository-selected derivation commands or use derivation claims to raise trust (§4.4) | Low for baseline; future proof profiles must address toolchain compromise explicitly |
| History rewrite on protected branch | Immutable predecessor/`TO` bindings and ancestry checks; rewrite ⇒ verification failure (§10) | Low |
| Gaming promotion cascades | Promotion requires its own signed evidence and re-runs the full decision (§7.3) | Low |

## 12. Open questions

1. **T1 efficacy.** Whether independent agent review provides enough corroboration for any clean-channel policy is unsettled; the baseline excludes it until evidence emerges.
2. **Trust decay.** Should clean releases age (e.g., unpatched components lose standing), or is trust strictly monotonic per release? Current position: attestations are supersedable (§7.3.5), but no time-based decay is defined.
3. **External dependencies.** Interface point to SLSA Build levels exists (§1.2); a mapping between SLSA Build levels and T-levels is deliberately not defined in v0.1. SLSA Source integration for first-party source evidence is defined in §8.3.
4. **Cross-repo propagation.** Effective trust across repository boundaries (internal registries of first-party components) — likely via consuming the dependency's release attestation — is deferred.
5. **Review-quality signals.** Approval latency, comment depth, and diff coverage of review are measurable but gameable; excluded from v0.1.
6. **Naming.** *Resolved (v0.2):* the scheme is SemVer-Trust, hosted at `github.com/semver-trust`, with predicate-type URIs bound to `semver-trust.dev` (specification repository ADR-013). The `t` identifier is final. This entry is retained for numbering stability.
7. **Security-patch velocity vs. channel demotion.** Under `strategy = "demote"`, an under-evidenced security fix lands in a trust pre-release channel that many ecosystem profiles intentionally keep out of ordinary upgrade paths — the scheme can slow patch propagation exactly when speed matters most, and any expedite carve-out is a door an attacker will label "security fix" to walk through. Candidate directions, all unproven: expedited *review* SLAs rather than expedited channels; advisory-linked promotion (a patch promotes when a linked advisory is published by a distinct accountable identity); accepting the tension and documenting emergency response as out of band. This is currently the scheme's strongest known internal counterargument.
8. **Empirical validation of the trust–outcome link.** The keystone empirical claim — that trust levels correlate with outcome risk — is untested. Retrospective trust profiling of existing repositories against vulnerability and incident history (see the reference-implementation roadmap) is the designated test. A null result does not void the scheme (Principle 6) but would reposition it as accountability infrastructure rather than a risk signal, and should reshape default policy tables.
9. **Authoritative current state and freshness.** Signatures and predecessor
   links prove an internally consistent chain but cannot prove that a verifier
   was shown its newest accepted head or latest superseding decision. A hidden
   successor, promotion, or demotion is a rollback/freeze attack, not a
   signature failure. Predicate v0.2 binds the verifier's accepted attestation
   set and verification instant, but profiles that need freshness MUST also
   define source- and version-head discovery and conflict resolution, likely
   through verifier-pinned state or a transparency mechanism with freshness
   evidence. Until then, continuity claims are relative to the verifier's
   supplied accepted heads, not globally latest state.

---

## Appendix A: Worked example (monorepo)

Workspace: `services/auth`, `services/billing`, `pkg/common`; graph: both services depend on `common`. Policy: threshold T2, strategy `demote`.

1. Since `common/v0.8.4`, `pkg/common` received three commits from a CI agent (machine identity, `Provenance: agent`, no review) → `own(common) = T0`. Release cut: `common/v0.9.0-t0.1` (pre-release channel; MINOR floor from `apidiff`: additive only).
2. `services/auth` since `auth/v1.3.2`: five human-authored,
   human-reviewed commits plus regenerated `internal/gen/**` committed by a CI
   agent. The OpenAPI spec was reviewed, but the portable baseline does not
   execute derivation commands or raise generated outputs from derivation
   metadata (§4.4), so the generated commit contributes T0 and
   `own(auth) = T0`. Decision: `auth/v1.4.0-t0.1`; the attestation records both
   the local derivation metadata and the fact that it supplied no portable trust
   elevation.
3. A maintainer reviews `common`'s three commits post-hoc; a signed review attestation lands. Re-evaluation: `own(common) = T2` ≥ threshold → promotion tag `common/v0.9.0` on the identical SHA, superseding attestation published.
4. Cascade check: `auth`'s pinned floor source now resolves as promoted, but
   `auth` still cannot promote because its own generated-output commit remains
   T0. A later qualified human review of that generated-output commit can
   produce a superseding `auth/v1.4.0` attestation on the same SHA; until then,
   the release remains `auth/v1.4.0-t0.1`.
5. A later `billing` release includes one commit editing
   `.semver-trust/policy.toml` authored at T2 while meta-paths require T3 →
   verification **fails**; no tag is produced until the policy change is
   re-reviewed.

## Appendix B: Level assignment quick reference

```
authorship \ review |  none  | agent* |  human
--------------------+--------+--------+--------
agent               |   T0   |   T1   |   T2
mixed / ambiguous   |   T0   |   T1   |   T2
human               |   T2   |   T2   |   T3**
```
\* independent per §3.3 · \*\* distinct canonical human actors; self-review = none

---

## Appendix C: Changes from v0.1

- Added Principle 6 — levels order accountability, not risk — to §1.1, with a §3.1 clarification (spec repository ADR-019).
- §4.4 added derivation toolchain pinning guidance in draft v0.2 (ADR-015);
  ADR-015 was later superseded by ADR-033 in draft v0.8.
- §12.6 naming resolved (ADR-013); predicate-type URIs bound to `semver-trust.dev` in §4.3 and §8.1. The review predicate version was aligned from `v1` to `v0.1` to match specification maturity — permissible only because no attestation has yet been emitted.
- New open questions: §12.7 (security-patch velocity vs. channel demotion) and §12.8 (empirical validation of the trust–outcome link), from the adversarial review at `docs/analysis/2026-07-02-steelman.md`.
- No changes to the trust taxonomy, level assignment, aggregation, propagation, encoding grammar, decision tables, or verification algorithm.


## Appendix D: Changes from v0.2

- §3.2 note 2 clarified (spec repository ADR-025): the self-review exclusion prevents one human from
  counting twice, not from counting once — same-identity human review of agent-, mixed-, or
  ambiguous-authored commits counts as the single accountable human (T2). Surfaced by the reference
  implementation's own first-release ceremony, where honestly agent-trailered commits signed and
  post-hoc-reviewed by the sole maintainer classified T0 under the stricter misreading.
- §7.1 states the reservation of the trust-shaped pre-release namespace (closes spec repository issue #13):
  a pre-release whose first identifier is trust-shaped (`t` + a level digit) is reserved, and a malformed
  trust identifier (two-digit level, missing or zero iteration, level out of range) is invalid and rejected,
  never reinterpreted as a plain pre-release. This states in normative text the fail-closed rule the
  conformance grammar vectors already enforce; the spoofing-surface and single-digit-cap rationale is the
  ADR-010 context. No change to the trust-suffix grammar itself.
- §5.2 and §10 step 2 mirror the adoption boundary (spec repository ADR-024, superseded by ADR-026): a policy MAY declare one
  policy-pinned `[policy] adoption_boundary`; a first release then verifies `boundary..TO` in place of
  `root..TO`. The boundary is disclosed in the release attestation (§8.1 `range.from_is_adoption_boundary`)
  and pre-boundary history is exempt, contributing no trust level at all — never laundered to T0.
- §9 documents three optional policy fields the reference implementation already recognizes: `[policy]
  adoption_boundary` (ADR-024, superseded by ADR-026), `[identity.human] gpg_keyring` (armored OpenPGP commit-signer registry),
  and `[identity] attestation_signers` (the SSHSIG-over-DSSE attestation-signer registry, §4.3, §8.2,
  ADR-022). All three default to absent; a verifier MAY default trust-material paths from them.
- No changes to the trust taxonomy, level assignment, aggregation semantics, propagation, decision tables,
  or the trust-suffix grammar; the additions above state an existing parse reservation, add an optional
  range anchor, and register optional policy vocabulary. Conformance vectors gained additive classification
  cases and re-pinned `spec_version: "0.3"`; no vector files change in this pass.

## Appendix E: Changes from v0.3

- §5.2 and §10 replace ambiguous producer-selected `FROM..TO` ranges with
  explicit inception, adoption, and recurring reachability sets. Inception
  includes every reachable root; adoption includes the boundary while exempting
  its parent history; recurrence chains to the accepted predecessor attestation
  (ADR-027, superseding ADR-026).
- §5.4, §9, and §10 replace self-authorizing `TO` policy loading with an
  out-of-band bootstrap authority at chain genesis and previous-policy
  governance thereafter. Candidate policy and key changes activate only after
  an accepted release (ADR-028, superseding ADR-007).
- §7.5 separates authenticated version ancestry from release intervals and
  policy state. Bootstrap binds explicit new-line genesis or an immutable legacy
  predecessor; recurrence derives target cores and trust iterations from
  accepted version state rather than caller `current_version`/iteration inputs
  (ADR-029).
- §8.1 states the additional continuity/policy bindings required for v0.4 and
  explicitly preserves predicate v0.1 as historical. Because v0.1 cannot carry
  the new bindings, v0.4 release emission waited for a successor predicate URI
  and schema, now assigned in Appendix F.
- New range, policy-transition, and version-ancestry conformance vectors cover
  roots, boundaries, skipped/moved predecessors, bootstrap mismatch,
  self-enrollment, meta-path weakening, mandatory-workflow removal, boundary
  movement, role/clock mismatch, legacy version continuation, caller overrides,
  prerelease re-cuts, target-lineage trust laundering, iteration derivation,
  corrective advances, late attestation-only supersessions, and valid delayed
  key/scope rotation.
- No changes to trust-level assignment, scope-floor arithmetic, transitive
  propagation, tag grammar, or the release decision table.

## Appendix F: Changes from v0.4

- §4.3 and §8.1 assign successor predicate types
  `https://semver-trust.dev/release/v0.2` and
  `https://semver-trust.dev/review/v0.2` (ADR-030). Predicate v0.1 remains
  historical and is not extended in place.
- §8.1 makes explicit profile identity mandatory for successor release and
  review attestations: specification, predicate contract, evaluator,
  repository identity, graph/policy or actor/source-control profile, and
  verification-time profile.
- Successor schemas `schemas/release-v0.2.json` and
  `schemas/review-v0.2.json` register the compatibility-critical envelope and
  state bindings for v0.5/v0.4 trust-chain conformance.
- Schema evolution now uses a new predicate URI for any change that alters
  validation or interpretation; additive optional fields inside a closed
  emitted schema are not a compatibility mechanism.

## Appendix G: Changes from v0.5

- §2, §3.2, §4.2, §4.3, and §9 define canonical actors and require qualified
  review before review evidence can raise trust (ADR-031).
- T3 distinctness is evaluated on canonical human actors, not raw keys,
  accounts, or other credential strings. Key rotation and account aliases do
  not create additional accountable humans.
- Qualified review requires an `approved` verdict, active approval at merge,
  final-revision or final-diff binding, repository and merge-context binding,
  and fail-closed treatment for stale, withdrawn, dismissed, wrong-revision, and
  non-independent reviews.
- The review/v0.2 successor predicate, which had not emitted bytes before this
  decision, now carries the approval-state, coverage, merge-context, actor, and
  agent-independence facts required for draft v0.6 review classification.

## Appendix H: Changes from v0.6

- §6 defines threshold as a hard clean-channel accountability gate evaluated
  before the blast/differ table (ADR-032).
- §6 separates compatibility evidence, accountability evidence, and operational
  blast policy inputs. Trust levels remain accountability claims, not quality,
  security, safety, compatibility, or defect-probability scores.
- The portable baseline threshold is T2; T1 does not satisfy the baseline clean
  profile before empirical validation of independent agent-review efficacy.
- §6.4 is now the deterministic baseline decision profile, and release/v0.2
  decision bindings include the threshold used for replay.
- Provider-specific blast scoring is portable only when bound to a named,
  versioned blast-scoring profile; otherwise it is local policy input rather
  than a cross-implementation conformance claim.

## Appendix I: Changes from v0.7

- §4.4 removes executable derivation proofs from the portable baseline
  (ADR-033, superseding ADR-004 and ADR-015). Verifiers do not execute
  repository- or policy-supplied commands to raise generated-output trust.
- Fixed-point/idempotence evidence is distinguished from derivation evidence:
  byte-identical regeneration of an already committed tree is not proof that
  outputs came from trusted inputs.
- Generated outputs, formatting-only commits, and lockfile rewrites are
  classified by ordinary authorship/review evidence under the no-de-minimis
  rule unless a future accepted proof profile defines stronger evidence.
- Aggregation conformance vectors now require derivation claims to fail closed
  to raw commit trust in the portable baseline.

## Appendix J: Changes from v0.8

- §7.1 and §7.4 narrow the prerelease-routing claim (ADR-034, superseding
  ADR-001 and revising ADR-011's registry-projection clause). SemVer-Trust
  prereleases provide native ordering friction, but resolver behavior is
  ecosystem-specific and does not replace attestation verification.
- §7.4 replaces unconditional registry projections with ecosystem publishing
  profiles for Go modules, npm, Cargo, and Python/PyPI. npm trust prereleases
  must not be published under `latest` unless ordinary installation is intended;
  Go and Python prerelease fallback cases are explicit; the portable baseline
  defers PyPI projection until an injective mapping is accepted.
- §7.3 clarifies that promotion promises identical source by default. Artifact
  digest equality is a separate reproducible-build promise, not a consequence
  of same-source promotion.

## Appendix K: Changes from v0.9

- §8.3 defines source evidence profiles and SLSA Source integration (ADR-035).
  SLSA Source facts are consumed as profiled evidence inputs, either by replay
  of source provenance or explicit trust in a Source VSA/equivalent issuer.
- Source evidence matching now fails closed on repository-resource mismatch,
  source-revision subject mismatch, disallowed digest algorithms, unauthorized
  issuers, stale evidence, hidden demotion, and equivocation.
- `release/v0.2` remains schema-frozen after first signed emission. Draft v0.10
  source-evidence bindings use the declared `predicate.extensions` map; any
  future required top-level source-evidence field requires a new predicate URI.

---

SemVer-Trust Specification © 2026 The SemVer-Trust Authors.
Licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
