import re
from importlib.metadata import PackageNotFoundError, version

import pytest

import kotobacore


def test_version_exists():
    assert isinstance(kotobacore.__version__, str)
    # PEP 440 / semver-ish: 0.1.12, 1.0.0, 0.2.0rc1, ...
    assert re.fullmatch(r"\d+\.\d+\.\d+([abrc]\w*)?", kotobacore.__version__)


def test_version_matches_package_metadata():
    """``_version.py`` must stay in sync with the version declared in pyproject."""
    try:
        installed = version("kotobacore")
    except PackageNotFoundError:
        pytest.skip("kotobacore not installed (run `pip install -e .`)")
    assert kotobacore.__version__ == installed
