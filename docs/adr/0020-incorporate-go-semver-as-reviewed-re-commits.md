<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# ADR-020 — Incorporate go-semver as reviewed re-commits

**Status:** Accepted (2026-07-06)
**Date:** 2026-07-06
**Decision:** `semver-trust-go` incorporates the legacy `go-semver` code (parse/sort/increment logic, git tag
enumeration, CLI surface) as **fresh signed, `Provenance:`-trailered commits** carrying
`Imported-From: go-semver@<sha>` origin trailers — never by merging the legacy history. The provenance target is
**`b427cc5`**, the last MIT-licensed snapshot (its successor changed only license/README files; the Go code is
byte-identical), so origin trailers point into MIT-licensed history rather than the later custom-licensed HEAD.
Ported files carry `SPDX-License-Identifier: Apache-2.0`: the maintainer is the sole author of all 24 legacy
commits, confirmed (2026-07-06) that no employer work-for-hire interest exists, and as copyright holder
relicenses the ported code directly. The audit feeding this decision, including the port map and the behavioral
quirks the port must preserve or deliberately break, is `docs/go-semver-audit.md` in `semver-trust-go` (GO-005).
**Rationale:** `semver-trust-go` must maintain an unbroken scheme-compliant history from commit #1 — that history
is itself a project deliverable, and the adoption boundary for the repository is its first commit by
construction. Merging legacy history would import 24 commits that are unsigned, untrailered, and unverifiable
under the scheme, recreating exactly the adoption-boundary problem the repository exists to demonstrate the
absence of. Re-commits keep every commit verifiable while `Imported-From:` trailers preserve provenance honestly
(P2: the re-committer signs as the accountable party standing behind the imported change). Porting beats
rewriting because the increment logic is hard-won, node-semver-conformant behavior pinned by an ~80-case test
suite.
**Rejected:** history-preserving merge (imports unverifiable commits, breaks the verifying-from-root
deliverable); clean-room rewrite (discards proven, well-tested logic to avoid a license problem that does not
exist — the maintainer owns the copyright outright).
**Revisit trigger:** none foreseen; the decision is consumed once (GO-020/GO-021) and its record is what matters
thereafter.
