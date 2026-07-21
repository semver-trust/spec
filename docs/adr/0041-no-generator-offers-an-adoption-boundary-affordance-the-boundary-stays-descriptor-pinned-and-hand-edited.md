<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# ADR-041 — No generator offers an adoption-boundary affordance; the boundary stays descriptor-pinned and hand-edited

**Status:** Proposed (2026-07-21)
**Date:** 2026-07-21
**Related:** ADR-026, ADR-027, ADR-028
**Decision:** no bootstrap-family generator — not `enroll`, not `setup`, not a future `init` —
accepts an adoption-boundary flag or writes an adoption-boundary value. The adoption boundary
remains a hand-edit to a reviewed policy file whose authority is the out-of-band bootstrap
descriptor (ADR-028); under the authenticated chain the boundary is chain-genesis state pinned by
that descriptor (ADR-027), and a legacy `[policy] adoption_boundary` value may only mirror it and
must match it. A `doctor` check may *diagnose* the boundary — that it resolves, that it matches
the descriptor pin when one is supplied, that the commit introducing it meets the meta-path gate
— but never *set* it.
**Rationale:** the adoption boundary is the single most consequential admission in the scheme —
it declares a span of history exempt from verification — so it must stay a deliberate, reviewed
human act, not a value a convenience command emits. ADR-024 and ADR-026 established the boundary;
ADR-027 and ADR-028 made it immutable chain-genesis state pinned by the out-of-band descriptor
rather than a mutable policy choice. A generator flag would reintroduce exactly the mutability
those decisions removed, letting tooling — or an agent running it — move the verification start.
Extending the no-affordance rule to generation time keeps the reasoning of ADR-027/028 intact
where the mistake would be easiest to make.
**Rejected:** an `init --adoption-boundary <rev>` flag (hands the most consequential admission to
a command line); generating or defaulting a boundary value during scaffolding; letting a
generator write the `[policy] adoption_boundary` mirror (the mirror must be a reviewed hand-edit
that matches the descriptor).
**Revisit trigger:** none foreseen — the boundary is designed to remain a hand-edited, reviewed
admission; any change would itself supersede ADR-027/028.
