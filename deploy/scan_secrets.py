"""Bounded Git-visible source scan. Reports rule/path/line, never secret values."""
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
RULES = {
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github-token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})\b"),
    "aws-key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "provider-key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{40,}\b"),
    "slack-token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    "credential-url": re.compile(r"(?:postgres(?:ql)?|rediss?)://[^\s:/]+:([^\s@]+)@"),
}


def scan_text(name, text):
    found = []
    for index, line in enumerate(text.splitlines(), 1):
        for rule, pattern in RULES.items():
            match = pattern.search(line)
            if not match:
                continue
            if rule == "credential-url":
                # Existing explicit synthetic test inputs and inert placeholders.
                if name.startswith(("backend/tests/", "backend/redistests/")) or any(
                    marker in match[1] for marker in ("test", "synthetic", "<", "PASSWORD", "password")):
                    continue
            found.append((rule, name, index))
    return found


def main():
    names = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT).decode().split("\0")
    findings = []
    count = 0
    for name in sorted(set(names)):
        if not name:
            continue
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            continue
        if path.name == ".env" or (path.name.startswith(".env.") and not path.name.endswith(".example")):
            findings.append(("non-template-env", name, 0))
            continue
        if path.stat().st_size > 2_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeError:
            continue
        count += 1
        findings.extend(scan_text(name, text))
    for rule, name, line in findings:
        print(f"FINDING {rule} {name}:{line}")
    print(f"Scanned {count} text files; {len(findings)} findings. Not a historical Git/full secret certification.")
    return int(bool(findings))


if __name__ == "__main__":
    sys.exit(main())
