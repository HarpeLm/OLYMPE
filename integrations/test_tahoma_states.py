"""Test des endpoints d'état TaHoma pour trouver où se cache la closure."""
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


# Récupérer un volet au hasard pour tester
status, body = req("setup/devices")
devices = json.loads(body)
shutter = next(d for d in devices if "RollerShutter" in d.get("controllableName", ""))
device_url = shutter["deviceURL"]

print(f"Test sur : {shutter['label']}")
print(f"deviceURL : {device_url}\n")

# Tester plusieurs endpoints
endpoints = [
    f"setup/devices/{device_url}/states",
    "setup",
    "setup/devices/states",
]

for ep in endpoints:
    print(f"GET {ep}")
    status, body = req(ep)
    print(f"  → HTTP {status}")
    if status == 200:
        try:
            data = json.loads(body)
            if isinstance(data, list) and len(data) > 0:
                print(f"  → {len(data)} élément(s)")
                # Chercher closure dans les premiers éléments
                for item in data[:5]:
                    if isinstance(item, dict) and "name" in item:
                        print(f"     - {item.get('name')}: {item.get('value')}")
            elif isinstance(data, dict):
                print(f"  → dict avec {len(data)} clé(s)")
                # Afficher quelques clés
                for k in list(data.keys())[:5]:
                    print(f"     - {k}: {str(data[k])[:100]}")
        except json.JSONDecodeError:
            print(f"  → Réponse non-JSON : {body[:200]}")
    else:
        print(f"  → {body[:150]}")
    print()
