<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# SemVer-Trust

**Provenance-scoped trust levels for semantic versioning — verifiable
release trust for the age of AI-authored code.**

When agents author a growing share of software, a version number's implicit
claim — *safe drop-in replacement* — needs evidence behind it. SemVer-Trust
encodes verifiable **trust levels** (T0–T3, counting the independent
accountable humans behind a release) in standard SemVer pre-release
identifiers, so under-evidenced releases are opt-in by construction:

```
v1.4.0-t1.1  <  v1.4.0     ← low-trust releases sort below the clean
                              version; default resolvers skip them
```

Signed in-toto attestations carry the full evidence — who authored, who
reviewed, what was proven. SLSA answers *how was this built*; sigstore
answers *who signed this*; SemVer-Trust answers *what human evidence stands
behind this release's claims*.

## Read the specification

**[SemVer-Trust specification — draft v0.4](spec/semver-trust.md)**

New readers: start with §1 (principles), §3 (the trust model), and
Appendix A (a worked monorepo example). The project keeps its full
reasoning on the record — see the design record below for why every
decision is the way it is.

## Repository map

| Path | Contents | License |
|---|---|---|
| [spec/semver-trust.md](spec/semver-trust.md) | The normative specification | CC BY 4.0 |
| [docs/design-record.md](docs/design-record.md) | Design rationale, QA record, and the agent handoff contract | CC BY 4.0 |
| [docs/adr/](docs/adr/README.md) | Decision log — one file per architecture decision record | CC BY 4.0 |
| [docs/analysis/](docs/analysis/2026-07-04-steelman.md) | Adversarial (steelman) analyses and standing predictions | CC BY 4.0 |
| [release/](release/v0.1.md) · [review/](review/v0.1.md) | Predicate-type definitions, resolvable at `semver-trust.dev` | CC BY 4.0 |
| [schemas/](schemas/README.md) | JSON Schemas for the attestation predicates | Apache 2.0 |
| `conformance/` | Conformance vectors — the sync contract for implementations | Apache 2.0 |
| `scripts/` | Repository consistency checks (`check-drift.py`) | Apache 2.0 |

## Status

The specification is a **v0.4 working draft**. The official Go
implementation ([semver-trust-go](https://github.com/semver-trust/semver-trust-go))
passes the draft v0.3 conformance suite and releases itself under the scheme
(v0.1.0 and v0.2.0 are published, verified, reproducible dogfood). The legacy
release path is not suitable for production claims until the successor protocol
and conformance contract land. Draft v0.4 adds release-interval,
policy-transition, and authenticated version-ancestry vectors that are pending
implementation. Design discussion happens in [issues](https://github.com/semver-trust/spec/issues) — see
[CONTRIBUTING](CONTRIBUTING.md) before opening a pull request.

## License and trademark

This repository is dual-licensed by content type: specification text and
documentation are [CC BY 4.0](LICENSE); schemas, conformance vectors, and
scripts are [Apache 2.0](LICENSE-APACHE), with a license copy inside each
Apache-licensed directory so vendored copies stay self-describing. Unless
a file's SPDX header states otherwise, prose is CC BY 4.0 and
machine-consumable artifacts are Apache 2.0.

Use of the SemVer-Trust name and of conformance claims is governed by the
[trademark policy](TRADEMARK.md): implementations that pass the
conformance suite may say so — verifiable claims are the point.
