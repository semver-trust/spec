#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""check-conformance.py — independent validation of the SemVer-Trust conformance vectors.

Validates the core, release-range, policy-transition, version-ancestry,
qualified-review, and cryptographic vector files against a second, independent implementation of the
spec rules they encode (``spec/semver-trust.md`` §3.2-§3.3, §4.1-§4.2,
§5.1-§5.4, §6.1-§6.4, §7.1-§7.5, §10, Appendix A). This is deliberately NOT the reference
Go implementation, and it shares no code with ``scripts/check-drift.py`` — the
SemVer comparator, level invariant, interval reachability, policy-transition,
version-ancestry, and qualified-review rules, scope/floor/propagation arithmetic, and decision
table are re-implemented here from first principles. Agreement between
independent implementations is the point.

    uv run --group dev python3 scripts/check-conformance.py

Exit code 0 = all vectors valid. Requires Python 3.11+, ssh-keygen and git on
PATH (for the cryptographic fixture gates), and the dev dependency group for
the pinned Draft 2020-12 schema validator (jsonschema) — the one deliberate
exception to the scripts-run-on-bare-Python rule, recorded in pyproject.toml:
schema validation at the first-emission freeze must be the real thing, not a
hand-rolled subset.
"""

import base64
import binascii
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from itertools import pairwise
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parent.parent
CONFORMANCE = ROOT / "conformance"
LEVELS = CONFORMANCE / "levels.json"
PRECEDENCE = CONFORMANCE / "precedence.json"
AGGREGATION = CONFORMANCE / "aggregation.json"
PROPAGATION = CONFORMANCE / "propagation.json"
DECISION = CONFORMANCE / "decision.json"
RANGE = CONFORMANCE / "range.json"
VERSION_ANCESTRY = CONFORMANCE / "version-ancestry.json"
POLICY_TRANSITION = CONFORMANCE / "policy-transition.json"
REVIEW_QUALIFICATION = CONFORMANCE / "review-qualification.json"
PREDICATE_V02 = CONFORMANCE / "predicate-v0.2.json"
SIGNATURE = CONFORMANCE / "crypto" / "signature-vectors.json"
ATTESTATION = CONFORMANCE / "crypto" / "attestations" / "attestation-vectors.json"
SCHEMAS = ROOT / "schemas"
VECTOR_FILES = (
    LEVELS,
    PRECEDENCE,
    AGGREGATION,
    PROPAGATION,
    DECISION,
    RANGE,
    VERSION_ANCESTRY,
    POLICY_TRANSITION,
    REVIEW_QUALIFICATION,
    PREDICATE_V02,
    SIGNATURE,
    ATTESTATION,
)
PREDICATE_SCHEMAS = {
    "https://semver-trust.dev/release/v0.1": "release-v0.1.json",
    "https://semver-trust.dev/review/v0.1": "review-v0.1.json",
    "https://semver-trust.dev/release/v0.2": "release-v0.2.json",
    "https://semver-trust.dev/review/v0.2": "review-v0.2.json",
}
ATTESTATIONS_DIR = ATTESTATION.parent
SPEC = ROOT / "spec" / "semver-trust.md"

AUTHORSHIP = ("agent", "mixed", "ambiguous", "human")
REVIEW = ("none", "agent_independent", "human_distinct")
LEVEL_RANK = {"T0": 0, "T1": 1, "T2": 2, "T3": 3}
BUMP_RANK = {"patch": 0, "minor": 1, "major": 2}

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {name}{('  — ' + detail) if (detail and not ok) else ''}")
    if not ok:
        failures.append(name)


# ---- Independent spec implementations --------------------------------------
#
# level = f(accountable-human count, agent corroboration), per §3.2 / Appendix B.
# Humans: the author (if human) plus a *distinct* human reviewer. Agent
# corroboration (independent agent review, §3.3) lifts the zero-human case T0->T1.
def invariant_level(authorship: str, review: str) -> str:
    humans = (authorship == "human") + (review == "human_distinct")
    if humans == 0:
        return "T1" if review == "agent_independent" else "T0"
    if humans == 1:
        return "T2"
    return "T3"


# SemVer 2.0.0 §11 precedence via a total-order sort key. A release outranks any
# pre-release of the same core; numeric identifiers sort below alphanumeric ones;
# a shorter run of equal-prefixed identifiers sorts lower.
_SEMVER = re.compile(
    r"^(?P<major>0|[1-9][0-9]*)\.(?P<minor>0|[1-9][0-9]*)\.(?P<patch>0|[1-9][0-9]*)"
    r"(?:-(?P<pre>[0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?$"
)


def precedence_key(version: str) -> tuple:
    m = _SEMVER.match(version)
    if not m:
        raise ValueError(f"not a SemVer version: {version}")
    core = (int(m["major"]), int(m["minor"]), int(m["patch"]))
    pre = m["pre"]
    if not pre:
        return (core, (1,))  # release ranks above any pre-release
    identifiers = []
    for token in pre.split("."):
        if token.isdigit():
            identifiers.append((0, int(token), ""))  # numeric < alphanumeric
        else:
            identifiers.append((1, -1, token))  # ASCII-lexical
    return (core, (0, tuple(identifiers)))


# §7.1 ABNF, exactly: the strict trust-tag grammar (clean core-version OR
# trust-version), and a general SemVer-tag grammar used to tell a plain
# pre-release version (accepted, trust absent) from a rejected malformed tag.
_TRUST_TAG = re.compile(
    r"^(?:(?P<path>[0-9A-Za-z._-]+(?:/[0-9A-Za-z._-]+)*)/)?"
    r"v(?P<core>(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*))"
    r"(?:-t(?P<level>[0-3])\.(?P<iter>[1-9][0-9]*))?$"
)
_SEMVER_TAG = re.compile(
    r"^(?:(?P<path>[0-9A-Za-z._-]+(?:/[0-9A-Za-z._-]+)*)/)?"
    r"v(?P<core>(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*))"
    r"(?:-(?P<pre>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+[0-9A-Za-z.-]+)?$"
)


# §5.1 scope globs, gitignore-style segments: '*' stays inside a path segment,
# '**' crosses segments. Segment-aware on purpose: services/auth/** must not
# match services/authz/….
def _glob_to_re(pattern: str) -> re.Pattern:
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def _scopes_of(path: str, compiled: list[tuple[re.Pattern, str]]) -> set[str]:
    touched = {scope for rx, scope in compiled if rx.match(path)}
    return touched or {"default"}  # §5.1: unmatched paths fall to the implicit default scope


# Per-path contributed level after §4.4: the portable baseline does not define
# executable derivation proofs, so derivation metadata never re-levels paths.
def _path_level(commit: dict, path: str) -> str:
    _ = path
    return commit["level"]


def _partition(scopes: dict[str, str], commits: list[dict]) -> dict[str, list[str]]:
    compiled = [(_glob_to_re(g), name) for g, name in scopes.items()]
    result: dict[str, list[str]] = {}
    for commit in commits:
        touched: set[str] = set()
        for path in commit["paths"]:
            touched |= _scopes_of(path, compiled)
        for scope in touched:
            result.setdefault(scope, []).append(commit["id"])
    return result


# §5.2: own_trust(scope) = min over commits touching the scope of level(c).
# Unsupported derivation claims do not elevate path levels (§4.4).
def _floors(scopes: dict[str, str], commits: list[dict]) -> dict[str, str]:
    compiled = [(_glob_to_re(g), name) for g, name in scopes.items()]
    floors: dict[str, int] = {}
    for commit in commits:
        for path in commit["paths"]:
            rank = LEVEL_RANK[_path_level(commit, path)]
            for scope in _scopes_of(path, compiled):
                floors[scope] = min(floors.get(scope, 3), rank)
    return {scope: f"T{rank}" for scope, rank in floors.items()}


def _edges_to_adj(edges: list[list[str]]) -> dict[str, list[str]]:
    adj: dict[str, list[str]] = {}
    for consumer, dependency in edges:
        adj.setdefault(consumer, []).append(dependency)
    return adj


# Tarjan SCC over the dependency graph (edges point consumer -> dependency).
def _sccs(nodes: list[str], adj: dict[str, list[str]]) -> dict[str, int]:
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    on_stack: set[str] = set()
    stack: list[str] = []
    scc_of: dict[str, int] = {}
    counter = [0, 0]  # next index, next scc id

    def visit(v: str) -> None:
        index[v] = low[v] = counter[0]
        counter[0] += 1
        stack.append(v)
        on_stack.add(v)
        for w in adj.get(v, []):
            if w not in index:
                visit(w)
                low[v] = min(low[v], low[w])
            elif w in on_stack:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            while True:
                w = stack.pop()
                on_stack.discard(w)
                scc_of[w] = counter[1]
                if w == v:
                    break
            counter[1] += 1

    for v in nodes:
        if v not in index:
            visit(v)
    return scc_of


# §5.3: effective(C) = min(own(C), min over deps D of effective(D)), with cycles
# collapsed to their SCC (every member shares the SCC's minimum own trust).
def _effective(own: dict[str, str], edges: list[list[str]]) -> dict[str, str]:
    scc_of = _sccs(list(own), _edges_to_adj(edges))
    scc_own: dict[int, int] = {}
    for node, scc in scc_of.items():
        scc_own[scc] = min(scc_own.get(scc, 3), LEVEL_RANK[own[node]])
    scc_adj: dict[int, set[int]] = {}
    for consumer, dependency in edges:
        a, b = scc_of[consumer], scc_of[dependency]
        if a != b:
            scc_adj.setdefault(a, set()).add(b)
    memo: dict[int, int] = {}

    def eff(scc: int) -> int:
        if scc not in memo:
            memo[scc] = min(
                [scc_own[scc]] + [eff(dep) for dep in scc_adj.get(scc, ())],
            )
        return memo[scc]

    return {node: f"T{eff(scc_of[node])}" for node in own}


def _reachable(start: str, edges: list[list[str]]) -> set[str]:
    adj = _edges_to_adj(edges)
    seen, frontier = {start}, [start]
    while frontier:
        for nxt in adj.get(frontier.pop(), []):
            if nxt not in seen:
                seen.add(nxt)
                frontier.append(nxt)
    return seen


# §5.2 release intervals over a Git-style parent graph. Commit arrays in the
# vectors are oldest-first fixtures; the set arithmetic is normative and input
# order is used only to serialize the expected provenance membership.
def _commit_reach(start: str, parents: dict[str, list[str]]) -> set[str]:
    seen: set[str] = set()
    frontier = [start]
    while frontier:
        commit = frontier.pop()
        if commit in seen:
            continue
        seen.add(commit)
        frontier.extend(parents.get(commit, []))
    return seen


def _release_interval(inputs: dict) -> dict:
    ordered = [commit["id"] for commit in inputs["commits"]]
    parents = {commit["id"]: commit["parents"] for commit in inputs["commits"]}

    def fail(reason: str) -> dict:
        return {"outcome": "verification_failed", "commits": [], "reason": reason}

    if len(parents) != len(ordered) or any(
        parent not in parents for commit_parents in parents.values() for parent in commit_parents
    ):
        return fail("invalid_commit_graph")
    to = inputs["to"]
    if to not in parents:
        return fail("unknown_to")
    reachable_to = _commit_reach(to, parents)
    mode = inputs["mode"]

    if mode == "inception":
        if inputs["existing_chain_heads"] != 0:
            return fail("predecessor_required")
        if inputs.get("requested_from") is not None:
            return fail("untrusted_from")
        included = reachable_to
    elif mode == "adoption":
        if inputs["existing_chain_heads"] != 0:
            return fail("predecessor_required")
        if inputs.get("requested_from") is not None:
            return fail("untrusted_from")
        boundary = inputs.get("boundary")
        if boundary is None:
            return fail("boundary_required")
        if not boundary["bootstrap_pinned"]:
            return fail("boundary_not_bootstrap_pinned")
        if boundary["ref_target"] != boundary["oid"]:
            return fail("boundary_ref_moved")
        boundary_oid = boundary["oid"]
        if boundary_oid not in reachable_to:
            return fail("boundary_not_reachable")
        excluded: set[str] = set()
        for parent in parents[boundary_oid]:
            excluded |= _commit_reach(parent, parents)
        included = reachable_to - excluded
    elif mode == "recurring":
        predecessor = inputs.get("predecessor")
        if predecessor is None:
            return fail("predecessor_missing")
        if not predecessor["accepted"]:
            return fail("predecessor_not_accepted")
        if not predecessor["chain_head"] or inputs["existing_chain_heads"] != 1:
            return fail("predecessor_not_unique_head")
        if predecessor["repository"] != inputs["repository"]:
            return fail("predecessor_repository_mismatch")
        if predecessor["component"] != inputs["component"]:
            return fail("predecessor_component_mismatch")
        previous_to = predecessor["to"]
        if previous_to not in reachable_to:
            return fail("predecessor_not_ancestor")
        if predecessor["tag_target"] != previous_to:
            return fail("predecessor_ref_moved")
        if inputs.get("requested_from") != previous_to:
            return fail("from_not_predecessor")
        if previous_to == to:
            return fail("promotion_required")
        included = reachable_to - _commit_reach(previous_to, parents)
    else:
        return fail("unknown_interval_mode")

    return {
        "outcome": "verified",
        "commits": [commit for commit in ordered if commit in included],
        "reason": None,
    }


def _meta_covers(policy: dict, path: str) -> bool:
    return any(_glob_to_re(pattern).match(path) for pattern in policy["meta_paths"])


def _mandatory_meta_covered(policy: dict) -> bool:
    mandatory = [policy["path"], *policy["trust_material"]]
    return all(_meta_covers(policy, path) for path in mandatory)


def _trust_roles_valid(state: dict) -> bool:
    role_paths = list(state["trust_roles"].values())
    material_paths = set(state["trust_material"])
    return bool(role_paths) and set(role_paths) == material_paths


def _verification_time_valid(value: object) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return parsed.utcoffset() is not None and parsed.utcoffset().total_seconds() == 0


# §5.4 / ADR-028: bootstrap or predecessor state selects the active policy;
# candidate state never authorizes its own transition and activates only after
# the release succeeds.
def _policy_transition(doc: dict, inputs: dict) -> dict:
    policies = doc["policies"]
    active = policies[inputs["active_policy"]]
    candidate = policies[inputs["candidate_policy"]]

    def fail(reason: str) -> dict:
        return {
            "outcome": "verification_failed",
            "reason": reason,
            "evaluated_policy": active["digest"],
            "activated_policy": None,
        }

    if not _trust_roles_valid(active):
        return fail("active_trust_roles_invalid")
    if not _trust_roles_valid(candidate):
        return fail("candidate_trust_roles_invalid")

    if inputs["authority"] == "bootstrap":
        bootstrap_ref = inputs.get("bootstrap")
        if bootstrap_ref is None:
            return fail("bootstrap_missing")
        bootstrap = doc["bootstraps"][bootstrap_ref]
        if not bootstrap["authenticated"]:
            return fail("bootstrap_unauthenticated")
        if (
            bootstrap["repository"] != inputs["repository"]
            or bootstrap["component"] != inputs["component"]
        ):
            return fail("bootstrap_subject_mismatch")
        if bootstrap["range_mode"] != inputs["range_mode"]:
            return fail("bootstrap_range_mode_mismatch")
        if bootstrap["boundary"] != inputs["boundary"]:
            return fail("bootstrap_boundary_mismatch")
        if bootstrap["verification_profile"] != inputs["verification_profile"]:
            return fail("bootstrap_profile_mismatch")
        if bootstrap["clock_profile"] != inputs["clock_profile"]:
            return fail("bootstrap_clock_profile_mismatch")
        if (
            bootstrap["policy_path"] != active["path"]
            or bootstrap["policy_digest"] != active["digest"]
        ):
            return fail("bootstrap_policy_mismatch")
        if bootstrap["trust_material"] != active["trust_material"]:
            return fail("bootstrap_trust_material_mismatch")
        if bootstrap["trust_roles"] != active["trust_roles"]:
            return fail("bootstrap_trust_roles_mismatch")
        mandatory_meta_paths = bootstrap["mandatory_meta_paths"]
        if (
            candidate["path"] != active["path"]
            or candidate["digest"] != active["digest"]
            or candidate["trust_material"] != active["trust_material"]
            or candidate["trust_roles"] != active["trust_roles"]
        ):
            return fail("bootstrap_candidate_mismatch")
    elif inputs["authority"] == "predecessor":
        predecessor_ref = inputs.get("predecessor")
        if predecessor_ref is None:
            return fail("predecessor_missing")
        predecessor = doc["predecessors"][predecessor_ref]
        if not predecessor["accepted"]:
            return fail("predecessor_not_accepted")
        if not predecessor["chain_head"]:
            return fail("predecessor_not_chain_head")
        if (
            predecessor["repository"] != inputs["repository"]
            or predecessor["component"] != inputs["component"]
        ):
            return fail("predecessor_subject_mismatch")
        if predecessor["verification_profile"] != inputs["verification_profile"]:
            return fail("predecessor_profile_mismatch")
        if predecessor["clock_profile"] != inputs["clock_profile"]:
            return fail("predecessor_clock_profile_mismatch")
        if (
            predecessor["policy_path"] != active["path"]
            or predecessor["policy_digest"] != active["digest"]
            or predecessor["trust_material"] != active["trust_material"]
        ):
            return fail("predecessor_policy_mismatch")
        if predecessor["trust_roles"] != active["trust_roles"]:
            return fail("predecessor_trust_roles_mismatch")
        mandatory_meta_paths = predecessor["mandatory_meta_paths"]
    else:
        return fail("unknown_policy_authority")

    if not _verification_time_valid(inputs.get("verification_time")):
        return fail("verification_time_missing_or_invalid")
    if not all(_meta_covers(active, path) for path in mandatory_meta_paths):
        return fail("active_authority_meta_uncovered")
    if not all(_meta_covers(candidate, path) for path in mandatory_meta_paths):
        return fail("candidate_authority_meta_uncovered")
    if not _mandatory_meta_covered(active):
        return fail("active_mandatory_meta_uncovered")
    if inputs["provided_trust_material"] != active["trust_material"]:
        return fail("trust_material_mismatch")
    if candidate["path"] != active["path"]:
        return fail("candidate_policy_path_changed")
    if LEVEL_RANK[candidate["required_level"]] < LEVEL_RANK[active["required_level"]]:
        return fail("candidate_meta_level_lowered")
    if (
        candidate["adoption_boundary"] is not None
        and candidate["adoption_boundary"] != inputs["boundary"]
    ):
        return fail("adoption_boundary_changed")
    if not _mandatory_meta_covered(candidate):
        return fail("candidate_mandatory_meta_uncovered")

    active_signers = set(active["authorized_signers"])
    for commit in inputs["commits"]:
        if commit["signer"] not in active_signers:
            return fail("unknown_active_signer")

    meta_patterns = [*active["meta_paths"], *candidate["meta_paths"]]
    meta_patterns += mandatory_meta_paths
    meta_patterns += [active["path"], candidate["path"]]
    meta_patterns += list(active["trust_material"])
    meta_patterns += list(candidate["trust_material"])
    compiled = [_glob_to_re(pattern) for pattern in meta_patterns]
    required = LEVEL_RANK[active["required_level"]]
    for commit in inputs["commits"]:
        touches_meta = any(rx.match(path) for path in commit["paths"] for rx in compiled)
        if touches_meta and LEVEL_RANK[commit["level"]] < required:
            return fail("under_level_meta_commit")

    return {
        "outcome": "verified",
        "reason": None,
        "evaluated_policy": active["digest"],
        "activated_policy": candidate["digest"],
    }


# §6.4 default decision table after the §6.2 threshold gate. Cell values:
# the clean channel is available unconditionally, conditioned on a differ proof
# for PATCH claims, or unavailable. The portable baseline does not allow T1 to
# satisfy the clean profile before empirical validation.
_TABLE = {
    ("T3", "low"): "clean",
    ("T3", "moderate"): "clean",
    ("T3", "high"): "differ_patch",
    ("T2", "low"): "clean",
    ("T2", "moderate"): "differ_patch",
    ("T2", "high"): "prerelease",
    ("T1", "low"): "prerelease",
    ("T1", "moderate"): "prerelease",
    ("T1", "high"): "prerelease",
    ("T0", "low"): "prerelease",
    ("T0", "moderate"): "prerelease",
    ("T0", "high"): "prerelease",
}


def _decision_outcome(inputs: dict) -> dict:
    cell = _TABLE[(inputs["effective_trust"], inputs["blast"])]
    bump = max(inputs["claimed_bump"], inputs["semantic_floor"], key=BUMP_RANK.__getitem__)
    below_threshold = LEVEL_RANK[inputs["effective_trust"]] < LEVEL_RANK[inputs["threshold"]]
    differ_needed = cell == "differ_any" or (cell == "differ_patch" and bump == "patch")
    demoted = (
        below_threshold
        or cell == "prerelease"
        or (differ_needed and not inputs["differ_available"])
    )

    if inputs["strategy"] == "inflate":
        if demoted:
            return {"channel": "clean", "escalate": True, "bump": None}
        return {"channel": "clean", "escalate": False, "bump": bump}
    return {"channel": "prerelease" if demoted else "clean", "bump": bump}


def _decide(inputs: dict) -> dict:
    decision = _decision_outcome(inputs)
    if decision.get("escalate"):
        return {**decision, "version": None}

    base = inputs["authenticated_version_base"]
    m = _TRUST_TAG.match(base)
    if m is None or m["level"] is not None:
        raise ValueError(f"authenticated_version_base must be a clean §7.1 tag: {base}")
    bump = decision["bump"]
    major, minor, patch = (int(x) for x in m["core"].split("."))
    if bump == "major":
        core = f"{major + 1}.0.0"
    elif bump == "minor":
        core = f"{major}.{minor + 1}.0"
    else:
        core = f"{major}.{minor}.{patch + 1}"
    prefix = f"{m['path']}/" if m["path"] else ""

    if decision["channel"] == "prerelease":
        iteration = inputs["authenticated_iteration"]
        suffix = f"-t{LEVEL_RANK[inputs['effective_trust']]}.{iteration}"
        return {**decision, "version": f"{prefix}v{core}{suffix}"}
    return {**decision, "version": f"{prefix}v{core}"}


def _bump_core(core: str, bump: str) -> str:
    major, minor, patch = (int(part) for part in core.split("."))
    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


# §7.5 / ADR-029: interval selection never supplies version ancestry. Bootstrap
# or accepted predecessor state selects the baseline; action and bump are signed
# candidate facts; exact target and iteration are derived.
def _version_ancestry(doc: dict, inputs: dict) -> dict:
    def fail(reason: str) -> dict:
        return {
            "outcome": "verification_failed",
            "version_predecessor": None,
            "target_core": None,
            "iteration": None,
            "version": None,
            "advances_version_head": False,
            "reason": reason,
        }

    graph = doc["graphs"][inputs["graph"]]
    ordered = [commit["id"] for commit in graph]
    parents = {commit["id"]: commit["parents"] for commit in graph}
    if len(ordered) != len(parents) or any(
        parent not in parents for commit_parents in parents.values() for parent in commit_parents
    ):
        return fail("invalid_version_graph")
    to = inputs["to"]
    if to not in parents:
        return fail("unknown_to")
    reachable_to = _commit_reach(to, parents)
    refs = doc["ref_sets"][inputs["refs"]]

    decision_inputs = doc["decisions"][inputs["decision"]]
    decision = _decision_outcome(decision_inputs)
    bump = decision["bump"]
    if bump is None:
        return fail("version_escalation_target_unresolved")

    def binding_parts(binding: object, require_clean: bool) -> tuple[re.Match | None, str | None]:
        if not isinstance(binding, dict):
            return None, "version_predecessor_malformed"
        tag = binding.get("tag")
        if not isinstance(tag, str):
            return None, "version_predecessor_malformed"
        match = _TRUST_TAG.match(tag)
        if match is None or (require_clean and match["level"] is not None):
            return None, "version_predecessor_malformed"
        if (match["path"] or "") != inputs["tag_prefix"]:
            return None, "version_predecessor_component_mismatch"
        observed = refs.get(tag)
        if observed is None:
            return None, "version_predecessor_missing"
        if observed["ref_oid"] != binding.get("ref_oid"):
            return None, "version_predecessor_ref_moved"
        if observed["commit_oid"] != binding.get("commit_oid"):
            return None, "version_predecessor_commit_moved"
        return match, None

    authority = inputs["authority"]
    state: dict | None = None
    version_predecessor: str | None = None
    source_successor_exists = False
    target_reevaluation_consumed = False

    if authority == "bootstrap":
        bootstrap_ref = inputs.get("bootstrap")
        if bootstrap_ref is None:
            return fail("version_bootstrap_missing")
        bootstrap = doc["bootstraps"][bootstrap_ref]
        if not bootstrap["authenticated"]:
            return fail("version_bootstrap_unauthenticated")
        if (
            bootstrap["repository"] != inputs["repository"]
            or bootstrap["component"] != inputs["component"]
        ):
            return fail("version_bootstrap_subject_mismatch")
        if bootstrap["interval_mode"] != inputs["interval_mode"]:
            return fail("version_bootstrap_interval_mismatch")
        if bootstrap["boundary"] != inputs["boundary"]:
            return fail("version_bootstrap_boundary_mismatch")
        if bootstrap["tag_prefix"] != inputs["tag_prefix"]:
            return fail("version_bootstrap_prefix_mismatch")
        if inputs["action"] != "advance":
            return fail("version_genesis_requires_advance")

        if "version_predecessor" not in bootstrap:
            return fail("version_predecessor_selection_missing")
        predecessor = bootstrap["version_predecessor"]
        if isinstance(predecessor, list):
            return fail("version_predecessor_ambiguous")
        if predecessor is None:
            base_core = "0.0.0"
        else:
            match, reason = binding_parts(predecessor, require_clean=True)
            if reason is not None:
                return fail(reason)
            predecessor_commit = predecessor["commit_oid"]
            if predecessor_commit not in parents:
                return fail("version_predecessor_not_ancestor")
            if inputs["interval_mode"] == "inception":
                ancestor_target = reachable_to
            elif inputs["interval_mode"] == "adoption":
                boundary = inputs["boundary"]
                if boundary not in parents or boundary not in reachable_to:
                    return fail("version_bootstrap_boundary_invalid")
                ancestor_target = _commit_reach(boundary, parents)
            else:
                return fail("version_bootstrap_interval_mismatch")
            if predecessor_commit not in ancestor_target:
                return fail("version_predecessor_not_ancestor")
            base_core = match["core"]
            version_predecessor = predecessor["tag"]
        target_core = _bump_core(base_core, bump)
        iterations: dict[str, int] = {}
        clean_accepted = False
    elif authority in {"predecessor", "superseded"}:
        collection = doc["predecessors"] if authority == "predecessor" else doc["superseded"]
        fixture_ref = inputs.get(authority)
        if fixture_ref is None:
            return fail("version_predecessor_missing")
        selected = collection[fixture_ref]
        if not selected["accepted"]:
            return fail("version_predecessor_not_accepted")
        if authority == "predecessor" and not selected["chain_head"]:
            return fail("version_predecessor_not_chain_head")
        if (
            selected["repository"] != inputs["repository"]
            or selected["component"] != inputs["component"]
        ):
            return fail("version_predecessor_subject_mismatch")
        if selected["tag_prefix"] != inputs["tag_prefix"]:
            return fail("version_predecessor_component_mismatch")
        if inputs["interval_mode"] != "recurring":
            return fail("version_predecessor_interval_mismatch")
        canonical_tags = selected["canonical_tags"]
        if len(canonical_tags) != 1:
            return fail("version_predecessor_ambiguous")
        canonical = canonical_tags[0]
        match, reason = binding_parts(canonical, require_clean=False)
        if reason is not None:
            return fail(reason)
        if canonical["commit_oid"] != selected["to"]:
            return fail("version_predecessor_state_mismatch")
        if authority == "predecessor":
            if selected["to"] not in reachable_to or selected["to"] == to:
                return fail("version_predecessor_not_ancestor")
            if inputs["action"] not in {"advance", "recut"}:
                return fail("version_action_invalid")
        else:
            if selected["to"] != to or inputs["action"] != "supersede":
                return fail("version_supersession_mismatch")
            source_successor_exists = selected["source_successor_exists"]

        state = selected["version_state"]
        if _SEMVER.fullmatch(state["target_core"]) is None or state["target_bump"] not in BUMP_RANK:
            return fail("version_predecessor_state_mismatch")
        corrective_floor = state.get("corrective_floor")
        if corrective_floor is not None and corrective_floor not in BUMP_RANK:
            return fail("version_predecessor_state_mismatch")
        if (
            corrective_floor is not None
            and BUMP_RANK[corrective_floor] <= BUMP_RANK[state["target_bump"]]
        ):
            return fail("version_predecessor_state_mismatch")
        target_intervals = state.get("target_intervals")
        if (
            not isinstance(target_intervals, list)
            or not target_intervals
            or not all(isinstance(interval, str) and interval for interval in target_intervals)
            or len(target_intervals) != len(set(target_intervals))
        ):
            return fail("version_predecessor_state_mismatch")
        if state["target_core"] != match["core"]:
            return fail("version_predecessor_state_mismatch")
        iterations = state["iterations"].copy()
        if any(
            level not in LEVEL_RANK or not isinstance(value, int) or value < 1
            for level, value in iterations.items()
        ):
            return fail("version_predecessor_state_mismatch")
        if match["level"] is None:
            if not state["clean_accepted"]:
                return fail("version_predecessor_state_mismatch")
        else:
            level = f"T{match['level']}"
            if state["clean_accepted"] or iterations.get(level) != int(match["iter"]):
                return fail("version_predecessor_state_mismatch")
        baseline = state["baseline"]
        if baseline is None:
            if state["baseline_core"] != "0.0.0":
                return fail("version_predecessor_state_mismatch")
        else:
            baseline_match, reason = binding_parts(baseline, require_clean=False)
            if reason is not None or baseline_match["core"] != state["baseline_core"]:
                return fail(reason or "version_predecessor_state_mismatch")
            if baseline["commit_oid"] not in _commit_reach(selected["to"], parents):
                return fail("version_predecessor_state_mismatch")
        if _bump_core(state["baseline_core"], state["target_bump"]) != state["target_core"]:
            return fail("version_predecessor_state_mismatch")

        version_predecessor = canonical["tag"]
        if inputs["action"] == "recut":
            if corrective_floor is not None:
                return fail("version_corrective_advance_required")
            if state["clean_accepted"]:
                return fail("recut_clean_target_accepted")
            if BUMP_RANK[bump] > BUMP_RANK[state["target_bump"]]:
                return fail("recut_target_bump_exceeded")

        carries_target_lineage = inputs["action"] == "recut" or (
            inputs["action"] == "advance" and not state["clean_accepted"]
        )
        reevaluation_ref = inputs.get("target_reevaluation")
        if carries_target_lineage:
            prior_target_trust = f"T{match['level']}"
            if reevaluation_ref is not None:
                reevaluation = doc.get("target_reevaluations", {}).get(reevaluation_ref)
                if (
                    not isinstance(reevaluation, dict)
                    or not reevaluation.get("authenticated")
                    or reevaluation.get("predecessor") != fixture_ref
                    or reevaluation.get("target_core") != state["target_core"]
                    or reevaluation.get("source_intervals")
                    != [*target_intervals, f"{selected['to']}..{to}"]
                    or reevaluation.get("effective_trust") != decision_inputs["effective_trust"]
                ):
                    return fail("version_target_trust_reevaluation_invalid")
                target_reevaluation_consumed = True
            elif LEVEL_RANK[decision_inputs["effective_trust"]] > LEVEL_RANK[prior_target_trust]:
                return fail("version_target_trust_reevaluation_required")

        if inputs["action"] == "advance":
            if corrective_floor is not None:
                decision_inputs = {
                    **decision_inputs,
                    "semantic_floor": max(
                        decision_inputs["semantic_floor"],
                        corrective_floor,
                        key=BUMP_RANK.__getitem__,
                    ),
                }
                decision = _decision_outcome(decision_inputs)
                bump = decision["bump"]
                if bump is None:
                    return fail("version_escalation_target_unresolved")
            advance_bump = max(
                (candidate for candidate in (bump, corrective_floor) if candidate is not None),
                key=BUMP_RANK.__getitem__,
            )
            target_core = _bump_core(state["target_core"], advance_bump)
            iterations = {}
            clean_accepted = False
        elif inputs["action"] == "recut":
            target_core = state["target_core"]
            clean_accepted = False
        else:
            target_core = state["target_core"]
            clean_accepted = state["clean_accepted"]
    else:
        return fail("version_authority_unknown")

    if inputs.get("target_reevaluation") is not None and not target_reevaluation_consumed:
        return fail("version_target_trust_reevaluation_invalid")

    requested_predecessor = inputs.get("requested_version_predecessor")
    if requested_predecessor is not None and requested_predecessor != version_predecessor:
        return fail("version_predecessor_override")

    channel = decision["channel"]
    advances_version_head = authority != "superseded" or not source_successor_exists

    if authority == "superseded" and source_successor_exists:
        if inputs.get("requested_iteration") is not None:
            return fail("version_iteration_override")
        return {
            "outcome": "verified",
            "version_predecessor": version_predecessor,
            "target_core": target_core,
            "iteration": None,
            "version": None,
            "advances_version_head": False,
            "reason": None,
        }

    if authority == "superseded" and BUMP_RANK[bump] > BUMP_RANK[state["target_bump"]]:
        if inputs.get("requested_iteration") is not None:
            return fail("version_iteration_override")
        return {
            "outcome": "verified",
            "version_predecessor": version_predecessor,
            "target_core": target_core,
            "iteration": None,
            "version": None,
            "advances_version_head": advances_version_head,
            "corrective_floor": max(
                (
                    candidate
                    for candidate in (bump, state.get("corrective_floor"))
                    if candidate is not None
                ),
                key=BUMP_RANK.__getitem__,
            ),
            "reason": None,
        }

    if authority == "superseded" and clean_accepted and channel == "prerelease":
        if inputs.get("requested_iteration") is not None:
            return fail("version_iteration_override")
        return {
            "outcome": "verified",
            "version_predecessor": version_predecessor,
            "target_core": target_core,
            "iteration": None,
            "version": None,
            "advances_version_head": advances_version_head,
            "reason": None,
        }

    prefix = f"{inputs['tag_prefix']}/" if inputs["tag_prefix"] else ""
    if channel == "clean":
        if clean_accepted:
            version = None
            iteration = None
        else:
            version = f"{prefix}v{target_core}"
            iteration = None
    else:
        level = decision_inputs["effective_trust"]
        iteration = iterations.get(level, 0) + 1
        version = f"{prefix}v{target_core}-t{LEVEL_RANK[level]}.{iteration}"

    requested_iteration = inputs.get("requested_iteration")
    if requested_iteration is not None and requested_iteration != iteration:
        return fail("version_iteration_override")
    if version is not None and version in refs:
        return fail("version_output_tag_exists")
    return {
        "outcome": "verified",
        "version_predecessor": version_predecessor,
        "target_core": target_core,
        "iteration": iteration,
        "version": version,
        "advances_version_head": advances_version_head,
        "reason": None,
    }


# §4.3 / ADR-031: only qualified approvals can contribute a review class. This
# deliberately evaluates canonical actor ids, not credential strings.
def _review_qualification(inputs: dict) -> dict:
    authorship = inputs["authorship"]["class"]
    author_actor = inputs["authorship"]["actor"]
    review = inputs["review"]
    merge = inputs["merge"]

    def result(review_class: str, reason: str | None) -> dict:
        return {
            "review": review_class,
            "level": invariant_level(authorship, review_class),
            "reason": reason,
        }

    if review["verdict"] != "approved":
        return result("none", "verdict_not_approved")
    if review["approval_state"] != "active" or not review["effective_at_merge"]:
        return result("none", "approval_not_active")
    if not review["signed_attestation"]:
        return result("none", "unsigned_attestation")
    if review["credential_actor"] != review["actor"]:
        return result("none", "credential_actor_mismatch")
    if merge["post_approval_change"]:
        return result("none", "post_approval_change")

    coverage = review["coverage"]
    if coverage == "final_revision":
        if review["approved_revision"] != review["final_revision"]:
            return result("none", "revision_mismatch")
    elif coverage == "final_diff":
        if merge["strategy"] not in {"squash", "rebase"} or merge["capture_mode"] != "pre_rewrite":
            return result("none", "unsupported_final_diff_flow")
        if review.get("approved_diff") != review.get("result_diff"):
            return result("none", "diff_mismatch")
    else:
        return result("none", "unknown_coverage")

    if review["class"] == "agent":
        if review["actor"] == author_actor or not review.get("separate_context"):
            return result("none", "agent_not_independent")
        return result("agent_independent", None)

    if review["class"] == "human":
        if authorship == "human" and review["actor"] == author_actor:
            return result("none", "same_canonical_actor")
        return result("human_distinct", None)

    return result("none", "unknown_reviewer_class")


# ---- Checks ----------------------------------------------------------------
def check_structure(docs: dict[str, dict]) -> None:
    ids: list[str] = []
    versions = []
    for doc in docs.values():
        versions.append(doc.get("spec_version"))
        for vec in doc.get("vectors", []):
            ids.append(vec.get("id"))
            spec = vec.get("spec")
            check(
                f"vector-spec-ref-{vec.get('id')}",
                isinstance(spec, str) and spec.strip() != "",
                "empty spec reference",
            )
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    check("vector-ids-unique", not duplicates, f"duplicate ids: {duplicates}")
    check("vector-ids-nonempty", all(isinstance(i, str) and i for i in ids))
    check(
        "spec-version-consistent",
        len(set(versions)) == 1 and bool(versions[0]),
        f"spec_version differs across files: {versions}",
    )


def check_spec_version_matches_spec(version: str) -> None:
    if not SPEC.exists():
        print(f"PASS  spec-version-matches-spec  (skipped: {SPEC.name} not in this checkout)")
        return
    m = re.search(r"\*\*Draft v(?P<v>[0-9]+\.[0-9]+)\*\*", SPEC.read_text(encoding="utf-8"))
    check(
        "spec-version-matches-spec",
        m is not None and m["v"] == version,
        f"vectors pin {version} but spec header is {m['v'] if m else 'unknown'}",
    )


def check_predicate_schemas() -> None:
    for predicate_type, schema_name in PREDICATE_SCHEMAS.items():
        path = SCHEMAS / schema_name
        try:
            schema = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            check(f"schema-load-{schema_name}", False, str(exc))
            continue
        check(f"schema-load-{schema_name}", True)
        try:
            jsonschema.Draft202012Validator.check_schema(schema)
            check(f"schema-draft202012-{schema_name}", True)
        except jsonschema.SchemaError as exc:
            check(f"schema-draft202012-{schema_name}", False, str(exc))
        check(
            f"schema-id-{schema_name}",
            schema.get("$id") == f"https://semver-trust.dev/schemas/{schema_name}",
            f"unexpected $id {schema.get('$id')!r}",
        )
        predicate_const = schema.get("properties", {}).get("predicateType", {}).get("const")
        check(
            f"schema-predicate-type-{schema_name}",
            predicate_const == predicate_type,
            f"expected {predicate_type}, got {predicate_const!r}",
        )


def check_levels(vectors: list[dict]) -> None:
    matrix = [v for v in vectors if v.get("kind") == "matrix"]
    classify = [v for v in vectors if v.get("kind") == "classify"]
    check("levels-matrix-nonempty", bool(matrix))
    check("levels-classify-nonempty", bool(classify))

    for vec in matrix:
        author, review = vec["inputs"]["authorship"], vec["inputs"]["review"]
        want = invariant_level(author, review)
        check(
            f"levels-invariant-{vec['id']}",
            vec["expected"]["level"] == want,
            f"{author}/{review}: invariant says {want}, vector says {vec['expected']['level']}",
        )

    for vec in classify:
        author, review = vec["expected"]["authorship"], vec["expected"]["review"]
        want = invariant_level(author, review)
        check(
            f"levels-invariant-{vec['id']}",
            vec["expected"]["level"] == want,
            f"{author}/{review}: invariant says {want}, vector says {vec['expected']['level']}",
        )

    present = {(v["inputs"]["authorship"], v["inputs"]["review"]) for v in matrix}
    missing = [f"{a}/{r}" for a in AUTHORSHIP for r in REVIEW if (a, r) not in present]
    check("levels-matrix-exhaustive", not missing, f"missing combos: {missing}")
    check(
        "levels-matrix-self-review",
        ("human", "human_same_identity") in present,
        "missing the human/human_same_identity self-review vector",
    )


def check_precedence(vectors: list[dict]) -> None:
    prec = [v for v in vectors if v.get("kind") == "precedence"]
    check("precedence-group-nonempty", bool(prec))
    for vec in prec:
        ordered = vec.get("ordered", [])
        try:
            keys = [precedence_key(s) for s in ordered]
        except ValueError as exc:
            check(f"precedence-{vec['id']}", False, str(exc))
            continue
        ascending = len(ordered) >= 2 and all(a < b for a, b in pairwise(keys))
        check(f"precedence-{vec['id']}", ascending, f"not strictly ascending: {ordered}")


def _check_trust_version(vec: dict, tag: str, exp: dict) -> None:
    m = _TRUST_TAG.match(tag)
    ok = m is not None
    if m is not None:
        level = int(m["level"]) if m["level"] is not None else None
        iteration = int(m["iter"]) if m["iter"] is not None else None
        ok = (
            m["path"] == exp["component_path"]
            and m["core"] == exp["core"]
            and level == exp["level"]
            and iteration == exp["iteration"]
        )
    check(f"grammar-{vec['id']}", ok, f"trust-version parse mismatch for {tag}")


def _check_plain_version(vec: dict, tag: str, exp: dict) -> None:
    sm = _SEMVER_TAG.match(tag)
    pre = sm["pre"] if sm else None
    ok = (
        _TRUST_TAG.match(tag) is None
        and sm is not None
        and pre is not None
        and re.match(r"t[0-9]", pre) is None
        and sm["path"] == exp["component_path"]
        and sm["core"] == exp["core"]
        and pre == exp["prerelease"]
        and exp["level"] is None
        and exp["iteration"] is None
    )
    check(f"grammar-{vec['id']}", ok, f"plain-version parse mismatch for {tag}")


def _check_invalid(vec: dict, tag: str, exp: dict) -> None:
    reason = exp.get("reason")
    ok = _TRUST_TAG.match(tag) is None and isinstance(reason, str) and reason != ""
    check(f"grammar-{vec['id']}", ok, f"strict grammar accepted a tag marked invalid: {tag}")


def check_grammar(vectors: list[dict]) -> None:
    gram = [v for v in vectors if v.get("kind") == "grammar"]
    check("grammar-group-nonempty", bool(gram))
    handlers = {
        "trust_version": _check_trust_version,
        "plain_version": _check_plain_version,
        "invalid": _check_invalid,
    }
    for vec in gram:
        exp = vec["expected"]
        handler = handlers.get(exp["outcome"])
        if handler is None:
            check(f"grammar-{vec['id']}", False, f"unknown outcome {exp['outcome']!r}")
            continue
        handler(vec, vec["tag"], exp)


def check_aggregation(vectors: list[dict]) -> None:
    partition = [v for v in vectors if v.get("kind") == "scope_partition"]
    floor = [v for v in vectors if v.get("kind") == "scope_floor"]
    meta = [v for v in vectors if v.get("kind") == "meta_path"]
    check("aggregation-partition-nonempty", bool(partition))
    check("aggregation-floor-nonempty", bool(floor))
    check("aggregation-meta-path-nonempty", bool(meta))

    for vec in partition:
        got = _partition(vec["inputs"]["scopes"], vec["inputs"]["commits"])
        check(
            f"aggregation-{vec['id']}",
            got == vec["expected"]["scopes"],
            f"partition mismatch: computed {got}, vector says {vec['expected']['scopes']}",
        )

    for vec in floor:
        got = _floors(vec["inputs"]["scopes"], vec["inputs"]["commits"])
        check(
            f"aggregation-{vec['id']}",
            got == vec["expected"]["own_trust"],
            f"floor mismatch: computed {got}, vector says {vec['expected']['own_trust']}",
        )

    for vec in meta:
        meta_cfg = vec["inputs"]["meta"]
        required = LEVEL_RANK[meta_cfg["required_level"]]
        compiled = [_glob_to_re(g) for g in meta_cfg["paths"]]
        violations = [
            c["id"]
            for c in vec["inputs"]["commits"]
            if LEVEL_RANK[c["level"]] < required
            and any(rx.match(p) for p in c["paths"] for rx in compiled)
        ]
        got = {
            "outcome": "verification_failed" if violations else "verified",
            "violations": violations,
        }
        check(
            f"aggregation-{vec['id']}",
            got == vec["expected"],
            f"meta-path mismatch: computed {got}, vector says {vec['expected']}",
        )


def check_propagation(vectors: list[dict]) -> None:
    prop = [v for v in vectors if v.get("kind") == "propagation"]
    check("propagation-group-nonempty", bool(prop))
    has_scc = False
    for vec in prop:
        own, edges = vec["inputs"]["nodes"], vec["inputs"]["edges"]
        scc_of = _sccs(list(own), _edges_to_adj(edges))
        has_scc = has_scc or len(set(scc_of.values())) < len(own)
        got = _effective(own, edges)
        check(
            f"propagation-{vec['id']}",
            got == vec["expected"]["effective"],
            f"effective mismatch: computed {got}, vector says {vec['expected']['effective']}",
        )
        # floor_source is asserted where present: the named component must be the
        # node itself or a reachable dependency, and its own trust must equal the
        # node's effective trust (it is the component whose own level set the floor).
        for node, source in vec["expected"].get("floor_source", {}).items():
            ok = (
                source in _reachable(node, edges)
                and own[source] == got[node]
                and (source != node or own[node] == got[node])
            )
            check(
                f"propagation-floor-source-{vec['id']}-{node}",
                ok,
                f"{source} cannot have floored {node} "
                f"(own {own.get(source)}, effective {got[node]})",
            )
    check("propagation-covers-scc-cycle", has_scc, "no vector exercises an SCC cycle")


def check_decision(vectors: list[dict]) -> None:
    dec = [v for v in vectors if v.get("kind") == "decision"]
    check("decision-group-nonempty", bool(dec))
    for vec in dec:
        try:
            got = _decide(vec["inputs"])
        except (KeyError, ValueError) as exc:
            check(f"decision-{vec['id']}", False, str(exc))
            continue
        check(
            f"decision-{vec['id']}",
            got == vec["expected"],
            f"decision mismatch: computed {got}, vector says {vec['expected']}",
        )
    demote_cells = {
        (v["inputs"]["effective_trust"], v["inputs"]["blast"])
        for v in dec
        if v["inputs"]["strategy"] == "demote"
    }
    missing = [f"{t}/{b}" for t, b in _TABLE if (t, b) not in demote_cells]
    check("decision-table-exhaustive", not missing, f"uncovered §6.4 cells: {missing}")
    thresholds = {v["inputs"]["threshold"] for v in dec}
    check(
        "decision-threshold-coverage",
        {"T1", "T2", "T3"}.issubset(thresholds),
        f"threshold vectors missing: {sorted({'T1', 'T2', 'T3'} - thresholds)}",
    )


def check_ranges(vectors: list[dict]) -> None:
    ranges = [vector for vector in vectors if vector.get("kind") == "release_range"]
    check("range-group-nonempty", bool(ranges))
    modes = set()
    for vector in ranges:
        modes.add(vector["inputs"]["mode"])
        got = _release_interval(vector["inputs"])
        check(
            f"range-{vector['id']}",
            got == vector["expected"],
            f"release interval mismatch: computed {got}, vector says {vector['expected']}",
        )
    missing = {"inception", "adoption", "recurring"} - modes
    check("range-modes-exhaustive", not missing, f"missing interval modes: {sorted(missing)}")


def check_git_interval_commands() -> None:
    """Prove the §5.2 set definitions match the specified Git commands,
    including a merge boundary with two parents and a root boundary, and prove
    §7.5's distinction between a tag ref's raw and peeled object IDs."""

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"

        def git(*args: str) -> str:
            result = subprocess.run(
                ["git", "-C", str(repo), *args],
                capture_output=True,
                check=True,
                text=True,
            )
            return result.stdout.strip()

        def commit(message: str) -> str:
            git("commit", "--allow-empty", "--no-gpg-sign", "-m", message)
            return git("rev-parse", "HEAD")

        try:
            subprocess.run(
                ["git", "init", "-q", "-b", "main", str(repo)],
                capture_output=True,
                check=True,
            )
            git("config", "user.name", "Conformance Fixture")
            git("config", "user.email", "fixture@semver-trust.test")
            git("config", "commit.gpgSign", "false")

            root = commit("root")
            left = commit("left parent")
            git("switch", "-q", "-c", "side", root)
            side = commit("side parent")
            git("switch", "-q", "main")
            git("merge", "--no-ff", "--no-gpg-sign", "-m", "boundary", "side")
            boundary = git("rev-parse", "HEAD")
            after = commit("after boundary")

            def revs(*args: str) -> set[str]:
                output = git("rev-list", *args)
                return set(output.split()) if output else set()

            inception = revs(after)
            adoption = revs(after, "--not", f"{boundary}^@")
            recurring = revs(f"{boundary}..{after}")
            root_adoption = revs(after, "--not", f"{root}^@")
            expected_all = {root, left, side, boundary, after}

            check(
                "range-git-inception-command",
                inception == expected_all,
                f"git rev-list TO produced {sorted(inception)}",
            )
            check(
                "range-git-adoption-command",
                adoption == {boundary, after},
                f"git rev-list TO --not B^@ produced {sorted(adoption)}",
            )
            check(
                "range-git-recurring-command",
                recurring == {after},
                f"git rev-list P..TO produced {sorted(recurring)}",
            )
            check(
                "range-git-root-boundary-command",
                root_adoption == expected_all,
                f"root B^@ handling produced {sorted(root_adoption)}",
            )
            before_boundary = subprocess.run(
                ["git", "-C", str(repo), "merge-base", "--is-ancestor", root, boundary],
                capture_output=True,
                check=False,
            ).returncode
            after_boundary = subprocess.run(
                ["git", "-C", str(repo), "merge-base", "--is-ancestor", after, boundary],
                capture_output=True,
                check=False,
            ).returncode
            check(
                "version-git-predecessor-before-boundary",
                before_boundary == 0,
                "git merge-base rejected an ancestor version predecessor",
            )
            check(
                "version-git-predecessor-after-boundary",
                after_boundary != 0,
                "git merge-base accepted a descendant version predecessor",
            )
            git(
                "tag",
                "--no-sign",
                "-a",
                "version-predecessor",
                "-m",
                "version predecessor",
                root,
            )
            raw_tag_oid = git("rev-parse", "refs/tags/version-predecessor")
            peeled_commit_oid = git("rev-parse", "refs/tags/version-predecessor^{commit}")
            check(
                "version-git-annotated-tag-raw-and-peeled-differ",
                raw_tag_oid != peeled_commit_oid,
                "annotated tag raw and peeled object IDs unexpectedly match",
            )
            check(
                "version-git-annotated-tag-peeled-target",
                peeled_commit_oid == root,
                "annotated tag did not peel to its exact bound commit",
            )
        except subprocess.CalledProcessError as exc:
            check(
                "range-git-command-fixture",
                False,
                exc.stderr.strip() if isinstance(exc.stderr, str) else str(exc),
            )


def check_policy_transitions(doc: dict) -> None:
    vectors = [
        vector for vector in doc.get("vectors", []) if vector.get("kind") == "policy_transition"
    ]
    check("policy-transition-group-nonempty", bool(vectors))
    authorities = set()
    for vector in vectors:
        authorities.add(vector["inputs"]["authority"])
        got = _policy_transition(doc, vector["inputs"])
        check(
            f"policy-transition-{vector['id']}",
            got == vector["expected"],
            f"policy transition mismatch: computed {got}, vector says {vector['expected']}",
        )
    missing = {"bootstrap", "predecessor"} - authorities
    check(
        "policy-transition-authorities-exhaustive",
        not missing,
        f"missing authorities: {sorted(missing)}",
    )


def check_review_qualification(vectors: list[dict]) -> None:
    group = [vector for vector in vectors if vector.get("kind") == "review_qualification"]
    check("review-qualification-group-nonempty", bool(group))
    reasons = set()
    positives = set()
    for vector in group:
        got = _review_qualification(vector["inputs"])
        expected = vector["expected"]
        if expected["reason"] is None:
            positives.add(vector["id"])
        else:
            reasons.add(expected["reason"])
        check(
            f"review-qualification-{vector['id']}",
            got == expected,
            f"review qualification mismatch: computed {got}, vector says {expected}",
        )
    required_reasons = {
        "verdict_not_approved",
        "approval_not_active",
        "revision_mismatch",
        "post_approval_change",
        "same_canonical_actor",
        "agent_not_independent",
    }
    missing_reasons = required_reasons - reasons
    check(
        "review-qualification-negative-coverage",
        not missing_reasons,
        f"missing negative reasons: {sorted(missing_reasons)}",
    )
    required_positive_fragments = ("key-rotation", "distinct-human", "squash", "rebase")
    missing_positive = [
        fragment
        for fragment in required_positive_fragments
        if not any(fragment in vector_id for vector_id in positives)
    ]
    check(
        "review-qualification-positive-coverage",
        not missing_positive,
        f"missing positive cases: {missing_positive}",
    )


def check_version_ancestry(doc: dict) -> None:
    vectors = [
        vector for vector in doc.get("vectors", []) if vector.get("kind") == "version_ancestry"
    ]
    check("version-ancestry-group-nonempty", bool(vectors))
    authorities = set()
    actions = set()
    for vector in vectors:
        authorities.add(vector["inputs"]["authority"])
        actions.add(vector["inputs"]["action"])
        got = _version_ancestry(doc, vector["inputs"])
        check(
            f"version-ancestry-{vector['id']}",
            got == vector["expected"],
            f"version ancestry mismatch: computed {got}, vector says {vector['expected']}",
        )
    missing_authorities = {"bootstrap", "predecessor", "superseded"} - authorities
    check(
        "version-ancestry-authorities-exhaustive",
        not missing_authorities,
        f"missing authorities: {sorted(missing_authorities)}",
    )
    missing_actions = {"advance", "recut", "supersede"} - actions
    check(
        "version-ancestry-actions-exhaustive",
        not missing_actions,
        f"missing actions: {sorted(missing_actions)}",
    )


# ---- Attestation envelope checks (fixture plan §6) --------------------------
#
# Independent re-implementation of the envelope contract: the DSSE shape, the
# frozen predicate types' required skeleton (a subset of the schemas,
# re-derived here so the vendored envelopes are gated by a second
# implementation), SSHSIG verification via ssh-keygen, byte-exact
# regeneration, and coherence between the release payload and the fixture
# repository it claims to describe.

PAYLOAD_TYPE = "application/vnd.in-toto+json"
STATEMENT_TYPE = "https://in-toto.io/Statement/v1"
ATTESTATION_NAMESPACE = "attestation@semver-trust.dev"
PREDICATE_REQUIRED = {
    "https://semver-trust.dev/release/v0.1": (
        "component",
        "range",
        "trust",
        "commits",
        "evidence",
        "decision",
        "timestamp",
    ),
    "https://semver-trust.dev/review/v0.1": (
        "reviewers",
        "pull_request",
        "merge_strategy",
        "timestamp",
    ),
    "https://semver-trust.dev/release/v0.2": (
        "profile",
        "repository",
        "component",
        "interval",
        "policy_state",
        "version_state",
        "trust",
        "provenance",
        "evidence",
        "decision",
        "timestamp",
    ),
    "https://semver-trust.dev/review/v0.2": (
        "profile",
        "repository",
        "review_target",
        "reviewers",
        "merge",
        "timestamp",
    ),
}


def _pae(payload_type: str, payload: bytes) -> bytes:
    t = payload_type.encode()
    return b"DSSEv1 %d %s %d %s" % (len(t), t, len(payload), payload)


def _decode_envelope(vec: dict) -> tuple[dict, bytes] | None:
    path = ATTESTATIONS_DIR / vec["inputs"]["envelope"]
    if not path.exists():
        check(f"attest-envelope-exists-{vec['id']}", False, str(path))
        return None
    env = json.loads(path.read_text(encoding="utf-8"))
    ok = (
        env.get("payloadType") == PAYLOAD_TYPE
        and isinstance(env.get("signatures"), list)
        and len(env["signatures"]) == 1
        and env["signatures"][0].get("keyid", "").startswith("SHA256:")
        and env["signatures"][0].get("sig")
    )
    check(f"attest-envelope-shape-{vec['id']}", bool(ok), "malformed DSSE envelope")
    try:
        payload = base64.b64decode(env["payload"], validate=True)
    except (KeyError, binascii.Error) as exc:
        check(f"attest-envelope-payload-{vec['id']}", False, str(exc))
        return None
    return env, payload


def _statement_shape_ok(payload: bytes) -> bool:
    try:
        stmt = json.loads(payload)
    except json.JSONDecodeError:
        return False
    if stmt.get("_type") != STATEMENT_TYPE or not stmt.get("subject"):
        return False
    required = PREDICATE_REQUIRED.get(stmt.get("predicateType"))
    if required is None:
        return False
    return all(field in stmt.get("predicate", {}) for field in required)


def _schema_validates(payload: bytes) -> bool:
    """Full Draft 2020-12 validation against the merged schemas — the actual
    freeze gate. The skeleton check above stays as a second, independent
    opinion, but only the pinned validator speaks for the schemas."""
    try:
        stmt = json.loads(payload)
    except json.JSONDecodeError:
        return False
    schema_file = PREDICATE_SCHEMAS.get(stmt.get("predicateType"))
    if schema_file is None:
        return False
    schema = json.loads((ROOT / "schemas" / schema_file).read_text(encoding="utf-8"))
    # FORMAT_CHECKER enforces the schemas' format: "date-time" (RFC 3339 via
    # the pinned rfc3339-validator). jsonschema silently skips formats whose
    # checker package is absent, so check_format_gate proves the checker is
    # armed on every run.
    validator = jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER
    )
    return not list(validator.iter_errors(stmt))


def _payload_schema_validates(path: Path) -> bool:
    try:
        payload = path.read_bytes()
    except FileNotFoundError:
        return False
    return _schema_validates(payload)


def check_predicate_v02_instances(vectors: list[dict]) -> None:
    check("predicate-v02-group-nonempty", bool(vectors))
    for vec in vectors:
        payload = CONFORMANCE / vec["inputs"]["payload"]
        got = _payload_schema_validates(payload)
        check(
            f"predicate-v02-{vec['id']}",
            got == vec["expected"]["schema_valid"],
            f"{payload.relative_to(ROOT)} schema_valid={got}",
        )


def check_format_gate() -> None:
    """Standing mutation assertion: a payload whose timestamp is not RFC 3339
    must fail schema validation. Guards both against regression of the format
    gate and against jsonschema's silent skip-when-unarmed behavior."""
    payload = json.loads(
        (ATTESTATIONS_DIR / "payloads" / "release-valid.json").read_text(encoding="utf-8")
    )
    payload["predicate"]["timestamp"] = "not-a-date"
    check(
        "attest-format-checker-armed",
        not _schema_validates(json.dumps(payload).encode()),
        "a non-RFC-3339 timestamp validated: the date-time format checker is not armed",
    )


