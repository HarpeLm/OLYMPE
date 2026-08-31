"""Diagnostic connexion locale TaHoma (V2/Switch) — dev only.
Lit host+token depuis config/tahoma.yaml (gitignoré), liste les équipements.
Lecture seule : n'envoie AUCUNE commande aux volets.
Stdlib uniquement : fonctionne avec python3, sans venv."""
import json
import re
import ssl
import sys
import urllib.request
import urllib.error

cfg = {}
for line in open("config/tahoma.yaml", encoding="utf-8"):
    m = re.match(r"^(\w+):\s*(.+)$", line.strip())
    if m:
        cfg[m.group(1)] = m.group(2).strip().strip('"')

HOST = cfg.get("host", "")
TOKEN = cfg.get("token", "")

if not TOKEN or "COLLE" in TOKEN:
    sys.exit("❌ Remplis d'abord host et token dans config/tahoma.yaml")

ctx = ssl._create_unverified_context()
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


def get(base, path):
    url = f"https://{HOST}:8443/{base}{path}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


devices = None
body = ""
for base in ("enduser-mobile-web/1/enduserAPI/",
             "enduser-mobile-web/enduserAPI/"):
    status, body = get(base, "setup/devices")
    print(f"GET {base}setup/devices -> HTTP {status}")
    if status == 200:
        devices = json.loads(body)
        break

if devices is None:
    sys.exit(f"❌ Réponse : {body[:200]}\n   401 = mauvais token | 403 = mode dev non activé")

print(f"\n✅ {len(devices)} équipement(s) trouvé(s) :")
for d in devices:
    print(f"  - {d.get('label', '?')} | {d.get('controllableName', '?')} | {d.get('deviceURL', '?')}")
