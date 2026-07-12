#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""check-drift.py — mechanical consistency checks for semver-trust/spec.

Every check here encodes a drift class caught or anticipated during design
review (see docs/design-record.md section 5). Run from anywhere:

    python3 scripts/check-drift.py

Exit code 0 = all checks pass. Requires Python 3.11+ (tomllib), stdlib only.
"""

import sys

if sys.version_info < (3, 11):  # noqa: UP036 (guards bare-python invocation below the floor)
    sys.exit(
        f"check-drift.py requires Python 3.11+ (tomllib); found "
        f"{sys.version_info[0]}.{sys.version_info[1]} — run inside `devbox shell`."
    )

import itertools
import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "spec" / "semver-trust.md"  # adjust if the spec moves
DESIGN_RECORD = ROOT / "docs" / "design-record.md"
ADR_DIR = ROOT / "docs" / "adr"
README = ROOT / "README.md"
CONTRIBUTING = ROOT / "CONTRIBUTING.md"
AGENT_CONTRACT = ROOT / "AGENTS.md"
DOMAIN = "https://semver-trust.dev"
APACHE_DIRS = {"schemas", "conformance", "scripts"}
# Directories that are not repository content: virtualenvs, vendored deps,
# and anything hidden (.git, .venv, .devbox, .direnv, ...) except .github.
SKIP_DIRS = {"node_modules", "vendor", "venv", ".venv"}

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {name}{('  — ' + detail) if (detail and not ok) else ''}")
    if not ok:
        failures.append(name)


def md_files() -> list[Path]:
    def skipped(p: Path) -> bool:
        return any(
            part in SKIP_DIRS or (part.startswith(".") and part != ".github")
            for part in p.relative_to(ROOT).parts[:-1]
        )

    return [p for p in ROOT.rglob("*.md") if not skipped(p)]


def slugify(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


# ---- 1. SPDX headers -------------------------------------------------------
def check_spdx() -> None:
    bad = []
    for p in md_files():
        want = "Apache-2.0" if APACHE_DIRS & set(p.relative_to(ROOT).parts) else "CC-BY-4.0"
        head = p.read_text(encoding="utf-8").lstrip()[:120]
        if f"SPDX-License-Identifier: {want}" not in head.splitlines()[0] if head else True:
            bad.append(str(p.relative_to(ROOT)))
    check("spdx-headers", not bad, ", ".join(bad))


# ---- 2. Spec integrity -----------------------------------------------------
def check_spec() -> None:
    if not SPEC.exists():
        check("spec-exists", False, str(SPEC.relative_to(ROOT)))
        return
    t = SPEC.read_text(encoding="utf-8")
    check("spec-exists", True)
    check(
        "spec-attribution-footer",
        t.rstrip().endswith(
            "Licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)."
        ),
    )
    check("spec-no-placeholders", "<spec-domain>" not in t and "working name" not in t.lower())
    check("spec-changelog-appendix", "## Appendix C" in t)
    try:
        tomllib.loads(re.search(r"```toml\n(.*?)```", t, re.S).group(1))
        json.loads(re.search(r"```json\n(.*?)```", t, re.S).group(1))
        check("spec-embedded-examples-parse", True)
    except Exception as e:
        check("spec-embedded-examples-parse", False, str(e))
    # Level table: parse section 3.2 rows and verify the accountability invariant
    rows = re.findall(
        r"^\| (agent|mixed / ambiguous|human) \| "
        r"(none|agent \(independent\)|"
        r"human(?: \(distinct (?:identity|canonical actor)\))?) \| \*\*(T[0-3])\*\* \|$",
        t,
        re.M,
    )
    check("spec-level-table-shape", len(rows) == 9, f"found {len(rows)} rows, expected 9")

    def expected(author: str, review: str) -> str:
        a, r = author.split()[0].rstrip(" /"), review.split()[0]
        humans = (a == "human") + (r == "human")
        return ("T1" if r == "agent" else "T0") if humans == 0 else f"T{humans + 1}"

    bad = [f"{a}/{r}={lvl}" for a, r, lvl in rows if lvl != expected(a, r)]
    check("spec-accountability-invariant", not bad, ", ".join(bad))

    # SemVer precedence claims the spec relies on
    def cmp_ids(a, b):
        an, bn = a.isdigit(), b.isdigit()
        if an and bn:
            return (int(a) > int(b)) - (int(a) < int(b))
        if an != bn:
            return -1 if an else 1
        return (a > b) - (a < b)

    def cmp_pre(p1, p2):
        if not p1 and not p2:
            return 0
        if not p1:
            return 1
        if not p2:
            return -1
        for x, y in itertools.zip_longest(p1, p2):
            if x is None:
                return -1
            if y is None:
                return 1
            if c := cmp_ids(x, y):
                return c
        return 0

    def P(s):
        return s.split(".") if s else []

    prec_ok = all(
        cmp_pre(P(a), P(b)) == w
        for a, b, w in [
            ("rc.1", "t1.1", -1),
            ("t1.1", "", -1),
            ("t10", "t2", -1),
            ("t0.1", "t2.1", -1),
        ]
    )
    check("spec-precedence-claims", prec_ok)


# ---- 3. Project-state documentation ---------------------------------------
def check_project_state() -> None:
    spec_text = SPEC.read_text(encoding="utf-8") if SPEC.exists() else ""
    version_match = re.search(r"^\*\*Draft v(\d+\.\d+)\*\*$", spec_text, re.M)
    check("project-state-spec-version", version_match is not None)
    if version_match is None:
        return

    version = version_match.group(1)
    readme = README.read_text(encoding="utf-8") if README.exists() else ""
    contributing = CONTRIBUTING.read_text(encoding="utf-8") if CONTRIBUTING.exists() else ""
    agents = AGENT_CONTRACT.read_text(encoding="utf-8") if AGENT_CONTRACT.exists() else ""
    design = DESIGN_RECORD.read_text(encoding="utf-8") if DESIGN_RECORD.exists() else ""

    check(
        "project-state-readme-version",
        f"specification — draft v{version}" in readme and f"**v{version} working draft**" in readme,
    )
    check("project-state-contributing-version", f"spec v{version}" in contributing)
    check(
        "project-state-agent-contract",
        f"`spec/semver-trust.md` | **Normative specification** (draft v{version})" in agents
        and "`schemas/` (planned)" not in agents
        and "`conformance/` (planned)" not in agents,
    )
    check(
        "project-state-design-record",
        "location `spec/semver-trust.md`" in design
        and f"Current state: **spec draft v{version}**" in design,
    )

    stale_status = [
        phrase
        for phrase in (
            "No implementation exists yet.",
            "Implementation **not started**",
            "Formal JSON Schemas for predicates | Not started",
            "Conformance suite | Not started",
        )
        if phrase in design
    ]
    check("project-state-no-stale-artifact-status", not stale_status, ", ".join(stale_status))

    adr_files = {
        f"ADR-{int(path.name[:4]):03d}" for path in ADR_DIR.glob("0*.md") if path.name[:4].isdigit()
    }
    design_adrs = set(re.findall(r"^\| (ADR-\d{3}) \|", design, re.M))
    check(
        "project-state-design-record-adrs",
        design_adrs == adr_files,
        f"missing={sorted(adr_files - design_adrs)}, extra={sorted(design_adrs - adr_files)}",
    )


# ---- 4. Predicate pages ----------------------------------------------------
def check_predicates() -> None:
    spec_text = SPEC.read_text(encoding="utf-8") if SPEC.exists() else ""
    for kind in ("release", "review"):
        pages = sorted((ROOT / kind).glob("v*.md")) if (ROOT / kind).exists() else []
        check(f"predicate-pages-exist-{kind}", bool(pages))
        for page in pages:
            uri = f"{DOMAIN}/{kind}/{page.stem}"
            body = page.read_text(encoding="utf-8")
            check(
                f"predicate-uri-matches-path-{kind}/{page.stem}",
                uri in body,
                f"page must state its own URI {uri}",
            )
            wrong = [d for d in ("release", "review") if d != kind and f"{DOMAIN}/{d}/" in body]
            check(
                f"predicate-no-cross-copy-{kind}/{page.stem}",
                not wrong,
                f"mentions {wrong} predicate URI — copy/paste drift",
            )
        # every predicate URI the spec declares must have a page
        for m in re.finditer(rf"{re.escape(DOMAIN)}/{kind}/(v[\d.]+\d)", spec_text):
            check(
                f"spec-predicate-page-{kind}/{m.group(1)}",
                (ROOT / kind / f"{m.group(1)}.md").exists(),
            )


# ---- 5. ADR discipline -----------------------------------------------------
def check_adrs() -> None:
    files = sorted(ADR_DIR.glob("0*.md")) if ADR_DIR.exists() else []
    check("adr-dir", bool(files))
    ids = set()
    for p in files:
        m = re.search(r"^# (ADR-(\d{3})) — (.+)$", p.read_text(encoding="utf-8"), re.M)
        if not m:
            check(f"adr-header-{p.name}", False, "no '# ADR-NNN — Title' header")
            continue
        ids.add(m.group(1))
        want = f"{int(m.group(2)):04d}-{slugify(m.group(3))}.md"
        check(f"adr-filename-{m.group(1)}", p.name == want, f"expected {want}")
    index = ADR_DIR / "README.md"
    if index.exists():
        rows = re.findall(
            r"^\| (ADR-\d{3}) \| \[.+?\]\((.+?)\) \|", index.read_text(encoding="utf-8"), re.M
        )
        indexed = {a for a, _ in rows}
        check("adr-index-covers-files", ids <= indexed, f"missing rows: {sorted(ids - indexed)}")
        check("adr-index-no-ghosts", indexed <= ids, f"rows without files: {sorted(indexed - ids)}")
        badlinks = [f for _, f in rows if not (ADR_DIR / f).exists()]
        check("adr-index-links-resolve", not badlinks, ", ".join(badlinks))
    else:
        check("adr-index-exists", False)
    refs = set()
    for p in md_files():
        refs |= set(re.findall(r"ADR-\d{3}", p.read_text(encoding="utf-8")))
    check("adr-refs-resolve", refs <= ids, f"dangling: {sorted(refs - ids)}")


# ---- 6. Links --------------------------------------------------------------
def check_links() -> None:
    rooty, broken = [], []
    for p in md_files():
        text = p.read_text(encoding="utf-8")
        for m in re.finditer(r"\]\(([^)\s]+?)(?:#[^)]*)?\)", text):
            target = m.group(1)
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            if target.startswith("/"):
                rooty.append(f"{p.relative_to(ROOT)} -> {target}")
                continue
            if not (p.parent / target).exists():
                broken.append(f"{p.relative_to(ROOT)} -> {target}")
    check("links-no-root-relative", not rooty, "; ".join(rooty))
    check("links-relative-resolve", not broken, "; ".join(broken))


# ---- 7. Licensing arrangement ----------------------------------------------
def check_licenses() -> None:
    lic = ROOT / "LICENSE"
    if lic.exists():
        t = lic.read_text(encoding="utf-8")
        check(
            "license-cc-by",
            "Attribution 4.0 International" in t
            and not re.search(r"NonCommercial|NoDerivatives|ShareAlike", t),
        )
    else:
        check("license-cc-by", False, "LICENSE missing")
    la = ROOT / "LICENSE-APACHE"
    check("license-apache", la.exists() and "Apache License" in la.read_text(encoding="utf-8"))
    for d in ("schemas", "conformance"):
        if (ROOT / d).exists():
            check(f"license-copy-in-{d}", (ROOT / d / "LICENSE").exists())


# ---- 8. Pages / domain wiring ----------------------------------------------
def check_site() -> None:
    cname = ROOT / "CNAME"
    check(
        "cname", cname.exists() and cname.read_text(encoding="utf-8").strip() == "semver-trust.dev"
    )
    cfg = ROOT / "_config.yml"
    check("config-site-url", cfg.exists() and f"url: {DOMAIN}" in cfg.read_text(encoding="utf-8"))


CHECKS = (
    check_spdx,
    check_spec,
    check_project_state,
    check_predicates,
    check_adrs,
    check_links,
    check_licenses,
    check_site,
)
for fn in CHECKS:
    fn()
print(
    f"\n{'OK' if not failures else 'DRIFT DETECTED'}: "
    f"{len(failures)} failure(s)" + (f" -> {failures}" if failures else "")
)
sys.exit(1 if failures else 0)
