<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# ADR-033 — Executable derivation proofs are out of the portable baseline

**Status:** Accepted (2026-07-13)
**Date:** 2026-07-13
**Supersedes:** ADR-004, ADR-015
**Related:** ADR-006, ADR-008, ADR-019
**Decision:** Remove executable derivation proofs from the interoperable
SemVer-Trust baseline. A downstream verifier MUST NOT execute repository-,
policy-, or producer-supplied commands to raise the trust level of generated or
formatted outputs. In the portable baseline, generated outputs, formatting-only
changes, lockfile rewrites, and other mechanically produced files contribute the
trust level of the commits that changed them unless a future accepted proof
profile defines a non-ambient, reproducible, capability-bounded evidence
format.

Fixed-point evidence is not derivation evidence. Re-running a command and
observing byte-identical outputs proves only that the current tree is stable
under that command. It does not prove that the committed outputs were derived
from trusted inputs, that the command did not read undeclared inputs, that it
did not depend on time/environment/network state, or that the toolchain was not
compromised.

Projects may record derivation metadata for local policy or future profiles,
but portable conformance MUST ignore that metadata for trust re-leveling. A
claimed derivation that cannot be evaluated under an accepted proof profile is
not a verifier error and not a waiver; it simply supplies no elevation. Ordinary
weakest-link flooring and the no-de-minimis rule continue to apply.

**Rationale:** ADR-004 identified a valuable intuition: reviewed source
contracts should be able to justify generated artifacts. The proposed mechanism
was too weak and too dangerous for interoperable verification. It asked
verifiers to execute repository-selected commands with ambient host
capabilities, while the observed property was only idempotence over the already
committed tree. That creates both a soundness gap and a verifier compromise
surface.

This decision preserves the safety invariant: less proof means lower provable
trust, not equal trust with less backing. It also keeps SemVer-Trust
language-agnostic. A future proof profile can be accepted if it specifies exact
inputs and outputs, hermetic toolchain identity, denied network access,
controlled time/environment, capability isolation, and comparison against
outputs generated from trusted inputs rather than merely checking a fixed point.

**Rejected:** keep the ADR-004 command re-run as the default; treat idempotent
formatting as trust-preserving; allow repository policy to choose verifier
sandboxing requirements; waive generated directories by path; introduce
size/type/triviality exemptions; or execute producer-selected commands and
classify failures as T0 rather than treating the attempted elevation as absent.

**Revisit trigger:** an implementation proposes and validates a concrete
non-ambient derivation proof profile with hermetic execution, declared
input/output closure, pinned toolchain identity, denied network access,
controlled time/environment, and adversarial conformance vectors showing that
no-op generators, preexisting malicious outputs, undeclared reads/writes,
environment/time/network dependence, and tampered toolchains fail closed.
