"""Validate release metadata before publishing to PyPI."""

from __future__ import annotations

import argparse
import importlib.util
import re
import shutil
import subprocess
import sys

from pathlib import Path
from typing import Protocol, cast


CHECK_CHANGELOG_PATH = Path(__file__).with_name("check_changelog.py")
TAG_VERSION_RE = re.compile(r"^([0-9]+\.[0-9]+\.[0-9]+)$")


class _CheckChangelogModule(Protocol):
    """Typed interface for the sibling changelog helper module."""

    CHANGELOG_PATH: Path
    PYPROJECT_PATH: Path

    def load_latest_changelog_version(self, changelog_text: str) -> str: ...

    def load_project_version(self, pyproject_text: str) -> str: ...


def _load_check_changelog_module() -> _CheckChangelogModule:
    """Load the shared changelog helpers from the sibling script."""
    spec = importlib.util.spec_from_file_location("check_changelog", CHECK_CHANGELOG_PATH)
    if spec is None or spec.loader is None:
        msg = "Could not load the changelog validation helpers."
        raise RuntimeError(msg)

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return cast("_CheckChangelogModule", module)


CHECK_CHANGELOG = _load_check_changelog_module()
CHANGELOG_PATH = CHECK_CHANGELOG.CHANGELOG_PATH
PYPROJECT_PATH = CHECK_CHANGELOG.PYPROJECT_PATH
load_latest_changelog_version = CHECK_CHANGELOG.load_latest_changelog_version
load_project_version = CHECK_CHANGELOG.load_project_version


def parse_release_tag(tag_name: str) -> str:
    """Return the version embedded in a GitHub release tag."""
    match = TAG_VERSION_RE.fullmatch(tag_name)
    if match is None:
        msg = "Release tag must have the form 'X.Y.Z'."
        raise ValueError(msg)
    return match.group(1)


def commit_is_reachable_from_ref(
    *,
    repo_root: Path,
    commit_ref: str,
    containing_ref: str,
) -> bool:
    """Return whether a commit is reachable from another ref."""
    git_bin = shutil.which("git")
    if git_bin is None:
        msg = "git was not found on PATH."
        raise RuntimeError(msg)

    result = subprocess.run(  # noqa: S603
        [git_bin, "merge-base", "--is-ancestor", commit_ref, containing_ref],
        capture_output=True,
        check=False,
        cwd=repo_root,
        encoding="utf-8",
    )
    if result.returncode in {0, 1}:
        return result.returncode == 0

    msg = result.stderr.strip() or result.stdout.strip() or "git merge-base failed"
    raise RuntimeError(msg)


def validate_published_release(
    *,
    tag_name: str,
    project_version: str,
    changelog_version: str,
    tag_is_on_main: bool,
) -> list[str]:
    """Return validation errors for a publishable release."""
    errors: list[str] = []

    try:
        tag_version = parse_release_tag(tag_name)
    except ValueError as exc:
        errors.append(str(exc))
        return errors

    if tag_version != project_version:
        errors.append(
            f"Release tag version {tag_version} does not match "
            f"[project].version {project_version} in pyproject.toml.",
        )

    if changelog_version != project_version:
        errors.append(
            "The latest version in CHANGELOG.md does not match "
            "[project].version in pyproject.toml.",
        )

    if not tag_is_on_main:
        errors.append("Release tag commit is not reachable from the main branch.")

    return errors


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--tag",
        required=True,
        help="GitHub release tag, expected in the form 'X.Y.Z'.",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root containing CHANGELOG.md and pyproject.toml.",
    )
    parser.add_argument(
        "--commit-ref",
        default="HEAD",
        help="Git commit or ref pointed to by the release tag.",
    )
    parser.add_argument(
        "--main-ref",
        default="origin/main",
        help="Git ref that release commits must be reachable from.",
    )
    return parser.parse_args()


def main() -> int:
    """Run the release metadata checks."""
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()

    project_version = load_project_version((repo_root / PYPROJECT_PATH).read_text())
    changelog_version = load_latest_changelog_version((repo_root / CHANGELOG_PATH).read_text())

    try:
        tag_is_on_main = commit_is_reachable_from_ref(
            repo_root=repo_root,
            commit_ref=args.commit_ref,
            containing_ref=args.main_ref,
        )
    except RuntimeError as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        return 1

    errors = validate_published_release(
        tag_name=args.tag,
        project_version=project_version,
        changelog_version=changelog_version,
        tag_is_on_main=tag_is_on_main,
    )

    if not errors:
        return 0

    for error in errors:
        sys.stderr.write(f"ERROR: {error}\n")

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
