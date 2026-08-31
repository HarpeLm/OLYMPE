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


def compress_file(filename=None, destination=None, **_):
    """REVERSIBLE : zippe via ditto (natif macOS)."""
    if not filename:
        return "Compresser quoi ?"
    src = _find(filename)
    if src is None:
        return f"Je ne trouve pas {filename}."
    ok, reason = is_readable(str(src))
    if not ok:
        return f"Je ne peux pas lire {src.name} : {reason}"
    dst = (_dst_from(destination) if destination
           else src.with_name(src.name + ".zip"))
    if dst.exists() and dst.is_dir():
        dst = dst / (src.name + ".zip")
    ok2, r2 = is_allowed("file", str(dst))
    if not ok2:
        return f"Je ne peux pas écrire ici : {r2}"
    r = subprocess.run(["ditto", "-c", "-k", "--sequesterRsrc",
                        str(src), str(dst)],
                       capture_output=True, text=True, timeout=60)
    if r.returncode == 0:
        return f"Compressé : {dst.name}"
    return f"Erreur de compression : {r.stderr.strip()}"


def extract_archive(filename=None, destination=None, **_):
    """REVERSIBLE : dézippe via ditto/tar (bsdtar natif bloque les chemins absolus)."""
    if not filename:
        return "Décompresser quoi ?"
    src = _find(filename)
    if src is None:
        return f"Je ne trouve pas {filename}."
    ok, reason = is_readable(str(src))
    if not ok:
        return f"Je ne peux pas lire {src.name} : {reason}"
    dst = (_dst_from(destination) if destination
           else src.parent / src.stem)
    ok2, r2 = is_allowed("folder", str(dst))
    if not ok2:
        return f"Je ne peux pas extraire ici : {r2}"
    dst.mkdir(parents=True, exist_ok=True)
    if src.suffix.lower() == ".zip":
        cmd = ["ditto", "-x", "-k", str(src), str(dst)]
    elif src.suffix.lower() in (".tar", ".tgz", ".gz", ".bz2", ".xz"):
        cmd = ["tar", "-xf", str(src), "-C", str(dst)]
    else:
        return f"Format non géré : {src.suffix}"
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if r.returncode == 0:
        return f"Extrait dans : {dst}"
    return f"Erreur d'extraction : {r.stderr.strip()}"


