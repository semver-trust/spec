<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# SemVer-Trust — Supporting Discussion & Design Record

**Companion to:** the SemVer-Trust specification (normative) — canonical
location `spec/semver-trust.md` in `github.com/semver-trust/spec`
**This document:** explanatory — rationale, rejected alternatives, review findings, open threads, agent handoff
**Date:** 2026-07-13 · **Revision:** r15 (see revision history)
**Audience:** Both human engineering teams, and future AI agents continuing this work

---

## 1. Executive summary

This project retires `go-semver` (a Go utility for managing git tags with semantic versioning) and relaunches the concept for AI-driven development. The core idea: **when agents author a growing share of production code, a version number's implicit claim — "safe drop-in replacement" — needs explicit, verifiable evidence behind it.** SemVer-Trust (working name) defines trust levels T0–T3 derived from cryptographically verified provenance, aggregates them per release using weakest-link flooring with transitive propagation through the workspace dependency graph, encodes the result in SemVer pre-release identifiers so that low-trust releases sort below the corresponding clean release and can be routed through ecosystem-specific opt-in channels, and publishes signed in-toto attestations as the portable, living record.

Two sentences carry the entire design; everything else is derivation:

1. **A version bump is a compatibility claim; a trust level is the strength of evidence behind the claim.**
2. **Trust levels measure attested accountability, not keystrokes.**

Current state: **spec draft v0.10** is published at `spec/semver-trust.md`;
release/review predicate definitions, schemas, core and cryptographic
conformance vectors, and consistency checks are committed. The official Go
implementation consumes the vendored v0.3 conformance contract and has
published v0.1.0 and v0.2.0 as public dogfood under the scheme; the legacy
release path is not suitable for production claims until the successor
predicate behavior is implemented and covered by coordinated conformance
fixtures. v0.4 adds release-range, policy-transition, and authenticated
version-ancestry vectors; v0.5 assigns v0.2 release/review successor predicates
with explicit profile identity; v0.6 requires qualified final-revision review
and canonical actor distinctness; v0.7 defines threshold as a hard
clean-channel accountability gate and separates accountability from blast/risk
policy; v0.8 removes executable derivation proofs from the portable baseline;
v0.9 replaces unconditional resolver-routing claims with ecosystem publishing
profiles and defers non-injective PyPI projection; v0.10 defines source
evidence profiles for SLSA Source and similar source-control evidence.
Decisions are recorded through ADR-035.

## 2. Project origin and intent

- **Starting point (Brad):** retire the `go-semver` repository; relaunch "for the AI age."
- **Founding concept (Brad):** use semantic versioning syntax to identify *trust levels* for a release — a release written and reviewed entirely by AI should not be trusted identically to one written and tested by humans. Included the instinct that a large-blast-radius change written solely by AI might warrant a "breaking" increment even when the same change, human-reviewed, would not.
- **Hard requirements issued during design (Brad):**
  1. Must work for non-OpenAPI-based projects.
  2. Must work for non-Golang projects.
  3. Path-scoped trust is required, because monorepos remain common in a post-AI world (agents favor them: context locality, atomic cross-cutting changes, single enforcement point).
- **Positioning:** the scheme sits beside SLSA/sigstore supply-chain work — human-legible, embedded in the version identifier, focused on *first-party* code provenance — rather than competing with them. The spec is deliberately separable from any implementation (the way SemVer-the-spec is separate from tools), so the idea can outlive one repo.
- **Strategic context (org-internal):** path-scoped trust produces a trust heatmap of the codebase over time — which zones are agent-run vs human-tended and how that boundary moves. This is effectively a per-scope **Presence** measurement (TAC KPI framework) with cryptographic backing instead of survey data: it converts "how much do we trust AI-written code" from a philosophy debate into a dashboard. Expect this to matter for leadership storytelling independent of the tool's engineering value.
- **Naming:** explored `trustver`, `vouch`, `attest`, `semver-agent`, `credence`, `lineage`, and others; leading candidates were `vouch` (evocative, works in a sentence) and `trustver` (discoverable). Decision was deferred at drafting time; **resolved by ADR-013** — the working name became the name, carried by the `github.com/semver-trust` organization. The `semver-trust.dev` domain was registered and the predicate URIs were bound in spec v0.2 (§8).

## 3. Foundational principles and their derivations

These were *derived during discussion*, not assumed. Recording the derivations so future agents understand what breaks if a principle is relaxed.

**P1 — Bump = claim; trust = evidence.** Reframes the founding "AI blast radius = breaking change" instinct without discarding it: an unreviewed AI rewrite of core paths can't *evidence* a PATCH claim ("drop-in safe"), so either the claim escalates or the release waits in an opt-in channel for evidence. Avoids the trap of encoding *who* wrote code as inherently good/bad; encodes what has been *shown*.

