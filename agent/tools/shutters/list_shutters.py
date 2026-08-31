"""Outil : lister les volets Somfy et leur état."""

TOOL = {
    "name": "list_shutters",
    "description": "Liste les volets Somfy (TaHoma) et leur position.",
    "inputSchema": {"type": "object", "properties": {}, "required": []}
}

def run(args):
    from integrations.tahoma import list_shutters as ls
    lignes = []
    for s in ls():
        c = s["closure"]
        pos = "ferme" if c == 100 else ("ouvert" if c == 0 else str(100 - c) + "% ouvert")
        lignes.append(f"{s['name']} ({pos})")
    return "Volets : " + ", ".join(lignes)
