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
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from integrations._core.applescript_runner import run_applescript
from integrations._core.permissions import is_allowed, _ALLOWED_PATHS


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


def search_file(query=None, filename=None, extension=None,
                folder=None, location=None, **_):
    """Recherche un fichier par nom/extension via Spotlight."""
    q = query or filename
    if extension:
        ext = str(extension).lstrip(".")
        q = f'kMDItemFSName == "*.{ext}"' + (f' && {q}' if q else "")
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
        return f"Aucun fichier trouvé pour '{q}'."
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
        set folderItems to name of every item of folder (POSIX file "{abs_path}" as alias)
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


def open_file(path=None, filename=None, **_):
    """Ouvre un fichier ou dossier via la commande open."""
    target = path or filename
    if not target:
        return "Quel fichier ouvrir ?"
    p = Path(target).expanduser()
    if not p.exists():
        hits = _mdfind(f'kMDItemDisplayName == "{target}"cd')
        if not hits:
            return f"Je ne trouve pas {target}."
        p = Path(hits[0])
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


def create_folder(path=None, name=None, **_):
    """Crée un dossier (REVERSIBLE, passe par is_allowed)."""
    if not path or not name:
        return "Où créer le dossier, et comment l'appeler ?"
    allowed, reason = is_allowed("folder", path)
    if not allowed:
        return f"Je ne peux pas créer ici : {reason}"
    parent = Path(path).expanduser().resolve()
    target = parent / name
    if target.exists():
        return f"{target} existe déjà."
    script = f'''
    tell application "Finder"
        make new folder at (POSIX file "{str(parent)}" as alias) with properties {{name:"{name}"}}
    end tell
    '''
    try:
        run_applescript(script)
        return f"Dossier créé : {target}"
    except RuntimeError as e:
        return f"Erreur de création : {e}"


def move_file(source=None, destination=None, **_):
    """Déplace un fichier (REVERSIBLE, passe par is_allowed)."""
    if not source or not destination:
        return "Quel fichier déplacer, et où ?"
    src = Path(source).expanduser().resolve()
    dst = Path(destination).expanduser().resolve()
    if not src.exists():
        return f"{source} n'existe pas."
    src_ok, src_reason = is_allowed("file", str(src))
    dst_ok, dst_reason = is_allowed("folder", str(dst))
    if not src_ok:
        return f"Je ne peux pas déplacer depuis {source} : {src_reason}"
    if not dst_ok:
        return f"Je ne peux pas déplacer vers {destination} : {dst_reason}"
    script = f'''
    tell application "Finder"
        move (POSIX file "{str(src)}" as alias) to (POSIX file "{str(dst)}" as alias)
    end tell
    '''
    try:
        run_applescript(script)
        return f"Déplacé : {src.name} vers {dst}"
    except RuntimeError as e:
        return f"Erreur de déplacement : {e}"


if __name__ == "__main__":
    print("=== Test finder.py (lecture seule) ===\n")
    print("open_folder('téléchargements') :", open_folder("téléchargements"))
    print("\nlist_recent_files(24) :", list_recent_files(24))
    print("\nsearch_file(extension='pdf') :", search_file(extension="pdf"))