**P2 — Accountability, not keystrokes.** Forced by the identity-laundering limit: a developer running an agent locally commits under their own key, and no cryptography distinguishes that from hand-typed code. Rather than pretend, the scheme defines a human signature as an accountability assertion ("this is mine, or I reviewed what was produced under my name"). Consequence: T2/T3 mean "human stands behind it." Hiding this limit would invite exactly the gaming that discredits the scheme; stating it normatively (spec §4.2) is a feature.

**P3 — Weakest link, objectively scoped.** Floors, never averages: one unreviewed autonomous commit can compromise everything around it. Scoping keys off git diff paths (objective ground truth), never declared intent (gameable). Direct corollary: **no de-minimis exception** — any "trivial commits don't count" rule becomes the hiding place for a payload.

**P4 — Degrade honestly.** Ecosystems without a compatibility differ can *prove* less, so more of their releases stay in the pre-release channel until humans or soak time supply what tooling couldn't. Less verification capability ⇒ lower provable trust, never equal trust with less backing. ADR-033 applies the same rule to generated artifacts: a fixed-point generator run is not enough proof to raise trust.

**P5 — Git tag canonical; attestation portable.** Two independent forcing functions: (a) PEP 440 cannot carry arbitrary pre-release identifiers, so any consumer parsing trust out of version strings is non-portable; (b) trust *evolves* after a version string is frozen (post-hoc review, revocation), so the living record must live in supersedable attestations while the tag records trust at release time.

**P6 — Levels order accountability, not risk (ADR-019; steelman review).** Trust levels claim *who stands behind* a change, never a predicted defect rate. Forced by the capability-parity boundary: as agent review quality approaches the human median, a high-evidence T1 release may empirically outperform a rubber-stamped T3 — read as risk-ordering the levels would be falsified by parity; read as accountability-ordering they remain true indefinitely. Risk mapping belongs to the policy layer via the evidence vector. P6 also buffers the keystone empirical claim (trust↔outcome correlation): accountability retains market value — someone to answer, liability attachment, incentive alignment — even if that correlation proves weak.

## 4. Decision record

Decisions live as **one file per ADR under `docs/adr/`** (maintainer convention),
indexed with statuses at `docs/adr/README.md`. Identifiers (ADR-001…) are stable
regardless of location; every ADR reference in this document resolves there.
Field format: Status / Date / Decision / Rationale / Rejected / Revisit trigger
(+ Supersedes where applicable). The ADR index is authoritative for current
status.

| ADR | Title |
|---|---|
| ADR-001 | Encode trust in SemVer pre-release identifiers, not build metadata (superseded by ADR-034) |
| ADR-002 | Trust levels count independent accountable humans |
| ADR-003 | Scalar level in the tag; full provenance vector in the attestation |
| ADR-004 | Derivation proofs are the only exception to weakest-link flooring (superseded by ADR-033) |
| ADR-005 | Bump policy: semantic floor + evidence ceiling, two strategies |
| ADR-006 | Path-scoped trust with transitive propagation is first-class |
| ADR-007 | Configuration is the root of trust; meta-path violations hard-fail (superseded by ADR-028) |
| ADR-008 | Unverifiable ≠ T0: verification failures abort |
| ADR-009 | Promotion: same SHA, new attestation; cascades; supersession over mutation |
| ADR-010 | Trust channel generalizes (and should not mix with) rc |
| ADR-011 | Language-agnostic core; ecosystem plugins; lossy registry projections (registry-projection clause revised by ADR-034) |
| ADR-012 | External dependencies out of scope for v0.1 |
| ADR-013 | Naming and repository topology |
| ADR-014 | Licensing and control strategy |
| ADR-015 | Derivation inputs pin via language-native mechanisms, not environment managers (superseded by ADR-033) |
| ADR-016 | Development environments: outcome-based convention, devbox as maintainer default |
| ADR-017 | Roadmap reorders around demand-side artifacts and keystone instrumentation |
| ADR-018 | Verification interfaces accept injectable trust roots and clock from day one |
| ADR-019 | Trust levels order accountability, not risk |
| ADR-020 | Incorporate go-semver as reviewed re-commits |
| ADR-021 | Implementations consume conformance artifacts as vendored digest-pinned copies |
| ADR-022 | Attestation signatures are SSHSIG over the DSSE PAE with purpose-binding namespaces |
| ADR-023 | Merge commits are created locally, signed and trailered, never by web-flow |
| ADR-024 | Adoption boundary: pre-scheme history is exempt, disclosed, and policy-pinned (superseded by ADR-026) |
| ADR-025 | Self-review exclusion prevents double-counting, not first-counting |
| ADR-026 | Adoption boundary reaffirmed: the motivating lost key was the GitHub web-flow signer (superseded by ADR-027) |
| ADR-027 | Release intervals are explicit and every recurring release chains to the accepted predecessor |
| ADR-028 | Bootstrap trust anchors and the previously accepted policy govern policy transitions |
| ADR-029 | Version ancestry is authenticated independently from release intervals |
| ADR-030 | Predicate v0.1 is historical and successor predicates carry explicit profile identity |
| ADR-031 | Qualified review requires final-revision approval and canonical actors |
| ADR-032 | Threshold is a hard clean-channel accountability gate |
| ADR-033 | Executable derivation proofs are out of the portable baseline |
| ADR-034 | Ecosystem publishing profiles constrain resolver-routing claims |
| ADR-035 | Source evidence profiles consume SLSA Source with explicit verification mode |
| ADR-036 | Version-state digests use a reproducible canonical-JSON profile |

