"""Package TTS — re-export paresseux (compatibilite imports)."""

_EXPORTS = {
    "TTSEngine": "engine",
    "save_wav": "_helpers",
    "get_role_entry": "_helpers",
    "get_model_id": "_helpers",
}

def __getattr__(name):
    if name in _EXPORTS:
        import importlib
        m = importlib.import_module(f"voice.tts.{_EXPORTS[name]}")
        return getattr(m, name)
    raise AttributeError(name)
