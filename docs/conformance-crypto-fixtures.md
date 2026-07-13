<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Conformance Cryptographic Fixtures — Design Plan

**Status:** Signed off by the maintainer 2026-07-06 (§7); the SSH and DSSE
fixture phases are implemented under `conformance/crypto/`, while the keyless
phase remains planned. This document records the fixture design. The governing decision is
[ADR-018](adr/0018-verification-interfaces-accept-injectable-trust-roots-and-clock-from-day-one.md);
the finding that motivates it is the fixture-aging boundary condition in
[the steelman analysis §3.2 item 6](analysis/2026-07-04-steelman.md).

The purpose is to fix, before any key or fixture exists, the small set of decisions that are expensive to
change afterwards: what test key material exists, where it lives, what instant every fixture verifies at, and
how the two hard cases — SSH allowed-signers and sigstore keyless — stay verifiable indefinitely.

## 1. Problem: why naive cryptographic fixtures rot

A conformance suite is only a durable sync contract if its expectations do not change with the calendar. The
timeless core of SemVer-Trust — level assignment (spec §3.2), version precedence (§7), aggregation (§5) —
fixtures cleanly: the inputs and expected outputs are pure data. Cryptographic verification (§4.2, §8.2, §10)
is where a naive fixture decays, for three compounding reasons:

- **Keyless signing certificates are short-lived by design.** sigstore Fulcio issues leaf certificates with
  validity windows measured in minutes, on the theory that the transparency-log record, not the certificate
  lifetime, is the durable proof. A fixture that embeds a real Fulcio certificate is expired within the hour.
- **Historical verification depends on transparency-log inclusion.** Verifying a past keyless signature means
  proving the certificate was valid *at the instant it was logged* — which requires the log's inclusion proof
  and the roots that were trusted then. Both drift: production roots rotate, and a recorded proof is only
  checkable against the root that signed it.
- **Real signatures embedded in fixtures decay** (steelman §3.2.6). Left unaddressed, the suite quietly
  narrows to testing only the timeless core and skips cryptographic verification — the hard part, and the part
  cross-implementation agreement most needs pinned.

ADR-018's answer is an interface invariant: every verification path accepts explicitly injected trust
material (allowed-signers registries, CA and transparency-log roots, identity maps) and an injected
verification clock — no package globals, no implicit system time, no ambient network fetch of roots. Under
injected roots and a pinned clock, a fixture verifies to the same result on any future date. This same
capability is what retrospective trust profiling ([ADR-017](adr/0017-roadmap-reorders-around-demand-side-artifacts-and-keystone-instrumentation.md))
requires, since profiling the past is verification of the past. Everything below is the concrete shape of the
fixtures that invariant makes possible.

## 2. Fixture key strategy — SSH allowed-signers path (`GO-031`)

### 2.1 Recommended key set

Vendor long-lived Ed25519 test keypairs — no expiry, so the SSH path has no time-bomb of its own and the
pinned clock (§3) governs validity only through explicit allowed-signers options. Ed25519 matches the spec's
first-class example (§4.2, §9 `allowed_signers`) and the Go toolchain's native support. The proposed set:

| Label | Class | Role in fixtures |
|---|---|---|
| `human-alice` | Human | Enrolled human author; drives T2 and, as author, T3. |
| `human-bob` | Human | Second, distinct enrolled human; the independent reviewer that makes T3 reachable (§3.2). |
| `agent-ci-bot` | Agent | Machine identity for agent-authored / CI-signed commits; drives T0 and T1. |
| `unknown-mallory` | Unknown | Valid Ed25519 key **not** in any allowed-signers file → the unknown-signer abort case. |
| `revoked-carol` | Revoked | Enrolled, then invalid at the fixture epoch → the revoked-signer abort case, distinct from unknown. |

