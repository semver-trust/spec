<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# AGENTS.md — semver-trust/spec

Agent contract for the SemVer-Trust specification repository. Read fully
before changing anything. The design record's **agent handoff contract**
(`docs/design-record.md`, §9) is incorporated by reference
and governs wherever this file is silent.

## What this repository is

The home of the SemVer-Trust specification and its supporting artifacts:

| Path | Role | License |
|---|---|---|
| `spec/semver-trust.md` | **Normative specification** (draft v0.9) | CC BY 4.0 |
| `docs/design-record.md` | Design record: rationale, QA record, handoff contract | CC BY 4.0 |
| `docs/adr/` | Decision records, one file per ADR, indexed at `docs/adr/README.md` | CC BY 4.0 |
| `release/`, `review/` | Predicate-type definitions | CC BY 4.0 |
| `schemas/` | JSON Schemas for attestation predicates | Apache 2.0 |
| `conformance/` | Conformance vectors — the sync contract with implementations | Apache 2.0 |
| `TRADEMARK.md`, `LICENSE`, `LICENSE-APACHE` | Governance and licensing | do not modify |

Document precedence: the spec is normative; the design record explains why.
If they conflict, the spec wins and the conflict is a defect to report.

## Commands

Environment: `devbox shell` (pins Python, `uv`, `go-task`, and every lint
tool used below — ADR-016). Outside devbox, `scripts/check-drift.py`
requires Python 3.11+ (`tomllib`) and nothing else.

- `task verify` — run all repository drift/consistency checks
  (`scripts/check-drift.py`); this is what "Verification duties" below
  refers to.
- `task lint` — run every linter: `ruff check`/`ruff format --check` on
  `scripts/`, `markdownlint`, `shellcheck`, `actionlint`, `yamlfmt -lint`.
- `task fmt` — format YAML (`yamlfmt .`).
- `python3 scripts/check-drift.py` — run the drift checks directly.

## Hard rules

1. **Never edit an accepted ADR's Decision/Rationale/Rejected text.**
   Decisions change only by superseding: a new `docs/adr/NNNN-slug.md` with
   the next number and a `Supersedes:` field, plus a row in the index. The
   sole permitted edit to a superseded file is its Status line
   (`Superseded by ADR-NNN`). Never renumber or delete ADR files.
2. **Do not re-litigate rejected alternatives** (each ADR's Rejected list)
   absent new evidence or a changed requirement from the maintainer. Known
   temptations: build-metadata encoding (ADR-001), de-minimis exemptions
   (ADR-033/P3), unverifiable→T0 (ADR-008), inflation-as-only-strategy
   (ADR-005), CC0 or restrictive licensing (ADR-014).
3. **Never modify `LICENSE`, `LICENSE-APACHE`, or `TRADEMARK.md`** without
   explicit maintainer instruction in the current session. The license
   files are verbatim canonical texts; verbatim-ness is load-bearing.
4. **Do not change an emitted predicate version in place.** The project
   domain is registered and the v0.1 release/review predicates have been
   emitted. Incompatible wire or interpretation changes require a new
   predicate version plus coordinated schema and conformance updates.
5. **Do not restructure or renumber spec sections** without instruction.
   `§` cross-references span both documents and external discussion;
   renumbering breaks them silently.
6. Normative changes to `spec/semver-trust.md` require a spec version bump and
   a matching design-record update (new ADR or QA-record entry). Editorial
   changes (typos, wording without meaning change) do not.

## Licensing rules for new files

- Prose (spec text, docs) → first line `<!-- SPDX-License-Identifier: CC-BY-4.0 -->`
- Machine-consumable artifacts (schemas, vectors, scripts) → SPDX header
  `Apache-2.0` in the appropriate comment syntax.
- When creating `schemas/` or `conformance/`, place a verbatim copy of the
  Apache 2.0 text as `LICENSE` **inside** the directory (ADR-014
  implementation notes) so vendored copies carry their license.
- Keep the README's path→license map in sync with any new top-level path.

## Verification duties

After any edit to `spec/semver-trust.md` or the design record, verify before
presenting the change — run `task verify`, which covers:

- All `§` and ADR cross-references resolve across the spec, the design
  record, and `docs/adr/` (every referenced ADR has a file and index row).
- The §3.2 level table, Appendix B grid, and the accountability invariant
  (level = accountable-human count; agent corroboration lifts T0→T1 only)
  remain mutually consistent.
- SemVer precedence claims hold under the spec's comparison rules
  (`rc.1 < t1.1 <` clean; `t10 < t2` hazard ⇒ levels stay single-digit).
- Embedded TOML and JSON examples parse.
- Every `docs/adr/` filename equals `NNNN-` + the slugified file title
  (lowercase, non-alphanumeric runs → single hyphen, trimmed), and the
  index row links to it.
- RFC 2119 keywords (MUST/SHOULD/MAY) are used only with intent; changing
  one is a normative change (rule 6).

## Terminology discipline

Use spec §2 terms exactly: *own trust* vs *effective trust*; *scope* vs
*component*; *channel*; *accountable human*; *derivation*. Terminology
drift has already caused one recorded bug (`docs/design-record.md` §5.8).

## Style

- The spec stays language-agnostic; Go-specific material belongs in
  `semver-trust-go`, ecosystem specifics in evidence-provider terms.
- Honesty clauses are load-bearing (P2, P4): never draft text that claims
  more than the evidence supports — no inferred authorship beyond what
  signatures prove, no waived evidence where a differ is missing.

## Out of scope for this repository

Implementation code, CLI design beyond the sketch in the design record,
and release automation. This repo will eventually dogfood SemVer-Trust
itself (trust-tagged releases of the spec); until a policy file exists
here, do not invent one.