def _sshsig_verify(env: dict, payload: bytes, registry: Path, signer: str) -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        sig = Path(tmp) / "envelope.sig"
        sig.write_bytes(base64.b64decode(env["signatures"][0]["sig"]))
        result = subprocess.run(
            [
                "ssh-keygen",
                "-Y",
                "verify",
                "-f",
                str(registry),
                "-I",
                signer,
                "-n",
                ATTESTATION_NAMESPACE,
                "-s",
                str(sig),
            ],
            input=_pae(env["payloadType"], payload),
            capture_output=True,
            check=False,
        )
    return result.returncode == 0


def _permissive_registry(workdir: Path) -> Path:
    """A registry enrolling EVERY fixture key for the attestation namespace
    under a wildcard principal: verification against it answers 'is this
    signature cryptographically valid by any fixture key at all?',
    independently of enrollment — the discriminator between a forged
    signature and a valid-but-unenrolled one."""
    lines = []
    for pub in sorted((CONFORMANCE / "crypto" / "keys").glob("*.pub")):
        keytype, b64 = pub.read_text().split()[:2]
        lines.append(f'* namespaces="{ATTESTATION_NAMESPACE}" {keytype} {b64}\n')
    registry = workdir / "permissive_signers"
    registry.write_text("".join(lines), encoding="utf-8")
    return registry


