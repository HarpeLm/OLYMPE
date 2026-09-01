"""Package pipeline — ré-export paresseux (compatibilité imports)."""

_EXPORTS = {
    "VoicePipeline": "_pipeline",
    "main": "__main__",
}

def __getattr__(name):
    if name in _EXPORTS:
        import importlib
        m = importlib.import_module(f"voice.pipeline.{_EXPORTS[name]}")
        return getattr(m, name)
    raise AttributeError(name)
