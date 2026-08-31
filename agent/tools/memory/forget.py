"""Outil : oublier un fait mémorisé."""

TOOL = {
    "name": "forget",
    "description": "Supprime un fait de la mémoire par son identifiant.",
    "inputSchema": {
        "type": "object",
        "properties": {"fact_id": {"type": "integer", "description": "Identifiant du fait"}},
        "required": ["fact_id"]
    }
}

def run(args):
    from agent.memory import Memory
    m = Memory()
    m.forget(args.get("fact_id", 0))
    m.close()
    return "C'est oublie."
