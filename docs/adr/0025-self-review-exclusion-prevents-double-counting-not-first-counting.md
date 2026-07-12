<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# ADR-025 — Self-review exclusion prevents double-counting, not first-counting

**Status:** Accepted (2026-07-12)
**Date:** 2026-07-12
**Decision:** the §3.2 self-review exclusion is a **double-counting** rule, not an independence rule: it
prevents one human from being counted as two (the T3 gate), never from being counted as one. Accountable
human identities are counted by role — human authorship adds the verified human author; a signed human
review adds the verified human reviewer; the same identity appearing in both roles counts once. Therefore,
for agent-, mixed-, or ambiguous-authored commits — where no human author is counted — a signed human
review counts as the single accountable human **even when the reviewer's identity equals the commit's
signer principal**: agent + human = T2. Human-authored commits are unchanged (same-identity review adds no
second human: human/none → T2; distinct identities → T3), and agent-review independence is unchanged
(same-identity agent review remains none — §3.3's conditions are about corroboration, which self-checking
cannot provide). Normative text: §3.2 note 2 is clarified accordingly and the spec draft bumps to v0.3,
because this interpretation directly changes release verification outcomes.
**Rationale:** T2's definition is "exactly one accountable human, in either role" (§3.1), and ADR-002
derives the levels by counting humans — nowhere does T2 claim review independence; T3 is the
independent-two-humans claim. The implementation error that surfaced this (the reference implementation's
own first-release ceremony) conflated the commit's verified *signer* with its classified *author*: after
`Provenance: agent` honestly classifies authorship as agent, the signer principal is no longer a counted
human author, so a same-identity human review is the first — and only — accountable human. The stricter
misreading also inverts the honesty gradient: omitting the agent trailer would have classified the same
commits human-authored and reached T2 directly, so honesty about agent authorship would be punished with an
unreachable level — precisely what P2/P4 forbid the scheme to do. Meta-path policy is not weakened: the
same maintainer can already produce T2 by authoring a meta-path commit directly; this merely gives honestly
declared agent authorship an equivalent accountable-review path.
**Rejected:** treating same-identity human review as void for all authorship classes (punishes the honest
trailer; makes T2 unreachable for solo-maintained agent-authored history — recoverable prospectively via a
dedicated machine signing identity, but never for immutable history without a second human); an
implementation-only exception without spec clarification (the ambiguity is normative and would fragment
implementations); lowering meta-path requirements or forcing releases around the abort (the abort was the
verifier working as designed on an ambiguous rule).
**Revisit trigger:** evidence that same-identity post-hoc review is being used as a rubber stamp at scale
(the review-quality question §12.5 already defers); or a future level taxonomy revision (steelman standing
prediction 2: authorship-axis decay toward reviewer-counting), which should re-derive this rule from
whatever replaces the matrix.