## 5. Design review findings (QA record)

The spec was reviewed *before and after* drafting; recording findings so future agents know these were considered, not missed.

**Caught before drafting (design-level):**

1. **Taxonomy hole** — human-authored/unreviewed code had no level → rederived levels around accountable-human count (ADR-002).
2. **Pre-release precedence interactions** — `rc` vs `t` ordering and the `t10 < t2` lexical hazard → single-digit levels, rc-generalization position (ADR-010).
3. **Immutable registries vs promotion** — version strings baked into npm/PyPI artifacts → republication-from-identical-SHA clause (ADR-009).
4. **Scalar/vector tension** → split responsibilities (ADR-003).
5. **Merge-commit conflict resolutions** are authored changes; PR review attestations don't automatically cover novel resolution hunks (spec §4.3.4).
6. **Dependency cycles** → SCC collapse (spec §5.3).
7. **Cascade re-evaluation** on dependency promotion via pinned floor sources (spec §7.3.4).

**Caught after drafting (document-level):**

8. **Worked-example arithmetic bug** — Appendix A step 4 originally claimed `effective(auth) = T3` after promoting `common`; correct is `min(own T3, common T2) = T2` (same clean-channel outcome, wrong level). Fixed.

**Mechanical verification performed on the spec document:**

- All `§` cross-references resolve to real sections/items.
- SemVer precedence claims (`rc.1 < t1.1`, `t1.1 <` clean, `t10 < t2`, `t0 < t2`) verified by implementing the SemVer comparison rules and testing.
- §3.2 level table ≡ Appendix B grid, and both satisfy the accountability invariant: `level = f(count of accountable humans, agent corroboration)`.
- The TOML policy example parses (`tomllib`); the JSON attestation example parses.

