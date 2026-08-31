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


def search_file(query=None, filename=None, extension=None,
                folder=None, location=None, **_):
    """Recherche un fichier par nom/extension via Spotlight."""
    q = query
    if filename and not re.search(r"\bfichiers?\b", filename):
        q = f'kMDItemDisplayName == "*{filename}*"cd'
    if extension:
        ext = str(extension).lstrip(".")
        ext_q = f'kMDItemFSName == "*.{ext}"'
        q = f"{ext_q} && {q}" if q else ext_q
    if not q:
        return "Tu veux chercher quoi ?"
    if folder or location:
        results = _mdfind(q, onlyin=folder or location)
    else:
        roots = sorted({str(Path(p2).expanduser()) for p2 in
                        (_ALLOWED_PATHS["readable"] + _ALLOWED_PATHS["writable"])})
        results = []
        for root in roots:
            if Path(root).exists():
                results += _mdfind(q, onlyin=root)
        if not results:
            results = [r for r in _mdfind(q)
                       if not r.startswith(("/System", "/Library", "/private", "/usr"))]
    if not results:
        label = filename or query or extension
        return f"Aucun fichier trouvé pour '{label}'."
    if len(results) == 1:
        return f"Un seul résultat : {results[0]}"
    shown = results[:5]
    response = f"{len(results)} fichiers trouvés, les {len(shown)} premiers :\n"
    response += "\n".join(f"- {r}" for r in shown)
    if len(results) > 5:
        response += f"\n... et {len(results) - 5} autres."
    return response


def search_content(query=None, **_):
    """Cherche dans le contenu des fichiers (Spotlight indexe le contenu)."""
    if not query:
        return "Tu veux chercher quel texte ?"
    return search_file(query=query)


def list_folder(path=None, **_):
    """Liste le contenu d'un dossier via AppleScript (lecture seule)."""
    if not path:
        return "Quel dossier veux-tu lister ?"
    p = Path(path).expanduser().resolve()
    abs_path = str(p)
    for forbidden in _ALLOWED_PATHS["never_touch"]:
        if abs_path == forbidden or abs_path.startswith(forbidden + "/"):
            return f"Je ne peux pas accéder à {path} (chemin protégé)."
    if not p.exists():
        return f"Le dossier {path} n'existe pas."
    if not p.is_dir():
        return f"{path} n'est pas un dossier."
    script = f'''
    tell application "Finder"
        set folderItems to name of every item of folder (POSIX file {_as_literal(abs_path)} as alias)
        set output to ""
        repeat with i from 1 to count of folderItems
            if i > 10 then
                set output to output & "... et " & ((count of folderItems) - 10) & " autres."
                exit repeat
            end if
            set output to output & item i of folderItems & "\\n"
        end repeat
        return output
    end tell
    '''
    try:
        result = run_applescript(script)
        if not result.strip():
            return f"{path} est vide."
        return f"Contenu de {path} :\n{result}"
    except RuntimeError as e:
        return f"Erreur de lecture : {e}"


def list_recent_files(hours=None, **_):
    """Liste les fichiers modifiés récemment dans les dossiers autorisés."""
    try:
        h = int(hours) if hours else 24
    except (TypeError, ValueError):
        h = 24
    days = max(1, round(h / 24))
    roots = sorted({str(Path(p).expanduser()) for p in
                    (_ALLOWED_PATHS["readable"] + _ALLOWED_PATHS["writable"])})
    results = []
    for root in roots:
        if Path(root).exists():
            results += _mdfind(f"kMDItemFSContentChangeDate >= $time.today(-{days})",
                               onlyin=root)
    if not results:
        return f"Aucun fichier modifié dans les dernières {h} heures."
    return f"Fichiers récents :\n" + "\n".join(f"- {r}" for r in results[:5])
