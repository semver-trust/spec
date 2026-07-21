<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# ADR-037 — The bootstrap-family capability table bounds which command may write which path class

**Status:** Proposed (2026-07-21)
**Date:** 2026-07-21
**Related:** ADR-038, ADR-039
**Decision:** the `semver-trust` binary gains an environment-tooling command family
(`doctor`, `enroll`, `setup`) whose write authority is fixed by a capability table, and no
command may write outside its cell:

- `enroll` writes **policy-named registry files in the working tree** (the SSH allowed-signers
  and attestation-signers registries and the OpenPGP keyring) and nothing else.
- `setup` writes **an enumerated set of `.git/config` keys** for this clone (through the git
  binary, ADR-042) and nothing else — never the working tree, never `--global`.
- `verify` and `doctor` **write nothing, ever.** They are read-only by construction, which is
  what makes `doctor` safe to run in an agent context.
- `doctor --persona agent` is the **single** family command an agent is sanctioned to run; the
  generators (`enroll`, `setup`) and any future writer are human-invoked.

Widening any cell — a new writable path class, or a command that writes a class it does not
today — requires a superseding ADR. The trust boundary the family never crosses is the
human-signed commit through the meta-path gate: no command stages, commits, or signs, so
generated material becomes trusted only through a person's reviewed, signed commit.
**Rationale:** the family adds mutation to a binary that was previously verification-only, so
the capability surface must be enumerable and frozen rather than growing feature by feature. A
fixed table lets `verify`/`doctor` be *provably* write-free — the property an agent-safe
diagnostic needs — and forces the next convenience feature to argue its case by superseding
this decision rather than quietly appending a write path. The steelman's sharpest hit, that a
verifier which also writes becomes a mutation engine that attests its own output, is answered
here: the only bytes a command writes land unstaged in the working tree or in repo-local git
config, and neither enters history except through the meta-path-gated signed commit.
**Rejected:** letting each command define its own write scope ad hoc (no enforceable boundary,
scope creep by default); a hook installer that writes executable code run on every commit (a
genuine capability escalation — cut in favor of a committed hook script plus a printed
`core.hooksPath` line); a single do-everything command whose generated founding material is
never forced through human eyes.
**Revisit trigger:** a concrete bootstrap or diagnosis need that no cell in the table can serve
read-only, at which point the widening is made explicit by a superseding ADR, not a flag.
