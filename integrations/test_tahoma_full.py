"""Exploration complète de l'API TaHoma pour trouver où se cache la closure."""
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


def req(path):
    r = urllib.request.Request(
        f"{BASE}/{path}",
        headers={"Authorization": f"Bearer {TOKEN}"})
    try:
        with urllib.request.urlopen(r, timeout=10, context=ctx) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


# 1. Récupérer setup complet
print("=" * 60)
print("1. GET /setup")
print("=" * 60)
status, body = req("setup")
if status != 200:
    sys.exit(f"Erreur : HTTP {status}")

setup = json.loads(body)
print(f"Clés : {list(setup.keys())}\n")

# Trouver un volet
shutter = None
for d in setup.get("devices", []):
    if "RollerShutter" in d.get("controllableName", ""):
        shutter = d
        break

if not shutter:
    sys.exit("Aucun volet trouvé")

print(f"Volet sélectionné : {shutter['label']}")
print(f"deviceURL : {shutter['deviceURL']}\n")

# 2. Explorer la structure du volet dans setup
print("=" * 60)
print("2. Structure du volet dans /setup")
print("=" * 60)
print(f"Clés du volet : {list(shutter.keys())}\n")

if "attributes" in shutter:
    print(f"ATTRIBUTES ({len(shutter['attributes'])} éléments) :")
    for attr in shutter["attributes"][:10]:
        name = attr.get("name", "?")
        value = attr.get("value", "?")
        val_str = str(value)
        if len(val_str) > 80:
            val_str = val_str[:80] + "..."
        print(f"  - {name}: {val_str}")

if "states" in shutter:
    print(f"\nSTATES ({len(shutter['states'])} éléments) :")
    for state in shutter["states"]:
        name = state.get("name", "?")
        value = state.get("value", "?")
        print(f"  - {name}: {value}")

# 3. Tester l'endpoint spécifique au device
print("\n" + "=" * 60)
print(f"3. GET /setup/devices/{{deviceURL}}")
print("=" * 60)
device_url = shutter["deviceURL"]
status, body = req(f"setup/devices/{device_url}")
print(f"HTTP {status}")

if status == 200:
    device_data = json.loads(body)
    print(f"Clés : {list(device_data.keys())}\n")
    
    if "states" in device_data and len(device_data["states"]) > 0:
        print(f"STATES ({len(device_data['states'])} éléments) :")
        for state in device_data["states"]:
            name = state.get("name", "?")
            value = state.get("value", "?")
            print(f"  - {name}: {value}")
    else:
        print("Pas de states dans cette réponse")
else:
    print(f"Réponse : {body[:200]}")

# 4. Tester tous les volets pour voir si certains ont des states
print("\n" + "=" * 60)
print("4. Test de tous les volets")
print("=" * 60)
for d in setup.get("devices", []):
    if "RollerShutter" in d.get("controllableName", ""):
        label = d.get("label", "?")
        has_states = "states" in d and len(d.get("states", [])) > 0
        has_attrs = "attributes" in d and len(d.get("attributes", [])) > 0
        
        closure = None
        if has_states:
            for s in d["states"]:
                if s.get("name") == "closure":
                    closure = s.get("value")
        
        print(f"  - {label}: states={has_states}, attrs={has_attrs}, closure={closure}")
