"""Sync the committed fixture DAG image into the top-level docs folder."""

from __future__ import annotations

import shutil
import sys

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DAG = REPO_ROOT / "tests" / "fixtures" / "dvc_project" / "docs" / "dvc_project_dag.png"
DOCS_DAG = REPO_ROOT / "docs" / "dvc_project_dag.png"


def main() -> None:
    """Copy the fixture DAG image into the docs directory."""
    if not FIXTURE_DAG.exists():
        msg = f"Fixture DAG image does not exist: {FIXTURE_DAG}"
        raise FileNotFoundError(msg)

    DOCS_DAG.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(FIXTURE_DAG, DOCS_DAG)
    sys.stdout.write(
        f"Synced {FIXTURE_DAG.relative_to(REPO_ROOT)} -> {DOCS_DAG.relative_to(REPO_ROOT)}\n",
    )


if __name__ == "__main__":
    main()