def check_attestations(doc: dict) -> None:
    vectors = [v for v in doc.get("vectors", []) if v.get("kind") == "dsse_attestation"]
    check("attest-group-nonempty", bool(vectors))

    enrolled_registry = ATTESTATIONS_DIR / "allowed_signers"
    with tempfile.TemporaryDirectory() as tmp:
        permissive = _permissive_registry(Path(tmp))

        for vec in vectors:
            decoded = _decode_envelope(vec)
            if decoded is None:
                continue
            env, payload = decoded
            expected = vec["expected"]

            shape_ok = _statement_shape_ok(payload)
            schema_ok = _schema_validates(payload)
            signer = expected.get("signer", "ci-bot@semver-trust.test")
            # enrolled: valid signature by a key enrolled in the injected
            # registry. crypto_valid: valid signature by ANY fixture key —
            # true for a well-signed envelope from an unenrolled key, false
            # for a signature that covers different bytes.
            enrolled = _sshsig_verify(env, payload, enrolled_registry, signer)
            crypto_valid = enrolled or _sshsig_verify(env, payload, permissive, "anyone")

            if expected["outcome"] == "verified":
                stmt = json.loads(payload)
                ok = (
                    shape_ok
                    and schema_ok
                    and enrolled
                    and stmt.get("predicateType") == expected["predicate_type"]
                )
                check(
                    f"attest-{vec['id']}",
                    ok,
                    f"shape={shape_ok} schema={schema_ok} enrolled={enrolled}",
                )
                continue
            want_reason = expected["reason"]
            got = {
                # A genuine signature over a payload the schemas reject.
                "schema_invalid": not schema_ok and not shape_ok and enrolled,
                # A signature that covers no fixture key's bytes at all —
                # forgery/tamper, not an enrollment question.
                "signature_invalid": schema_ok and not crypto_valid,
                # Cryptographically valid under some fixture key, absent
                # from the injected registry: distinct from tamper.
                "unknown_signer": schema_ok and crypto_valid and not enrolled,
            }.get(want_reason, False)
            check(
                f"attest-{vec['id']}",
                got,
                f"expected {want_reason}, observed shape={shape_ok} schema={schema_ok} "
                f"enrolled={enrolled} crypto_valid={crypto_valid}",
            )


