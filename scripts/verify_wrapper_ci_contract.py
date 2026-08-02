#!/usr/bin/env python3
"""Fail closed when the W6 wrapper-security CI contract drifts.

This verifier intentionally uses only repository source text and Python's standard
library. It makes no network request and can run in pull-request and main-push
contexts without secrets.
"""

from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/ci.yml"
WORKFLOW_DIRECTORY = WORKFLOW.parent
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
    "needs: [frontend, api, quote-core, migration, bot, worker, worker-integration, stage7-worker-integration, tradingview-wrapper, wrapper-ci-security-contract]",
    "Do not request a provider",
    "docker compose up -d api mini-app tradingview-wrapper",
)
FORBIDDEN_WORKFLOW_SNIPPETS = (
    "pull_request_target:",
    "npm run provider-check",
    "npm run subresource-revalidation",
    "secrets.",
    "actions/upload-artifact@",
    "actions/download-artifact@",
    "environment:",
)


def job_block(workflow: str, job_name: str) -> str:
    match = re.search(
        rf"^  {re.escape(job_name)}:\n(?P<body>.*?)(?=^  [a-z0-9-]+:\n|\Z)",
        workflow,
        re.MULTILINE | re.DOTALL,
    )
    if match is None:
        return ""
    return match.group(0)


def main() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    missing = [snippet for snippet in REQUIRED_WORKFLOW_SNIPPETS if snippet not in workflow]
    security_job = job_block(workflow, "wrapper-ci-security-contract")
    if "persist-credentials: false" not in security_job:
        missing.append("persist-credentials: false in wrapper-ci-security-contract")

    workflow_files = sorted(WORKFLOW_DIRECTORY.glob("*.y*ml"))
    forbidden = []
    for workflow_file in workflow_files:
        source = workflow_file.read_text(encoding="utf-8")
        for snippet in FORBIDDEN_WORKFLOW_SNIPPETS:
            if snippet in source:
                forbidden.append(f"{workflow_file.relative_to(ROOT)}: {snippet}")
        if re.search(r"^\s+(?:contents|actions|checks|statuses|packages|pull-requests): write\s*$", source, re.MULTILINE):
            forbidden.append(f"{workflow_file.relative_to(ROOT)}: write workflow permission")
        if re.search(r"^\s*-\s+uses:\s+[^\n]*deploy", source, re.MULTILINE | re.IGNORECASE):
            forbidden.append(f"{workflow_file.relative_to(ROOT)}: deployment action")
    if missing or forbidden:
        details = []
        if missing:
            details.append(f"missing required CI contract: {missing}")
        if forbidden:
            details.append(f"forbidden CI contract: {forbidden}")
        raise SystemExit("; ".join(details))


if __name__ == "__main__":
    main()
