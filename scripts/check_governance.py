"""Read GitHub settings and report drift from the single-maintainer policy."""

import json
import subprocess

REPO = "guadaloop-07/platform-work-reform-mx"


def api(path: str) -> dict:
    result = subprocess.run(
        ["gh", "api", f"repos/{REPO}{path}"], check=True, capture_output=True, text=True
    )
    return json.loads(result.stdout)


def main() -> None:
    repo = api("")
    protection = api("/branches/main/protection")
    reviews = protection["required_pull_request_reviews"]
    checks = protection["required_status_checks"]
    expected = {
        "default branch": repo["default_branch"] == "main",
        "squash only": repo["allow_squash_merge"]
        and not repo["allow_merge_commit"]
        and not repo["allow_rebase_merge"],
        "delete merged branches": repo["delete_branch_on_merge"],
        "administrator enforcement": protection["enforce_admins"]["enabled"],
        "linear history": protection["required_linear_history"]["enabled"],
        "resolved conversations": protection["required_conversation_resolution"]["enabled"],
        "no force pushes": not protection["allow_force_pushes"]["enabled"],
        "no deletion": not protection["allow_deletions"]["enabled"],
        "single-maintainer approvals": reviews["required_approving_review_count"] == 0,
        "no review bypass": not any(reviews.get("bypass_pull_request_allowances", {}).values()),
        "up-to-date CI": checks["strict"],
        "required Actions gate": {"context": "ci", "app_id": 15368} in checks["checks"],
    }
    failures = [name for name, passed in expected.items() if not passed]
    if failures:
        raise SystemExit("Governance drift: " + ", ".join(failures))
    print("Repository governance matches the single-maintainer policy.")


if __name__ == "__main__":
    main()
