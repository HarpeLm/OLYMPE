"""Outil : mémoriser un fait durable."""

TOOL = {
    "name": "remember",
    "description": "Mémorise un fait durable (mémoire persistante SQLite).",
    "inputSchema": {
        "type": "object",
        "properties": {
            "content": {"type": "string", "description": "Fait à mémoriser"},
            "category": {"type": "string", "description": "Catégorie (défaut : general)"}
        },
        "required": ["content"]
    }
}

def run(args):
    from agent.memory import Memory
    m = Memory()
    fid = m.remember(args.get("content", ""), args.get("category", "general"))
    m.close()
    return f"C'est note, je m'en souviendrai (id={fid})."
