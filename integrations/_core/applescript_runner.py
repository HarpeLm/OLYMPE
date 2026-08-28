"""
Wrapper commun pour l'exécution d'AppleScript depuis Python.

Uniformise le format de retour et la gestion d'erreur pour toutes
les intégrations macOS (Calendrier, Finder, Rappels, Notes, etc.).
"""
import subprocess


def run_applescript(script, timeout=10):
    """
    Exécute un script AppleScript et retourne la sortie stdout.
    
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
