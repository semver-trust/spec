<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# SemVer-Trust: Provenance-Scoped Trust Levels for Semantic Versioning

**Draft v0.3**
**Status:** Design draft for review
**Date:** 2026-07-03
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
| **Accountable human** | A natural person whose verified identity (via signature or platform-authenticated review) is bound to a change in the role of author or reviewer. |
| **Agent** | An automated system (LLM-based or otherwise) that authors or reviews code under a machine identity or under a human's identity. |
| **Attestation** | A signed [in-toto Statement](https://in-toto.io) binding a subject (commit SHA, tag, artifact digest) to a predicate (facts about provenance, review, evidence, or a release decision). |
| **Component** | A releasable unit within a repository, identified by a scope and released under a (possibly path-prefixed) tag. |
| **Derivation** | A deterministic transformation from declared input paths to declared output paths via a pinned command. |
| **Effective trust** | A component's trust level after transitive propagation through its internal dependency graph (§5.3). |
| **Evidence provider** | A pluggable, ecosystem-specific analyzer supplying compatibility proofs, coverage, or blast-radius inputs (§6). |
| **Own trust** | The trust floor over commits touching a component's scope, before propagation. |
| **Scope** | A named set of repository paths defined in the policy file (§9). |
| **Trust channel** | The release lane implied by trust: the *clean channel* (plain version) or the *pre-release channel* (version carrying a trust identifier). |

## 3. Trust model

### 3.1 Levels

A trust level is a scalar `T0`–`T3` counting **independent accountable humans** bound to a change, with one intermediate rung for agent corroboration:

| Level | Definition | Intuition |
|---|---|---|
| **T0** | No accountable human. Agent-authored (or mixed/ambiguous authorship) with no independent review. | Fully autonomous. |
| **T1** | No accountable human, but independently agent-reviewed (§3.3). | Autonomous with machine corroboration. |
| **T2** | Exactly one accountable human, in either role. | One human stands behind it. |
| **T3** | Two distinct accountable humans: verified author identity ≠ verified reviewer identity. | Authored and independently reviewed by different humans. |

Levels are an accountability ordering, not a risk ordering (Principle 6, §1.1): policy maps levels plus evidence to risk; the levels themselves claim only the count of independent accountable humans.

### 3.2 Level assignment (normative)

Per-commit levels are assigned from the full authorship × review matrix. Authorship class is determined by the commit's verified signer identity class (§4.2) combined with provenance trailers (§4.1); review class by merge-time attestations (§4.3).

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
| human | human (distinct identity) | **T3** |

Notes:

- *Ambiguous* means the signer identity class and the provenance trailers conflict, or required trailers are absent under a policy that mandates them. Ambiguity MUST floor to the agent-authored row — unverifiable claims of human authorship are treated as absent.
- The self-review exclusion prevents one human from counting twice, never from counting once: a human reviewing their own *human-authored* commit adds no second human (T3 requires distinct verified identities), but for agent-, mixed-, or ambiguous-authored commits — where no human author is counted — a signed human review adds the first accountable human even when the reviewer is the commit's signer (agent + human = T2; spec repository ADR-025). Anything else would punish the honest `Provenance: agent` trailer: omitting it would classify the commit human-authored and reach T2 directly.
- Multiple unverified co-authors (e.g., `Co-authored-by:` trailers without signatures) do not raise a commit above T2. Only signature-verified or platform-attested identities count.
- The scalar is deliberately lossy: `human + none` and `agent + human` both map to T2. Policies that need the distinction MUST consume the full **provenance vector** in the attestation (§8.1), which preserves authorship and review classes separately. The scalar exists for tag encoding and precedence; the vector exists for policy.

### 3.3 Independent agent review (T1)

An agent review qualifies as *independent* only if all of the following hold:

1. The reviewing agent runs in a separate execution context with no shared conversational or working state with the authoring agent.
2. The reviewer's identity (workload identity, §4.2) differs from the author's identity.
3. The review produces a signed review attestation naming the commit SHA(s), the reviewing agent/model, and a verdict.

Implementations SHOULD prefer a different model family for the reviewer. This spec makes no empirical claim that T1 review approaches human review efficacy — self-preference bias in model-reviewing-model settings is an open research question. T1 exists as a distinct rung so that policy can price it separately from both T0 and T2.

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

**The identity-laundering limit (normative honesty clause).** When a human runs an agent locally and commits under their own key, the scheme cannot detect it. Such commits classify as human-authored *as an accountability assertion by the signer* (Principle 2, §1.1). Organizations SHOULD state this interpretation in contributor policy, SHOULD require agents to emit provenance trailers even in local use, and MAY audit via spot review. The residual risk is accepted and documented in the threat model (§11) rather than hidden.

### 4.3 Merge-time review attestation

Review facts live outside git (platform PR approvals), so they MUST be captured into the provenance record at merge time:

1. At merge, a trusted workflow (CI or merge queue) generates an in-toto attestation with predicate type `https://semver-trust.dev/review/v0.1` whose subjects are the merged commit SHAs, recording: reviewer identities and their classes (human/agent), approval verdicts, the PR/MR reference, and the merge strategy used.
2. The attestation MUST be signed by the workflow's workload identity and stored per §8.2.
3. **Merge strategies:** squash and rebase merges rewrite authorship and destroy per-commit provenance. Repositories MUST either (a) forbid squash/rebase merges on protected branches, or (b) ensure the merge-time attestation records the pre-squash commit provenance so the resulting single commit can be classified from attested facts.
4. **Merge commits themselves:** a merge commit with a non-empty diff (conflict resolution) introduces authored changes. It MUST be classified like any other commit — the resolver is its author; the review attestation covering the PR does not automatically cover novel conflict-resolution hunks unless the reviewer re-approved after resolution.

### 4.4 Derivation proofs

A **derivation rule** (declared in policy, §9) states: *outputs O are deterministically produced from inputs I by pinned command C.* At verification time, the verifier re-runs C on the tree and diffs against the committed outputs.

- If the regenerated outputs are byte-identical, the output paths **inherit the minimum trust level of the input paths** (as of the same tree), regardless of who ran the generator. The proof is reproducibility, not identity.
- The generator toolchain is itself an input: its version MUST be pinned via lockfile, checksum, or vendored binary, and changes to the pin are ordinary commits subject to ordinary trust classification.
- Toolchain pins SHOULD be self-contained and language-native (module/tool manifests with checksum verification, or container image digests). Environment-manager state (development-environment lockfiles) MUST NOT serve as a derivation input: re-running a derivation for verification requires only the language toolchain and the pinned inputs, never the maintainer's development tooling.
- If regeneration differs, the outputs are classified by their commits' own provenance — the derivation claim is simply void for that release, and the discrepancy SHOULD be reported.
- Formatting-only rules are a degenerate derivation (inputs = outputs, command = formatter): if re-formatting yields an identical tree, a commit that only reformats inherits the trust of the content it formatted.

Derivation proofs are the scheme's only exception to weakest-link flooring, and they are principled because they are *verified*, not declared. Projects with no derivations simply have no exceptions. Spec-first architectures (OpenAPI, protobuf, schema DSLs) benefit most: a human-reviewed contract extends its trust to everything provably generated from it.

## 5. Aggregation

### 5.1 Scope partitioning

The policy file (§9) maps path globs to named scopes. A commit **touches** a scope if any path in its diff matches the scope's globs. Scoping keys off diff paths — objective ground truth from git — never off declared intent, commit messages, or size heuristics. A commit touching `services/auth/**` and `docs/**` contributes its trust level to both scopes. Paths matching no scope fall into an implicit `default` scope.

There is no *de minimis* exception: a one-line T0 commit floors its scope exactly like a thousand-line one. Any "trivial commits don't count" rule becomes the hiding place for a payload; the only sanctioned exception is a verified derivation proof (§4.4).

### 5.2 Own trust (per-scope floor)

For a component release covering commit range `FROM..TO` (git two-dot: commits reachable from `TO` and not from `FROM`; for a first release, `FROM` is the root):

```
own_trust(scope) = min over commits c in range, c touches scope:
                     level(c)        # per §3.2, after derivation proofs (§4.4)
```

A commit that fails signature verification, or whose required attestations cannot be located and verified, has no level: verification of the release MUST fail (§10). Unverifiable is not T0 — T0 is a verified fact about a verified commit.

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

### 5.4 Meta-paths: the configuration is the root of trust

The policy file, scope map, derivation rules, identity map, and the workflows that generate attestations can reclassify anything. Therefore:

- These paths MUST be declared as **meta-paths** in policy.
- Commits touching meta-paths MUST meet the maximum trust level required anywhere in the policy (typically T3), regardless of which scope they otherwise fall in, and SHOULD additionally require review by designated owners (CODEOWNERS or equivalent).
- A release range containing a meta-path commit below the required level MUST fail verification outright — not demote, fail. The config protects the system; the system must protect the config.

## 6. Release evaluation

A release decision consumes two independent inputs and applies policy:

- **Semantic floor** — the *minimum* bump the change semantics permit.
- **Evidence ceiling** — the *maximum* claim the provenance evidence supports.

### 6.1 Semantic floor

Determined by the strongest available compatibility evidence, in order of preference:

1. **Compatibility differ** (evidence provider): `apidiff` (Go), `cargo-semver-checks` (Rust), `japicmp` (Java), API Extractor (TypeScript), etc. A detected breaking change in the public surface forces MAJOR. No trust level overrides the semantic floor — T3 code that breaks the API is still a MAJOR release.
2. **Declared intent**: Conventional Commits (`feat:` → MINOR, `fix:` → PATCH, `!`/`BREAKING CHANGE:` → MAJOR) where no differ exists. Declared intent is weak evidence and interacts with §6.2 accordingly.

### 6.2 Evidence ceiling and blast radius

To *claim* a bump is to claim what it implies (PATCH: drop-in safe; MINOR: additive only). The claim must be supported by evidence proportional to risk:

```
risk ∝ blast_radius × inverse(effective_trust)
```

**Blast-radius inputs** (pluggable; core inputs are language-agnostic, starred inputs come from evidence providers):

| Input | Source |
|---|---|
| Changed lines / files / churn concentration | git (universal) |
| Scope criticality weight | policy file (universal) |
| Dependency manifest changes (`go.mod`, `package.json`, `Cargo.toml`, lockfiles) | git (universal) |
| Public-surface delta * | compatibility differ |
| Import-graph fan-in of touched packages * | language adapter |
| Test coverage on changed lines * | coverage provider |

Implementations map these to a qualitative score (`low` / `moderate` / `high`). This spec deliberately does not define a numeric formula; false precision here invites gaming. The score, its inputs, and the provider versions MUST all appear in the release attestation.

### 6.3 Enforcement strategies

When evidence does not support the claimed bump at the computed risk, policy selects one strategy:

- **`demote` (RECOMMENDED):** keep the semantically correct bump but confine the release to the pre-release channel (§7) until evidence accumulates — post-hoc human review, canary/soak results, audit. Preserves the API-compatibility meaning of MAJOR/MINOR/PATCH; consumers opt in explicitly.
- **`inflate`:** escalate the bump (PATCH→MINOR or →MAJOR) so default-range consumers do not auto-adopt. Supported because some organizations want risk expressed in the precedence-relevant part of the version; costs include diluting MAJOR's "your code must change" signal and forcing migration review where no API changed.

### 6.4 Default decision table (illustrative policy, tunable)

Channel for the *clean* (plain-version) release; anything else goes to the pre-release channel under `demote`, or bumps under `inflate`:

| Effective trust | Blast: low | moderate | high |
|---|---|---|---|
| **T3** | clean | clean | clean, differ proof REQUIRED for PATCH claim |
| **T2** | clean | clean, differ proof required for PATCH claim | pre-release |
| **T1** | clean, differ proof required | pre-release | pre-release |
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

- The trust identifier occupies SemVer pre-release position, so `v1.4.0-t1.1 < v1.4.0` by SemVer precedence, and default dependency-range resolution in Go modules, npm, and Cargo will not select it. **Low-trust releases are opt-in by construction**, with zero consumer-side tooling.
- Levels are a fixed single digit. (Lexical ASCII comparison of alphanumeric identifiers would order `t10 < t2`; capping at one digit forecloses the hazard.)
- Component paths follow the ecosystem's nested-tag convention where one exists (Go nested modules use exactly this `dir/vX.Y.Z` prefix form).

### 7.2 Precedence interactions and the rc question

SemVer compares dot-separated pre-release identifiers left to right, ASCII-lexically for alphanumerics; numerics sort below alphanumerics. Consequences worth pinning:

- `v1.4.0-rc.1 < v1.4.0-t1.1 < v1.4.0` (`"rc" < "t1"`). A trust-gated release outranks an rc among pre-releases.
- This spec's position: **the trust channel generalizes the rc pattern.** An rc's traditional job — publish, soak, gather evidence, promote — is precisely the trust-promotion lane. Projects adopting SemVer-Trust SHOULD NOT combine `rc`-style identifiers and trust identifiers on the same version; a below-threshold release *is* the release candidate, with the trust level stating *why* it is not yet clean.
- Iteration (`.2`, `.3`) increments for re-cuts at the same core version and level; a re-cut at a *different* level starts a new suffix (`-t0.1` → fixes reviewed → `-t2.1`).

### 7.3 Promotion

Promotion moves a release from the pre-release channel to the clean channel **without changing its source**:

1. New evidence is attested (human review attestation, soak/canary evidence, audit) against the same commit SHA.
2. The verifier recomputes effective trust and the decision table; if the release now qualifies, the clean tag (`v1.4.0`) is created **on the identical SHA**, with a fresh release attestation citing the promotion evidence and superseding the prior decision.
3. **Immutable registries:** git and Go modules tolerate two tags on one commit, but npm/PyPI artifacts bake the version string into package metadata, so promotion there means *republication from the identical source SHA*. With reproducible builds the artifact digest matches; without, each artifact carries its own attestation bound to the same source SHA, and the source binding — not the digest match — is the promotion guarantee.
4. **Cascade:** promotion of a dependency MAY trigger re-evaluation of downstream components whose effective trust was floored by it (their attestations pin the dependency, §5.3, making affected components discoverable). Downstream promotion follows the same rule: same SHA, new attestation. This resolves the "auth is stuck in pre-release because pkg/common was T0" case without rebuilding auth.
5. Demotion (evidence invalidated, e.g., a review attestation revoked) cannot un-publish a clean version; it is expressed by publishing a superseding attestation and, where warranted, a security advisory. This is the standing reason the attestation, not the tag, is the living record (§1.1, Principle 5).

### 7.4 Registry projections

The git tag is canonical; registries receive projections:

| Ecosystem | Projection | Notes |
|---|---|---|
| Go modules | native | Pre-release identifiers pass through. Build metadata is not an option regardless: the go command requires canonical versions and rejects build-metadata suffixes (only the special `+incompatible` form exists). Nested-module tags align with component paths. |
| npm | native + dist-tags | `1.4.0-t1.1` is a valid npm version; default ranges exclude pre-releases. Additionally publish under a dist-tag (e.g., `trust-t1`) so `npm install pkg@trust-t1` is ergonomic. |
| Cargo | native | Pre-release versions excluded from default `^` resolution. |
| PyPI | lossy | PEP 440 permits only `a`/`b`/`rc` pre-release segments — `1.4.0-t1.1` is not publishable. Project to `1.4.0rc<iteration>` and carry the trust detail exclusively in the attestation. The canonical trust-version remains the git tag. |

The PyPI row is the existence proof for Principle 5: any consumer logic that depends on parsing trust out of a version string is non-portable; portable consumers verify attestations.

## 8. Attestation

### 8.1 Release attestation predicate

Release attestations are in-toto Statements (`https://in-toto.io/Statement/v1`). Subjects bind the tag name to the commit SHA (and artifact digests where applicable). Sketch of the predicate (schema to be formalized; field names illustrative):

```json
{
  "_type": "https://in-toto.io/Statement/v1",
  "subject": [
    { "name": "auth/v1.4.0-t1.1", "digest": { "gitCommit": "8c1f2e…" } }
  ],
  "predicateType": "https://semver-trust.dev/release/v0.1",
  "predicate": {
    "component": "auth",
    "range": { "from": "auth/v1.3.2", "to": "8c1f2e…" },
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

Normative points: the **provenance vector** (per-commit authorship and review classes) MUST be preserved even though the tag carries only the scalar level (§3.2); the policy file digest MUST be pinned so a decision is reproducible against the exact policy that produced it; `supersedes` links promotion/demotion chains.

### 8.2 Storage and verification of attestations

- Attestations MUST be signed (sigstore keyless with a transparency log entry, or organization-managed keys).
- Storage options: a git ref namespace (e.g., `refs/attestations/*`), an OCI registry (attestation-as-artifact), or a transparency-log-backed store (Rekor). Git notes are acceptable for convenience but are mutable and not fetched or protected by default — **storage integrity is never the trust anchor; the signature inside the attestation is.** Verifiers MUST validate signatures and subject digests regardless of where the attestation was fetched from.
- Review attestations (§4.3), derivation results (§4.4), promotion evidence (§7.3), and release attestations (§8.1) share the storage and signing requirements.

## 9. Policy file

The policy file is TOML, lives in the repository, and is itself a meta-path (§5.4). Reference example:

```toml
[policy]
version   = "0.1"
threshold = "T2"        # minimum effective trust for the clean channel
strategy  = "demote"    # "demote" (recommended) | "inflate"

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

[[derivation]]
name    = "openapi-server"
inputs  = ["api/openapi.yaml", "tools/oapi-codegen.version"]
command = "make generate"           # toolchain pinned via the inputs above
outputs = ["internal/gen/**"]

[[derivation]]
name    = "gofmt"
inputs  = ["**/*.go"]
command = "gofmt -l -w ."
outputs = ["**/*.go"]               # formatting-only degenerate derivation (§4.4)

[identity.human]
allowed_signers = ".semver-trust/allowed_signers"   # ssh allowed-signers format
oidc_issuers    = ["https://accounts.example.com"]  # gitsign identities mapped to people

[identity.agent]
oidc_issuers     = ["https://token.actions.githubusercontent.com"]
subject_patterns = ["repo:acme/platform:*"]
bot_accounts     = ["release-bot@acme.dev"]

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

## 10. Verification algorithm (normative)

Given a component `C`, a proposed release at commit `TO`, and previous tag `FROM`:

1. **Load policy** from `TO`'s tree; record its digest. Verify the policy file's own history within `FROM..TO` satisfies §5.4 (meta-path level); on failure, **abort**.
2. **Enumerate commits**: `git rev-list FROM..TO` (root..`TO` for a first release). History rewrites on the protected branch invalidate prior tags' ranges and MUST be treated as verification failure.
3. **Per commit**: verify the signature and resolve the signer's identity class (§4.2); read trailers (§4.1); locate and cryptographically verify the covering review attestation (§4.3). Any commit that cannot be verified end-to-end → **abort** (unverifiable ≠ T0, §5.2). Assign the level per §3.2.
4. **Apply derivation proofs** (§4.4): re-run each rule against `TO`'s tree; on byte-identical outputs, re-level output paths to the inputs' floor.
5. **Partition by scope** (§5.1) using each commit's diff paths; compute `own_trust` per touched scope (§5.2).
6. **Propagate**: resolve the internal dependency graph via the graph adapter at the consumed versions; collapse SCCs; compute `effective(C)` (§5.3); record pinned dependencies and the floor source.
7. **Collect evidence**: run configured evidence providers (compatibility differ, coverage, blast-radius inputs); compute the semantic floor (§6.1) and blast score (§6.2).
8. **Decide** via the policy table (§6.4) and strategy (§6.3): channel and final version string (§7.1), honoring the semantic floor unconditionally.
9. **Emit**: create the signed annotated tag; assemble, sign, and store the release attestation (§8); project to registries (§7.4).
10. **Promotion runs** re-execute steps 6–9 against the same `TO` with the new evidence attached, producing a superseding attestation (§7.3).

## 11. Threat model

| Threat | Mitigation | Residual risk |
|---|---|---|
| Forged provenance trailers | Trailers advisory; identity class from verified signature governs; conflicts floor to agent (§3.2, §4.1) | Low |
| Identity laundering (agent under human key) | Accountability semantics stated normatively (§4.2); agent trailers required by policy; CI agents forced onto machine identities; spot audits | **Accepted & documented** — T2/T3 mean "human stands behind it," not "human typed it" |
| Review rubber-stamping | Evidence ceiling still applies (differ proofs, coverage); distinct-identity requirement for T3; audit trails in attestations | Moderate — review *quality* is out of scope by design |
| Payload hidden in "trivial" commit | No de-minimis exception (§5.1); only verified derivations bypass flooring | Low |
| Risk laundering via shared libs | Transitive propagation over the workspace graph (§5.3) | Low |
| Scope-map / policy tampering | Meta-paths require max level; violations fail verification outright (§5.4) | Low |
| Squash/rebase provenance destruction | Forbid, or capture pre-squash provenance in merge attestation (§4.3) | Low |
| Conflict-resolution smuggling in merge commits | Non-empty merge diffs classified as authored changes (§4.3.4) | Low |
| Attestation store tampering | Signatures inside attestations are the anchor; transparency logs; storage never trusted (§8.2) | Low |
| Generator/toolchain compromise | Toolchain pinned as derivation input; pin changes are ordinary trust-classified commits (§4.4) | Moderate — inherits general supply-chain exposure |
| History rewrite on protected branch | Branch protection; rewrite ⇒ verification failure (§10.2) | Low |
| Gaming promotion cascades | Promotion requires its own signed evidence and re-runs the full decision (§7.3) | Low |

## 12. Open questions

1. **T1 efficacy.** Whether independent agent review measurably reduces defect/exploit rates versus none is unsettled; the level's policy pricing should follow evidence as it emerges.
2. **Trust decay.** Should clean releases age (e.g., unpatched components lose standing), or is trust strictly monotonic per release? Current position: attestations are supersedable (§7.3.5), but no time-based decay is defined.
3. **External dependencies.** Interface point to SLSA levels exists (§1.2); a mapping between SLSA build levels and T-levels is deliberately not defined in v0.1.
4. **Cross-repo propagation.** Effective trust across repository boundaries (internal registries of first-party components) — likely via consuming the dependency's release attestation — is deferred.
5. **Review-quality signals.** Approval latency, comment depth, and diff coverage of review are measurable but gameable; excluded from v0.1.
6. **Naming.** *Resolved (v0.2):* the scheme is SemVer-Trust, hosted at `github.com/semver-trust`, with predicate-type URIs bound to `semver-trust.dev` (specification repository ADR-013). The `t` identifier is final. This entry is retained for numbering stability.
7. **Security-patch velocity vs. channel demotion.** Under `strategy = "demote"`, an under-evidenced security fix lands in the pre-release channel that default resolvers do not select — the scheme can slow patch propagation exactly when speed matters most, and any expedite carve-out is a door an attacker will label "security fix" to walk through. Candidate directions, all unproven: expedited *review* SLAs rather than expedited channels; advisory-linked promotion (a patch promotes when a linked advisory is published by a distinct accountable identity); accepting the tension and documenting emergency response as out of band. This is currently the scheme's strongest known internal counterargument.
8. **Empirical validation of the trust–outcome link.** The keystone empirical claim — that trust levels correlate with outcome risk — is untested. Retrospective trust profiling of existing repositories against vulnerability and incident history (see the reference-implementation roadmap) is the designated test. A null result does not void the scheme (Principle 6) but would reposition it as accountability infrastructure rather than a risk signal, and should reshape default policy tables.

---

## Appendix A: Worked example (monorepo)

Workspace: `services/auth`, `services/billing`, `pkg/common`; graph: both services depend on `common`. Policy: threshold T2, strategy `demote`.

1. Since `common/v0.8.4`, `pkg/common` received three commits from a CI agent (machine identity, `Provenance: agent`, no review) → `own(common) = T0`. Release cut: `common/v0.9.0-t0.1` (pre-release channel; MINOR floor from `apidiff`: additive only).
2. `services/auth` since `auth/v1.3.2`: five human-authored, human-reviewed commits (`own(auth) = T3`) plus regenerated `internal/gen/**` from a reviewed OpenAPI spec change — derivation proof verifies, generated paths inherit the spec commits' T3. But `effective(auth) = min(T3, effective(common)) = T0`. Decision: `auth/v1.4.0-t0.1`, floor source recorded as `common@v0.9.0-t0.1`.
3. A maintainer reviews `common`'s three commits post-hoc; a signed review attestation lands. Re-evaluation: `own(common) = T2` ≥ threshold → promotion tag `common/v0.9.0` on the identical SHA, superseding attestation published.
4. Cascade: `auth`'s pinned floor source resolves as promoted; re-evaluation gives `effective(auth) = min(own T3, common T2) = T2`, which meets the threshold → `auth/v1.4.0` on the same SHA (attestation records `effective: T2`, `own: T3`, floor source `common@v0.9.0`). No rebuild of source occurred at any step; only evidence changed.
5. A later `billing` release includes one commit editing `.semver-trust/policy.toml` authored at T2 while meta-paths require T3 → verification **fails**; no tag is produced until the policy change is re-reviewed.

## Appendix B: Level assignment quick reference

```
authorship \ review |  none  | agent* |  human
--------------------+--------+--------+--------
agent               |   T0   |   T1   |   T2
mixed / ambiguous   |   T0   |   T1   |   T2
human               |   T2   |   T2   |   T3**
```
\* independent per §3.3 · \*\* distinct verified identities; self-review = none

---

## Appendix C: Changes from v0.1

- Added Principle 6 — levels order accountability, not risk — to §1.1, with a §3.1 clarification (spec repository ADR-019).
- §4.4: derivation toolchain pins are self-contained and language-native; environment-manager state is excluded as a derivation input (ADR-015).
- §12.6 naming resolved (ADR-013); predicate-type URIs bound to `semver-trust.dev` in §4.3 and §8.1. The review predicate version was aligned from `v1` to `v0.1` to match specification maturity — permissible only because no attestation has yet been emitted.
- New open questions: §12.7 (security-patch velocity vs. channel demotion) and §12.8 (empirical validation of the trust–outcome link), from the adversarial review at `docs/analysis/2026-07-02-steelman.md`.
- No changes to the trust taxonomy, level assignment, aggregation, propagation, encoding grammar, decision tables, or verification algorithm.


## Appendix D: Changes from v0.2

- §3.2 note 2 clarified (spec repository ADR-025): the self-review exclusion prevents one human from
  counting twice, not from counting once — same-identity human review of agent-, mixed-, or
  ambiguous-authored commits counts as the single accountable human (T2). Surfaced by the reference
  implementation's own first-release ceremony, where honestly agent-trailered commits signed and
  post-hoc-reviewed by the sole maintainer classified T0 under the stricter misreading.
- No other changes to the trust taxonomy, level assignment, aggregation, propagation, encoding grammar,
  decision tables, or verification algorithm; conformance vectors gained additive classification cases
  and re-pinned `spec_version: "0.3"`.

---

SemVer-Trust Specification © 2026 The SemVer-Trust Authors.
Licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
