"""Outil : batterie et espace disque du Mac."""
import re
import shutil
import subprocess

TOOL = {
    "name": "get_system_info",
    "description": "Retourne le niveau de batterie et l'espace disque libre.",
    "inputSchema": {"type": "object", "properties": {}, "required": []}
}

def run(args):
    parts = []
    try:
        out = subprocess.run(["pmset", "-g", "batt"], capture_output=True,
                             text=True, timeout=3).stdout
        m = re.search(r"(\d+)\s*%", out)
        if m:
            state = "en charge" if "AC Power" in out else "sur batterie"
            parts.append(f"batterie {m.group(1)} % ({state})")
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        parts.append("batterie : info indisponible")
    try:
        du = shutil.disk_usage("/")
        parts.append(f"disque libre {du.free // (1024**3)} Go")
    except OSError:
        parts.append("disque : info indisponible")
    return ", ".join(parts)
