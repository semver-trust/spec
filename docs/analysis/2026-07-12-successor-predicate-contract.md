<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Steelman Analysis — Successor Predicate Contract

**Date:** 2026-07-12 · **Status:** dispositioned by ADR-030
**Context:** follow-on to spec issue #33 after PR #37 merged

## 1. Problem statement

The v0.4 trust-chain work now has a clean split between release intervals,
policy transitions, and authenticated version ancestry. That closes the
internal state problem. The remaining gap is the wire contract for the
attestation predicates themselves: v0.1 bytes already exist, they are frozen,
and they cannot express the new continuity facts without changing meaning under
old validators.

That makes this a compatibility decision, not just a schema edit.

The design question is therefore:

If a future verifier sees a historical v0.1 attestation, a successor attestation,
or both, what must be explicit in the wire format so that the same bytes mean
the same thing everywhere?

## 2. Strongest argument for a versioned successor

The strongest case is that the repository has already crossed the point where
“add a field and keep the old URI” is no longer honest.

Reasons:

- The current `release/v0.1` and `review/v0.1` schemas are closed objects.
  Older vendored validators will reject newly added fields rather than ignore
  them.
- v0.1 was emitted before the project had stabilized the continuity and
  freshness semantics now required by v0.4.
- The spec now says v0.1 is historical and cannot claim v0.4 continuity.
- A compatibility contract that depends on silent parser behavior is fragile:
  one verifier can treat the same bytes as legacy-only while another treats them
  as successor-capable.

The honest conclusion is that successor behavior needs a new predicate type URI
and a new schema family. The version bump is not ceremony; it is the mechanism
that keeps old and new interpretations from colliding.

## 3. Recommended contract shape

The successor family should keep the legacy bytes untouched and introduce a new
wire contract with explicit profile identity.

Recommended properties:

- Preserve v0.1 exactly as historical evidence.
- Mint a new predicate type URI for the successor family rather than extending
  the old one in place.
- Bind an explicit profile/specification version so verifiers know which rule
  set was used.
- Bind stable repository identity, not just a tag name.
- Bind the predecessor attestation and immutable predecessor/resource digests
  needed to reproduce the emitted release or review decision.
- Bind trust-root identity and verification-time semantics.
- Keep source-attester and release-attester authority separate.
- Make freshness or current-state assumptions explicit when replay or demotion
  matters.

The practical reading is simple: if a field can change the meaning of the
attestation, or if two conforming verifiers could otherwise disagree on the
same bytes, it belongs in the successor predicate rather than in ambient caller
state.

## 4. Why not extend v0.1 in place

Three tempting alternatives fail under pressure.

1. Add optional fields to v0.1 and rely on tolerant parsers.

   This is the weakest option. The repository already shipped closed schemas,
   so old validators would reject the new bytes. Any verifier that “helpfully”
   ignores unknown fields would create a second compatibility regime without
   an explicit contract.

2. Keep one URI and reinterpret existing fields more richly.

   This creates a meaning drift problem. Historical v0.1 attestations would
   appear to satisfy a contract they never actually encoded.

3. Push the new meaning into repository policy only.

   That does not travel with the attestation. A verifier that only has the
   signed bytes, the schema, and a trust root still needs the profile to be
   explicit in the predicate itself.

## 5. Failure modes to avoid

The successor contract should specifically prevent these regressions:

- caller-selected version state deciding the emitted line again;
- repository name or ref name being treated as sufficient identity;
- silent acceptance of successor fields by legacy validators;
- mixing compatibility semantics with freshness semantics;
- letting one predicate URI cover materially different wire contracts;
- making v0.1 look like it already knew about v0.4 continuity.

These are the kinds of mistakes that are easy to make once the internal model is
correct but the wire contract is still underspecified.

## 6. Recommendation

Freeze v0.1 as historical and define a successor predicate family as a new
versioned contract, likely starting at `v0.2` for both release and review
predicates. The successor should carry explicit profile identity plus the
minimum set of bindings needed to reproduce the attestation without caller
guesswork.

That is the least surprising path for implementers, the safest path for old
validators, and the only path that keeps the project honest about what v0.1 can
and cannot prove.

## 7. Practical next steps

1. Turn this contract into an ADR so the decision is explicit and supersedable.
2. Add successor release/review schema pages and schemas, leaving v0.1 frozen.
3. Add conformance vectors that distinguish historical verification from
   successor verification.
4. Only then update the Go implementation to emit and verify the successor
   predicate family.

The ancestry merge made this the next real gating item. ADR-030, release/review
v0.2 predicate pages, and v0.2 schemas disposition the specification side.
Until the Go implementation consumes that contract, v0.1 remains historical and
production release claims stay blocked by design.
