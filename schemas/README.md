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

Schemas in this directory are licensed under [Apache 2.0](LICENSE) so
implementations may vendor them freely. The specification prose remains
CC BY 4.0 — see the repository root for the license map.
