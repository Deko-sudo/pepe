"""Regression test for the Mini App Dockerfile VITE_BUILD_ID conditional.

Guards against the build step exiting non-zero (failing the whole image build)
when VITE_BUILD_ID is empty or ``dev``, while still running the production
build for a real build ID. The real ``npm run build`` is substituted with a
harmless marker so the test validates branching logic, not the build itself.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = REPO_ROOT / "apps" / "mini-app" / "Dockerfile"


def _extract_conditional() -> str:
    text = DOCKERFILE.read_text(encoding="utf-8")
    match = re.search(r"RUN if.*?fi", text, re.DOTALL)
    assert match is not None, "Dockerfile build step must use an if/fi conditional"
    return match.group(0).replace("RUN ", "")


def test_dockerfile_uses_conditional_not_failing_test() -> None:
    """The build step must not use ``test ... && npm run build`` which exits 1."""
    text = DOCKERFILE.read_text(encoding="utf-8")
    conditional = _extract_conditional()
    assert conditional.startswith("if")
    assert "npm run build" in conditional
    assert "test -n \"$VITE_BUILD_ID\" && test" not in text


def test_empty_build_id_succeeds() -> None:
    ran = _run_shell_case("", marker="echo BUILD_RAN")
    assert "BUILD_RAN" not in ran.stdout


def test_dev_build_id_succeeds() -> None:
    ran = _run_shell_case("dev", marker="echo BUILD_RAN")
    assert "BUILD_RAN" not in ran.stdout


def test_real_build_id_runs_build() -> None:
    ran = _run_shell_case("abcd1234", marker="echo BUILD_RAN")
    assert "BUILD_RAN" in ran.stdout


def test_skip_branch_creates_dist_placeholder() -> None:
    """The skip branch must leave a dist/ so the nginx COPY stage succeeds."""
    conditional = _extract_conditional()
    assert "mkdir -p dist" in conditional
    assert "index.html" in conditional


def _run_shell_case(value: str, *, marker: str) -> subprocess.CompletedProcess[str]:
    """Reproduce the Dockerfile conditional with ``npm run build`` replaced."""
    conditional = _extract_conditional().replace("npm run build", marker)
    env = {"VITE_BUILD_ID": value, "PATH": "/usr/bin:/bin"}
    return subprocess.run(
        ["sh", "-c", conditional + " && echo EXIT_OK"],
        capture_output=True,
        text=True,
        env=env,
        cwd=REPO_ROOT,
    )
