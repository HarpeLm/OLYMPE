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
import re
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


def _resolve_by_name(target):
    """Résout un nom vers un chemin : exact d'abord, puis wildcard insensible à la casse."""
    hits = _mdfind(f'kMDItemDisplayName == "{target}"cd')
    if not hits:
        hits = _mdfind(f'kMDItemDisplayName == "*{target}*"cd')
    return Path(hits[0]) if hits else None


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


def delete_file(filename=None, path=None, **_):
    """Déplace un fichier vers la corbeille (jamais de suppression définitive)."""
    target = path or filename
    if not target:
        return "Quel fichier veux-tu supprimer ?"
    p = Path(target).expanduser()
    if not p.exists():
        roots = sorted({str(Path(r).expanduser()) for r in
                        (_ALLOWED_PATHS["readable"] + _ALLOWED_PATHS["writable"])})
        hit = None
        for root in roots:
            cand = Path(root) / target
            if cand.exists():
                hit = cand
                break
        if hit is None:
            hit = _resolve_by_name(target)
        if hit is None:
            return f"Je ne trouve pas {target}."
        p = hit
    allowed, reason = is_allowed("file", str(p))
    if not allowed:
        return f"Je ne peux pas supprimer {p.name} : {reason}"
    script = f"""
    tell application "Finder"
        delete (POSIX file "{str(p.resolve())}" as alias)
    end tell
    """
    try:
        run_applescript(script)
        return f"{p.name} est dans la corbeille."
    except RuntimeError as e:
        return f"Erreur : {e}"


def empty_trash(**_):
    """Vide la corbeille (DESTRUCTIVE, confirmation vocale obligatoire)."""
    try:
        run_applescript('tell application "Finder" to empty trash')
        return "Corbeille vidée."
    except RuntimeError as e:
        return f"Erreur : {e}"


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
        tell application "{app}"
            if (count of (every document whose name is "{target}")) > 0 then
                close (every document whose name is "{target}")
                return "ok:{app}"
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


if __name__ == "__main__":
    print("=== Test finder.py (lecture seule) ===\n")
    print("open_folder('téléchargements') :", open_folder("téléchargements"))
    print("\nlist_recent_files(24) :", list_recent_files(24))
    print("\nsearch_file(extension='pdf') :", search_file(extension="pdf"))
