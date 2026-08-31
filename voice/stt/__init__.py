"""Package STT — re-export paresseux (compatibilite imports)."""

_EXPORTS = {
    "STTEngine": "engine",
    "AudioRecorder": "_recorder",
    "get_role_entry": "_helpers",
}

def __getattr__(name):
    if name in _EXPORTS:
        import importlib
        m = importlib.import_module(f"voice.stt.{_EXPORTS[name]}")
        return getattr(m, name)
    raise AttributeError(name)
