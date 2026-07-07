<!-- SPDX-License-Identifier: Apache-2.0 -->
# SemVer-Trust Attestation Schemas

JSON Schemas for the SemVer-Trust attestation predicates:

| Predicate type | Schema | Status |
|---|---|---|
| `https://semver-trust.dev/release/v0.1` | [`release-v0.1.json`](release-v0.1.json) | available |
| `https://semver-trust.dev/review/v0.1` | [`review-v0.1.json`](review-v0.1.json) | available |

Both schemas are JSON Schema draft 2020-12 and validate a complete in-toto
Statement (envelope plus predicate). See the specification for the normative
predicate definitions: [release §8.1](../spec/semver-trust.md),
[review §4.3](../spec/semver-trust.md).

## Versioning policy

Predicate-type versions freeze at first emission (maintainer decision,
2026-07-06). Within a version, schema changes are **additive-only**: new
optional fields may be added; nothing is removed, renamed, retyped, or made
newly required. Any breaking change mints a new predicate-type URI and schema
file (`…/release/v0.2`, `release-v0.2.json`); prior versions remain in this
directory so attestations emitted against them stay verifiable forever.

Schemas in this directory are licensed under [Apache 2.0](LICENSE) so
implementations may vendor them freely. The specification prose remains
CC BY 4.0 — see the repository root for the license map.
