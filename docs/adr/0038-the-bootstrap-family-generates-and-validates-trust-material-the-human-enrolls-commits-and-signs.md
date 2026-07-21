<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# ADR-038 — The bootstrap family generates and validates trust material; the human enrolls, commits, and signs

**Status:** Proposed (2026-07-21)
**Date:** 2026-07-21
**Related:** ADR-037, ADR-022
**Decision:** the division of labor across the bootstrap family is a normative line: the tool
**generates, formats, validates, and configures**; the human **enrolls, commits, and signs**.

- No family command runs `git add`, `git commit`, or emits any signature. Adding a key to a
  registry is not bookkeeping — it is the moment a person becomes accountable under the scheme
  — so the accountability act stays a human's signed commit through the meta-path gate.
- **Print-by-default is the family invariant.** Where a command produces trust material
  (`enroll`'s registry line, a diagnosis's suggested fix), it prints that material to stdout,
  in front of the human, at the moment of the decision. A `--write` mode that appends to a
  working-tree file is opt-in and still never stages or commits.
- Generation that cannot take the print-by-default shape does not ship in the initial family.
  `keys generate` and `init` are deferred on this ground and recorded with un-defer triggers.

**Rationale:** the scheme prices human attention on the trust path; tooling that removes that
attention attacks the product's one differentiating property. The objection collapses for a
generator whose output is *printed*: today's `printf … >> registry` redirect puts the enrolled
line in front of no one, while print-by-default puts the byte-exact line in front of the person
at the accountability moment — strictly more attention than the status quo. It lands only for a
command whose generated material is not forced through eyes, which is exactly why `init` is
deferred: its founding commit is the maximum-stakes, minimum-frequency moment, and a
generate-and-commit `init` reduces it to a rubber stamp over unread files.
**Rejected:** a generator that stages or commits on the human's behalf (manufactures the rubber
stamp the scheme derides); an `init` that writes and commits the founding trust material unseen;
hiding generated material behind a silent file write with no printed form.
**Revisit trigger:** `keys generate` un-defers when the signing stack supports
passphrase-protected or agent-held keys; `init` un-defers only behind a print-by-default,
refuse-if-exists, review-first design.
