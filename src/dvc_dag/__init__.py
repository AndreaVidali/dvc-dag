"""dvc_dag package."""

from importlib.metadata import PackageNotFoundError, version


try:
    __version__ = version("dvc-dag")
except PackageNotFoundError:
    __version__ = "0+unknown"