`unknown-mallory` and `revoked-carol` are deliberately separate: "signer never enrolled" and "signer enrolled
but not valid at the verification instant" are different failure modes, and §10 step 5 aborts on both
(unverifiable ≠ T0). Keeping them distinct lets the suite prove the verifier distinguishes them. GPG is a
permitted alternative in §4.2; a parallel GPG key family is deferred (§7 OQ3, resolved) so `GO-031` ships one
signing format first — **with fail-closed proven, not assumed** (maintainer rider, 2026-07-06): the verifier's
key-family seam must be extensible rather than SSH-hardcoded, and the suite includes a vector containing a
GPG-signed commit whose **expected outcome is verification failure** (unverifiable ⇒ abort, §5.2) — a verifier
that cannot verify a key family must treat it as unverifiable, never skip or silently degrade. The conformance
README documents this capability limitation so "v1 conformant" is honest about what it covers.

### 2.2 Location decision — recommend the spec repo

Two forces pull in opposite directions:

- **Vectors-as-sync-contract argues the spec repo.** `conformance/` is defined as the sync contract with
  implementations (spec `AGENTS.md`). ADR-018 rejects regenerating fixtures per CI run *precisely* because it
  "breaks cross-implementation identity of the vectors." Key material that a future Rust or JS implementation
  must verify against has to be *the same bytes* everyone verifies against — which means one vendored copy in
  the normative repo, not a copy forked into each implementation's test tree.
- **Key-material hygiene argues the implementation repo.** Committing private keys — even public-by-
  construction test keys — into the normative spec repo invites secret-scanner noise and reads, at a glance,
  like a mistake.

**Recommendation: the spec repo, under `conformance/crypto/`.** Cross-implementation identity is the whole
reason ADR-018 forbids per-run regeneration; scattering the keys into implementation test trees reintroduces
exactly the fork it rejects. The hygiene objection is real but addressable with labeling and scanner
allowlisting (§2.4), whereas the identity property cannot be recovered once vectors diverge. The alternative —
Go-repo `internal/.../testdata` — is rejected on that ground: it would make the vectors Go-specific and
un-shareable.

What lives in `conformance/crypto/` is the durable, language-neutral material: the vendored public/private
test keys, the allowed-signers and revocation files, the pinned sigstore roots (§4), the signed attestation
envelopes (§6), and the expected verification outcomes. The fixture git repositories are **not** committed
there (§5). How the Go suite reads this material offline for `GO-032`'s no-network acceptance is the same
distribution question the `GO-011`/`GO-012` conformance vectors already face (git submodule or a vendored,
digest-pinned copy); it rides that shared mechanism and is not re-solved here.

### 2.3 allowed-signers fixture format

Fixtures ship OpenSSH `allowed_signers` files in their native format — one principal line per enrolled key,
scoped to the git namespace, with validity options where a case needs them:

```text
# conformance/crypto/keys/allowed_signers  (illustrative — TEST KEYS, DO NOT USE)
alice@semver-trust.test namespaces="git" ssh-ed25519 AAAA...alice  semver-trust-conformance TEST KEY - DO NOT USE
bob@semver-trust.test   namespaces="git" ssh-ed25519 AAAA...bob    semver-trust-conformance TEST KEY - DO NOT USE
ci-bot@semver-trust.test namespaces="git" ssh-ed25519 AAAA...bot   semver-trust-conformance TEST KEY - DO NOT USE
```

Revocation is modeled two ways, matching the two negative cases: `revoked-carol` is expressed either by an
explicit revoked-keys list or by a `valid-before` option whose instant precedes the fixture epoch, so the key
was enrolled but is invalid at verification time; `unknown-mallory` is simply absent from every file. Negative
fixtures pin their allowed-signers state exactly like positive ones — the registry is injected trust material
(ADR-018), so it is part of the fixture, never the verifier's ambient environment.

### 2.4 Security requirements for test keys

Test keys are public by construction — their private halves are committed on purpose. That is safe only if
they can never be mistaken for, or used against, real infrastructure. Requirements:

- **Reserved identity domain.** Every fixture identity uses `@semver-trust.test`. The `.test` TLD is reserved
  by RFC 6761 and is never globally resolvable, so no fixture identity can collide with a real account.
- **Distinctive comment string in every key.** Every fixture key's comment MUST contain
  `semver-trust-conformance TEST KEY - DO NOT USE`. This makes the intent legible in the key itself, in
  `allowed_signers` lines, and in any log that echoes the comment — and gives secret scanners a stable string
  to allowlist.