**Adversarial (steelman) review (2026-07-04):** full analysis at `docs/analysis/2026-07-04-steelman.md`. Keystone identified: E2 (trust↔outcome correlation), buffered by V1 (accountability's independent value) — collapse requires the conjunction, which held under pressure. Strongest internal counterargument found: the security-patch velocity conflict under `demote` (queued as a spec §12 open question rather than quietly patched). Dispositions: roadmap reorder (ADR-017), injectable trust roots/clock (ADR-018), P6 (ADR-019), spec v0.2 queue expansion. Standing predictions recorded in the analysis §5: Goodhart equilibrium → "accountability infrastructure first" framing; mixed-authorship decay of the authorship axis toward reviewer-counting; null-E2 repositioning path.

**Protocol audit (2026-07-12):** full analysis at
`docs/analysis/2026-07-12-protocol-audit.md`. F-01 found that literal
`root..TO` excludes the root and arbitrary `FROM` permits history skipping;
ADR-027 replaces ranges with explicit inception/adoption/recurring sets and an
accepted-predecessor chain. F-02 found that loading policy from `TO` lets a
candidate authorize itself; ADR-028 introduces out-of-band bootstrap authority,
previous-policy governance, authority-pinned workflow paths, role/clock
bindings, union meta-path enforcement, and component-local delayed candidate
activation. The audit's F-10 freshness caveat remains explicit in spec §12.9:
signed links do not by themselves prove that a verifier was shown the newest
head. Remaining findings stay issue-tracked and non-normative.

**Legacy-adoption dogfood finding (2026-07-12):** `semver-trust-go` issue #70
showed that the same effective adoption interval produced either a restarted
`v0.1.0` line or continued `v0.10.0` line depending on `FROM` spelling. Spec
issue #36 identified the missing third chain dimension: interval boundary,
source predecessor, and version predecessor are independent. ADR-029 binds
genesis/recurring version state, prerelease target and iteration lineage, raw
and peeled tag identities, and advance/re-cut/supersede behavior. This also
closes the hidden assumption that `current_version` and iteration were safe
caller inputs. Adversarial review additionally made late supersessions and
under-bump corrections attestation-only, carried corrective floors forward, and
accumulated unpromoted target intervals so a high-trust fix cannot launder an
earlier low-trust prerelease.

## 6. External facts relied upon (re-verify before relying)

The design leans on ecosystem behaviors that were asserted from knowledge, not re-checked against live documentation during the founding session. Any agent extending the specification or implementation MUST re-verify them against current docs — several are load-bearing:

| # | Fact relied upon | Load-bearing for |
|---|---|---|
| 1 | Go modules reject build-metadata suffixes; only special suffixes such as `+incompatible` survive canonicalization; nested-module tags use `dir/vX.Y.Z` | ADR-034, ADR-006 |
| 2 | Go modules / npm / Cargo / Python resolver and publication behavior is ecosystem-specific: Go `latest` may fall back to prereleases, npm publication must avoid `latest` for trust prereleases unless ordinary install is intended, Cargo excludes prereleases unless requested, and PEP 440 allows prerelease fallback | ADR-034 |
| 3 | PEP 440 pre-release segments cannot carry the SemVer-Trust `-tN.I` identifier | ADR-034, P5 |
| 4 | SemVer 2.0.0 precedence: numeric identifiers < alphanumeric; alphanumerics compare ASCII-lexically; pre-release < release | ADR-010 (verified mechanically against spec rules, §5 above) |
| 5 | `golang.org/x/exp/apidiff`, `cargo-semver-checks`, `japicmp`, API Extractor exist and detect public-surface breakage | ADR-005, ADR-011 |
| 6 | sigstore gitsign (keyless commit signing), keyless workload identities via OIDC, Rekor transparency log | spec §4.2, §8.2 |
| 7 | in-toto Statement v1 (`https://in-toto.io/Statement/v1`) as the attestation envelope | spec §8 |
| 8 | Claude Code emits `Co-authored-by` trailers for agent-assisted commits | spec §4.1 |
| 9 | npm dist-tags can reference any published version, including pre-releases; `npm publish` sets `latest` unless `--tag` or equivalent registry handling is used | ADR-034 |
| 10 | GitHub's new-repo license picker includes only CC0 among CC licenses; CC BY 4.0 must be added manually (**verified against the live UI, July 2026** — corrected an incorrect assertion made during discussion) | ADR-014 execution |
| 11 | GitHub license detection (Licensee) recognizes verbatim CC BY 4.0 text and badges it; dual-license repos surface a single badge or "View license" | ADR-014 execution |
| 12 | sigstore keyless signing certificates are short-lived by design; verification of historical signatures depends on transparency-log inclusion proofs | ADR-018, conformance fixture design |
| 13 | Git two-dot `A..B` means commits reachable from B excluding A and every commit reachable from A; `git rev-list TO --not BOUNDARY^@` includes the boundary while excluding its parent history | ADR-027, spec §5.2 (**verified against Git documentation and this repository, 2026-07-12**) |
| 14 | Git distinguishes a tag ref's raw target object from its peeled commit; `git merge-base --is-ancestor A B` succeeds exactly when A is an ancestor of or equal to B | ADR-029, spec §7.5 (**verified by the conformance Git command gate, 2026-07-12**) |

## 7. Current state and artifacts

| Artifact | Status |
|---|---|
| GitHub organization `semver-trust` | **Exists** (created July 2026). Pending: `.github` profile repo/README as the org front door. |
| `spec` repository | **Active**; contains the draft v0.10 normative spec, design record, ADRs through ADR-035, predicate definitions, schemas, conformance vectors, consistency checks, governance files, and the dual-license arrangement. |
| Normative spec | **Draft v0.10** at `spec/semver-trust.md`; Appendix C–K record the v0.2–v0.10 deltas. |
| This document | Explanatory companion, revision r17. |
| `TRADEMARK.md` | **Committed**; ecosystem naming, conformance claims, fork naming, and affiliation rules are documented. IP-counsel review remains advisable if traction arrives. |
| `semver-trust-go` repository | **Conformance-aligned through draft v0.10**; consumes the digest-pinned v0.10 conformance suite and has published v0.1.0 and v0.2.0 as dogfood. Its legacy production release path is still not suitable for v0.10 production claims until the ported trust-chain, successor-predicate, publishing-profile, and source-evidence evaluators are wired into release and verify flows. |
| Formal JSON Schemas for predicates | **Emitted at v0.1 and draft successor v0.2** under `schemas/`, with Apache 2.0 licensing and closed-object validation. Predicate v0.1 is historical; v0.2 carries the compatibility-critical successor bindings. |
| Release/review predicate definitions | **Published at v0.1 and v0.2** under `release/` and `review/`; the first DSSE fixture emission occurred in spec PR #16 and remains v0.1 historical evidence. |
| Conformance suite | **Implemented for draft v0.10**; covers level assignment, qualified review classification, precedence, release intervals/predecessors, policy bootstrap/transitions, authenticated version ancestry, propagation, aggregation, derivation-fail-closed behavior, thresholded decisions, ecosystem publishing-profile registry projection, source-evidence profile binding, commit signatures, DSSE attestation verification, successor predicate schema registration, unsigned v0.2 schema-instance fixtures, and signed positive v0.2 DSSE fixtures. |
| Predicate-type domain | **Registered and wired:** `semver-trust.dev`; v0.1 and v0.2 release/review predicate definitions are present in the Pages source. |
| Name | **Decided:** SemVer-Trust (ADR-013). |
| Licensing & control | **Implemented** per ADR-014: CC BY 4.0 prose, Apache 2.0 machine-consumable artifacts, directory-local Apache license copies, and trademark-based conformance control. CLA-vs-DCO remains deferred until the first external contribution. |
| Old `go-semver` repo | Supersession notice tracked in `semver-trust-go` issue #60. |

## 8. Open threads and next steps

**Pressure-test with the team first** (predicted adoption-friction points, in order):

1. ~~**Unverifiable → fail adoption pressure**~~ — the adoption boundary was designed through ADR-024/026, then made an immutable bootstrap-pinned chain anchor whose commit is included by ADR-027. ADR-028 defines the bootstrap authority; ADR-029 independently preserves or starts the component's version line.
2. **No de-minimis** (P3, spec §5.1): expect "why did a typo fix demote our release" complaints; the answer is accountable review, narrower scopes, or local policy outside portable conformance — not an executable derivation waiver. Possible gap: a `docs`-scope carve-out via scope weights vs. flooring. Undecided.
3. **Meta-path hard-fail** (ADR-007): interacts badly with agents that helpfully "fix" CI workflows mid-task. Contributor policy and agent contracts (CLAUDE.md) must warn agents off meta-paths explicitly.

**Then, roughly in order:**

4. ~~Decide the name; register and wire the predicate-type domain~~ (done — ADR-013; `semver-trust.dev` registered and predicate definition pages committed).
5. ~~Populate the `spec` repository and implement its dual-license arrangement~~ (done; org `.github` profile remains optional follow-up work).
6. ~~Execute the spec v0.2 pass and formalize v0.1 release/review schemas~~ (done; spec Appendix C records the delta, and the schemas were first emitted in PR #16).
7. ~~Build the core and cryptographic conformance suites~~ (done; ADR-021 defines their digest-pinned consumption contract).
8. ~~Build and dogfood the Go reference implementation~~ (v0.1.0 and v0.2.0 released under the scheme). Remaining per ADR-017: a minimal demand-side consumer (`verify` GitHub Action + README trust badge) and retrospective trust profiling — the E5 artifact and E2 test, respectively.
9. Dogfood target #2: Brad's Go API starter repo (oapi-codegen) — it already has the human-reviewed-contract philosophy and a `CLAUDE.md` agent contract; after ADR-033, generated outputs need ordinary accountable review or a future accepted proof profile before they can raise trust in portable conformance.
10. Design the `go-semver` retirement/redirect story (deprecation notice pointing at the org).
11. Revisit spec §12 open questions as evidence accumulates (T1 efficacy, trust decay, SLSA Build mapping for external dependencies, cross-repo propagation). Note the irony recorded for honesty: the project defining transitive trust for monorepos chose a polyrepo for itself, so cross-repo trust (spec §12.4) will eventually be felt firsthand.

## 9. Agent handoff contract

Instructions to any agent (or human) resuming this work:

1. **Document precedence:** the spec — `spec/semver-trust.md` in `github.com/semver-trust/spec` — is normative. This document explains *why*; where they conflict, the spec wins and the conflict should be reported as a defect.
2. **Do not re-litigate rejected alternatives** (ADR "Rejected" entries) without *new evidence or a changed requirement*. In particular: build-metadata encoding (ADR-001), de-minimis exemptions (P3/ADR-033), unverifiable→T0 (ADR-008), and inflation-as-only-strategy (ADR-005) were each rejected for stated reasons that have not changed.
3. **Change protocol:** decisions change by *superseding* — create `docs/adr/NNNN-slug.md` with the next number and a `Supersedes:` field; never edit an accepted ADR's Decision/Rationale/Rejected content in place (the sole permitted edit to a superseded file is its Status line, set to `Superseded by ADR-NNN`). Update the `docs/adr/README.md` index. Mirror material changes into the spec with a version bump of the spec itself. Predicate v0.1 remains historical and cannot carry draft v0.10 interval, policy, version-state, qualified-review, threshold-decision, derivation-fail-closed, publishing-profile, or source-evidence claims; do not mutate it. Successor predicate changes after first emission require a new predicate URI when validation or interpretation changes.
4. **Before implementing anything**, re-verify §6 facts against current ecosystem documentation; several postdate nothing but all predate you.
5. **Terminology discipline:** use the spec's §2 terms exactly (own trust vs effective trust; scope vs component; channel; accountable human). Drift here has already been the source of one caught bug (§5.8).
6. **Honesty clauses are load-bearing:** P2 (accountability, not keystrokes) and P4 (degrade honestly) are commitments, not caveats. Any feature that quietly claims more than the evidence supports — e.g., inferring authorship the signatures can't prove, or waiving evidence where a differ is missing — violates the design's core defense against being discredited.
7. **Implementation coordination:** the conformance artifacts are the cross-repository contract; implementations consume vendored, digest-pinned copies under ADR-021. Change the specification and conformance source first, then update implementation copies and behavior.
8. **Context that won't be in the repo:** the founding conversation reframed "AI blast radius should force a breaking change" into the semantic-floor/evidence-ceiling split (ADR-005) — if a stakeholder asks why big AI changes don't bump MAJOR, that reframing (P1) is the answer, and `strategy = "inflate"` exists for orgs that insist.
9. **Agent-contract files:** `AGENTS.md` is the canonical per-repo agent contract — vendor-neutral, matching the project's own thesis — and `CLAUDE.md` is a two-line pointer for tools that read only that file. Replicate the pair in every repository.

---

## Appendix: Conversation timeline (condensed)

1. **Naming exploration** for a `go-semver` successor "for the AI age" → surfaced trust/provenance-centric candidates; deferred.
2. **Founding concept** (Brad): semver-encoded trust levels; AI-authored large-blast-radius changes as possibly "breaking."
3. **Design session:** four enforcement points (commit / merge / release / consume + attestation store); trust taxonomy v1; weakest-link flooring; reproducibility exception for generated code; pre-release-identifier encoding discovered as the key trick (ordering/routing friction; Go build-metadata blocker); bump-claim reframing (P1); identity-laundering limit → accountability principle (P2).
4. **Generalization requirements** (Brad): non-OpenAPI, non-Go, path-scoped monorepo trust → derivation proofs (ADR-004), plugin architecture (ADR-011), transitive propagation with the auth/billing/common worked example (ADR-006), meta-paths (ADR-007).
5. **Spec drafting with review** ("double-check your work"): four design-level fixes pre-draft, mechanical verification post-draft, one arithmetic bug caught and fixed (§5).
6. **This document** (r1).
7. **Repository topology** (Brad: two repos, spec + Go implementation) → conformance-suite-as-sync-contract insight; org recommendation → `github.com/semver-trust` created; naming resolved as a conscious side effect of repo creation → ADR-013.
8. **Licensing** (Brad: control vs. traction weighing) → ADR-014, control moved to trademark/governance/copyright levers; execution correction — GitHub's picker offers no CC BY (verified live; CC0 rejected as inverted intent) → manual verbatim paste; `TRADEMARK.md` drafted as ADR-014 lever (a).
9. **Spec committed** to the `spec` repo as `semver-trust.md`; design record revised to r2. Root files landed: `LICENSE` (CC BY 4.0 legalcode, verbatim incl. the CC trailer block), `LICENSE-APACHE` (nit fixed: hyphen), `TRADEMARK.md`, README license map, `CONTRIBUTING.md` CLA/DCO guard, `CLAUDE.md` agent contract.
10. **ADR extraction**: 14 ADRs relocated verbatim to one-file-per-decision layout with index; design record §4 became the pointer/index; r3.
11. **`semver-trust-go` starter set:** provenance hygiene from commit #1 (signing, trailers, merge-commits-only) as a project deliverable; contract convention corrected after a tool-agnosticism review (Brad) to **AGENTS.md canonical + CLAUDE.md pointer**; `.gitmessage` trailer examples neutralized across agent tooling.
12. **Environment tooling evaluation** (devbox/direnv vs. 2026 alternatives; mise Go-issue follow-ups dissolved on inspection) → ADR-015 (self-contained derivation pins — extends P5 to verification portability) and ADR-016 (outcome-based convention, devbox maintainer default, explicit mise trigger).
13. **Steelman analysis** (maintainer-directed) of specification and codification strategy → `docs/analysis/2026-07-04-steelman.md`; ADR-017 (demand-side artifacts + keystone instrumentation), ADR-018 (injectable trust roots/clock), ADR-019 (P6); spec v0.2 queue expanded; r4.
14. **Domain registered** (`semver-trust.dev`, 2026-07-03) → **spec v0.2 pass executed** per §8.6: placeholders resolved, P6 and ADR-015 mirrored, §12.7–12.8 added, predicate URIs bound (review predicate aligned `v1`→`v0.1` pre-first-attestation); verification suite re-run clean; this revision (**r5**).
15. **Schemas and conformance core:** v0.1 release/review JSON Schemas, level/precedence vectors, aggregation/decision vectors, and digest-pinned consumption landed (ADR-020–ADR-021).
16. **Cryptographic conformance:** purpose-bound SSHSIG verification and DSSE predicate fixtures landed; the DSSE fixture PR was the first v0.1 predicate emission (ADR-022).
17. **Repository provenance controls:** locally signed/trailered merge commits and reviewable branch-ruleset artifacts landed (ADR-023).
18. **Reference implementation dogfood and spec v0.3:** the Go implementation released v0.1.0 and v0.2.0 under the scheme; adoption-boundary and self-review pressure produced ADR-024–ADR-026 and spec v0.3.
19. **Protocol audit trust-chain disposition and spec v0.4:** F-01/F-02 produced ADR-027–ADR-028; release intervals now include inception roots/adoption boundary and chain to accepted predecessors, while bootstrap/previous policy governs transitions. Range and policy-transition vectors landed; predicate successor and Go implementation follow separately.
20. **Legacy version-line dogfood and authenticated ancestry:** `semver-trust-go` #70 exposed `FROM` as both interval and version donor; spec #36 produced ADR-029 and §7.5. Bootstrap now distinguishes null version genesis from an immutable legacy predecessor; recurring state derives targets/iterations, carries unpromoted target evidence and corrective floors, and rejects moved/ambiguous tags, trust laundering, and caller overrides.
21. **Successor predicate contract:** spec #33 produced ADR-030, `release/v0.2`, `review/v0.2`, and schemas that bind explicit profile identity plus release-interval, policy, and version-state continuity. Predicate v0.1 remains historical. Unsigned v0.2 schema fixtures are present; signed DSSE fixtures and Go implementation remain follow-up work.
22. **Qualified review and canonical actors:** spec #32 produced ADR-031, draft v0.6, canonical actor identity rules, qualified final-revision/final-diff review semantics, review/v0.2 schema refinements before first emission, and review-qualification conformance vectors.
23. **Threshold and risk-policy separation:** spec #31 produced ADR-032, draft v0.7, threshold as a hard clean-channel accountability gate, a deterministic baseline decision order, threshold-bearing release/v0.2 decisions, and threshold decision vectors.
24. **Executable derivation retirement:** spec #34 produced ADR-033, draft v0.8, no executable derivation proofs in the portable baseline, fixed-point evidence distinguished from derivation evidence, and fail-closed aggregation vectors for derivation claims.
25. **Signed successor fixtures:** spec #33 follow-up added signed positive
    DSSE envelopes for `release/v0.2` and `review/v0.2`, extending the
    attestation checker's independent skeleton validation to successor
    predicates while retaining v0.1 historical fixtures.
26. **Ecosystem publishing profiles:** spec #30 produced ADR-034 and draft
    v0.9, replacing unconditional prerelease/default-resolver claims with
    ecosystem profiles for Go modules, npm, Cargo, and Python/PyPI. PyPI
    projection is deferred until an injective mapping exists, and same-source
    promotion is separated from artifact-digest equality.
27. **SLSA Source and source evidence binding:** spec #28 produced ADR-035 and
    draft v0.10. SLSA Source is consumed through explicit source evidence
    profiles with replay vs trusted-issuer modes, repository/resource and
    subject matching, issuer authorization, digest algorithms, and
    freshness/equivocation semantics. `release/v0.2` remains schema-frozen; v0.10
    bindings use the declared extension map unless a future predicate URI adds
    first-class fields.
28. **Reference implementation conformance catch-up:** `semver-trust-go` PRs
    #79–#89 re-vendored the digest-pinned draft v0.10 suite and added enforced
    consumers for the hardening groups: threshold decisions, release intervals,
    policy transitions, authenticated version ancestry, qualified review,
    source evidence, publishing profiles, and predicate-v0.2 schema/extension
    checks. This satisfies the independent-consumer gate for spec issues #26 and
    #29; production wiring remains implementation work tracked in
    `semver-trust-go` #76.

---

## Revision history

| Rev | Date | Changes |
|---|---|---|
| r1 | 2026-07-04 | Initial record: principles P1–P5, ADR-001…012, QA record, external-facts table, handoff contract, timeline 1–6. |
| r2 | 2026-07-04 | Added ADR-013 (naming/topology) and ADR-014 (licensing/control); §1 and §2 updated for resolved naming; §6 facts 10–11 added; §7 current-state table rebuilt around live repos; §8 next steps renumbered (4–11) with domain registration on the critical path; §9 cross-references updated (items 1, 7); timeline 7–9; this table. |
| r3 | 2026-07-04 | ADRs extracted verbatim to `docs/adr/` (one file each + index); §4 converted to pointer + title index; §9 change protocol updated with file-per-ADR mechanics; document destined for `docs/design-record.md`; timeline 9 amended for root-file completion, entry 10 added. |
| r4 | 2026-07-04 | Steelman review integrated: P6 added to §3; §5 adversarial-review block; §6 fact 12; §4 index rows ADR-015…019; §8 items 6 and 8 expanded (v0.2 queue with Appendix-A pointers; ADR-017/018 requirements); §9 item 9 (AGENTS.md convention); timeline 11–13. |
| r5 | 2026-07-04 | Domain registration recorded; spec v0.2 pass marked executed (§7 rows, §8 items 4 and 6); timeline 14. |
| r6 | 2026-07-12 | Synchronized the canonical spec path, draft v0.3 and implementation status, ADR index through ADR-026, artifact table, completed roadmap items, handoff guidance, and timeline 15–18. |
| r7 | 2026-07-12 | Integrated protocol-audit F-01/F-02 dispositions: ADR-027–ADR-028, draft v0.4 trust-chain semantics, role/clock/workflow and component-local policy-transition rules, new conformance groups, v0.1 predicate limitation, artifact/roadmap status, external fact 13, and timeline 19. |
| r8 | 2026-07-12 | Integrated legacy-adoption dogfood issue #36: ADR-029, authenticated version state/actions, target-lineage and corrective-floor invariants, version-ancestry vectors/oracle, raw/peeled ref and iteration checks, artifact/handoff updates, and timeline 20. |
| r9 | 2026-07-12 | Integrated successor-predicate contract: ADR-030, draft v0.5, release/review v0.2 predicate pages and schemas, explicit profile identity, v0.1 historical status, unsigned v0.2 schema fixtures, conformance pin update, artifact table, and timeline 21. |
| r10 | 2026-07-12 | Integrated qualified-review hardening: ADR-031, draft v0.6, canonical actor distinctness, active final-revision/final-diff approvals, review/v0.2 schema refinement before emission, review-qualification vectors, and timeline 22. |
| r11 | 2026-07-13 | Integrated threshold/risk-policy hardening: ADR-032, draft v0.7, hard clean-channel threshold gate, deterministic baseline decision order, threshold-bearing release decisions, threshold vectors, artifact table, and timeline 23. |
| r12 | 2026-07-13 | Integrated executable-derivation hardening: ADR-033, draft v0.8, derivation claims ignored for portable trust re-leveling, Appendix A update, aggregation vectors, artifact table, and timeline 24. |
| r13 | 2026-07-13 | Added signed v0.2 successor DSSE fixtures for #33, extended attestation skeleton validation to v0.2 predicates, updated conformance docs, artifact table, and timeline 25. |
| r14 | 2026-07-13 | Integrated ecosystem publishing profile hardening: ADR-034, draft v0.9, narrowed resolver-routing claims, deferred non-injective PyPI projection, clarified same-source promotion, artifact table, external-facts table, and timeline 26. |
| r15 | 2026-07-13 | Integrated SLSA Source/source-evidence hardening: ADR-035, draft v0.10, source evidence profiles, replay vs trusted-issuer modes, subject/resource matching, freshness/equivocation semantics, source-evidence vectors, artifact table, and timeline 27. |
| r16 | 2026-07-13 | Added adversarial publishing-profile conformance coverage for ADR-034/§7.4: Go prerelease fallback, npm latest/dist-tag behavior, Cargo prerelease opt-in, deferred/non-injective PyPI projection, registry-not-authority, and same-source promotion artifact claims. |
| r17 | 2026-07-14 | Recorded `semver-trust-go` draft v0.10 conformance alignment through PRs #79–#89, satisfying the independent-consumer gate while leaving production release/verify wiring tracked separately. |
