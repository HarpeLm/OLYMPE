import os
import plistlib
import re
import shutil
import subprocess
from pathlib import Path

from integrations._core.applescript_runner import run_applescript, _as_literal
from integrations._core.permissions import is_allowed, is_readable, _ALLOWED_PATHS
from integrations.finder._helpers import (
    SAFE_EXTENSIONS, DESTRUCTIVE_EXTENSIONS, FOLDER_ALIASES,
    _mdfind, _resolve_by_name, _find, _dst_from,
)


def check_file_exists(filename=None, **_):
    """SAFE : dit si un fichier existe et où."""
    if not filename:
        return "Quel fichier ?"
    hit = _find(filename)
    if hit is not None:
        return f"Oui, {hit.name} existe : {hit}"
    return f"Non, je ne trouve pas {filename}."


def get_file_info(filename=None, **_):
    """SAFE : taille, type, date, chemin."""
    from datetime import datetime
    if not filename:
        return "Quel fichier ?"
    p = _find(filename)
    if p is None:
        return f"Je ne trouve pas {filename}."
    st = p.stat()
    size, unit = float(st.st_size), "o"
    for u in ("Ko", "Mo", "Go"):
        if size >= 1024:
            size /= 1024
            unit = u
    mod = datetime.fromtimestamp(st.st_mtime).strftime("%d/%m/%Y à %H:%M")
    kind = "dossier" if p.is_dir() else f"fichier {p.suffix or ''}".strip()
    return f"{p.name} : {kind}, {size:.1f} {unit}, modifié le {mod}, chemin {p}"
