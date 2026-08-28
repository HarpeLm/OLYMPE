"""
Contrôle d'accès aux ressources système pour les intégrations macOS.

Charge les whitelists depuis config/allowed_paths.yaml et expose
is_allowed(resource_type, path) pour vérifier l'autorisation avant
toute action d'écriture ou suppression.

Règle : un chemin hors whitelist est refusé silencieusement côté action,
avec fallback vers une réponse texte expliquant pourquoi.
"""
from pathlib import Path
import yaml


def _load_allowed_paths():
    """Charge config/allowed_paths.yaml et retourne les listes de chemins."""
    config_path = Path(__file__).resolve().parent.parent.parent / "config" / "allowed_paths.yaml"
    
    if not config_path.exists():
        return {"writable": [], "readable": [], "never_touch": []}
    
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    
    # Résoudre les ~ en chemins absolus
    def resolve_paths(path_list):
        return [str(Path(p).expanduser().resolve()) for p in (path_list or [])]
    
    return {
        "writable": resolve_paths(cfg.get("writable", [])),
        "readable": resolve_paths(cfg.get("readable", [])),
        "never_touch": resolve_paths(cfg.get("never_touch", [])),
    }


# Cache global chargé une seule fois
_ALLOWED_PATHS = _load_allowed_paths()


def is_allowed(resource_type, path):
    """
    Vérifie si une action sur une ressource est autorisée.
    
    Args:
        resource_type: "file" ou "folder" (pour l'instant, traité identiquement)
        path: chemin absolu ou relatif à vérifier
    
    Returns:
        tuple: (allowed: bool, reason: str)
    
    Règles :
    - Chemin dans never_touch → refusé
    - Action d'écriture : doit être dans writable
    - Action de lecture : doit être dans readable ou writable
    - Chemin hors whitelist → refusé par défaut
    """
    try:
        abs_path = str(Path(path).expanduser().resolve())
    except Exception:
        return False, f"Chemin invalide : {path}"
    
    # Vérifier never_touch en premier
    for forbidden in _ALLOWED_PATHS["never_touch"]:
        if abs_path == forbidden or abs_path.startswith(forbidden + "/"):
            return False, f"Chemin protégé : {path}"
    
    # Pour l'instant, on considère toute action comme écriture
    # (lecture seule = SAFE, pas besoin de permission)
    for allowed in _ALLOWED_PATHS["writable"]:
        if abs_path == allowed or abs_path.startswith(allowed + "/"):
            return True, "OK"
    
    return False, f"Chemin hors whitelist : {path}"


def reload_permissions():
    """Recharge les permissions depuis le fichier YAML (pour tests)."""
    global _ALLOWED_PATHS
    _ALLOWED_PATHS = _load_allowed_paths()
