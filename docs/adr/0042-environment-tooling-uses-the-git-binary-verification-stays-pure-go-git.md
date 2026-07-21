<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# ADR-042 — Environment tooling uses the git binary; verification stays pure go-git

**Status:** Proposed (2026-07-21)
**Date:** 2026-07-21
**Related:** ADR-018, ADR-028
**Decision:** the bootstrap family's environment mutation and diagnosis (`setup`, and any
git-config or git-environment read a command performs) shell out to the user's `git` binary;
verification stays pure go-git. Raw go-git config writing is forbidden for this family: `setup`
manages its enumerated `.git/config` keys through `git config` — which provides `config.lock`
locking, `include`/`includeIf` semantics, linked-worktree config routing, and `GIT_DIR` handling
for free — and diagnoses the environment through git rather than a partial reimplementation.
**Rationale:** the go-git-only convention exists for *verification* determinism — reads from
trees, an injectable clock (ADR-018), no ambient environment dependence. Environment tooling is
the opposite kind of code: its correctness *is* fidelity to the user's actual git. The pinned
go-git version's config writer is a lockless, truncate-in-place, whole-file rewrite: it destroys
comments, corrupts `pushurl` remotes on round-trip, ignores git's `config.lock`, and an interrupt
mid-write leaves an empty `.git/config` — to the user, a destroyed repository. Concurrent editor
config writes are silently reverted, and the contributor fork workflow's push targets break. The
git binary gets all of this right; go-git gets it wrong today. Drawing the line here keeps
verification hermetic while making mutation safe.
**Rejected:** raw go-git config writing for the family (the verified corruption and lockless-write
findings); a pure-Go lock-and-rename textual config patcher that edits only the owned keys (more
code for the same guarantee — the git binary is simpler and canonical); routing verification
through the git binary too (would forfeit the determinism the go-git-only rule protects).
**Revisit trigger:** go-git gains a safe config writer — locking, comment-preserving,
`pushurl`-correct — verified by a round-trip probe test, at which point the shell-out could be
reconsidered.
