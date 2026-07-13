<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# ADR-031 — Qualified review requires final-revision approval and canonical actors

**Status:** Accepted (2026-07-12)
**Date:** 2026-07-12
**Related:** ADR-002, ADR-025, ADR-030
**Decision:** Only qualified reviews can raise review class for SemVer-Trust
level assignment. A qualified review MUST be an `approved` verdict, active at
merge, signed into the review predicate, bound to the final reviewed source
revision set or final diff, and evaluated under the repository, merge context,
source-control, actor-identity, evaluator, and verification-time profiles
recorded in the attestation.

Review distinctness is evaluated on canonical actors, not raw credentials. The
active policy maps every trust-relevant credential and platform account to one
canonical actor with a class of `human` or `agent`. Key rotations and account
aliases map to the same canonical actor; they do not create additional
accountable humans. A human-authored change reaches T3 only when the author and
reviewer map to two distinct canonical human actors. A human review of
agent-authored, mixed, or ambiguous work still counts once even if that reviewer
is also the signer who accepted accountability for the change, preserving
ADR-025.

Comments, `changes_requested`, stale approvals, withdrawn or dismissed
approvals, wrong-revision approvals, post-approval changes without a preserved
final-diff proof, unmapped credentials, and approvals that collapse to the same
canonical actor when a distinct actor is required MUST NOT raise trust. If
policy requires such a review, verification fails rather than silently demoting
the release.

Agent review qualifies for T1 only when the agent approval is otherwise
qualified, the reviewing canonical agent actor differs from the authoring
canonical actor, and the attestation records evidence that the reviewer ran in a
separate execution context with no shared conversational or working state.

The `review/v0.2` successor predicate had not emitted bytes before this
decision, so it is refined in place before first emission to carry the required
actor, approval-state, coverage, merge-context, and agent-independence facts.
This deliberately resolves ADR-030's pre-#32 warning that omitted facts would
require `review/v0.3`: the operative freeze point is first emission, and that
freeze point had not occurred. Future changes after emission follow ADR-030's
strict-URI rule.
**Rationale:** Raw credential comparison overcounts accountability. One person
can hold multiple keys, rotate keys, or review from multiple platform accounts;
without a canonical actor layer, a verifier can mistake operational hygiene or
account aliases for independent human review. The scheme's central claim is the
count of independent accountable humans, so the counted unit must be the actor
that policy binds to a person or agent, not the credential string observed in a
signature or forge event.

Approval freshness is equally load-bearing. A comment, a changes-requested
review, or an approval of a superseded revision does not establish that the
reviewer accepted the content that actually merged. Squash and rebase workflows
are not intrinsically invalid, but they destroy the simple post-merge commit
shape; they can qualify only when the pre-rewrite content and the result
revision are bound by the source-control profile.

This decision keeps the trust scalar honest. Non-qualified review facts may
still be useful audit evidence, but counting them would make T1/T2/T3 claims
mean more than the evidence proves.
**Rejected:** count any review event by reviewer class (comments and
changes-requested events are not approval); compare raw credential strings for
T3 distinctness (key rotation and aliases become fake humans); treat stale
approvals as active unless the source-control platform says otherwise (fail-open
on the exact content question); ban squash/rebase entirely (safe if the
pre-rewrite content and result binding are captured); infer agent independence
from different model names alone (model names do not prove separate execution
state).
**Revisit trigger:** source-control platforms expose stronger native,
cryptographically signed final-diff approval facts; actor identity profiles are
standardized externally; or implementation evidence shows the predicate still
lacks a binding required for independent replay.
