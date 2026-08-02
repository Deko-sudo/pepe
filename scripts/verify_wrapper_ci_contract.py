#!/usr/bin/env python3
"""Fail closed when the W6 wrapper-security CI contract drifts.

This verifier intentionally uses only repository source text and Python's standard
library. It makes no network request and can run in pull-request and main-push
contexts without secrets.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/ci.yml"
REQUIRED_WORKFLOW_SNIPPETS = (
    "push:\n    branches: [main, develop]",
    "pull_request:\n    branches: [main]",
    "permissions:\n  contents: read",
    "wrapper-ci-security-contract:",
    "name: Wrapper CI security contract",
    "python scripts/verify_wrapper_ci_contract.py",
    "tradingview-wrapper:",
    "npm run e2e",
    "docker:",
    "needs: [frontend, api, quote-core, migration, bot, worker, tradingview-wrapper]",
    "Do not request a provider",
    "docker compose up -d api mini-app tradingview-wrapper",
)
FORBIDDEN_WORKFLOW_SNIPPETS = (
    "pull_request_target:",
    "npm run provider-check",
    "npm run subresource-revalidation",
)


def main() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    missing = [snippet for snippet in REQUIRED_WORKFLOW_SNIPPETS if snippet not in workflow]
    forbidden = [snippet for snippet in FORBIDDEN_WORKFLOW_SNIPPETS if snippet in workflow]
    if missing or forbidden:
        details = []
        if missing:
            details.append(f"missing required CI contract: {missing}")
        if forbidden:
            details.append(f"forbidden CI contract: {forbidden}")
        raise SystemExit("; ".join(details))


if __name__ == "__main__":
    main()
