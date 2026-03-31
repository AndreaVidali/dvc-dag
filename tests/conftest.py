"""Pytest fixtures for isolated DVC workspace tests."""

from __future__ import annotations

import os
import shutil
import subprocess

from dataclasses import dataclass
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "dvc_workspace"
WORKSPACE_FIXTURE_RELATIVE = WORKSPACE_FIXTURE.relative_to(REPO_ROOT)
VENV_BIN = REPO_ROOT / ".venv" / "bin"


def _find_executable(name: str) -> Path | None:
    """Return the resolved path to an executable if it can be found."""
    path = shutil.which(name)
    if path is not None:
        return Path(path)

    for directory in (Path("/opt/homebrew/bin"), Path("/usr/local/bin")):
        candidate = directory / name
        if candidate.exists():
            return candidate

    return None


@dataclass(frozen=True)
class DvcWorkspace:
    """Temporary DVC workspace prepared for end-to-end testing."""

    root: Path
    env: dict[str, str]

    def activate(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Apply the workspace environment to the active pytest context."""
        monkeypatch.chdir(self.root)
        for key in ("PATH", "DVC_GLOBAL_CONFIG_DIR", "DVC_SITE_CACHE_DIR"):
            monkeypatch.setenv(key, self.env[key])


@pytest.fixture
def e2e_workspace(tmp_path: Path) -> DvcWorkspace:
    """Create an isolated Git repo containing the committed DVC fixture workspace."""
    dvc_bin = VENV_BIN / "dvc"
    if not dvc_bin.exists():
        pytest.skip("The end-to-end tests require .venv/bin/dvc.")

    git_bin = _find_executable("git")
    if git_bin is None:
        pytest.skip("The end-to-end tests require git.")

    dot_bin = _find_executable("dot")
    tred_bin = _find_executable("tred")
    if dot_bin is None or tred_bin is None:
        pytest.skip("The end-to-end tests require Graphviz 'dot' and 'tred'.")

    repo_root = tmp_path / "repo"
    workspace = repo_root / WORKSPACE_FIXTURE_RELATIVE
    workspace.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        WORKSPACE_FIXTURE,
        workspace,
        ignore=shutil.ignore_patterns(".DS_Store", "__pycache__", "*.pyc"),
    )

    path_entries = [str(dvc_bin.parent), str(dot_bin.parent)]
    current_path = os.environ.get("PATH")
    if current_path:
        path_entries.append(current_path)

    env = os.environ.copy()
    env["PATH"] = os.pathsep.join(path_entries)
    env["DVC_GLOBAL_CONFIG_DIR"] = str(tmp_path / ".dvc-global")
    env["DVC_SITE_CACHE_DIR"] = str(tmp_path / ".dvc-site-cache")

    subprocess.run(  # noqa: S603
        [str(git_bin), "init", "-q"],
        cwd=repo_root,
        env=env,
        check=True,
    )

    return DvcWorkspace(root=workspace, env=env)
