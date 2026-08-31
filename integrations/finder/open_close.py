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


def open_file(path=None, filename=None, **_):
    """Ouvre un fichier ou dossier via la commande open."""
    target = path or filename
    if not target:
        return "Quel fichier ouvrir ?"
    p = Path(target).expanduser()
    if not p.exists():
        hit = _resolve_by_name(target)
        if hit is None:
            return f"Je ne trouve pas {target}."
        p = hit
    ext = p.suffix.lower()
    if ext in DESTRUCTIVE_EXTENSIONS:
        if not (ext == ".app" and "/Applications" in str(p)):
            return f"Je n'ouvre pas les fichiers {ext} par sécurité."
    abs_path = str(p.resolve())
    for forbidden in _ALLOWED_PATHS["never_touch"]:
        if abs_path == forbidden or abs_path.startswith(forbidden + "/"):
            return f"Je ne peux pas ouvrir {p.name} (chemin protégé)."
    try:
        subprocess.run(["open", str(p)], timeout=5)
        return f"Ouvert : {p.name}"
    except Exception as e:
        return f"Erreur : {e}"


def open_folder(folder_name=None, **_):
    """Ouvre un dossier par nom (alias français puis Spotlight)."""
    if not folder_name:
        return "Quel dossier veux-tu ouvrir ?"
    key = folder_name.lower().strip()
    path = FOLDER_ALIASES.get(key)
    if path is None:
        hits = _mdfind(f'kMDItemDisplayName == "{folder_name}"cd '
                       f'&& kMDItemContentType == "public.folder"',
                       onlyin=Path.home())
        path = hits[0] if hits else None
    if path is None:
        return f"Je ne trouve pas le dossier {folder_name}."
    return open_file(path=path)


def locate_file(filename=None, **_):
    """Révèle un fichier dans le Finder (open -R) : fenêtre visible, fichier sélectionné."""
    if not filename:
        return "Quel fichier veux-tu voir dans le Finder ?"
    p = Path(filename).expanduser()
    if not p.exists():
        hit = _resolve_by_name(filename)
        if hit is None:
            return f"Je ne trouve pas {filename}."
        p = hit
    try:
        subprocess.run(["open", "-R", str(p)], timeout=5)
        return f"Voilà : {p.name} est montré dans le Finder."
    except Exception as e:
        return f"Erreur : {e}"


def _running_apps(names):
    """Filtre les apps réellement en cours via ps (aucune permission requise)."""
    r = subprocess.run(["ps", "-ax", "-o", "command="],
                       capture_output=True, text=True)
    return [n for n in names if f"{n}.app" in r.stdout]


def close_file(filename=None, **_):
    """Ferme un document ouvert dans les apps aperçu/bureautique.
    Tell LITTÉRAL par app (même forme que le test manuel qui fonctionnait :
    le tell par variable laissait close muet). Ne cible que les apps en cours
    (ps) : jamais de dialogue bloquant macOS."""
    if not filename:
        return "Quel fichier fermer ?"
    target = filename
    if not Path(target).expanduser().exists():
        hit = _resolve_by_name(target)
        if hit is not None:
            target = hit.name
    apps = ["Preview", "TextEdit", "Pages", "Keynote", "Numbers",
            "Microsoft Word", "Microsoft Excel", "Microsoft PowerPoint"]
    for app in _running_apps(apps):
        script = f"""
        tell application {_as_literal(app)}
            if (count of (every document whose name is {_as_literal(target)})) > 0 then
                close (every document whose name is {_as_literal(target)})
                return "ok:" & {_as_literal(app)}
            end if
        end tell
        return "none"
        """
        try:
            out = run_applescript(script, timeout=10)
        except RuntimeError as e:
            return f"Je n'ai pas pu fermer {target} : {e}"
        if out.startswith("ok:"):
            return f"Fermé : {target} (dans {app})."
    return f"{target} n'est ouvert dans aucune application que je gère."
