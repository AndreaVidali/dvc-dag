"""Tests for built package artifacts."""

from __future__ import annotations

import importlib.metadata
import shutil
import subprocess
import tarfile
import zipfile

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def built_package_artifacts(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    """Build the wheel and sdist once for artifact inspection tests."""
    uv_bin = shutil.which("uv")
    if uv_bin is None:
        pytest.skip("The package artifact tests require uv.")

    build_dir = tmp_path_factory.mktemp("package-build")
    subprocess.run(  # noqa: S603
        [uv_bin, "build", "--out-dir", str(build_dir)],
        check=True,
        cwd=REPO_ROOT,
    )

    package_version = importlib.metadata.version("dvc-dag")
    sdist = build_dir / f"dvc_dag-{package_version}.tar.gz"
    wheel = build_dir / f"dvc_dag-{package_version}-py3-none-any.whl"
    return sdist, wheel


def test_wheel_contains_runtime_files_only(
    built_package_artifacts: tuple[Path, Path],
) -> None:
    """The wheel should contain the runtime package and metadata only."""
    _sdist, wheel = built_package_artifacts
    package_version = importlib.metadata.version("dvc-dag")
    dist_info = f"dvc_dag-{package_version}.dist-info"

    with zipfile.ZipFile(wheel) as zip_file:
        names = set(zip_file.namelist())
        entry_points = zip_file.read(f"{dist_info}/entry_points.txt").decode("utf-8")

    assert "dvc_dag/__main__.py" in names
    assert "dvc_dag/py.typed" in names
    assert f"{dist_info}/licenses/LICENSE" in names
    assert "tests/test_dag_e2e.py" not in names
    assert "docs/dvc_dag.png" not in names
    assert "dvc-dag = dvc_dag.cli:app" in entry_points


def test_sdist_contains_curated_release_files(
    built_package_artifacts: tuple[Path, Path],
) -> None:
    """The sdist should ship only the intended release files."""
    sdist, _wheel = built_package_artifacts
    package_version = importlib.metadata.version("dvc-dag")
    root = f"dvc_dag-{package_version}"

    with tarfile.open(sdist) as tar_file:
        names = set(tar_file.getnames())

    assert f"{root}/src/dvc_dag/__main__.py" in names
    assert f"{root}/src/dvc_dag/py.typed" in names
    assert f"{root}/README.md" in names
    assert f"{root}/LICENSE" in names
    assert f"{root}/CHANGELOG.md" in names
    assert f"{root}/docs/dvc_dag.png" in names
    assert not any(name.startswith(f"{root}/tests/") for name in names)
    assert not any(name.startswith(f"{root}/.github/") for name in names)
    assert f"{root}/Makefile" not in names
    assert f"{root}/uv.lock" not in names
    assert not any(".dvc/tmp/" in name for name in names)
