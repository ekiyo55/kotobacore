"""Configuration file (v1.1): user / domain dictionaries by listing them in YAML.

A config file lets an application pick up its dictionaries without code changes::

    # kotobacore.yaml
    dictionaries:
      - builtin:dd              # bundled domain dictionary (M&A due diligence)
      - ./dict/my_terms.csv     # entity.csv format (only `surface` is required)
      - ./dict/legal/           # a folder of CSVs in the bundled formats

Earlier entries take precedence over later ones, and all of them over the
bundled dictionaries. Relative paths resolve against the config file's folder.

Where the config is looked up (first hit wins):

1. ``Analyzer(config_path=...)`` / CLI ``--config``
2. environment variable ``KOTOBACORE_CONFIG`` (``none`` disables lookup)
3. ``./kotobacore.yaml`` in the current working directory
4. ``~/.config/kotobacore/config.yaml``

``Analyzer(use_config=False)`` ignores config files altogether.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from kotobacore.errors import DictionaryLoadError

CONFIG_ENV = "KOTOBACORE_CONFIG"
CONFIG_FILENAME = "kotobacore.yaml"
_USER_CONFIG = Path.home() / ".config" / "kotobacore" / "config.yaml"
_DOMAINS_DIR = Path(__file__).parent / "resources" / "dict" / "domains"
BUILTIN_PREFIX = "builtin:"


@dataclass
class KotobaConfig:
    path: Path | None = None
    dictionaries: list[str] = field(default_factory=list)  # resolved: absolute paths


def domain_dictionaries() -> dict[str, dict]:
    """Bundled domain dictionaries: {name: {file, version, rows, description}}."""
    manifest = _DOMAINS_DIR / "domains.json"
    if not manifest.exists():
        return {}
    return json.loads(manifest.read_text(encoding="utf-8"))["domains"]


def resolve_dictionary(entry: str, base: Path | None = None) -> str:
    """``builtin:NAME`` → bundled file; a relative path → against ``base``."""
    entry = str(entry).strip()
    if entry.startswith(BUILTIN_PREFIX):
        name = entry[len(BUILTIN_PREFIX):]
        domains = domain_dictionaries()
        if name not in domains:
            raise DictionaryLoadError(
                f"Unknown built-in dictionary {name!r} (available: {', '.join(sorted(domains)) or 'none'})"
            )
        return str(_DOMAINS_DIR / domains[name]["file"])
    p = Path(os.path.expanduser(entry))
    if not p.is_absolute() and base is not None:
        p = base / p
    return str(p)


def find_config(explicit: str | os.PathLike | None = None) -> Path | None:
    if explicit:
        p = Path(explicit)
        if not p.exists():
            raise DictionaryLoadError(f"Config file not found: {p}")
        return p
    env = os.environ.get(CONFIG_ENV)
    if env is not None:
        if env.strip().lower() in ("", "none", "off", "0"):
            return None
        p = Path(env)
        if not p.exists():
            raise DictionaryLoadError(f"{CONFIG_ENV} points to a missing file: {p}")
        return p
    for p in (Path.cwd() / CONFIG_FILENAME, _USER_CONFIG):
        if p.exists():
            return p
    return None


def load_config(explicit: str | os.PathLike | None = None) -> KotobaConfig:
    path = find_config(explicit)
    if path is None:
        return KotobaConfig()
    import yaml

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise DictionaryLoadError(f"Invalid YAML in {path}: {e}") from e
    if not isinstance(data, dict):
        raise DictionaryLoadError(f"{path}: the config must be a mapping (e.g. `dictionaries: [...]`)")
    entries = data.get("dictionaries") or []
    if isinstance(entries, str):
        entries = [entries]
    if not isinstance(entries, list):
        raise DictionaryLoadError(f"{path}: `dictionaries` must be a list")
    base = path.parent
    return KotobaConfig(path=path, dictionaries=[resolve_dictionary(e, base) for e in entries])
