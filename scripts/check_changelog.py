"""Validate changelog and version updates for pull requests."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys

from pathlib import Path


CHANGELOG_PATH = Path("CHANGELOG.md")
PYPROJECT_PATH = Path("pyproject.toml")
CHANGELOG_VERSION_RE = re.compile(r"^\s*## ([0-9]+\.[0-9]+\.[0-9]+) - ", re.MULTILINE)


def run_git(args: list[str], cwd: Path) -> str:
    """Run a git command and return stdout."""
    git_bin = shutil.which("git")
    if git_bin is None:
        msg = "git was not found on PATH."
        raise RuntimeError(msg)

    result = subprocess.run(  # noqa: S603
        [git_bin, *args],
        capture_output=True,
        check=False,
        cwd=cwd,
        encoding="utf-8",
    )
    if result.returncode != 0:
        msg = result.stderr.strip() or result.stdout.strip() or "git command failed"
        raise RuntimeError(msg)
    return result.stdout


def get_changed_paths(repo_root: Path, *, base_ref: str, head_ref: str) -> set[str]:
    """Return the set of changed files between two refs."""
    output = run_git(["diff", "--name-only", f"{base_ref}...{head_ref}"], cwd=repo_root)
    return {line.strip() for line in output.splitlines() if line.strip()}


def read_file_at_ref(repo_root: Path, *, ref: str, path: Path) -> str:
    """Return file contents from a specific git ref."""
    return run_git(["show", f"{ref}:{path.as_posix()}"], cwd=repo_root)


def load_project_version(pyproject_text: str) -> str:
    """Return the package version from pyproject text."""
    match = re.search(r'(?ms)^\s*\[project\].*?^\s*version = "([^"]+)"\s*$', pyproject_text)
    if match is None:
        msg = "Could not find [project].version in pyproject.toml."
        raise ValueError(msg)
    return match.group(1)


def load_latest_changelog_version(changelog_text: str) -> str:
    """Return the latest version declared in the changelog."""
    match = CHANGELOG_VERSION_RE.search(changelog_text)
    if match is None:
        msg = "Could not find a changelog release heading like '## 0.0.1 - 2026/03/30'."
        raise ValueError(msg)
    return match.group(1)


def validate_release_metadata(
    *,
    changelog_changed: bool,
    base_version: str,
    head_version: str,
    changelog_version: str,
) -> list[str]:
    """Return validation errors for changelog and version updates."""
    errors: list[str] = []

    if not changelog_changed:
        errors.append("CHANGELOG.md was not updated in this pull request.")

    if base_version == head_version:
        errors.append(
            "The package version in pyproject.toml was not bumped in this pull request.",
        )

    if changelog_version != head_version:
        errors.append(
            "The latest version in CHANGELOG.md does not match "
            "[project].version in pyproject.toml.",
        )

    return errors


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-ref", required=True, help="Base git ref or SHA for the PR.")
    parser.add_argument("--head-ref", required=True, help="Head git ref or SHA for the PR.")
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root containing CHANGELOG.md and pyproject.toml.",
    )
    return parser.parse_args()


def main() -> int:
    """Run the changelog checks."""
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()

    changed_paths = get_changed_paths(
        repo_root,
        base_ref=args.base_ref,
        head_ref=args.head_ref,
    )
    changelog_changed = CHANGELOG_PATH.as_posix() in changed_paths

    base_pyproject_text = read_file_at_ref(
        repo_root,
        ref=args.base_ref,
        path=PYPROJECT_PATH,
    )
    head_pyproject_text = PYPROJECT_PATH.read_text()
    head_changelog_text = CHANGELOG_PATH.read_text()

    errors = validate_release_metadata(
        changelog_changed=changelog_changed,
        base_version=load_project_version(base_pyproject_text),
        head_version=load_project_version(head_pyproject_text),
        changelog_version=load_latest_changelog_version(head_changelog_text),
    )

    if not errors:
        return 0

    for error in errors:
        sys.stderr.write(f"ERROR: {error}\n")

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