def check_attestation_regeneration() -> None:
    """Frozen-byte tripwire: regeneration must reproduce the vendored bytes."""
    generator = ATTESTATIONS_DIR / "build-attestation-envelopes.py"
    with tempfile.TemporaryDirectory() as tmp:
        result = subprocess.run(
            ["python3", str(generator), tmp],
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            check("attest-regeneration", False, result.stderr.decode(errors="replace"))
            return
        drifted = [
            p.name
            for p in sorted(Path(tmp).iterdir())
            if p.read_bytes() != (ATTESTATIONS_DIR / "envelopes" / p.name).read_bytes()
        ]
    check(
        "attest-regeneration",
        not drifted,
        f"regenerated envelopes differ from vendored bytes: {drifted}",
    )


def check_release_payload_coherence() -> None:
    """The release-valid payload must be reproducible from the fixture tree:
    its tag, commits, and pinned policy digest all exist there (§8.1)."""
    payload = json.loads(
        (ATTESTATIONS_DIR / "payloads" / "release-valid.json").read_text(encoding="utf-8")
    )
    builder = CONFORMANCE / "crypto" / "build-fixture-repos.sh"
    with tempfile.TemporaryDirectory() as tmp:
        result = subprocess.run(["bash", str(builder), tmp], capture_output=True, check=False)
        if result.returncode != 0:
            check("attest-release-coherence", False, result.stderr.decode(errors="replace"))
            return
        repo = Path(tmp) / "release"

        def rev(ref: str) -> str:
            out = subprocess.run(
                ["git", "-C", str(repo), "rev-parse", ref], capture_output=True, check=False
            )
            return out.stdout.decode().strip() if out.returncode == 0 else ""

        subject = payload["subject"][0]
        pred = payload["predicate"]

        # The provenance vector must BE the release range: the exact ordered
        # git rev-list FROM..TO, oldest first — an omitted commit could hide
        # a floor-setting T0 change behind a higher claimed own trust.
        rev_list = subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "rev-list",
                "--reverse",
                f"{pred['range']['from']}..{pred['range']['to']}",
            ],
            capture_output=True,
            check=False,
        )
        range_shas = rev_list.stdout.decode().split()

        # Recompute the per-commit levels and the own floor from the recorded
        # classes via the same independent §3.2 invariant the level vectors
        # use. Payload review classes are the counted §3.2 classes.
        review_class = {"human": "human_distinct", "agent": "agent_independent", "none": "none"}
        levels = [
            invariant_level(c["authorship"]["class"], review_class[c["review"]["class"]])
            for c in pred["commits"]
        ]
        floor = min(levels, key=lambda level: int(level[1]))

        checks = {
            "subject tag": rev(subject["name"] + "^{commit}") == subject["digest"]["gitCommit"],
            "range from": rev(pred["range"]["from"] + "^{commit}") != "",
            "range to": rev(pred["range"]["to"] + "^{commit}") == pred["range"]["to"],
            "provenance vector equals rev-list": [c["sha"] for c in pred["commits"]] == range_shas,
            "recorded levels match §3.2": [c["level"] for c in pred["commits"]] == levels,
            "own trust is the floor": pred["trust"]["own"] == floor,
        }
        policy_path = pred["decision"]["policy"]["path"]
        policy_file = repo / policy_path
        digest = "sha256:" + hashlib.sha256(policy_file.read_bytes()).hexdigest()
        checks["policy digest"] = (
            policy_file.exists() and digest == pred["decision"]["policy"]["digest"]
        )
        bad = [name for name, ok in checks.items() if not ok]
    check(
        "attest-release-coherence",
        not bad,
        f"release payload does not match the fixture tree: {bad}",
    )


