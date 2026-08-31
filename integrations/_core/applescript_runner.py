"""Wrapper commun pour l'exécution d'AppleScript depuis Python.
Uniformise le format de retour et la gestion d'erreur pour toutes
les intégrations macOS (Calendrier, Finder, Rappels, Notes, etc.).

SÉCURITÉ (review 31/08/2026, point 1 — critique) :
toute valeur d'origine utilisateur insérée dans un script AppleScript
ou JXA DOIT passer par _as_literal(). Jamais d'interpolation directe."""
import subprocess

MAX_LITERAL_LEN = 500


def _as_literal(value) -> str:
    """Transforme une valeur en littéral AppleScript/JXA sûr.

    Règles appliquées dans l'ordre :
      1. caractères de contrôle remplacés par des espaces
      2. longueur plafonnée à MAX_LITERAL_LEN
      3. échappement de \\ puis " dans CET ordre
      4. résultat entouré de guillemets doubles

    Usage : f'set x to {_as_literal(entree_utilisateur)}'
    """
    s = "" if value is None else str(value)
    s = "".join(c if c.isprintable() else " " for c in s)
    s = " ".join(s.split())
    s = s[:MAX_LITERAL_LEN]
    s = s.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{s}"'


def run_applescript(script, timeout=10):
    """Exécute un script AppleScript et retourne la sortie stdout.

    Args:
        script: le code AppleScript à exécuter
        timeout: délai max en secondes (défaut 10)
    Returns:
        str: la sortie stdout du script (strip)
    Raises:
        RuntimeError: si le script échoue (returncode != 0)
    """
    r = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        timeout=timeout
    )
    if r.returncode != 0:
        raise RuntimeError(f"AppleScript: {r.stderr.strip()}")
    return r.stdout.strip()
