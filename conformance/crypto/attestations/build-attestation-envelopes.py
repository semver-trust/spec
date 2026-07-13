#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""build-attestation-envelopes.py — (re)generate the vendored DSSE envelopes.

Unlike the fixture repositories (built at test time), the envelopes are
vendored: signed bytes are frozen — they cannot be patched, only regenerated,
and regeneration breaks downstream expectations
(docs/conformance-crypto-fixtures.md §6). Run this only when the payloads
deliberately change, and re-validate every non-negative payload against the
schemas BEFORE running it (the §6 rider: no fixture gets signed unless its
payload validates).

Signature convention (documented in ../README.md): DSSE pre-authentication
encoding (PAE) signed as an OpenSSH SSHSIG with namespace
"attestation@semver-trust.dev"; sig is the base64 of the armored SSHSIG;
keyid is the signer's SHA256 fingerprint. The namespace binds the signature
to attestation use — a git commit signature can never double as an
attestation signature, and vice versa.

Deterministic: Ed25519 signing is deterministic (RFC 8032), payload bytes are
the checked-in files verbatim.

    python3 build-attestation-envelopes.py

Requires ssh-keygen; stdlib only.
"""

import base64
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
KEYS = HERE.parent / "keys"
PAYLOADS = HERE / "payloads"
PREDICATE_V02 = HERE.parent.parent / "predicate-v0.2"
ENVELOPES = HERE / "envelopes"

PAYLOAD_TYPE = "application/vnd.in-toto+json"
NAMESPACE = "attestation@semver-trust.dev"

# envelope name -> (payload file, signing key, post-sign payload tamper)
PLAN = {
    "review-valid.dsse.json": ("review-valid.json", "agent-ci-bot", None),
    "release-valid.dsse.json": ("release-valid.json", "agent-ci-bot", None),
    "review-v02-valid.dsse.json": (PREDICATE_V02 / "review-valid.json", "agent-ci-bot", None),
    "release-v02-valid.dsse.json": (PREDICATE_V02 / "release-valid.json", "agent-ci-bot", None),
    "release-schema-invalid.dsse.json": ("release-schema-invalid.json", "agent-ci-bot", None),
    "release-sig-invalid.dsse.json": (
        "release-valid.json",
        "agent-ci-bot",
        # Tampered after signing: still schema-valid, so the only defect is
        # the signature no longer covering the bytes.
        (b'"timestamp": "2026-01-01T00:00:00Z"', b'"timestamp": "2027-01-01T00:00:00Z"'),
    ),
    "release-unknown-signer.dsse.json": ("release-valid.json", "unknown-mallory", None),
}


def payload_path(payload_file: str | Path) -> Path:
    if isinstance(payload_file, Path):
        return payload_file
    return PAYLOADS / payload_file


def pae(payload_type: str, payload: bytes) -> bytes:
    t = payload_type.encode()
    return b"DSSEv1 %d %s %d %s" % (len(t), t, len(payload), payload)


def sign(key: str, message: bytes, workdir: Path) -> str:
    # ssh-keygen refuses group-readable private keys; sign from a 0600 copy.
    staged = workdir / key
    shutil.copy(KEYS / key, staged)
    staged.chmod(0o600)
    msg = workdir / "message"
    sig = workdir / "message.sig"
    for stale in (msg, sig):
        stale.unlink(missing_ok=True)
    msg.write_bytes(message)
    subprocess.run(
        ["ssh-keygen", "-Y", "sign", "-q", "-f", str(staged), "-n", NAMESPACE, str(msg)],
        check=True,
    )
    return base64.b64encode(sig.read_bytes()).decode()


def fingerprint(key: str) -> str:
    out = subprocess.run(
        ["ssh-keygen", "-lf", str(KEYS / f"{key}.pub")],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return out.split()[1]  # "256 SHA256:... comment (ED25519)"


def main() -> int:
    # An output-directory argument lets the conformance validator regenerate
    # into a scratch dir and byte-compare against the vendored envelopes —
    # the frozen-byte drift tripwire.
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ENVELOPES
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        for name, (payload_file, key, tamper) in PLAN.items():
            payload = payload_path(payload_file).read_bytes()
            sig = sign(key, pae(PAYLOAD_TYPE, payload), workdir)
            if tamper is not None:
                old, new = tamper
                tampered = payload.replace(old, new, 1)
                if tampered == payload:
                    print(f"{name}: tamper pattern not found", file=sys.stderr)
                    return 1
                payload = tampered
            envelope = {
                "payloadType": PAYLOAD_TYPE,
                "payload": base64.b64encode(payload).decode(),
                "signatures": [{"keyid": fingerprint(key), "sig": sig}],
            }
            (out / name).write_text(json.dumps(envelope, indent=2) + "\n", encoding="utf-8")
            print(f"  {name}  (signed by {key})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
