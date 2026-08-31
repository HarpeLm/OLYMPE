"""Outil : rechercher dans les souvenirs."""

TOOL = {
    "name": "recall",
    "description": "Recherche dans les faits mémorisés.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Texte à rechercher"},
            "category": {"type": "string", "description": "Filtrer par catégorie"}
        },
        "required": []
    }
}

def run(args):
    from agent.memory import Memory
    m = Memory()
    results = m.recall(query=args.get("query"), category=args.get("category"), limit=5)
    m.close()
    if not results:
        return "Je n'ai aucun souvenir correspondant."
    return "Souvenirs : " + " ; ".join(
        f"{r['content']} [{r['category']}]" for r in results)
