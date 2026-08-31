"""Test manuel : ouvre puis referme UN volet avec confirmation explicite.
N'exécute AUCUNE action sans ton accord."""
import json, re, ssl, sys, time
import urllib.request, urllib.error

cfg = {}
for line in open("config/tahoma.yaml", encoding="utf-8"):
    m = re.match(r"^(\w+):\s*(.+)$", line.strip())
    if m:
        cfg[m.group(1)] = m.group(2).strip().strip('"')

HOST, TOKEN = cfg["host"], cfg["token"]
ctx = ssl._create_unverified_context()
BASE = f"https://{HOST}:8443/enduser-mobile-web/1/enduserAPI"


def req(method, path, payload=None):
    headers = {"Authorization": f"Bearer {TOKEN}"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode()
    r = urllib.request.Request(f"{BASE}/{path}", data=data, 
                               headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=10, context=ctx) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


# Récupérer tous les volets
status, body = req("GET", "setup")
devices = json.loads(body).get("devices", [])
shutters = [d for d in devices if "RollerShutter" in d.get("controllableName", "")]

print("=== Volets disponibles ===")
for i, s in enumerate(shutters, 1):
    closure = None
    for state in s.get("states", []):
        if state.get("name") == "core:ClosureState":
            closure = state.get("value")
            break
    pos = "ouvert" if closure == 0 else ("fermé" if closure == 100 else f"à {100-closure}%")
    print(f"  {i}. {s['label']} ({pos})")

choice = input("\nNuméro du volet à tester (ou 'q' pour quitter) : ").strip()
if choice.lower() == 'q':
    sys.exit(0)

try:
    idx = int(choice) - 1
    target = shutters[idx]
except (ValueError, IndexError):
    sys.exit("❌ Choix invalide")

print(f"\nTest sur : {target['label']}")
print("Ce script va :")
print("  1. OUVRIR complètement le volet")
print("  2. Attendre 8 secondes")
print("  3. REFERMER complètement le volet")
print("  4. Vérifier l'état final")

confirm = input("\nTape 'oui' pour continuer : ").strip().lower()
if confirm != 'oui':
    print("Annulé.")
    sys.exit(0)

device_url = target["deviceURL"]

def execute_action(cmd_name):
    """Envoie une commande à un volet."""
    payload = {
        "label": f"OLYMPE test {cmd_name}",
        "actions": [{
            "deviceURL": device_url,
            "commands": [{"name": cmd_name, "parameters": []}]
        }]
    }
    return req("POST", "exec/apply", payload)


print("\n1. OUVERTURE...")
status, body = execute_action("open")
print(f"   HTTP {status}")
if status != 200:
    print(f"   Erreur : {body[:200]}")
    sys.exit(1)

print("   Attente 8s...")
time.sleep(8)

print("\n2. FERMETURE...")
status, body = execute_action("close")
print(f"   HTTP {status}")
if status != 200:
    print(f"   Erreur : {body[:200]}")
    sys.exit(1)

print("   Attente 8s...")
time.sleep(8)

# Vérifier l'état final
print("\n3. Vérification état final...")
status, body = req("GET", "setup")
devices = json.loads(body).get("devices", [])
updated = next((d for d in devices if d["deviceURL"] == device_url), None)

if updated:
    for state in updated.get("states", []):
        if state.get("name") == "core:ClosureState":
            closure = state.get("value")
            print(f"   Position finale : closure={closure} (attendu : 100)")
            if closure == 100:
                print("   ✅ Le volet est bien refermé")
            else:
                print("   ⚠️  Le volet n'est pas à la position attendue")
            break

print("\n✅ Test terminé")