- **Scanner allowlisting is explicit, not silent.** `conformance/crypto/**` is registered as intentional test
  material in the repo's secret-scanning configuration, so committing the private keys is a recorded decision
  rather than a bypassed alarm.
- **No real trust anchors.** Fixture keys are never added to any real `allowed_signers`, CI signing config, or
  release path. They exist only inside the conformance tree and the fixture repos built from it.

## 3. Pinned-clock strategy

Every fixture records a `verification_time` in RFC 3339, UTC. All key and certificate validity windows in that
fixture bracket that instant, and verification is reproducible on any later date by injecting that clock — no
wall-clock reads (ADR-018).

**Recommend one canonical fixture epoch for the whole suite: `2026-01-01T00:00:00Z`.** A single shared epoch
means one clock value to inject across every fixture and one instant to reason about; it removes a whole class
of "which fixture uses which time" mistakes. Concretely:

- **Long-lived SSH/GPG keys** carry no inherent trusted timestamp. The verifier applies the injected
  `verification_time` against the key's allowed-signers `valid-after`/`valid-before` window (where present) and
  the revocation state as of that instant. This is the clock ADR-018 injects.
- **Keyless (sigstore) material** carries its own trusted timestamp: the transparency-log inclusion time (and
  any signed timestamp), recorded *in the fixture*. Cryptographic validity is anchored to that logged instant
  against the injected roots, so it is pinned by the fixture data itself; the injected `verification_time`
  still bounds policy-level freshness. Fixture roots and certificate windows are constructed to bracket the
  epoch so the logged instant and the injected clock agree.

Both paths therefore verify to the same result forever under injected roots and the pinned clock — the SSH
path because the clock is injected, the keyless path because the trusted instant is recorded and its roots are
vendored.

## 4. Keyless (sigstore) strategy (`GO-032`)

This section fixes *what is vendored versus generated* and *why*; the generation mechanism is Phase 3
implementation detail (`GO-032`) and is deliberately not specified here.

Options considered:

