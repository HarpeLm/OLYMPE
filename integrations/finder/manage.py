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
        make new folder at (POSIX file {_as_literal(parent)} as alias) with properties {{name:{_as_literal(name)}}}
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
        move (POSIX file {_as_literal(src)} as alias) to (POSIX file {_as_literal(dst)} as alias)
    end tell
    '''
    try:
        run_applescript(script)
        return f"Déplacé : {src.name} vers {dst}"
    except RuntimeError as e:
        return f"Erreur de déplacement : {e}"


def rename_file(filename=None, new_name=None, **_):
    """REVERSIBLE : renomme dans le même dossier."""
    if not filename or not new_name:
        return "Renommer quoi, en quoi ?"
    p = _find(filename)
    if p is None:
        return f"Je ne trouve pas {filename}."
    ok, reason = is_allowed("file", str(p))
    if not ok:
        return f"Je ne peux pas renommer {p.name} : {reason}"
    target = p.with_name(new_name)
    if target.exists():
        return f"{new_name} existe déjà."
    ok2, r2 = is_allowed("file", str(target))
    if not ok2:
        return f"Je ne peux pas renommer vers {new_name} : {r2}"
    p.rename(target)
    return f"Renommé : {p.name} en {target.name}"


def copy_file(filename=None, destination=None, **_):
    """REVERSIBLE : copie vers un dossier autorisé."""
    if not filename or not destination:
        return "Copier quoi, et où ?"
    src = _find(filename)
    if src is None:
        return f"Je ne trouve pas {filename}."
    dst = _dst_from(destination)
    if dst.is_dir():
        dst = dst / src.name
    ok1, r1 = is_readable(str(src))
    if not ok1:
        return f"Je ne peux pas lire {src.name} : {r1}"
    ok2, r2 = is_allowed("file", str(dst))
    if not ok2:
        return f"Je ne peux pas copier vers {destination} : {r2}"
    if dst.exists():
        return f"{dst.name} existe déjà (dis 'remplace' pour écraser)."
    shutil.copy2(src, dst)
    return f"Copié : {src.name} vers {dst}"


def duplicate_file(filename=None, **_):
    """REVERSIBLE : crée une copie à côté de l'original."""
    if not filename:
        return "Dupliquer quoi ?"
    src = _find(filename)
    if src is None:
        return f"Je ne trouve pas {filename}."
    ok, reason = is_allowed("file", str(src))
    if not ok:
        return f"Je ne peux pas dupliquer {src.name} : {reason}"
    dst = src.with_name(f"{src.stem} copie{src.suffix}")
    n = 1
    while dst.exists():
        n += 1
        dst = src.with_name(f"{src.stem} copie {n}{src.suffix}")
    shutil.copy2(src, dst)
    return f"Dupliqué : {dst.name}"
