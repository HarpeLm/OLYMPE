"""Outil : fermer un volet par son nom."""

TOOL = {
    "name": "close_shutters",
    "description": "Ferme complètement un volet Somfy par son nom.",
    "inputSchema": {
        "type": "object",
        "properties": {"name": {"type": "string", "description": "Nom du volet"}},
        "required": ["name"]
    }
}

def run(args):
    from integrations.tahoma import close_shutter
    try:
        r = close_shutter(args.get("name", ""))
    except ValueError as e:
        r = {"success": False, "message": str(e)}
    return r["message"]
