"""Tests for the changelog validation helper."""

from __future__ import annotations

import importlib.util

from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check_changelog.py"
SPEC = importlib.util.spec_from_file_location("check_changelog", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
CHECK_CHANGELOG = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK_CHANGELOG)

load_latest_changelog_version = CHECK_CHANGELOG.load_latest_changelog_version
load_project_version = CHECK_CHANGELOG.load_project_version
validate_release_metadata = CHECK_CHANGELOG.validate_release_metadata


def test_load_project_version_reads_the_project_version() -> None:
    """Read the project version from pyproject text."""
    pyproject_text = """
    [project]
    name = "dvc-dag"
    version = "0.2.0"
    """

    assert load_project_version(pyproject_text) == "0.2.0"


def test_load_latest_changelog_version_reads_the_latest_heading() -> None:
    """Read the first release heading from the changelog."""
    changelog_text = """
    # Changelog

    ## 0.2.0 - 2026/04/01

    - ⚙️ Something changed.

    ## 0.1.0 - 2026/03/01
    """

    assert load_latest_changelog_version(changelog_text) == "0.2.0"


def test_load_latest_changelog_version_requires_a_release_heading() -> None:
    """Fail when the changelog does not contain a valid release heading."""
    with pytest.raises(ValueError, match="Could not find a changelog release heading"):
        load_latest_changelog_version("# Changelog\n\nNo releases yet.\n")


def test_validate_release_metadata_accepts_a_bumped_matching_release() -> None:
    """Accept PR metadata when the changelog and version are both updated."""
    assert (
        validate_release_metadata(
            changelog_changed=True,
            base_version="0.0.1",
            head_version="0.0.2",
            changelog_version="0.0.2",
        )
        == []
    )


def test_validate_release_metadata_requires_the_changelog_to_change() -> None:
    """Require a changelog update in the PR."""
    errors = validate_release_metadata(
        changelog_changed=False,
        base_version="0.0.1",
        head_version="0.0.2",
        changelog_version="0.0.2",
    )

    assert "CHANGELOG.md was not updated" in errors[0]


def test_validate_release_metadata_requires_a_version_bump() -> None:
    """Require the package version to change in the PR."""
    errors = validate_release_metadata(
        changelog_changed=True,
        base_version="0.0.1",
        head_version="0.0.1",
        changelog_version="0.0.1",
    )

    assert "was not bumped" in errors[0]


def test_validate_release_metadata_requires_matching_versions() -> None:
    """Require the changelog and pyproject versions to match."""
    errors = validate_release_metadata(
        changelog_changed=True,
        base_version="0.0.1",
        head_version="0.0.2",
        changelog_version="0.0.3",
    )

    assert "does not match" in errors[0]
