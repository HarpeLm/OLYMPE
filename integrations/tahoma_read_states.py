"""Lecture de l'état de tous les volets TaHoma.
Stdlib uniquement. N'envoie AUCUNE commande."""
import json, re, ssl, sys
import urllib.request, urllib.error

cfg = {}
for line in open("config/tahoma.yaml", encoding="utf-8"):
    m = re.match(r"^(\w+):\s*(.+)$", line.strip())
    if m:
        cfg[m.group(1)] = m.group(2).strip().strip('"')

HOST, TOKEN = cfg["host"], cfg["token"]
ctx = ssl._create_unverified_context()
BASE = f"https://{HOST}:8443/enduser-mobile-web/1/enduserAPI"


def get_all_devices():
    """Récupère tous les équipements depuis /setup."""
    req = urllib.request.Request(
        f"{BASE}/setup",
        headers={"Authorization": f"Bearer {TOKEN}"})
    try:
        with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
            data = json.loads(r.read().decode())
            return data.get("devices", [])
    except urllib.error.HTTPError as e:
        sys.exit(f"❌ HTTP {e.code}")


def get_shutter_state(device):
    """Extrait l'état d'un volet depuis ses states."""
    states = {s["name"]: s.get("value") for s in device.get("states", [])}
    return {
        "label": device.get("label"),
        "deviceURL": device.get("deviceURL"),
        "closure": states.get("core:ClosureState"),
        "open_closed": states.get("core:OpenClosedState"),
        "target": states.get("core:TargetClosureState"),
        "moving": states.get("core:MovingState"),
        "memorized_pos": states.get("core:Memorized1PositionState"),
    }


print("=== État des volets (lecture seule) ===\n")
devices = get_all_devices()
shutters = [d for d in devices if "RollerShutter" in d.get("controllableName", "")]

for s in shutters:
    state = get_shutter_state(s)
    closure = state["closure"]
    open_closed = state["open_closed"]
    moving = state["moving"]
    
    # Interprétation humaine
    if closure == 0:
        pos_text = "complètement ouvert"
    elif closure == 100:
        pos_text = "complètement fermé"
    elif closure is not None:
        pos_text = f"ouvert à {100 - closure}%"
    else:
        pos_text = "position inconnue"
    
    moving_text = "en mouvement" if moving else "arrêté"
    
    print(f"{state['label']:30s} | {pos_text:20s} | {moving_text}")
    print(f"  closure={closure}, open_closed={open_closed}, target={state['target']}, mémorisée={state['memorized_pos']}")
    print()
