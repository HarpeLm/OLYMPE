"""
Gestion des confirmations vocales pour actions DESTRUCTIVE.

Cycle : action en attente → question posée → réponse attendue → exécution ou annulation.

Utilisé par toute action classée DESTRUCTIVE dans risk_levels.py.
Le pipeline vocal (voice/pipeline.py) doit appeler ask_confirmation()
avant d'exécuter l'action.
"""
import time
from typing import Optional, Callable


# État global de confirmation en cours (une seule à la fois)
_pending_confirmation = {
    "active": False,
    "description": "",
    "callback": None,
    "result": None,
    "executor": None,
    "timestamp": 0,
    "timeout_seconds": 10,
}


def request_confirmation(description: str, result: dict = None, executor: Callable = None, 
                       callback: Callable = None, timeout_seconds: int = 10):
    """
    Demande une confirmation vocale avant d'exécuter une action.
    
    Args:
        description: description de l'action à confirmer
        result: dictionnaire intent/slots/handler à passer à l'executor
        executor: fonction qui prend result et exécute l'action (ex: try_execute_handler)
        callback: (legacy) fonction sans arguments à appeler si confirmé
        timeout_seconds: délai max pour répondre (défaut 10s)
    
    Returns:
        str: message vocal à prononcer (la question)
    
    Usage côté pipeline :
        msg = request_confirmation("supprimer rapport.pdf", result, self.try_execute_handler)
    """
    _pending_confirmation["active"] = True
    _pending_confirmation["description"] = description
    _pending_confirmation["result"] = result
    _pending_confirmation["executor"] = executor
    _pending_confirmation["callback"] = callback
    _pending_confirmation["timestamp"] = time.time()
    _pending_confirmation["timeout_seconds"] = timeout_seconds
    
    question = f"Tu veux vraiment {description} ? Dis oui ou non."
    return question


def handle_response(response: str) -> Optional[str]:
    """
    Traite la réponse vocale à une demande de confirmation.
    
    Args:
        response: texte transcrit de la réponse vocale
    
    Returns:
        str: message de résultat à prononcer, ou None si pas de confirmation en cours
    
    Réponses acceptées :
    - "oui", "ouais", "confirme", "vas-y" → exécute le callback
    - "non", "annule", "stop" → annule
    - timeout (>10s) → annule automatiquement
    """
    if not _pending_confirmation["active"]:
        return None
    
    # Vérifier le timeout
    elapsed = time.time() - _pending_confirmation["timestamp"]
    if elapsed > _pending_confirmation["timeout_seconds"]:
        _reset_confirmation()
        return "Trop tard, j'ai annulé."
    
    response_lower = response.lower().strip()
    
    # Réponses positives
    if any(word in response_lower for word in ["oui", "ouais", "confirme", "vas-y", "oui vas-y"]):
        result = _pending_confirmation["result"]
        executor = _pending_confirmation["executor"]
        callback = _pending_confirmation["callback"]
        _reset_confirmation()
        try:
            if executor and result:
                response = executor(result)
                if response and "Erreur" not in str(response) and "pas" not in str(response):
                    return response
                elif response:
                    return response
            elif callback:
                callback()
            return "C'est fait."
        except Exception as e:
            return f"Erreur : {str(e)}"
    
    # Réponses négatives
    if any(word in response_lower for word in ["non", "annule", "stop", "arrête"]):
        _reset_confirmation()
        return "D'accord, j'ai annulé."
    
    # Réponse non reconnue
    return "Je n'ai pas compris. Dis oui ou non."


def _reset_confirmation():
    """Réinitialise l'état de confirmation."""
    _pending_confirmation["active"] = False
    _pending_confirmation["description"] = ""
    _pending_confirmation["result"] = None
    _pending_confirmation["executor"] = None
    _pending_confirmation["callback"] = None
    _pending_confirmation["timestamp"] = 0


def is_confirmation_pending() -> bool:
    """Vérifie si une confirmation est en attente."""
    if not _pending_confirmation["active"]:
        return False
    
    # Vérifier le timeout
    elapsed = time.time() - _pending_confirmation["timestamp"]
    if elapsed > _pending_confirmation["timeout_seconds"]:
        _reset_confirmation()
        return False
    
    return True


def get_pending_description() -> str:
    """Retourne la description de l'action en attente."""
    return _pending_confirmation["description"] if _pending_confirmation["active"] else ""
