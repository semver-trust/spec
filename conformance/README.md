<!-- SPDX-License-Identifier: Apache-2.0 -->
# SemVer-Trust Conformance Vectors

These vectors are the **sync contract** between the [SemVer-Trust specification](../spec/semver-trust.md)
and every implementation of it. They are data, not prose: a conformance harness loads them, exercises the
implementation under test, and asserts the implementation reproduces the encoded expectations. The Go
reference implementation treats them as acceptance tests, and any other implementation claims conformance by
passing them.

Each vector is derived directly from a normative section of the spec and carries a `spec` back-reference to
it. The vectors in this directory cover **level assignment** (§3.2, §3.3, §4.1–§4.2), **version precedence
and tag grammar** (§7.1, §7.2), **aggregation** (§5.1–§5.2 scope partitioning and floors, §5.4 meta-paths,
with §4.4 derivation re-leveling as it feeds §5.2), **transitive propagation** (§5.3, including SCC
collapse), and **release decisions** (§6.1–§6.4 with §7.1 encoding). Every step of the spec's Appendix A
worked example is reproduced as a vector (ids containing `appendix-a`). Cryptographic verification fixtures —
vendored test keys, the allowed-signers registry, deterministically built fixture repositories, and SSH
signature vectors (§4.2, §10 step 3) — live under [`crypto/`](crypto/README.md), which also documents the v1
capability limitation (SSH-only, with fail-closed behavior on other key families proven by vector).

## File inventory

| Path | Role | License |
|---|---|---|
| `levels.json` | Per-commit trust level assignment vectors (matrix + classification) | Apache 2.0 |
| `precedence.json` | SemVer precedence ordering vectors + §7.1 tag-grammar vectors | Apache 2.0 |
| `aggregation.json` | Scope partitioning, per-scope floor, and meta-path hard-fail vectors | Apache 2.0 |
| `propagation.json` | Effective-trust propagation vectors over dependency graphs (incl. SCCs) | Apache 2.0 |
| `decision.json` | §6.4 decision-table vectors: trust × blast × strategy → channel/version | Apache 2.0 |
| `crypto/` | Cryptographic fixtures: vendored test keys, allowed-signers registry, deterministic fixture-repo builder, SSH signature vectors (see `crypto/README.md`) | Apache 2.0 |
| `check-conformance.py` (in `../scripts/`) | Independent validator for these files (self-check, not the harness) | Apache 2.0 |
| `LICENSE` | Verbatim Apache 2.0 text, vendored so copies carry their license | Apache 2.0 |

`../scripts/check-conformance.py` is a *self-consistency* check: it re-implements the spec rules a second
time (independently of both the reference implementation and `check-drift.py`) and confirms the vectors agree
with that implementation. It is not the conformance harness — a harness runs the *implementation under test*
against these vectors.

## `spec_version` pinning

Every vector file carries a top-level `spec_version` (currently `"0.3"`). It names the spec draft the vectors
encode, not the version of the vector set. The rules:

- The vectors track the pinned spec draft. When they say `"0.3"`, their expectations are those of
  `spec/semver-trust.md` **Draft v0.3**.
- All vector files in this directory MUST share the same `spec_version`; the validator enforces this and
  cross-checks it against the spec's draft header.
- An implementation claims conformance **against a `spec_version`** — "conforms to SemVer-Trust 0.3 level and
  precedence vectors" is the precise claim.

## Vector format

Both files share an envelope:

```json
{
  "$comment": "SPDX-License-Identifier: Apache-2.0",
  "spec_version": "0.3",
  "description": "…what this file covers…",
  "vectors": [ /* … */ ]
}
```

Every vector, regardless of file, has these common fields:

| Field | Type | Meaning |
|---|---|---|
| `id` | string | Stable, unique identifier, e.g. `levels/matrix/agent-none`. Never reused or repurposed. |
| `kind` | string | Selects the consumption rule: `matrix`, `classify`, `precedence`, `grammar`, `scope_partition`, `scope_floor`, `meta_path`, `propagation`, or `decision`. |
| `description` | string | Human-readable intent; editorial, not asserted. |
| `spec` | string | Back-reference to the governing spec section, e.g. `§3.2`. Never empty. |

### `levels.json` — `kind: "matrix"`

Already-classified authorship and review classes mapped to a level. Tests the level function in isolation.

| Field | Type | Values |
|---|---|---|
| `inputs.authorship` | string | `agent`, `mixed`, `ambiguous`, `human` |
| `inputs.review` | string | `none`, `agent_independent`, `human_distinct`, `human_same_identity` |
| `expected.level` | string | `T0`, `T1`, `T2`, `T3` |

`human_same_identity` is self-review, which does not count as review (§3.2 note 2); it appears only on the
`human` authorship row. The matrix group covers every `authorship × review` combination exhaustively.

### `levels.json` — `kind: "classify"`

Raw commit facts mapped to the derived classes **and** the level. Tests the classifier plus the level
function end to end.

