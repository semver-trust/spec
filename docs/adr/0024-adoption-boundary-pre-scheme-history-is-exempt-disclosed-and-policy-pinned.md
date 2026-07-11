<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# ADR-024 — Adoption boundary: pre-scheme history is exempt, disclosed, and policy-pinned

**Status:** Accepted (2026-07-11)
**Date:** 2026-07-11
**Decision:** a repository MAY declare an **adoption boundary** in its policy file — a single commit (by SHA
or tag) before which history is exempt from verification. With a boundary declared, a first release verifies
`boundary..TO` instead of `root..TO`; ranges anchored at a previous verified tag are unaffected. Three
binding properties: (1) **policy-pinned** — the boundary lives in the policy file (`[policy]
adoption_boundary`), never in a CLI argument or environment, so it is protected by the §5.4 meta-path rule:
moving the boundary is itself a policy-file commit that must meet the required meta level, and the §8.1
attestation's pinned policy digest freezes which boundary produced each decision. (2) **Disclosed** — a
release attestation whose range begins at the boundary marks it (additive optional predicate field
`range.from_is_adoption_boundary: true`): consumers can always tell "verified since the boundary" from
"verified since inception"; the two claims are different and must never be conflated. (3) **Boundary-exempt,
never boundary-laundered** — commits before the boundary contribute no trust level at all (they are outside
every range), and retrospective profiling reports pre-boundary history as out-of-scope, not as any T level.
This repository's own implementation is the first user: its earliest commits are signed by a key whose
public half is lost, which no key-family support can recover.
**Rationale:** the design record predicted this need before it happened ("unverifiable → fail … is brutal on
repos with pre-scheme history; likely needs an *adoption boundary* concept — a designated first-verified tag
before which history is exempt"), and promoted it to a first-implementation requirement because the
reference implementation must release itself. The trigger arriving as a *lost key* rather than pre-scheme
history strengthens the case: unverifiability has many causes (adoption date, key loss, platform migration),
and per-cause recovery mechanisms cannot cover them all — a single, honest, disclosed exemption point can.
ADR-008's unverifiable-⇒-abort posture is preserved *inside* the verified region; the boundary moves where
the region starts, visibly, rather than weakening what verification means within it.
**Rejected:** exempt-nothing (leaves any repository with one unrecoverable signature permanently unable to
cut a first release — punishing adopters for their pre-adoption past contradicts the goal of being adoptable);
per-commit exemption lists (a hiding place: a payload commit "exempted" among legitimate ones is exactly the
de-minimis attack P3 forecloses — one boundary, everything before it, nothing after); CLI-supplied
boundaries (whoever runs the verifier could move the boundary; the config is the root of trust, §5.4);
treating pre-boundary commits as T0 (unverifiable is not T0 — ADR-008; pre-boundary history makes no claim
at all).
**Revisit trigger:** the spec v0.3 pass, which should mirror this into §5.2/§10 normative text (the ADR-015
pattern: decision now, spec mirror at the next version); or evidence that boundary declarations are being
used to repeatedly re-baseline history (multiple boundary moves in a repository's policy history), which
would argue for surfacing boundary-move counts in verification output.
