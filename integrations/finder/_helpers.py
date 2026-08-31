"""
Intégrations système OLYMPE — Palier 8a
Finder macOS via AppleScript et mdfind (Spotlight).

Handlers déterministes pour le dispatcher :
- search_file(...)         SAFE (mdfind nom/métadonnées)
- search_content(query)    SAFE (mdfind contenu)
- list_folder(path)        SAFE (AppleScript lecture seule)
- list_recent_files(hours) SAFE (mdfind dates de modification)
- open_file(path/filename) SAFE (commande open, whitelist extensions)
- open_folder(folder_name) SAFE (alias français + mdfind dossier)
- create_folder(path,name) REVERSIBLE (AppleScript + is_allowed)
- move_file(src,dst)       REVERSIBLE (AppleScript + is_allowed)

Les handlers DESTRUCTIVE (delete_file, empty_trash) arriveront avec
le branchement de la confirmation vocale dans le pipeline.
"""
import os
import plistlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from integrations._core.applescript_runner import run_applescript, _as_literal
from integrations._core.permissions import is_allowed, is_readable, _ALLOWED_PATHS


SAFE_EXTENSIONS = {".pdf", ".txt", ".md", ".jpg", ".jpeg", ".png",
                   ".mp3", ".wav", ".mp4", ".docx", ".xlsx", ".pages",
                   ".numbers", ".key"}

DESTRUCTIVE_EXTENSIONS = {".command", ".sh", ".py", ".pkg", ".dmg", ".app"}

FOLDER_ALIASES = {
    "téléchargements": "~/Downloads",
    "telechargements": "~/Downloads",
    "downloads": "~/Downloads",
    "bureau": "~/Desktop",
    "desktop": "~/Desktop",
    "documents": "~/Documents",
    "images": "~/Pictures",
    "photos": "~/Pictures",
    "musique": "~/Music",
    "vidéos": "~/Movies",
    "videos": "~/Movies",
}




def _mdfind(query, onlyin=None, timeout=10):
    cmd = ["mdfind"]
    if onlyin:
        cmd += ["-onlyin", str(Path(onlyin).expanduser())]
    cmd.append(query)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return [l for l in r.stdout.strip().split("\n") if l]


def _resolve_by_name(target):
    """Résout un nom vers un chemin : exact d'abord, puis wildcard insensible à la casse."""
    hits = _mdfind(f'kMDItemDisplayName == "{target}"cd')
    if not hits:
        hits = _mdfind(f'kMDItemDisplayName == "*{target}*"cd')
    return Path(hits[0]) if hits else None


def _find(name):
    """Résout un nom vers un Path existant : chemin direct, puis racines
    autorisées (immédiat, sans index), puis Spotlight en dernier recours."""
    p = Path(name).expanduser()
    if p.exists():
        return p
    roots = sorted({str(Path(r).expanduser()) for r in
                    (_ALLOWED_PATHS["readable"] + _ALLOWED_PATHS["writable"])})
    for root in roots:
        cand = Path(root) / name
        if cand.exists():
            return cand
    return _resolve_by_name(name)


def _dst_from(destination):
    key = str(destination).lower().strip()
    return Path(FOLDER_ALIASES.get(key, destination)).expanduser()