- **(a) Vendor sigstore's own test PKI.** sigstore-go ships test trust material and could be reused directly.
  Rejected as the contract: it is Go-specific and not a stable public interface — a future implementation on a
  different sigstore library would not share those bytes, breaking the cross-implementation identity of the
  vectors (ADR-018). ("sigstore-go ships test material" is the implementation plan's claim; either way the
  conformance vectors must be *our* vendored roots, not a borrowed library's internal testdata.)
- **(b) Generate a minimal, self-contained test PKI at fixture-build time and vendor the output.** A test
  Fulcio-style CA issues leaf certificates whose validity brackets the epoch (§3), with an OIDC-style identity
  SAN; the signing material and its inclusion record are produced against *our* test transparency-log key; the
  resulting bundles and roots are vendored as static files. **Recommended.**
- **(c) Record live sigstore material and pin the roots.** Rejected: it rots (short-lived certs, rotating
  production roots) and couples the suite to real infrastructure — the exact failure ADR-018 names.

**Decision (maintainer, 2026-07-06): (b)'s destination, reached by a staged, borrowed-before-built route.**
Keyless is not an edge case in this scheme — spec §4.2 requires CI agents to commit under machine identities,
which in practice means sigstore keyless, so a suite thin on keyless would certify verifiers that never proved
the mainstream path. But a fully hand-rolled generator has a worse failure mode than thinness: subtly wrong
Merkle inclusion proofs, checkpoints, or SETs do not fail — they freeze a wrong interpretation of sigstore
verification into the conformance contract. Four binding riders defuse that:

1. **Borrow before building.** Vendor or generate keyless material via the sigstore project's own
   client-conformance tooling and test material first; hand-roll only the gaps.
2. **The freeze gate: cross-verification admits a fixture, never generator correctness.** Before any bundle
   lands in `conformance/`, it must verify with an independent, pinned reference client (cosign or
   sigstore-go) under the same vendored roots and pinned clock the fixture declares.
3. **Staged depth.** v1 ships the long-lived-key fixtures complete, plus a small but fully real keyless set:
   one happy-path bundle exercising the entire chain (leaf certificate to test CA, inclusion proof,
   checkpoint, SET, time window against the injected clock) and three to four failure cases — certificate
   expired at the pinned clock, wrong identity, tampered payload, bad inclusion proof. The failure cases are
   not optional garnish: fail-closed is spec law (unverifiable ⇒ abort, §5.2), so the suite must prove
   verifiers reject, not just accept. Deferred: the bundle-format version matrix and exotic CT/SCT edges.
4. **Fixture provenance.** The conformance README documents how each fixture was produced, what validated it,
   and at which pinned versions — fixtures for a provenance scheme carry their own provenance.

The injectable trust material — carried in the sigstore trusted-root format so it plugs straight into the
verifier per ADR-018 — is a **test Fulcio CA certificate, a test Rekor (transparency log) public key, a test
CT-log key, and optionally a test timestamp-authority certificate**, all **vendored** static files under
`conformance/crypto/`, never fetched. Per-fixture keyless material is generated at fixture-build time (per
rider 1) and its output vendored, so unit tests read only local bytes and satisfy `GO-032`'s no-network
acceptance. If a homegrown generator does end up written despite rider 1, the "generator untrusted,
cross-validation admits" rule graduates to a durable decision record (ADR) at that point.

## 5. Fixture repository construction

Per the implementation convention (go-repo `AGENTS.md`: fixture repositories are constructed by scripts, never
committed as opaque `.git` blobs), the fixture git repositories are **built by deterministic scripts at test
time**, not stored. The suite must cover the repository shapes that `GO-030`/`GO-031` acceptance exercises:

| Fixture repo | Exercises | Expected outcome |
|---|---|---|
| squash-forbidden | §4.3.3 — squash/rebase merge under a policy that forbids it | verification aborts |
| merge-with-conflict-hunks | §4.3.4 — merge commit with a non-empty (conflict-resolution) diff | novel hunks classified as authored; review attestation does not auto-cover them |
| first-release inception | §5.2 / §10 step 3 — enumerate `git rev-list TO` | every reachable root included; levels assigned across the whole history |
| unknown-signer abort | §10 step 5 — commit signed by `unknown-mallory` | abort (unverifiable ≠ T0) |
| unverifiable-commit abort | §10 step 5 — invalid signature or missing covering attestation | abort |

Determinism is the constraint — not polish, but what makes SHA-level expectations possible at all. Scripts pin
every input a commit SHA depends on: `GIT_AUTHOR_DATE` and `GIT_COMMITTER_DATE` set to the fixture epoch (§3),
fixed author/committer name and email (the `@semver-trust.test` identities), fixed messages and trailers,
signing with the §2 test keys via git's SSH signing configuration, and **an explicitly pinned object format
(`sha1`)** so a future git default flip to SHA-256 cannot silently change every SHA. With all SHA inputs
pinned, the built history is byte-identical across runs and machines.

**Decision (maintainer, 2026-07-06): the build script lives in the spec repo's `conformance/`**, not the Go
repo — it is contract-adjacent regeneration/audit tooling, by the same reasoning that settled the
key-material location (§2.2). A ported script suffices now; a language-neutral manifest waits for a second
implementation (recipe language and implementation language are independent — a Rust implementation can run a
bash-and-git script).

**Decision (maintainer, 2026-07-06): dual assertion.** Expected outcomes reference commits by stable role
label (e.g. `author-t3-commit`) for readability, **and** additionally assert the pinned SHAs as a
build-recipe-drift tripwire. When a SHA assertion fails, the harness error must diagnose, not just report:
"fixture build recipe drifted — expected `<sha>` for role `<label>`, got `<sha>`; the recipe or its inputs
changed" — a bare mismatch reads as corruption, a recipe-drift message tells the next agent which class of
bug it is holding.

## 6. Attestation fixtures

Attestation fixtures are DSSE envelopes signed by the §2 test keys over in-toto
Statements. They use the **real** predicate-type URIs — initially
`https://semver-trust.dev/release/v0.1` (spec §8.1) and
`https://semver-trust.dev/review/v0.1` (spec §4.3), later also the v0.2
successor predicate URIs — never a placeholder, per the implementation plan's
ground rule. Because §8.2 makes the signature inside the attestation the trust
anchor and storage never the anchor, fixtures store envelopes as plain vendored
files under `conformance/crypto/`; no git-notes, OCI, or Rekor store needs
faking.

**Reconciling the two constraints.** The real predicate URIs must coexist with go-repo `AGENTS.md` gate 2,
which requires fixture attestations to be clearly-labeled test doubles that cannot escape the test tree. The
compliant combination is:

- **Real predicate-type URIs** — the URI is a *type name* the verifier matches, not a secret or a live
  endpoint. Using the real one is required for the fixture to exercise real predicate-type matching, and it is
  no longer a placeholder: spec §12.6 naming is resolved (v0.2,
  [ADR-013](adr/0013-naming-and-repository-topology.md)), the URIs are bound in §4.3 and §8.1, and the
  `semver-trust.dev` domain, CNAME, and predicate pages exist.
- **Fake local subjects** — subjects are the fixture repos' own commit SHAs and tags, which exist only inside
  the built fixture repositories and name nothing real.
- **Test-only signing keys** — the §2 keys, unusable against any real infrastructure.

Real URIs plus fake local subjects plus test-only keys is what keeps a fixture a test double while still
verifying the real predicate path. Building these fixtures is plausibly the *first emission* of these
predicate types, and first emission freezes the predicate-type version — the spec had deliberately held that
flexibility open (Appendix C records the review predicate's `v1` → `v0.1` realignment as "permissible only
because no attestation has yet been emitted").

**Decision (maintainer, 2026-07-06): v0.1 is frozen** — fixtures may emit against the real URIs, under two
binding riders:

1. **Sequencing gate.** No fixture gets signed until the GO-010 JSON Schemas are maintainer-reviewed and
   merged, and every fixture payload must validate against those schemas *before* the signing ceremony —
   signed bytes cannot be patched, only regenerated, and regeneration breaks every downstream expectation.
2. **Predicate evolution policy.** Within v0.1, schema changes are additive-only. Any breaking change mints a
   new URI (`…/release/v0.2`), and old fixtures are retained so attestations emitted against old versions
   remain verifiable forever. Without this policy, "v0.1" would mean different things at different times —
   which un-freezes the URI in the way that actually matters.

Separately, go-repo `AGENTS.md` gate 2's wording ("the URI is unset until the project domain is registered")
predates the ADR-013 resolution and is to be updated to the post-resolution reading: real v0.1 URIs; fake
only the subjects and keys.

## 7. Maintainer sign-off record (2026-07-06)

All open questions raised by the initial draft were resolved by the maintainer on 2026-07-06; the riders are
integrated into the body sections above. Summary:

1. **Key-material location: spec repo `conformance/crypto/`** (§2.2), accepting public-by-construction
   private test keys in the normative repo with `.test` identities, the distinctive comment string, and
   explicit scanner allowlisting.
2. **Crypto vectors are v1 spec-repo scope** — cross-implementation identity outweighs the latency of the
   benefit; no Go-repo staging period.
3. **SSH-only key family in v1, GPG deferred** — with the fail-closed rider: an extensible key-family seam
   and a conformance vector proving a GPG-signed commit yields verification failure, not silence (§2.1).
4. **Keyless: staged full depth, borrowed before built** — sigstore's own conformance tooling first,
   cross-verification with an independent pinned reference client as the admission gate, v1 = one full
   happy-path bundle + three to four failure cases, provenance of every fixture documented (§4).
5. **Build recipe: ported script, in the spec repo's `conformance/`**, fully deterministic including a pinned
   `sha1` object format (§5); language-neutral manifest deferred to a second implementation.
6. **Expected outcomes: dual assertion** — role labels plus pinned SHAs, with recipe-drift-diagnosing failure
   messages (§5).
7. **Predicate URIs: v0.1 frozen; fixtures are the intended first emission** — under the schemas-merged
   sequencing gate and the additive-only/new-URI-on-break evolution policy (§6). Go-repo `AGENTS.md` gate-2
   wording to be updated to the post-ADR-013 reading.
