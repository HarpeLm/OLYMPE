"""Outil : ouvrir un volet par son nom."""

TOOL = {
    "name": "open_shutters",
    "description": "Ouvre complètement un volet Somfy par son nom.",
    "inputSchema": {
        "type": "object",
        "properties": {"name": {"type": "string", "description": "Nom du volet"}},
        "required": ["name"]
    }
}

def run(args):
    from integrations.tahoma import open_shutter
    try:
        r = open_shutter(args.get("name", ""))
    except ValueError as e:
        r = {"success": False, "message": str(e)}
    return r["message"]
