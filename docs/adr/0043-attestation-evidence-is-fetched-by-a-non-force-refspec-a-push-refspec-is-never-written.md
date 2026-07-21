<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# ADR-043 — Attestation evidence is fetched by a non-force refspec; a push refspec is never written

**Status:** Proposed (2026-07-21)
**Date:** 2026-07-21
**Related:** ADR-022
**Decision:** the attestation refspec is configured asymmetrically. The **fetch** side is a
one-time, **non-force** config addition —
`git config --add remote.<remote>.fetch 'refs/attestations/*:refs/attestations/*'` — after which
every `git fetch`/`pull` moves attestation evidence automatically. The **push** side is **never**
written by any bootstrap-family command: publishing attestation evidence stays an explicit
`git push` (or the ref-store's own store-and-push step), which `release` and `attest --store`
already name.
**Rationale:** the attestation refspec is the single most repeated fragile setup step across the
guides — retyped at every push, fetch, CI job, and clone — so making the fetch side one-time
configuration removes a whole class of "evidence stranded while tags travel" errors. Non-force is
safe *because* attestation refs are content-addressed and append-only: each ref is named from the
digest of the envelope bytes, and supersession adds refs rather than moving them, so a
legitimately fetched ref never changes. Non-force therefore loses nothing and turns a remote-side
ref mutation into a visible fetch refusal instead of a silent local replacement. A written push
refspec is the opposite: setting `remote.<remote>.push` changes what a bare `git push` means for
the whole repository — a config landmine worse than the disease — so publishing stays an explicit,
visible command.
**Rejected:** a force (`+`) fetch refspec (would silently replace a local ref on a hostile remote
mutation, discarding the visible-refusal safety); writing `remote.<remote>.push` (redefines bare
`git push` for the repo); leaving the fetch refspec as per-invocation retyping (the status quo the
step-count keeps getting wrong).
**Revisit trigger:** the attestation ref model stops being content-addressed and append-only — if
refs could legitimately move, the non-force fetch decision would need reconsidering.
