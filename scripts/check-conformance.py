#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""check-conformance.py — independent validation of the SemVer-Trust conformance vectors.

Validates ``conformance/levels.json``, ``conformance/precedence.json``,
``conformance/aggregation.json``, ``conformance/propagation.json``, and
``conformance/decision.json`` against a second, independent implementation of the
spec rules they encode (``spec/semver-trust.md`` §3.2-§3.3, §4.1-§4.2, §5.1-§5.4,
§6.1-§6.4, §7.1-§7.2, Appendix A). This is deliberately NOT the reference Go
implementation, and it shares no code with ``scripts/check-drift.py`` — the SemVer
comparator, the level invariant, the scope/floor/propagation arithmetic, and the
decision table are re-implemented here from first principles. Agreement between two
independent implementations is the point.

    python3 scripts/check-conformance.py

Exit code 0 = all vectors valid. Requires Python 3.11+, stdlib only.
"""

import json
import re
import sys
from itertools import pairwise
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFORMANCE = ROOT / "conformance"
LEVELS = CONFORMANCE / "levels.json"
PRECEDENCE = CONFORMANCE / "precedence.json"
AGGREGATION = CONFORMANCE / "aggregation.json"
PROPAGATION = CONFORMANCE / "propagation.json"
DECISION = CONFORMANCE / "decision.json"
SIGNATURE = CONFORMANCE / "crypto" / "signature-vectors.json"
VECTOR_FILES = (LEVELS, PRECEDENCE, AGGREGATION, PROPAGATION, DECISION, SIGNATURE)
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


# Per-path contributed level, after §4.4: a verified derivation re-levels exactly
# its declared output paths to the inputs' floor; a failed proof is void.
def _path_level(commit: dict, path: str) -> str:
    deriv = commit.get("derivation")
    if deriv and deriv["verified"] and any(_glob_to_re(g).match(path) for g in deriv["outputs"]):
        return deriv["inherited_level"]
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


# §5.2: own_trust(scope) = min over commits touching the scope of level(c),
# levels taken per path after derivation re-leveling (§4.4).
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


# §6.4 default decision table. Cell values: the clean channel is available
# unconditionally, conditioned on a differ proof for PATCH claims, conditioned
# on a differ proof for any claim (the T1/low cell), or unavailable.
_TABLE = {
    ("T3", "low"): "clean",
    ("T3", "moderate"): "clean",
    ("T3", "high"): "differ_patch",
    ("T2", "low"): "clean",
    ("T2", "moderate"): "differ_patch",
    ("T2", "high"): "prerelease",
    ("T1", "low"): "differ_any",
    ("T1", "moderate"): "prerelease",
    ("T1", "high"): "prerelease",
    ("T0", "low"): "prerelease",
    ("T0", "moderate"): "prerelease",
    ("T0", "high"): "prerelease",
}


def _decide(inputs: dict) -> dict:
    cell = _TABLE[(inputs["effective_trust"], inputs["blast"])]
    bump = max(inputs["claimed_bump"], inputs["semantic_floor"], key=BUMP_RANK.__getitem__)
    differ_needed = cell == "differ_any" or (cell == "differ_patch" and bump == "patch")
    demoted = cell == "prerelease" or (differ_needed and not inputs["differ_available"])

    m = _TRUST_TAG.match(inputs["current_version"])
    if m is None or m["level"] is not None:
        raise ValueError(f"current_version must be a clean §7.1 tag: {inputs['current_version']}")
    major, minor, patch = (int(x) for x in m["core"].split("."))
    if bump == "major":
        core = f"{major + 1}.0.0"
    elif bump == "minor":
        core = f"{major}.{minor + 1}.0"
    else:
        core = f"{major}.{minor}.{patch + 1}"
    prefix = f"{m['path']}/" if m["path"] else ""

    if inputs["strategy"] == "inflate":
        # §6.3: the escalation target (MINOR vs MAJOR) is a policy choice the
        # spec does not pin, so escalated outcomes assert no exact version.
        if demoted:
            return {"channel": "clean", "escalate": True, "bump": None, "version": None}
        return {"channel": "clean", "escalate": False, "bump": bump, "version": f"{prefix}v{core}"}
    if demoted:
        suffix = f"-t{LEVEL_RANK[inputs['effective_trust']]}.{inputs['iteration']}"
        return {"channel": "prerelease", "bump": bump, "version": f"{prefix}v{core}{suffix}"}
    return {"channel": "clean", "bump": bump, "version": f"{prefix}v{core}"}


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
        check_levels(docs[LEVELS.name]["vectors"])
        check_precedence(docs[PRECEDENCE.name]["vectors"])
        check_grammar(docs[PRECEDENCE.name]["vectors"])
        check_aggregation(docs[AGGREGATION.name]["vectors"])
        check_propagation(docs[PROPAGATION.name]["vectors"])
        check_decision(docs[DECISION.name]["vectors"])

    print(
        f"\n{'OK' if not failures else 'CONFORMANCE VECTORS INVALID'}: "
        f"{len(failures)} failure(s)" + (f" -> {failures}" if failures else "")
    )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
