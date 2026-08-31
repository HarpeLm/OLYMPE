"""Outil : ouvrir tous les volets."""

TOOL = {
    "name": "open_all_shutters",
    "description": "Ouvre complètement tous les volets Somfy.",
    "inputSchema": {"type": "object", "properties": {}, "required": []}
}

def run(args):
    from integrations.tahoma import list_shutters as ls, open_shutter
    for s in ls():
        open_shutter(s["name"])
    return "Tous les volets sont en cours d'ouverture."
