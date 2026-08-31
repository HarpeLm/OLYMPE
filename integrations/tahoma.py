"""Couche métier TaHoma : les volets Somfy en langage humain.
Niveau de risque : REVERSIBLE (open/close/stop/position) — cohérent avec
le pattern de permissions du Palier 8, pas de confirmation vocale requise."""
try:
    from integrations._core.tahoma_client import TaHomaClient
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from integrations._core.tahoma_client import TaHomaClient

_CLIENT = None


def _client():
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = TaHomaClient()
    return _CLIENT


def _states_of(device):
    return {s["name"]: s.get("value") for s in device.get("states", [])}


def list_shutters():
    """Liste les volets avec leur état actuel."""
    out = []
    for d in _client().get_devices():
        if "RollerShutter" in d.get("controllableName", ""):
            st = _states_of(d)
            out.append({
                "name": d.get("label"),
                "device_url": d.get("deviceURL"),
                "closure": st.get("core:ClosureState"),
                "target": st.get("core:TargetClosureState"),
                "open_closed": st.get("core:OpenClosedState"),
                "moving": st.get("core:MovingState"),
            })
    return out


def _resolve(name):
    """Résout un nom humain -> volet : exact, puis casse, puis sous-chaîne."""
    shutters = list_shutters()
    for s in shutters:
        if s["name"] == name:
            return s
    low = name.strip().lower()
    for s in shutters:
        if s["name"].lower() == low:
            return s
    for s in shutters:
        if low in s["name"].lower():
            return s
    known = ", ".join(s["name"] for s in shutters)
    raise ValueError(f"Volet introuvable : {name!r}. Volets connus : {known}")


def get_shutter_state(name):
    """État actuel d'un volet par son nom."""
    return _resolve(name)


def open_shutter(name):
    """Ouvre complètement un volet."""
    s = _resolve(name)
    _client().execute(s["device_url"], "open")
    return {"success": True, "message": f"Ouverture de « {s['name']} » lancée"}


def close_shutter(name):
    """Ferme complètement un volet."""
    s = _resolve(name)
    _client().execute(s["device_url"], "close")
    return {"success": True, "message": f"Fermeture de « {s['name']} » lancée"}


def stop_shutter(name):
    """Arrête un volet en mouvement."""
    s = _resolve(name)
    _client().execute(s["device_url"], "stop")
    return {"success": True, "message": f"Arrêt de « {s['name']} »"}


def set_shutter_position(name, percent_open):
    """Positionne un volet. percent_open : 0 = fermé, 100 = ouvert.
    Traduit en closure Overkiz (sémantique inverse)."""
    s = _resolve(name)
    closure = max(0, min(100, 100 - int(percent_open)))
    _client().execute(s["device_url"], "setClosure", [closure])
    return {"success": True,
            "message": f"« {s['name']} » en route vers {percent_open}% ouvert"}


if __name__ == "__main__":
    for s in list_shutters():
        c = s["closure"]
        pos = ("ouvert" if c == 0 else "fermé" if c == 100
               else f"à {100 - c}%")
        print(f"  - {s['name']:25s} {pos}")