| Field | Type | Meaning |
|---|---|---|
| `inputs.signer_identity_class` | string | `human` or `agent` — the verified signer's identity class (§4.2). |
| `inputs.trailers` | object | Git trailers. `Provenance` is `human`/`agent`/`mixed`; `Co-authored-by` is a list of unsigned co-authors. |
| `inputs.policy` | object | `{ "trailers_require": bool }` — whether policy mandates provenance trailers (§4.1). |
| `inputs.review` | object or null | Review facts, or `null` when there is no review. |
| `inputs.review.reviewer_identity_class` | string | `human` or `agent`. |
| `inputs.review.reviewer_identity` | string | The reviewer's identity. |
| `inputs.review.author_identity` | string | The commit's verified **signer principal** (the name predates ADR-025's clarification). Same-identity tests: disqualifies agent review (§3.3(2)); for human review it prevents double-counting only — a same-identity human review of agent/mixed/ambiguous-authored work still counts as the one accountable human (§3.2 note 2, ADR-025). |
| `inputs.review.separate_context` | bool | Whether the reviewer ran with no shared state (§3.3(1)). |
| `inputs.review.signed_attestation` | bool | Whether a signed review attestation exists (§3.3(3)). |
| `expected.authorship` | string | Derived authorship class. |
| `expected.review` | string | Derived review class (a non-qualifying review classifies as `none`). |
| `expected.level` | string | Resulting level, consistent with `expected.authorship` and `expected.review`. |

### `precedence.json` — `kind: "precedence"`

| Field | Type | Meaning |
|---|---|---|
| `ordered` | array of string | Version strings in **strictly increasing** precedence order (no ties). |
| `note` | string | Why the ordering holds; editorial. |

### `precedence.json` — `kind: "grammar"`

| Field | Type | Meaning |
|---|---|---|
| `tag` | string | The tag string to parse. |
| `expected.outcome` | string | `trust_version`, `plain_version`, or `invalid`. |
| `expected.component_path` | string or null | Extracted path prefix (e.g. `pkg/common`), or `null`. |
| `expected.core` | string or null | Extracted `MAJOR.MINOR.PATCH`, or `null` for `invalid`. |
| `expected.level` | int or null | Trust level `0`–`3`, or `null` when there is no trust suffix. |
| `expected.iteration` | int or null | Iteration (≥ 1), or `null` when there is no trust suffix. |
| `expected.prerelease` | string or null | For `plain_version`, the non-trust pre-release (e.g. `rc.1`); otherwise `null`. |
| `expected.reason` | string or null | For `invalid`, why the tag is rejected; otherwise `null`. |

The three grammar outcomes are distinct on purpose:

- **`trust_version`** — matches the §7.1 grammar: either a clean `[path/]vMAJOR.MINOR.PATCH` or a trust
  suffix `-tLEVEL.ITERATION`. Trust components are extracted.
- **`plain_version`** — a valid SemVer version whose pre-release is not trust-shaped (e.g. `rc.1`). It is
  accepted as an ordinary pre-release with the trust suffix **absent**, not rejected. This keeps
  non-trust tags (rc/alpha/beta) usable while the trust layer simply reports "no trust information".
- **`invalid`** — a *trust-shaped* pre-release (begins with `t` then a digit) that violates the trust
  grammar (two-digit level, missing/zero iteration, level out of range), or a string that is not a valid
  `vMAJOR.MINOR.PATCH` tag at all. A malformed trust attempt is rejected loudly rather than silently
  ignored.

### `aggregation.json` — kind: `scope_partition`

Diff-path lists mapped through a policy scope-glob map (§5.1). Globs are gitignore-style and segment-aware:
`*` matches within a path segment, `**` matches across segments (so `services/auth/**` does not match
`services/authz/…`). Paths matching no glob fall into the implicit `default` scope.

| Field | Type | Meaning |
|---|---|---|
| `inputs.scopes` | object | Policy scope map: glob → scope name (§9 `[scopes]`). |
| `inputs.commits[]` | array | Commits in range; each has `id` (string) and `paths` (diff-path list). |
| `expected.scopes` | object | Scope name → ids of the commits touching it, in input order. Untouched scopes are absent. |

### `aggregation.json` — kind: `scope_floor`