def main() -> int:
    docs: dict[str, dict] = {}
    for path in VECTOR_FILES:
        if not path.exists():
            check(f"file-exists-{path.name}", False, str(path))
            continue
        try:
            docs[path.name] = json.loads(path.read_text(encoding="utf-8"))
            check(f"json-wellformed-{path.name}", True)
        except json.JSONDecodeError as exc:
            check(f"json-wellformed-{path.name}", False, str(exc))

    if len(docs) == len(VECTOR_FILES):
        check_structure(docs)
        check_spec_version_matches_spec(docs[LEVELS.name]["spec_version"])
        check_predicate_schemas()
        check_levels(docs[LEVELS.name]["vectors"])
        check_precedence(docs[PRECEDENCE.name]["vectors"])
        check_grammar(docs[PRECEDENCE.name]["vectors"])
        check_aggregation(docs[AGGREGATION.name]["vectors"])
        check_propagation(docs[PROPAGATION.name]["vectors"])
        check_decision(docs[DECISION.name]["vectors"])
        check_ranges(docs[RANGE.name]["vectors"])
        check_git_interval_commands()
        check_version_ancestry(docs[VERSION_ANCESTRY.name])
        check_policy_transitions(docs[POLICY_TRANSITION.name])
        check_review_qualification(docs[REVIEW_QUALIFICATION.name]["vectors"])
        check_predicate_v02_instances(docs[PREDICATE_V02.name]["vectors"])
        check_attestations(docs[ATTESTATION.name])
        check_format_gate()
        check_attestation_regeneration()
        check_release_payload_coherence()

    print(
        f"\n{'OK' if not failures else 'CONFORMANCE VECTORS INVALID'}: "
        f"{len(failures)} failure(s)" + (f" -> {failures}" if failures else "")
    )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
