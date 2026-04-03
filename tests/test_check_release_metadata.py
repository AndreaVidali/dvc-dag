"""Tests for the release publish validation helper."""

from __future__ import annotations

import importlib.util

from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check_release_metadata.py"
SPEC = importlib.util.spec_from_file_location("check_release_metadata", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
CHECK_RELEASE_METADATA = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK_RELEASE_METADATA)

parse_release_tag = CHECK_RELEASE_METADATA.parse_release_tag
validate_published_release = CHECK_RELEASE_METADATA.validate_published_release


def test_parse_release_tag_reads_the_version_from_a_github_release_tag() -> None:
    """Extract the version from a plain X.Y.Z release tag."""
    assert parse_release_tag("0.2.0") == "0.2.0"


def test_parse_release_tag_requires_the_expected_release_tag_format() -> None:
    """Reject release tags that do not use the expected X.Y.Z form."""
    with pytest.raises(ValueError, match=r"must have the form 'X\.Y\.Z'"):
        parse_release_tag("v0.2.0")


def test_validate_published_release_accepts_matching_metadata() -> None:
    """Accept matching tag, pyproject, and changelog versions."""
    assert (
        validate_published_release(
            tag_name="0.0.3",
            project_version="0.0.3",
            changelog_version="0.0.3",
        )
        == []
    )


def test_validate_published_release_requires_the_tag_to_match_pyproject() -> None:
    """Reject releases when the tag and pyproject version diverge."""
    errors = validate_published_release(
        tag_name="0.0.4",
        project_version="0.0.3",
        changelog_version="0.0.3",
    )

    assert "does not match [project].version" in errors[0]


def test_validate_published_release_requires_the_changelog_to_match_pyproject() -> None:
    """Reject releases when the changelog top version is stale or wrong."""
    errors = validate_published_release(
        tag_name="0.0.3",
        project_version="0.0.3",
        changelog_version="0.0.2",
    )

    assert "latest version in CHANGELOG.md does not match" in errors[0]
