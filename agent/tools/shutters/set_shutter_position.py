"""Outil : position partielle d'un volet."""

TOOL = {
    "name": "set_shutter_position",
    "description": "Positionne un volet à un pourcentage d'ouverture (0 = fermé, 100 = ouvert).",
    "inputSchema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Nom du volet"},
            "percent": {"type": "integer", "description": "Pourcentage d'ouverture"}
        },
        "required": ["name", "percent"]
    }
}

def run(args):
    from integrations.tahoma import set_shutter_position
    try:
        r = set_shutter_position(args.get("name", ""), int(args.get("percent", 50)))
    except ValueError as e:
        r = {"success": False, "message": str(e)}
    return r["message"]
