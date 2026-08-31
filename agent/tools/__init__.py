"""Registre des outils OLYMPE.
Chaque dossier est un domaine, chaque fichier (hors _*.py) expose
un dict TOOL et une fonction run(args). Découverte récursive."""
import importlib
from pathlib import Path

# L'import de _helpers ajoute la racine du projet à sys.path,
# nécessaire aux imports différés (integrations.*, agent.memory).
from agent.tools import _helpers  # noqa: F401

_ROOT = Path(__file__).parent
_REGISTRY = {}

def _discover():
    for f in sorted(_ROOT.rglob("*.py")):
        if f.name.startswith("_"):
            continue
        rel = f.relative_to(_ROOT)
        modpath = ".".join(rel.with_suffix("").parts)
        mod = importlib.import_module(f".{modpath}", package=__package__)
        _REGISTRY[mod.TOOL["name"]] = {"schema": mod.TOOL, "run": mod.run}

_discover()

def get_tool_schema(name):
    return _REGISTRY[name]["schema"]

def run_tool(name, args):
    return _REGISTRY[name]["run"](args or {})

def list_tools():
    return [e["schema"] for e in _REGISTRY.values()]
