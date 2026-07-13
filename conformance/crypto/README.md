<!-- SPDX-License-Identifier: Apache-2.0 -->
# Cryptographic conformance fixtures — SSH signature verification

This directory holds the durable, language-neutral cryptographic fixture
material planned in
[docs/conformance-crypto-fixtures.md](../../docs/conformance-crypto-fixtures.md)
and governed by [ADR-018](../../docs/adr/0018-verification-interfaces-accept-injectable-trust-roots-and-clock-from-day-one.md):
verification consumes injected trust material and an injected clock, so these
fixtures verify to the same result on any future date.

**Everything under `keys/` is a test double.** The private halves are
committed **on purpose** (fixture plan §2.4): every identity lives in the
RFC 6761-reserved `@semver-trust.test` domain, every key comment contains
`semver-trust-conformance TEST KEY - DO NOT USE`, the repository's
`.gitleaks.toml` records the allowlisting as an explicit decision, and none
of these keys is enrolled in any real allowed-signers file, CI signing
configuration, or release path.

## Contents

| Path | Role |
|---|---|
| `keys/` | Five vendored Ed25519 test keypairs (fixture plan §2.1): `human-alice`, `human-bob`, `agent-ci-bot`, `unknown-mallory`, `revoked-carol` |
| `allowed_signers` | The injected registry: alice/bob/ci-bot enrolled for the `git` namespace; carol enrolled with `valid-before="20251231"` (invalid at the epoch); mallory absent |
| `build-fixture-repos.sh` | Deterministic fixture-repository builder (see below) |
| `signature-vectors.json` | Expected verification outcomes, dual-asserted by role tag and pinned SHA |
| `attestations/` | DSSE attestation fixtures (§6): payloads, vendored frozen envelopes, the attestation-signer registry, generator, and vectors |

## The fixture epoch and determinism

Every fixture verifies at **`2026-01-01T00:00:00Z`** (fixture plan §3), the
single canonical epoch injected as the verification clock. The build script
pins every input a commit SHA depends on — author/committer identities and
dates (the epoch), messages, trailers, the `sha1` object format, and Ed25519
signatures (RFC 8032 signing is deterministic) — so the built repositories
are byte-identical across runs and machines. `signature-vectors.json`
asserts the resulting SHAs: **a SHA mismatch means the build recipe or its
inputs drifted**, not that verification broke.

Fixture repositories are built at test time, never committed
(implementation `AGENTS.md`; fixture plan §5):

```sh
./build-fixture-repos.sh /tmp/fixtures
```

## Capability limitation (v1): SSH only, fail-closed proven

v1 ships the SSH allowed-signers key family only; a GPG family is deferred
(fixture plan §7 OQ3). Per the maintainer's fail-closed rider, this
limitation is proven, not assumed: the `gpg-signed` fixture carries a
PGP-armored signature and its **expected outcome is verification failure**
(`unsupported_key_family`) — a verifier that cannot verify a key family must
treat the commit as unverifiable and abort (§5.2, unverifiable ≠ T0), never
skip it or silently degrade. A "conforms to the v1 crypto vectors" claim
covers exactly this: SSH verification plus fail-closed behavior on
everything else.

## Attestation envelopes (fixture plan §6)

`attestations/` carries the DSSE fixtures. The original fixtures were the
**first emission of the frozen v0.1 predicate types**; the same directory now
also includes signed positive envelopes for the v0.2 release/review successor
predicates. All fixtures use real predicate URIs, fake fixture-local subjects
(the signed-history commit SHAs and fixture tags), test-only keys, and every
non-negative payload is validated against its registered JSON Schema **before**
signing. Unlike the fixture repositories, the envelopes are vendored frozen
bytes: signed bytes cannot be patched, only regenerated
(`build-attestation-envelopes.py`), and regeneration breaks downstream
expectations — treat it as a ceremony, not a build step.

**Signature convention
([ADR-022](../../docs/adr/0022-attestation-signatures-are-sshsig-over-the-dsse-pae-with-purpose-binding-namespaces.md)).**
The DSSE pre-authentication encoding (PAE) is signed as an OpenSSH SSHSIG
with namespace `attestation@semver-trust.dev`; `sig` is the base64 of the
armored SSHSIG and `keyid` the signer's SHA256 fingerprint — an untrusted
lookup hint, never a trust anchor. The namespace binds purpose: a commit
signature (`namespaces="git"`) can never double as an attestation signature,
and vice versa — which is why `attestations/allowed_signers` is a separate
registry enrolling only the workflow identity, scoped to the attestation
namespace.

The release-attestation payloads are backed by the dedicated `release`
fixture repository: its tree pins `.semver-trust/policy.toml` (the digest in
the payload is the file's real digest), `v0.1.0` tags the setup commit, the
release range holds one human and one agent `fix:` commit (declared intent
PATCH, agreeing with the recorded semantic floor), and the demoted release
tag `v0.1.1-t0.1` points at the range head — every claim in the payload is
reproducible from the tree, and `check-conformance.py` gates that coherence
along with envelope shape, SSHSIG outcomes, and byte-exact regeneration.

## Provenance

- Keys generated 2026-07-11 with `ssh-keygen -t ed25519` (OpenSSH), no
  passphrase, comments carrying the mandated test-key string.
- Every vector's expected outcome was cross-verified with an independent
  reference verifier (`git verify-commit`, i.e. `ssh-keygen -Y verify`,
  against `allowed_signers`) before the SHAs were pinned: the three enrolled
  identities verify; unknown, revoked, PGP-armored, and tampered commits are
  rejected.
- Implementations consume this directory as a vendored, digest-pinned copy
  (ADR-021), exactly like the vector files one level up.
