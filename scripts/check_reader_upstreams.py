#!/usr/bin/env python3
"""Resolve accepted Reader-mode inputs without generating or publishing files."""

import json
import re
import subprocess
from urllib.parse import quote

UPSTREAMS = (
    ("schema", 1160447325, 19),
    ("registry", 1155264900, 553),
    ("engine", 1160447354, 175),
)


def github(path):
    """Read one public GitHub API path from the canonical host."""
    result = subprocess.run(["gh", "api", "--hostname", "github.com", path], capture_output=True, text=True, timeout=15)
    if result.returncode or len(result.stdout) > 2_000_000:
        raise ValueError("upstream read unavailable")
    return json.loads(result.stdout)


def sha(value):
    """Return whether value is an immutable lowercase Git commit SHA."""
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value) is not None


def inspect(get=github):
    """Resolve each accepted upstream by stable repository identity."""
    rows = []
    for name, expected_repo_id, number in UPSTREAMS:
        row = {"input": name, "repository_id": expected_repo_id, "pull_request": number, "status": "unmeasured"}
        try:
            identity = get(f"repositories/{expected_repo_id}")
            repo_id = identity.get("id")
            repo = identity.get("full_name")
            branch = identity.get("default_branch")
            if (type(repo_id) is not int or repo_id != expected_repo_id
                    or not isinstance(repo, str) or "/" not in repo
                    or not isinstance(branch, str) or not branch):
                raise ValueError("malformed upstream identity")
            row["repository"] = repo
            pr = get(f"repos/{repo}/pulls/{number}")
            if pr.get("merged") is not True:
                row["reason"] = "pr_not_merged"
                rows.append(row)
                continue
            merge = pr.get("merge_commit_sha")
            base_id = pr.get("base", {}).get("repo", {}).get("id")
            if not sha(merge) or type(base_id) is not int or base_id != repo_id:
                raise ValueError("malformed upstream identity")
            head = get(f"repos/{repo}/commits/{quote(branch, safe='')}").get("sha")
            if not sha(head):
                raise ValueError("malformed upstream head")
            relation = get(f"repos/{repo}/compare/{merge}...{head}")
            if relation.get("status") not in ("ahead", "identical"):
                row["reason"] = "merge_not_on_default"
            else:
                # Detect movement or rename during the read batch before issuing usable inputs.
                current = get(f"repos/{repo}/commits/{quote(branch, safe='')}").get("sha")
                after = get(f"repositories/{expected_repo_id}")
                if (current != head or type(after.get("id")) is not int
                        or after["id"] != repo_id or after.get("full_name") != repo
                        or after.get("default_branch") != branch):
                    raise ValueError("upstream moved during observation")
                row.update(status="accepted", merge_commit=merge, default_head=head)
        except (OSError, ValueError, TypeError, KeyError, AttributeError, subprocess.SubprocessError):
            row["reason"] = "upstream_evidence_unavailable_or_changed"
        rows.append(row)
    return {"status": "pass" if all(r["status"] == "accepted" for r in rows) else "unmeasured",
            "scope": "Source ancestry only; no CI, generation, deployment or runtime acceptance inferred.",
            "inputs": rows}


if __name__ == "__main__":
    report = inspect()
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["status"] == "pass" else 77)
