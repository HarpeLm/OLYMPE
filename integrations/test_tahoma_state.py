"""Lecture seule : position des volets. N'envoie AUCUNE commande."""
import json, re, ssl, sys
import urllib.request, urllib.error

cfg = {}
for line in open("config/tahoma.yaml", encoding="utf-8"):
    m = re.match(r"^(\w+):\s*(.+)$", line.strip())
    if m:
        cfg[m.group(1)] = m.group(2).strip().strip('"')

HOST, TOKEN = cfg["host"], cfg["token"]
ctx = ssl._create_unverified_context()

req = urllib.request.Request(
    f"https://{HOST}:8443/enduser-mobile-web/1/enduserAPI/setup/devices",
    headers={"Authorization": f"Bearer {TOKEN}"})
try:
    with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
        devices = json.loads(r.read().decode())
except urllib.error.HTTPError as e:
    sys.exit(f"❌ HTTP {e.code}")

def closure_of(d):
    for s in d.get("states", []):
        if s.get("name") == "closure":
            return s.get("value")
    return None

print("=== Volets (lecture seule — rien ne bouge) ===")
for d in devices:
    if "RollerShutter" in d.get("controllableName", ""):
        print(f"  - {d['label']} : closure = {closure_of(d)}")
