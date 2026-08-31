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


TAG_XATTR = "com.apple.metadata:_kMDItemUserTags"
def _read_tags(path):
    """Lit les tags Finder via l'outil natif xattr (plist binaire en hex)."""
    r = subprocess.run(["xattr", "-p", "-x", TAG_XATTR, str(path)],
                       capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        return []
    try:
        tags = plistlib.loads(bytes.fromhex(r.stdout.strip().replace(" ", "")))
        return [str(t).split("\n")[0] for t in tags]
    except Exception:
        return []


def _write_tags(path, tags):
    hexdata = plistlib.dumps(tags, fmt=plistlib.FMT_BINARY).hex()
    subprocess.run(["xattr", "-w", "-x", TAG_XATTR, hexdata, str(path)],
                   capture_output=True, text=True, check=True)


def add_tag(filename=None, tag=None, **_):
    """REVERSIBLE : tag Finder natif via xattr (visible dans Spotlight)."""
    if not filename or not tag:
        return "Quel fichier, et quel tag ?"
    p = _find(filename)
    if p is None:
        return f"Je ne trouve pas {filename}."
    ok, reason = is_allowed("file", str(p))
    if not ok:
        return f"Je ne peux pas taguer {p.name} : {reason}"
    tags = _read_tags(p)
    if tag in tags:
        return f"{p.name} a déjà le tag {tag}."
    tags.append(tag)
    _write_tags(p, tags)
    return f"Tag {tag} ajouté à {p.name}."


def set_favorite(filename=None, **_):
    """REVERSIBLE : favori = tag 'Favoris' (sidebar Finder non scriptable
    nativement — décision documentée, option A)."""
    if not filename:
        return "Quel fichier mettre en favori ?"
    return add_tag(filename=filename, tag="Favoris")
