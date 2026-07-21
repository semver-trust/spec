<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# ADR-039 — The bootstrap-family writer contract: atomic writes, dry-run purity, and a repo-relative path fence

**Status:** Proposed (2026-07-21)
**Date:** 2026-07-21
**Related:** ADR-037, ADR-028
**Decision:** every bootstrap-family command that writes obeys one contract, present and future:

- **Atomic writes.** New key files are created `O_EXCL` with the final mode passed at open
  (never create-then-`chmod`); registries and other content files are built in memory, re-parsed
  by the verifier's own strict parser, written to a temp file in the same directory, fsynced,
  and renamed into place; `.git/config` is written only under git's own `config.lock` protocol
  (ADR-042). The tool never writes trust material it would itself reject.
- **Dry-run purity.** `--dry-run` performs **zero** filesystem mutations — no directory
  creation, no lock, no temp file — and its output *is* the manual fallback, so the guides stay
  executable as written.
- **Interrupted-run safety.** An interrupted run removes only files it created and never leaves a
  partial live file; there is no `MkdirAll` on a missing parent (a missing parent is a refusal
  with a hint, not a silent creation).
- **The repo-relative path fence.** Every policy-named path is fenced on read and write: absolute
  paths and `..` elements are rejected literally (reject, never sanitize), resolution goes
  through a securejoin-style boundary, and a final `Lstat` refuses a symlink target.

**Rationale:** the policy's registry paths carry no path validation today, and verification is
safe only because it reads them exclusively from git *trees*, which cannot escape the repository.
The moment a command reads or writes those paths on the filesystem it inherits a traversal
surface: a hostile cloned repository could declare `allowed_signers = "../../.ssh/authorized_keys"`
and turn `enroll --write` into an append of attacker-shaped key material into `$HOME`. A torn or
partial registry write is worse than a no-op — it fails closed for *every* verifier of the
repository — so writes must be atomic and strict-re-parsed. The fence's reject-don't-sanitize
posture mirrors the existing attestation-subject validator.
**Rejected:** `MkdirAll` on attacker-chosen or typo'd parent paths; sanitizing a traversing path
instead of rejecting it; a non-atomic append that can leave a registry unparseable;
create-then-`chmod` on key files (a race and a symlink-follow window).
**Revisit trigger:** a new writer whose target cannot satisfy the atomic protocol — a reason to
reconsider the writer, not to weaken the contract.
