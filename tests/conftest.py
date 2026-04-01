"""Pytest fixtures for isolated DVC project tests."""

from __future__ import annotations

import os
import shutil
import subprocess

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECT_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "dvc_project"
PROJECT_FIXTURE_RELATIVE = PROJECT_FIXTURE.relative_to(REPO_ROOT)
VENV_BIN = REPO_ROOT / ".venv" / "bin"
CLI_BIN = VENV_BIN / "dvc-dag"
PYTHON_BIN = VENV_BIN / "python"


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
class DvcProject:
    """Temporary DVC project prepared for end-to-end testing."""

    root: Path
    env: dict[str, str]
    base_path: str
    dvc_bin_dir: Path
    graphviz_bin_dir: Path

    def activate(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Apply the project environment to the active pytest context."""
        monkeypatch.chdir(self.root)
        for key in ("PATH", "DVC_GLOBAL_CONFIG_DIR", "DVC_SITE_CACHE_DIR"):
            monkeypatch.setenv(key, self.env[key])

    def make_env(
        self,
        *,
        include_dvc: bool = True,
        include_graphviz: bool = True,
        extra_env: Mapping[str, str] | None = None,
    ) -> dict[str, str]:
        """Return an environment dictionary for subprocess-based CLI tests."""
        filtered_base_path = [
            entry
            for entry in self.base_path.split(os.pathsep)
            if entry and entry not in {str(self.dvc_bin_dir), str(self.graphviz_bin_dir)}
        ]
        path_entries: list[str] = []
        if include_dvc:
            path_entries.append(str(self.dvc_bin_dir))
        if include_graphviz:
            path_entries.append(str(self.graphviz_bin_dir))

        path_entries.extend(filtered_base_path)

        env = self.env.copy()
        env["PATH"] = os.pathsep.join(dict.fromkeys(path_entries))

        if extra_env:
            env.update(extra_env)

        return env

    def run_cli(
        self,
        args: Sequence[str],
        *,
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Run the installed console script and return the completed process."""
        return subprocess.run(  # noqa: S603
            [str(CLI_BIN), *args],
            capture_output=True,
            cwd=cwd or self.root,
            encoding="utf-8",
            env=dict(env or self.env),
            check=False,
        )

    def run_module(
        self,
        args: Sequence[str],
        *,
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Run `python -m dvc_dag` and return the completed process."""
        return subprocess.run(  # noqa: S603
            [str(PYTHON_BIN), "-m", "dvc_dag", *args],
            capture_output=True,
            cwd=cwd or self.root,
            encoding="utf-8",
            env=dict(env or self.env),
            check=False,
        )


@pytest.fixture
def dvc_project(tmp_path: Path) -> DvcProject:
    """Create an isolated Git repo containing the committed DVC fixture project."""
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
    project = repo_root / PROJECT_FIXTURE_RELATIVE
    project.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        PROJECT_FIXTURE,
        project,
        ignore=shutil.ignore_patterns(".DS_Store", "__pycache__", "*.pyc"),
    )

    path_entries = [str(dvc_bin.parent), str(dot_bin.parent)]
    if tred_bin.parent != dot_bin.parent:
        path_entries.append(str(tred_bin.parent))
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

    return DvcProject(
        root=project,
        env=env,
        base_path=current_path or "",
        dvc_bin_dir=dvc_bin.parent,
        graphviz_bin_dir=dot_bin.parent,
    )
