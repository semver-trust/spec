<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# ADR-036 — Version-state digests use a reproducible canonical-JSON profile

**Status:** Proposed (2026-07-16)
**Date:** 2026-07-16
**Related:** ADR-027, ADR-029, ADR-030
**Decision:** the version-state identities a `release/v0.2` predicate binds —
`prior_state` and `resulting_state` (§8.1, `schemas/release-v0.2.json`
`stateIdentity`) — are digested by a single defined profile,
`semver-trust-version-state-json` version `0.2`: the accepted, carried-forward
version state serialized with RFC 8785 (JSON Canonicalization Scheme, JCS) and
hashed with SHA-256. Each state binds its predecessor's digest, forming a
tamper-evident version-decision chain. This retires the §8.1 clause that blocked
v0.2 emission on an undefined profile.

## The object that is canonicalized

The digested object is **exactly the authenticated version state carried forward
to the successor** under §7.5/ADR-029 — and nothing else. This is the load-
bearing invariant: a successor release binds the predecessor's
`resulting_state.digest` as its own `prior_state` (and as the
`predecessor_state_digest` chain link below), and a verifier re-derives that
same state from the predecessor's carried facts, so the two digests MUST match
byte-for-byte. Anything a successor does not carry — the signed *action*
(advance/re-cut/supersede), the per-release *genesis* marker, or the emitted tag
— is therefore NOT part of the state digest; those remain bound elsewhere in the
predicate (`version_state.action`, `version_state.genesis`,
`version_state.emission`) but do not enter this identity. Excluding the emitted
tag also removes an ordering hazard: a tag's raw ref-target object ID exists only
after the tag is created, which is after the attestation would need the digest.

The canonical object has exactly these members (JCS orders them; the listing
here is for readability):

```json
{
  "profile": "semver-trust-version-state-json",
  "version": "0.2",
  "component": "<component name>",
  "tag_prefix": "<canonical tag prefix>",
  "baseline": null,
  "baseline_core": "<x.y.z>",
  "target_core": "<x.y.z>",
  "target_bump": "major | minor | patch",
  "clean_accepted": false,
  "target_lineage": ["<accepted-interval-id>", "..."],
  "iterations": { "T0": 0, "T1": 0, "T2": 0, "T3": 0 },
  "pending_corrective_floor": null,
  "predecessor_state_digest": null
}
```

with these rules:

- **`profile` and `version`** are the literal profile name and version. They are
  included in the digest for domain separation: a future
  `semver-trust-version-state-json` v`0.3` (or any other profile) over the same
  facts yields a distinct digest, so profiles cannot collide across a version
  boundary.
- **`component`** and **`tag_prefix`** are the canonical component chain identity
  (§5.1, §7.1). Every component chain binds one prefix (ADR-029); binding both
  scopes the state to its chain.
- **`baseline`** is the target baseline (ADR-029): `null` for a synthetic
  `v0.0.0` genesis line, or an object binding the immutable lineage tag and its
  source identity —
  `{ "name", "raw_ref_oid", "peeled_commit_oid", "source_identity": <digestSet> }`
  — where `name` is the canonical §7.1 tag, `raw_ref_oid`/`peeled_commit_oid` are
  its Git ref-target and peeled commit object IDs (so a moved or recreated ref is
  detected), and `source_identity` is the baseline's source digest set.
- **`baseline_core`** is the baseline SemVer core (`0.0.0` for synthetic
  genesis); **`target_core`** is the target core; **`target_bump`** is the bound
  bump class. Applying `target_bump` to `baseline_core` MUST produce `target_core`
  (ADR-029), so the trio is internally consistent.
- **`clean_accepted`** records whether the target's clean §7.1 tag has been
  accepted.
- **`target_lineage`** is the ordered array of accepted source-interval
  identities accumulated for the current trust claim (ADR-029: re-cut and
  advance-from-unpromoted append intervals so skipped prereleases cannot launder
  trust). Order is significant and preserved.
