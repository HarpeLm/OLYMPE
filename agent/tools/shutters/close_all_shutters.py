"""Outil : fermer tous les volets."""

TOOL = {
    "name": "close_all_shutters",
    "description": "Ferme complètement tous les volets Somfy.",
    "inputSchema": {"type": "object", "properties": {}, "required": []}
}

def run(args):
    from integrations.tahoma import list_shutters as ls, close_shutter
    for s in ls():
        close_shutter(s["name"])
    return "Tous les volets sont en cours de fermeture."