Same inputs plus per-commit levels; asserts the §5.2 per-scope floor. A commit MAY carry a `derivation`
object modeling §4.4 as it feeds aggregation: when `verified` is true, paths matching `outputs` contribute
`inherited_level` (the derivation inputs' floor, computed upstream and carried here as data); all other
paths — and every path when `verified` is false — contribute the commit's raw `level`.

| Field | Type | Meaning |
|---|---|---|
| `inputs.scopes` | object | Policy scope map, as above. |
| `inputs.commits[]` | array | Each has `id`, `level` (`T0`–`T3`), `paths`, and optionally `derivation`. |
| `inputs.commits[].derivation` | object | `{ "outputs": [globs], "verified": bool, "inherited_level": "T0"–"T3" }`. |
| `expected.own_trust` | object | Scope name → floored own trust (`T0`–`T3`) for every touched scope. |

### `aggregation.json` — kind: `meta_path`

The §5.4 hard-fail rule: a range containing a meta-path commit below the required level MUST fail
verification outright — not demote, fail.

| Field | Type | Meaning |
|---|---|---|
| `inputs.meta` | object | `{ "paths": [globs], "required_level": "T0"–"T3" }` (§9 `[meta]`). |
| `inputs.commits[]` | array | Each has `id`, `level`, `paths`. |
| `expected.outcome` | string | `verified` or `verification_failed`. |
| `expected.violations` | array | Ids of under-leveled commits touching a meta-path (empty when `verified`). |

### `propagation.json` — kind: `propagation`

Effective trust over the internal dependency graph (§5.3): `effective(C) = min(own(C), min over deps D of
effective(D))`, with cycles collapsed to their strongly connected component.

| Field | Type | Meaning |
|---|---|---|
| `inputs.nodes` | object | Component name → own trust (`T0`–`T3`). |
| `inputs.edges` | array | Directed edges `[consumer, dependency]`. |
| `expected.effective` | object | Component name → effective trust, for every node. |
| `expected.floor_source` | object | Optional. Component name → the component whose own trust set the floor (the node itself when its own trust attains the minimum). |

### `decision.json` — kind: `decision`

The §6.4 default decision table (the illustrative policy; tuned tables are out of scope) with §6.1 semantic
floor, §6.3 strategies, and §7.1 encoding. `differ proof required` cells resolve to pre-release when
`differ_available` is false (§1.1 honest degradation); the requirement is qualified to PATCH claims where
the table says so, and unqualified on the T1/low cell.

| Field | Type | Meaning |
|---|---|---|
| `inputs.effective_trust` | string | `T0`–`T3`. |
| `inputs.blast` | string | Qualitative blast score: `low`, `moderate`, `high` (§6.2). |
| `inputs.strategy` | string | `demote` or `inflate` (§6.3). |
| `inputs.differ_available` | bool | Whether a compatibility differ exists for the ecosystem (§6.1). |
| `inputs.semantic_floor` | string | The §6.1 minimum bump: `patch`, `minor`, `major`. |
| `inputs.claimed_bump` | string | The claimed bump, same values. |
| `inputs.current_version` | string | The previous release tag (clean §7.1 form, component path allowed). |
| `inputs.iteration` | int | Trust-suffix iteration for this cut (≥ 1; re-cuts increment it, §7.2). |
| `expected.channel` | string | `clean` or `prerelease`. |
| `expected.bump` | string or null | Final bump: max of claim and semantic floor (the floor is honored unconditionally). |
| `expected.version` | string or null | The exact §7.1 tag. |
| `expected.escalate` | bool | Present on `inflate` vectors only: whether the bump escalates. Escalated vectors carry `null` bump/version, because the escalation target (MINOR vs MAJOR) is a policy choice the spec does not pin (§6.3). |

## How a harness consumes each group

- **`matrix`** — feed `inputs.authorship` and `inputs.review` to the level-assignment function; assert the
  result equals `expected.level`.
- **`classify`** — feed the raw `inputs` (signer identity class, trailers, policy, review facts) to the
  classifier; assert the derived authorship and review classes equal `expected.authorship` /
  `expected.review`, and the assigned level equals `expected.level`.
- **`precedence`** — parse every string in `ordered`, sort by the implementation's SemVer precedence, and
  assert the sorted sequence equals `ordered`. Equivalently, assert each entry has strictly lower precedence
  than the next; equal precedence is a failure.
- **`grammar`** — parse `tag`; assert `expected.outcome`, and for `trust_version` / `plain_version` assert
  the extracted `component_path`, `core`, `level`, `iteration`, and `prerelease` match.
- **`scope_partition`** — partition `inputs.commits` by diff paths through `inputs.scopes`; assert the
  scope → commits map equals `expected.scopes`.
- **`scope_floor`** — compute the per-scope own-trust floor (applying any `derivation` re-leveling first);
  assert it equals `expected.own_trust`.
- **`meta_path`** — evaluate the §5.4 rule over `inputs.commits` against `inputs.meta`; assert
  `expected.outcome` and `expected.violations`. `verification_failed` means the whole range fails — an
  implementation MUST NOT translate it into a demotion.
- **`propagation`** — compute effective trust over the graph with SCC collapse; assert
  `expected.effective` for every node, and `expected.floor_source` where present.
- **`decision`** — run the decision with the §6.4 default table; assert channel, bump, and the exact
  version string (or, for escalated `inflate` vectors, that the bump escalates).

## Versioning and stability

- Vector `id`s are stable. A published `id` is never renamed, reused, or given a different meaning.
- **Adding** vectors (new `id`s) is non-breaking and does not require a `spec_version` bump.
- **Changing** a vector's asserted values (`expected`, `ordered`, or `tag`) is a semantic change that MUST
  accompany a spec change and a `spec_version` bump — implementations pin to a `spec_version`, so silently
  altering an expectation would break conformance claims.
- `description` and `note` fields are editorial and may be refined without a version bump.

## License

The vectors and the validator in this directory are licensed under [Apache 2.0](LICENSE) so implementations
may vendor them freely. The specification prose remains CC BY 4.0 — see the repository root for the full
path→license map.
