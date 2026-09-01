"""Client bas niveau box TaHoma (API locale Overkiz).
Ne connaît que des deviceURL et des commandes brutes.
Stdlib uniquement : zéro dépendance externe, 100 % local."""
import json
import ssl
import urllib.request
import urllib.error
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "tahoma.yaml"


class TaHomaError(Exception):
    pass


class TaHomaClient:
    def __init__(self, config_path=CONFIG_PATH):
        cfg = {}
        for line in open(config_path, encoding="utf-8"):
            line = line.strip()
            if not line or line.startswith("#") or ":" not in line:
                continue
            key, value = line.split(":", 1)
            cfg[key.strip()] = value.strip().strip('"')
        self.host = cfg["host"]
        self.port = int(cfg.get("port", "8443"))
        self.token = cfg["token"]
        self._ctx = ssl._create_unverified_context()
        self._base = (f"https://{self.host}:{self.port}"
                      "/enduser-mobile-web/1/enduserAPI")

    def _request(self, method, path, payload=None):
        headers = {"Authorization": f"Bearer {self.token}"}
        data = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(payload).encode()
        req = urllib.request.Request(f"{self._base}/{path}", data=data,
                                     headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=10, context=self._ctx) as resp:
                body = resp.read().decode()
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as e:
            raise TaHomaError(f"HTTP {e.code} : {e.read().decode()[:200]}") from e

    def get_devices(self):
        """Tous les équipements avec leurs états (GET /setup)."""
        return self._request("GET", "setup").get("devices", [])

    def execute(self, device_url, command, parameters=None):
        """Envoie une commande brute à un équipement (POST /exec/apply)."""
        payload = {
            "label": f"MJ {command}",
            "actions": [{
                "deviceURL": device_url,
                "commands": [{"name": command,
                              "parameters": parameters or []}],
            }],
        }
        return self._request("POST", "exec/apply", payload)
