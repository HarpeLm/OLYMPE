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
        delete (POSIX file {_as_literal(p.resolve())} as alias)
    end tell
    """
    try:
        run_applescript(script)
        return f"{p.name} est dans la corbeille."
    except RuntimeError as e:
        return f"Erreur : {e}"


def empty_trash(confirmed=False, **_):
    """Vide la corbeille (DESTRUCTIVE).

    Garde de sécurité locale : l'exécution est refusée tant que
    `confirmed` n'est pas True. Seul le chemin de confirmation vocale
    (voice/pipeline.py -> _core/confirmation.py) injecte confirmed=True
    dans les slots au moment de l'exécution. Ne jamais appeler cette
    fonction directement avec confirmed=True sans confirmation humaine.
    """
    if confirmed is not True:
        return ("Refusé : vider la corbeille exige une confirmation "
                "vocale (confirmed=True).")
    try:
        run_applescript('tell application "Finder" to empty trash')
        return "Corbeille vidée."
    except RuntimeError as e:
        return f"Erreur : {e}"


def delete_folder(filename=None, folder=None, **_):
    """DESTRUCTIVE : dossier vers la corbeille, jamais définitif."""
    target = folder or filename
    if not target:
        return "Quel dossier supprimer ?"
    p = _find(target)
    if p is None:
        return f"Je ne trouve pas {target}."
    if not p.is_dir():
        return f"{target} n'est pas un dossier."
    ok, reason = is_allowed("folder", str(p))
    if not ok:
        return f"Je ne peux pas supprimer {p.name} : {reason}"
    script = f"""
    ObjC.import('Foundation');
    var fm = $.NSFileManager.defaultManager;
    var url = $.NSURL.fileURLWithPath({_as_literal(p.resolve())});
    var err = Ref();
    var ok = fm.trashItemAtURLResultingItemURLError(url, null, err);
    ok ? 'ok' : ('err:' + err[0].localizedDescription);
    """
    r = subprocess.run(["osascript", "-l", "JavaScript", "-e", script],
                       capture_output=True, text=True, timeout=20)
    out = r.stdout.strip()
    if out == "ok":
        return f"{p.name} est dans la corbeille."
    return f"Erreur corbeille : {out or r.stderr.strip()}"


def overwrite_file(source=None, destination=None, **_):
    """DESTRUCTIVE : remplace un fichier par un autre (confirmation vocale)."""
    if not source or not destination:
        return "Remplacer quoi, par quoi ?"
    src = _find(source)
    if src is None:
        return f"Je ne trouve pas {source}."
    dst = _find(destination)
    if dst is None:
        return f"Je ne trouve pas {destination} (rien à écraser)."
    ok1, r1 = is_readable(str(src))
    if not ok1:
        return f"Je ne peux pas lire {src.name} : {r1}"
    ok2, r2 = is_allowed("file", str(dst))
    if not ok2:
        return f"Je ne peux pas écrire ici : {r2}"
    shutil.copy2(src, dst)
    return f"{dst.name} a été remplacé par {src.name}."