- **`iterations`** maps each trust level (`"T0"`–`"T3"`) present in the accepted
  decision lineage to its highest accepted trust-suffix iteration, so a successor
  derives the next iteration without a caller input. Levels with no accepted
  iteration are omitted (they are not `0`).
- **`pending_corrective_floor`** is `null`, or the carried-forward under-bump
  correction (a bump class strictly greater than `target_bump`) that a later
  same-head supersession must clear or continue (ADR-029).
- **`predecessor_state_digest`** is the **chain link**: the immediately preceding
  accepted state's digest as its `sha256:<hex>` string, or `null` at genesis.
  Because it enters this state's own digest, every accepted decision commits to
  its parent, and rewriting any earlier state invalidates every later digest.

## Serialization and digest

1. Construct the canonical object above from the authenticated version state.
   Omit `null`-valued OPTIONAL members only where these rules say to omit them
   (`iterations` levels with no accepted value); every other member is present,
   with `null` where defined.
2. Serialize with **RFC 8785 (JCS)**: UTF-8, lexicographically ordered object
   member names, minimal number and string forms. JCS is chosen because it is a
   published, deterministic canonicalization that independent implementations
   reproduce bit-for-bit — the §8.1 "reproducible by verifiers" requirement.
3. `resulting_state.digest = { "sha256": <lowercase-hex SHA-256 of the JCS bytes> }`.

`resulting_state.id` is the non-authenticated label
`version-state:<component>:<target tag or target core>` — a human/debug
reference only; the **digest**, not the id, authenticates the state. Two states
with equal digests are the same state regardless of id.

## Emission and verification

An emitter MUST populate `resulting_state.{id,digest,canonicalization}` by this
profile, and — for a recurring release — set `prior_state` to the predecessor's
`resulting_state` verbatim and `predecessor_state_digest` to the predecessor's
digest. A verifier MUST recompute the digest from the version state it
authenticated for the release and reject the release if it does not match the
bound `resulting_state.digest`, or if the bound `prior_state.digest` does not
match the accepted predecessor's `resulting_state.digest`. Reproduction failure
is a fail-closed abort, never a warning.

**Rationale:** §8.1 already required version-state identities to carry a digest
plus a canonicalization profile but left the profile undefined, so v0.2 emission
was explicitly blocked. Defining it as JCS-over-carried-state closes the gap with
the weakest sufficient mechanism: JCS is a standard both a Python oracle and a Go
implementation reproduce byte-for-byte, and digesting *exactly the carried
state* is what lets a successor validate the chain link without re-deriving the
predecessor's whole history. The `predecessor_state_digest` hash chain makes the
version-decision lineage tamper-evident with no transparency log, mirroring the
raw/peeled ref binding ADR-029 already uses to detect moved tags. Excluding the
action, genesis marker, and emitted tag keeps the identity to the state a
successor actually carries and sidesteps the tag-creation ordering hazard, while
those facts stay bound (and signed) in their own predicate fields.

**Rejected:** leave the profile a bare label and let each implementation choose
its own bytes (the §8.1 blocker; not reproducible across verifiers); include the
signed action or genesis marker in the digest (a successor does not carry them,
so it could not reproduce the predecessor's digest — breaks the chain link);
include the emitted tag or its raw ref OID (unknown until after tag creation — an
ordering hazard — and a derived artifact, not carried state); digest the entire
`release/v0.2` predicate (couples version-state identity to unrelated interval,
policy, trust, and evidence blocks, so an evidence-only supersession would change
the version-state digest); invent an ad-hoc key-sorted JSON instead of JCS
(re-derives a canonicalization standards already specify, and invites
implementation drift on number/string edge cases).

**Revisit trigger:** an accepted transparency-log or current-state-head profile
(the ADR-029 revisit trigger) that supplies a stronger canonical
version-decision lineage would supersede this profile under a new `version`
(e.g. `semver-trust-version-state-json` v`0.3`), leaving already-emitted v`0.2`
digests valid under their bound profile label.
